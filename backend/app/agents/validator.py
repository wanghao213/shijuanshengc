"""Validator Agent - 验证试卷质量."""

import asyncio
from typing import Any

import structlog

from app.agents.base import BaseAgent

logger = structlog.get_logger()

# 重复检测阈值：内容相似度超过此比例视为重复
_DUPLICATE_THRESHOLD = 0.95


class ValidatorAgent(BaseAgent):
    """验证试卷质量.

    对所有题目：
    1. 答案验证（仅针对AI新生成的题）
    2. 难度校准
    3. 整卷质量检查
    4. 跨题验证（重复检测、难度平衡）
    """

    async def run(self, context: dict) -> dict:
        """执行验证."""
        all_questions = context.get("all_questions", [])
        template = context.get("template", {})
        plan = context.get("plan", {})
        validation_service = context.get("validation_service")

        # 并行验证各题目
        validation_tasks = [
            self._validate_question(
                question=q,
                template=template,
                validation_service=validation_service,
            )
            for q in all_questions
        ]
        validation_results = await asyncio.gather(*validation_tasks)

        issues: list[dict] = []
        for result in validation_results:
            if result.get("has_issue"):
                issues.append(result)

        # 整卷质量检查
        paper_quality = await validation_service.check_paper_quality(
            questions=all_questions,
            expected_difficulty=plan.get("estimated_difficulty", 3.0),
        )

        # 跨题验证
        cross_issues = self._validate_cross_questions(all_questions, plan)

        return {
            "validation_results": validation_results,
            "issues": issues,
            "cross_issues": cross_issues,
            "paper_quality": paper_quality,
            "is_valid": (
                len(issues) == 0
                and len(cross_issues) == 0
                and paper_quality.get("is_valid", False)
            ),
        }

    async def _validate_question(
        self,
        question: dict,
        template: dict,
        validation_service: Any,
    ) -> dict:
        """验证单个题目."""
        qid = question.get("id", "unknown")
        is_ai_generated = question.get("is_ai_generated", False)

        result: dict[str, Any] = {
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
                    "detail": (
                        f"LLM答案: {answer_result.get('llm_answer')}, "
                        f"预期答案: {answer_result.get('expected_answer')}"
                    ),
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

    def _validate_cross_questions(
        self, questions: list[dict], plan: dict
    ) -> list[dict]:
        """跨题验证：重复检测 + 难度分布平衡."""
        cross_issues: list[dict] = []

        # 重复检测
        seen: dict[str, int] = {}
        for i, q in enumerate(questions):
            key = self._normalize_for_dedup(q)
            if key in seen:
                cross_issues.append({
                    "type": "duplicate",
                    "detail": f"题目 {i} 与题目 {seen[key]} 内容高度相似",
                    "question_indices": [seen[key], i],
                })
            else:
                seen[key] = i

        # 难度分布平衡检查
        if questions:
            difficulties = [q.get("difficulty", 3.0) for q in questions]
            avg = sum(difficulties) / len(difficulties)
            expected = plan.get("estimated_difficulty", 3.0)
            if abs(avg - expected) > 0.5:
                cross_issues.append({
                    "type": "difficulty_imbalance",
                    "detail": (
                        f"整卷平均难度 {avg:.2f}，"
                        f"预期 {expected:.2f}，偏差过大"
                    ),
                })

        return cross_issues

    def _normalize_for_dedup(self, question: dict) -> str:
        """提取题目内容用于去重比较（去除空白和标点差异）."""
        content = question.get("content_latex", "")
        # 去除空白字符，用于简单去重
        return "".join(content.split())
