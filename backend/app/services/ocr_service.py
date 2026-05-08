"""OCR 服务 - 试卷/习题文档识别与结构化提取.

支持两种模式：
1. MinerU OCR 模式：调用 PDF-Extract-Kit 进行版面分析和公式识别
2. 手动输入模式：用户粘贴文本，由 LLM 结构化提取
"""

import asyncio
import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import ValidationError
from app.core.llm_gateway import structured_chat
from app.core.prompts.ocr_cleanup import build_ocr_cleanup_prompt, build_ocr_extract_prompt
from app.models.knowledge import KnowledgeNode
from app.models.question import Question, QuestionKnowledge, QuestionTag, QuestionVersion

logger = structlog.get_logger()


@dataclass
class ExtractedQuestion:
    """OCR 提取的单道题目."""

    number: str
    content_latex: str
    question_type: str = "short_answer"
    options: list[dict] | None = None
    answer_latex: str | None = None
    knowledge_points: list[str] = field(default_factory=list)
    estimated_difficulty: float = 3.0


@dataclass
class OCRResult:
    """OCR 处理结果."""

    status: str  # 'success' / 'partial' / 'failed'
    raw_text: str = ""
    cleaned_text: str = ""
    questions: list[ExtractedQuestion] = field(default_factory=list)
    corrections: list[dict] = field(default_factory=list)
    confidence: float = 0.0
    notes: str = ""
    error: str | None = None
    saved_question_ids: list[int] = field(default_factory=list)


class OcrService:
    """OCR 识别服务.

    处理流程：
    1. 文件识别（MinerU 或手动输入）
    2. LLM 清洗修复 OCR 错误
    3. 结构化提取题目
    4. 自动标注知识点和难度
    5. 入库（review_status='pending'）
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def process_document(
        self,
        file_path: str | None = None,
        raw_text: str | None = None,
        metadata: dict | None = None,
    ) -> OCRResult:
        """处理文档，提取题目.

        Args:
            file_path: 文件路径（PDF/图片），与 raw_text 二选一
            raw_text: 用户手动输入的文本
            metadata: 附加元数据（source, exam_type, region 等）

        Returns:
            OCRResult 包含提取的题目列表
        """
        metadata = metadata or {}

        # 第一步：获取原始文本
        if raw_text:
            # 手动输入模式
            logger.info("ocr_manual_input", text_length=len(raw_text))
            ocr_text = raw_text
        elif file_path:
            # MinerU OCR 模式
            ocr_text = await self._run_mineru(file_path)
            if ocr_text is None:
                return OCRResult(
                    status="failed",
                    error="MinerU OCR 引擎不可用，请使用手动输入模式",
                )
        else:
            raise ValidationError("必须提供 file_path 或 raw_text")

        # 第二步：LLM 清洗
        cleanup_result = await self._llm_cleanup(ocr_text)

        # 第三步：结构化提取
        extract_result = await self._structured_extract(
            cleanup_result.get("cleaned_text", ocr_text)
        )

        # 组装结果
        questions = []
        for q_data in extract_result.get("questions", []):
            questions.append(
                ExtractedQuestion(
                    number=q_data.get("number", ""),
                    content_latex=q_data.get("content_latex", ""),
                    question_type=q_data.get("question_type", "short_answer"),
                    options=q_data.get("options"),
                    answer_latex=q_data.get("answer_latex"),
                    knowledge_points=q_data.get("knowledge_points", []),
                    estimated_difficulty=q_data.get("estimated_difficulty", 3.0),
                )
            )

        result = OCRResult(
            status="success" if questions else "partial",
            raw_text=ocr_text,
            cleaned_text=cleanup_result.get("cleaned_text", ""),
            questions=questions,
            corrections=cleanup_result.get("corrections", []),
            confidence=cleanup_result.get("confidence", 0.0),
            notes=cleanup_result.get("notes", ""),
        )

        return result

    async def process_and_save(
        self,
        file_path: str | None = None,
        raw_text: str | None = None,
        metadata: dict | None = None,
        auto_tag: bool = True,
    ) -> OCRResult:
        """处理文档并保存到数据库.

        所有 OCR 提取的题目 review_status='pending'。
        """
        result = await self.process_document(file_path, raw_text, metadata)
        if result.status == "failed":
            return result

        metadata = metadata or {}
        saved_ids = []

        for eq in result.questions:
            # 构建选项 JSON
            options_json = None
            if eq.options:
                options_json = {
                    opt.get("label", ""): opt.get("content_latex", "")
                    for opt in eq.options
                }

            # 创建题目
            question = Question(
                content_latex=eq.content_latex,
                content_plain=self._latex_to_plain(eq.content_latex),
                question_type=eq.question_type,
                difficulty=eq.estimated_difficulty,
                answer_latex=eq.answer_latex,
                options=options_json,
                source=metadata.get("source", "OCR导入"),
                source_year=metadata.get("source_year"),
                region=metadata.get("region"),
                exam_type=metadata.get("exam_type"),
                is_ai_generated=False,
                review_status="pending",
            )
            self.session.add(question)
            await self.session.flush()

            # 创建初始版本
            version = QuestionVersion(
                question_id=question.id,
                version_number=1,
                content_latex=eq.content_latex,
                answer_latex=eq.answer_latex,
                change_reason="OCR 导入",
            )
            self.session.add(version)

            # 自动标注知识点和难度
            if auto_tag:
                await self._auto_annotate(question, eq)

            saved_ids.append(question.id)

        await self.session.flush()

        result.saved_question_ids = saved_ids
        logger.info(
            "ocr_saved",
            count=len(saved_ids),
            question_ids=saved_ids,
        )

        return result

    async def _run_mineru(self, file_path: str) -> str | None:
        """调用 MinerU 进行 OCR 识别.

        如果 MinerU 不可用，返回 None。
        """
        if not settings.mineru_enabled:
            logger.info("mineru_disabled")
            return None

        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise ValidationError(f"文件不存在: {file_path}")

        try:
            # 检查 MinerU 是否安装（非阻塞）
            proc = await asyncio.create_subprocess_exec(
                "magic-pdf", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=10)
            if proc.returncode != 0:
                logger.warning("mineru_not_installed")
                return None
        except (FileNotFoundError, asyncio.TimeoutError, OSError):
            logger.warning("mineru_not_found")
            return None

        # 调用 MinerU 处理文件
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(output_dir, exist_ok=True)

            try:
                proc = await asyncio.create_subprocess_exec(
                    "magic-pdf",
                    "-p", file_path,
                    "-o", output_dir,
                    "-m", "auto",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=300
                )

                if proc.returncode != 0:
                    logger.error(
                        "mineru_failed",
                        stderr=stderr.decode(errors="replace")[:500],
                    )
                    return None

                # 收集 MinerU 输出的文本
                return self._collect_mineru_output(output_dir)

            except asyncio.TimeoutError:
                logger.error("mineru_timeout")
                return None
            except Exception as e:
                logger.error("mineru_error", error=str(e))
                return None

    def _collect_mineru_output(self, output_dir: str) -> str:
        """收集 MinerU 输出目录中的文本内容."""
        texts = []
        output_path = Path(output_dir)

        # MinerU 输出 markdown 文件
        for md_file in output_path.rglob("*.md"):
            try:
                texts.append(md_file.read_text(encoding="utf-8"))
            except Exception:
                continue

        # 也尝试读取纯文本输出
        for txt_file in output_path.rglob("*.txt"):
            try:
                texts.append(txt_file.read_text(encoding="utf-8"))
            except Exception:
                continue

        return "\n\n".join(texts) if texts else ""

    async def _llm_cleanup(self, raw_text: str) -> dict:
        """使用 LLM 清洗 OCR 结果."""
        prompt = build_ocr_cleanup_prompt(raw_text)
        messages = [{"role": "user", "content": prompt}]

        try:
            response = await structured_chat(
                messages=messages,
                session=self.session,
                temperature=0.2,
                max_tokens=8192,
            )
            result = json.loads(response.content)
            return result
        except (json.JSONDecodeError, Exception) as e:
            logger.error("ocr_cleanup_failed", error=str(e))
            return {
                "cleaned_text": raw_text,
                "questions": [],
                "corrections": [],
                "confidence": 0.3,
                "notes": f"LLM 清洗失败: {str(e)}",
            }

    async def _structured_extract(self, cleaned_text: str) -> dict:
        """从清洗后的文本中结构化提取题目."""
        prompt = build_ocr_extract_prompt(cleaned_text)
        messages = [{"role": "user", "content": prompt}]

        try:
            response = await structured_chat(
                messages=messages,
                session=self.session,
                temperature=0.2,
                max_tokens=8192,
            )
            result = json.loads(response.content)
            return result
        except (json.JSONDecodeError, Exception) as e:
            logger.error("ocr_extract_failed", error=str(e))
            return {"questions": []}

    async def _auto_annotate(self, question: Question, extracted: ExtractedQuestion) -> None:
        """对 OCR 提取的题目进行自动标注.

        - 关联知识点
        - 评估难度
        - 添加标签
        """
        # 获取所有知识点供匹配
        kp_result = await self.session.execute(
            select(KnowledgeNode).where(KnowledgeNode.level == "knowledge_point")
        )
        all_kps = {row.name: row for row in kp_result.scalars().all()}

        # 用 LLM 识别知识点和难度（如果提取时没有提供）
        if not extracted.knowledge_points or extracted.estimated_difficulty == 3.0:
            annotation = await self._llm_annotate(question, list(all_kps.keys()))
            if not extracted.knowledge_points:
                extracted.knowledge_points = annotation.get("knowledge_points", [])
            if extracted.estimated_difficulty == 3.0:
                extracted.estimated_difficulty = annotation.get("difficulty", 3.0)

        # 更新难度
        if 1.0 <= extracted.estimated_difficulty <= 5.0:
            question.difficulty = extracted.estimated_difficulty

        # 关联知识点
        for kp_name in extracted.knowledge_points:
            kp_node = all_kps.get(kp_name)
            if not kp_node:
                # 模糊匹配
                for name, node in all_kps.items():
                    if kp_name in name or name in kp_name:
                        kp_node = node
                        break

            if kp_node:
                assoc = QuestionKnowledge(
                    question_id=question.id,
                    knowledge_id=kp_node.id,
                    relevance_score=0.7,
                    is_primary=False,
                )
                self.session.add(assoc)

        # 添加 OCR 来源标签
        self.session.add(
            QuestionTag(
                question_id=question.id,
                tag_type="来源",
                tag_value="OCR导入",
            )
        )

    async def _llm_annotate(self, question: Question, kp_names: list[str]) -> dict:
        """使用 LLM 识别知识点和评估难度."""
        prompt = f"""你是一位数学教育专家，请分析以下数学题，提取考查的知识点并评估难度。

## 题目内容
{question.content_latex}

## 题型
{question.question_type}

## 可选知识点列表（从中选择）
{', '.join(kp_names[:100])}

## 请输出 JSON 格式：
{{
  "knowledge_points": ["知识点1", "知识点2"],
  "difficulty": 3.5
}}"""

        messages = [{"role": "user", "content": prompt}]
        try:
            response = await structured_chat(
                messages=messages,
                session=self.session,
                temperature=0.3,
            )
            return json.loads(response.content)
        except Exception as e:
            logger.error("ocr_annotate_failed", error=str(e))
            return {"knowledge_points": [], "difficulty": 3.0}

    @staticmethod
    def _latex_to_plain(latex: str) -> str:
        """将 LaTeX 转换为纯文本（简单去除命令）."""
        import re

        text = latex
        # 去除常见 LaTeX 命令
        text = re.sub(r"\\(?:frac|sqrt|text|textbf|textit)\{([^}]*)\}", r"\1", text)
        text = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", text)
        text = re.sub(r"\\[a-zA-Z]+", "", text)
        text = re.sub(r"[{}$\\]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text
