"""Generator Agent - 生成新题目."""


import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.core.latex_validator import validate_latex
from app.core.prompts.question_gen import build_question_gen_prompt
from app.models.question import Question, QuestionVersion

logger = structlog.get_logger()


class GeneratorAgent(BaseAgent):
    """生成新题目.

    对每个 gap：
    1. 用 hybrid_search 检索同知识点的真题作为风格参考
    2. 构造生成 Prompt
    3. 调用 LLM 生成新题
    4. 解析返回的 JSON
    5. 调用 LaTeX 验证器检查格式
    6. 将通过验证的题入库（is_ai_generated=True, review_status='pending'）
    """

    async def run(self, context: dict) -> dict:
        """执行题目生成."""
        sections = context.get("sections", [])
        retrieval_service = context.get("retrieval_service")
        template = context.get("template", {})
        custom_params = context.get("custom_params", {})
        session: AsyncSession | None = context.get("session")

        generated_questions = []

        for section in sections:
            for gap in section.get("gaps", []):
                questions = await self._generate_for_gap(
                    gap=gap,
                    section_name=section.get("section_name", ""),
                    template=template,
                    retrieval_service=retrieval_service,
                    allow_ai=custom_params.get("allow_ai_generation", True),
                )
                generated_questions.extend(questions)

        # 将生成的题目存入数据库
        if session and generated_questions:
            persisted = await self._persist_questions(session, generated_questions, template)
            return {"generated_questions": persisted}

        return {"generated_questions": generated_questions}

    async def _generate_for_gap(
        self,
        gap: dict,
        section_name: str,
        template: dict,
        retrieval_service,
        allow_ai: bool,
    ) -> list[dict]:
        """为单个缺口生成题目."""
        if not allow_ai:
            logger.warning("ai_generation_disabled", gap=gap)
            return []

        question_type = gap.get("type", "short_answer")
        difficulty_range = gap.get("difficulty_range", [1.0, 5.0])
        target_difficulty = sum(difficulty_range) / 2
        count = gap.get("count", 1)
        knowledge_points = gap.get("knowledge_points", ["数学综合"])

        # 检索参考题
        reference_examples = []
        for kp in knowledge_points[:3]:
            examples = await retrieval_service.hybrid_search(
                query_text=kp,
                filters={"question_type": question_type},
                top_k=3,
            )
            reference_examples.extend(examples)

        # 构建 Prompt
        prompt = build_question_gen_prompt(
            question_type=question_type,
            difficulty=target_difficulty,
            knowledge_points=knowledge_points,
            stage=template.get("stage", "初中"),
            grade=template.get("grade", "初三"),
            reference_examples=reference_examples[:5],
            count=count,
        )

        # 调用 LLM
        response = await self.call_llm_json(
            system_prompt="你是一位资深数学教育命题专家。",
            user_message=prompt,
        )

        if "error" in response:
            return []

        questions = response.get("questions", [])

        # 验证 LaTeX
        validated = []
        for q in questions:
            content = q.get("content_latex", "")
            result = validate_latex(content)
            if result.is_valid:
                q["content_latex"] = result.cleaned_latex
                q["is_ai_generated"] = True
                q["review_status"] = "pending"
                q["difficulty"] = q.get("difficulty_self_assessment", target_difficulty)
                q["knowledge_points_str"] = knowledge_points
                validated.append(q)
            else:
                logger.warning(
                    "latex_validation_failed",
                    errors=result.errors,
                    content=content[:100],
                )

        return validated

    async def _persist_questions(
        self,
        session: AsyncSession,
        questions: list[dict],
        template: dict,
    ) -> list[dict]:
        """将生成的题目存入数据库."""
        persisted = []

        for q_data in questions:
            try:
                question = Question(
                    content_latex=q_data.get("content_latex", ""),
                    content_plain=q_data.get("content_latex", ""),  # 简化：用 LaTeX 作为纯文本
                    question_type=q_data.get("question_type", "short_answer"),
                    difficulty=q_data.get("difficulty", 3.0),
                    answer_latex=q_data.get("answer_latex"),
                    solution_steps=q_data.get("solution_steps"),
                    options=q_data.get("options"),
                    source="AI生成",
                    is_ai_generated=True,
                    review_status="pending",
                )
                session.add(question)
                await session.flush()

                # 创建版本记录
                version = QuestionVersion(
                    question_id=question.id,
                    version_number=1,
                    content_latex=q_data.get("content_latex", ""),
                    answer_latex=q_data.get("answer_latex"),
                    solution_steps=q_data.get("solution_steps"),
                    change_reason="AI 自动生成",
                )
                session.add(version)

                # 返回时包含数据库 ID
                q_data["id"] = question.id
                q_data["db_persisted"] = True
                persisted.append(q_data)

                logger.info(
                    "question_persisted",
                    question_id=question.id,
                    question_type=q_data.get("question_type"),
                )

            except Exception as e:
                logger.error("question_persist_failed", error=str(e), q_data=str(q_data)[:200])
                # 即使入库失败，也保留生成的数据
                persisted.append(q_data)

        await session.flush()
        return persisted
