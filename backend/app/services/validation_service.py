"""验证服务 - 试卷质量校验."""

import json

import structlog

from app.core.llm_gateway import structured_chat
from app.core.prompts.difficulty import build_difficulty_prompt
from app.core.prompts.question_check import build_answer_check_prompt

logger = structlog.get_logger()


class ValidationService:
    """试卷质量校验服务."""

    async def verify_answer(
        self,
        content_latex: str,
        options: list[dict] | None,
        question_type: str,
        stage: str,
        grade: str,
        expected_answer: str,
    ) -> dict:
        """验证答案正确性."""
        prompt = build_answer_check_prompt(
            content_latex=content_latex,
            options=options,
            question_type=question_type,
            stage=stage,
            grade=grade,
        )

        response = await structured_chat(
            messages=[
                {"role": "system", "content": "你是一位数学教育专家，请独立解答数学题。"},
                {"role": "user", "content": prompt},
            ]
        )

        try:
            result = json.loads(response.content)
        except json.JSONDecodeError:
            return {
                "verified": False,
                "confidence": 0.0,
                "error": "LLM 返回格式错误",
            }

        llm_answer = result.get("final_answer", "")
        is_correct = llm_answer.strip().upper() == expected_answer.strip().upper()

        return {
            "verified": True,
            "is_correct": is_correct,
            "llm_answer": llm_answer,
            "expected_answer": expected_answer,
            "confidence": result.get("confidence", 0.0),
            "solution_steps": result.get("solution_steps", []),
            "reasoning": result.get("reasoning", ""),
        }

    async def assess_difficulty(
        self,
        content_latex: str,
        question_type: str,
        stage: str,
        grade: str,
    ) -> dict:
        """评估题目难度."""
        prompt = build_difficulty_prompt(
            content_latex=content_latex,
            question_type=question_type,
            stage=stage,
            grade=grade,
        )

        response = await structured_chat(
            messages=[
                {"role": "system", "content": "你是一位数学教育评估专家。"},
                {"role": "user", "content": prompt},
            ]
        )

        try:
            result = json.loads(response.content)
        except json.JSONDecodeError:
            return {"error": "LLM 返回格式错误"}

        return result

    async def check_paper_quality(
        self,
        questions: list[dict],
        expected_difficulty: float,
        min_knowledge_coverage: float = 0.6,
    ) -> dict:
        """整卷质量检查."""
        issues = []
        warnings = []

        # 检查难度分布
        difficulties = [q.get("difficulty", 0) for q in questions]
        avg_difficulty = 0.0
        if difficulties:
            avg_difficulty = sum(difficulties) / len(difficulties)
            if abs(avg_difficulty - expected_difficulty) > 0.5:
                warnings.append(
                    f"平均难度 {avg_difficulty:.2f} 与目标 {expected_difficulty} 偏差较大"
                )

        # 检查知识点覆盖
        all_kp = set()
        for q in questions:
            for kp in q.get("knowledge_points", []):
                all_kp.add(kp)
        # 这里需要从模板获取要求的知识点，简化处理

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "stats": {
                "total_questions": len(questions),
                "avg_difficulty": round(avg_difficulty, 2),
                "knowledge_points_covered": len(all_kp),
            },
        }
