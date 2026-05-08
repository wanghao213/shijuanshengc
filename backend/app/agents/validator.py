"""Validator Agent - 验证试卷质量."""

import structlog

from app.agents.base import BaseAgent

logger = structlog.get_logger()


class ValidatorAgent(BaseAgent):
    """验证试卷质量.

    对所有题目：
    1. 答案验证（仅针对AI新生成的题）
    2. 难度校准
    3. 整卷质量检查
    """

    async def run(self, context: dict) -> dict:
        """执行验证."""
        all_questions = context.get("all_questions", [])
        template = context.get("template", {})
        plan = context.get("plan", {})
        validation_service = context.get("validation_service")

        validation_results = []
        issues = []

        for q in all_questions:
            result = await self._validate_question(
                question=q,
                template=template,
                validation_service=validation_service,
            )
            validation_results.append(result)

            if result.get("has_issue"):
                issues.append(result)

        # 整卷质量检查
        paper_quality = await validation_service.check_paper_quality(
            questions=all_questions,
            expected_difficulty=plan.get("estimated_difficulty", 3.0),
        )

        return {
            "validation_results": validation_results,
            "issues": issues,
            "paper_quality": paper_quality,
            "is_valid": len(issues) == 0 and paper_quality.get("is_valid", False),
        }

    async def _validate_question(
        self,
        question: dict,
        template: dict,
        validation_service,
    ) -> dict:
        """验证单个题目."""
        qid = question.get("id", "unknown")
        is_ai_generated = question.get("is_ai_generated", False)

        result = {
            "question_id": qid,
            "is_ai_generated": is_ai_generated,
            "has_issue": False,
            "issues": [],
            "warnings": [],
        }

        # AI 生成的题目需要验证答案
        if is_ai_generated and question.get("correct_answer"):
            answer_result = await validation_service.verify_answer(
                content_latex=question.get("content_latex", ""),
                options=question.get("options"),
                question_type=question.get("question_type", ""),
                stage=template.get("stage", "初中"),
                grade=template.get("grade", "初三"),
                expected_answer=question["correct_answer"],
            )

            if answer_result.get("verified") and not answer_result.get("is_correct"):
                result["has_issue"] = True
                result["issues"].append({
                    "type": "answer_mismatch",
                    "detail": f"LLM答案: {answer_result.get('llm_answer')}, "
                              f"预期答案: {answer_result.get('expected_answer')}",
                })

        # 难度校准
        difficulty = question.get("difficulty", 3.0)
        if is_ai_generated:
            difficulty_result = await validation_service.assess_difficulty(
                content_latex=question.get("content_latex", ""),
                question_type=question.get("question_type", ""),
                stage=template.get("stage", "初中"),
                grade=template.get("grade", "初三"),
            )
            llm_difficulty = difficulty_result.get("weighted_score", 0)
            if llm_difficulty and abs(llm_difficulty - difficulty) > 0.5:
                result["warnings"].append({
                    "type": "difficulty_mismatch",
                    "detail": f"标注难度: {difficulty}, LLM评估: {llm_difficulty:.2f}",
                })

        return result
