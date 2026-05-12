"""Assembler Agent - 组装试卷."""

from datetime import datetime
from typing import Any

import structlog

from app.agents.base import BaseAgent
from app.models.paper import Paper, PaperQuestion

logger = structlog.get_logger()


class AssemblerAgent(BaseAgent):
    """组装试卷.

    1. 按 section 组装试卷
    2. 分配题号和分值
    3. 生成试卷标题
    4. 计算整卷统计
    5. 创建 Paper 记录和 PaperQuestion 关联记录
    """

    async def run(self, context: dict) -> dict:
        """组装试卷."""
        sections = context.get("sections", [])
        generated_questions = context.get("generated_questions", [])
        template = context.get("template", {})
        custom_params = context.get("custom_params", {})
        session = context.get("session")

        # 合并所有题目
        all_questions = self._merge_questions(sections, generated_questions)

        # 分值校验
        self._validate_scores(all_questions, template)

        # 生成标题
        title = custom_params.get("title_override") or self._generate_title(template)

        # 计算统计
        stats = self._calculate_stats(all_questions, template)

        # 创建试卷记录
        paper = Paper(
            title=title,
            template_id=template.get("id"),
            generation_params=custom_params,
            total_score=template.get("total_score", 0),
            difficulty_average=stats["avg_difficulty"],
            knowledge_coverage=stats["knowledge_coverage"],
            review_status="draft",
        )
        session.add(paper)
        await session.flush()

        # 创建题目关联记录
        position = 0
        for section_idx, section in enumerate(all_questions):
            for q_data in section.get("questions", []):
                pq = PaperQuestion(
                    paper_id=paper.id,
                    question_id=q_data.get("id"),
                    section_index=section_idx,
                    position=position,
                    assigned_score=q_data.get("score", 0),
                )
                session.add(pq)
                position += 1

        await session.flush()

        return {
            "paper_id": paper.id,
            "title": title,
            "total_questions": position,
            "stats": stats,
        }

    def _merge_questions(self, sections: list, generated: list) -> list:
        """合并题库题目和 AI 生成题目."""
        result: list[dict[str, Any]] = []
        gen_by_type: dict[str, list] = {}
        for q in generated:
            qtype = q.get("question_type", "unknown")
            gen_by_type.setdefault(qtype, []).append(q)

        for section in sections:
            section_questions = list(section.get("selected", []))
            # 填充缺口：使用索引消耗已使用的题目，避免修改迭代中的列表
            for gap in section.get("gaps", []):
                gap_type = gap.get("type", "")
                gap_count = gap.get("count", 0)
                available = gen_by_type.get(gap_type, [])
                consumed = 0
                for i, q in enumerate(available):
                    if consumed >= gap_count:
                        break
                    section_questions.append(q)
                    consumed += 1
                # 移除已消耗的题目
                gen_by_type[gap_type] = available[consumed:]

            result.append({
                "section_name": section.get("section_name", ""),
                "questions": section_questions,
            })

        return result

    def _validate_scores(self, sections: list, template: dict) -> None:
        """校验各 section 分值总和是否与模板匹配."""
        expected_total = template.get("total_score", 0)
        if not expected_total:
            return

        actual_total = 0
        for section in sections:
            for q in section.get("questions", []):
                actual_total += q.get("score", 0)

        if abs(actual_total - expected_total) > 0.01:
            logger.warning(
                "score_mismatch",
                expected=expected_total,
                actual=actual_total,
            )

    def _generate_title(self, template: dict) -> str:
        """生成试卷标题."""
        stage = template.get("stage", "")
        grade = template.get("grade", "")
        subject = template.get("subject", "数学")
        now = datetime.now()
        return f"{stage}{grade}{subject}试卷（{now.year}年{now.month}月）"

    def _calculate_stats(self, sections: list, template: dict) -> dict:
        """计算试卷统计."""
        all_questions: list[dict] = []
        for section in sections:
            all_questions.extend(section.get("questions", []))

        if not all_questions:
            return {
                "avg_difficulty": 0,
                "total_questions": 0,
                "knowledge_coverage": {},
            }

        difficulties = [q.get("difficulty", 3.0) for q in all_questions]
        avg_difficulty = sum(difficulties) / len(difficulties)

        # 知识点覆盖
        all_kp: set[str] = set()
        for q in all_questions:
            for kp in q.get("knowledge_points", []):
                if isinstance(kp, str):
                    all_kp.add(kp)
                elif isinstance(kp, dict):
                    all_kp.add(kp.get("name", ""))

        return {
            "avg_difficulty": round(avg_difficulty, 2),
            "total_questions": len(all_questions),
            "knowledge_coverage": {
                "covered": list(all_kp),
                "count": len(all_kp),
            },
        }
