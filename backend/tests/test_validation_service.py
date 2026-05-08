"""ValidationService 单元测试."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.validation_service import ValidationService


@pytest.mark.asyncio
@patch("app.services.validation_service.structured_chat")
async def test_verify_answer_correct(mock_structured_chat):
    """测试答案验证 - 正确答案."""
    mock_response = MagicMock()
    mock_response.content = '{"final_answer": "B", "confidence": 0.95, "solution_steps": ["步骤1", "步骤2"], "reasoning": "推理过程"}'
    mock_structured_chat.return_value = mock_response

    svc = ValidationService()
    result = await svc.verify_answer(
        content_latex="$x^2=4$",
        options=None,
        question_type="choice",
        stage="初中",
        grade="七年级",
        expected_answer="B",
    )

    assert result["verified"] is True
    assert result["is_correct"] is True
    assert result["llm_answer"] == "B"
    assert result["confidence"] == 0.95
    assert len(result["solution_steps"]) == 2


@pytest.mark.asyncio
@patch("app.services.validation_service.structured_chat")
async def test_verify_answer_incorrect(mock_structured_chat):
    """测试答案验证 - 错误答案."""
    mock_response = MagicMock()
    mock_response.content = '{"final_answer": "A", "confidence": 0.8, "solution_steps": [], "reasoning": ""}'
    mock_structured_chat.return_value = mock_response

    svc = ValidationService()
    result = await svc.verify_answer(
        content_latex="$x^2=4$",
        options=None,
        question_type="choice",
        stage="初中",
        grade="七年级",
        expected_answer="B",
    )

    assert result["verified"] is True
    assert result["is_correct"] is False
    assert result["llm_answer"] == "A"


@pytest.mark.asyncio
@patch("app.services.validation_service.structured_chat")
async def test_verify_answer_json_error(mock_structured_chat):
    """测试答案验证 - JSON 解析失败."""
    mock_response = MagicMock()
    mock_response.content = "这不是JSON"
    mock_structured_chat.return_value = mock_response

    svc = ValidationService()
    result = await svc.verify_answer(
        content_latex="$x^2=4$",
        options=None,
        question_type="choice",
        stage="初中",
        grade="七年级",
        expected_answer="B",
    )

    assert result["verified"] is False
    assert result["confidence"] == 0.0
    assert "error" in result


@pytest.mark.asyncio
@patch("app.services.validation_service.structured_chat")
async def test_assess_difficulty_success(mock_structured_chat):
    """测试难度评估成功."""
    mock_response = MagicMock()
    mock_response.content = '{"dimensions": {"knowledge": {"score": 3}, "calculation": {"score": 2}, "reasoning": {"score": 4}, "technique": {"score": 2}}, "weighted_score": 3.05, "difficulty_level": "中等偏难"}'
    mock_structured_chat.return_value = mock_response

    svc = ValidationService()
    result = await svc.assess_difficulty(
        content_latex="$x^2+2x+1=0$",
        question_type="short_answer",
        stage="初中",
        grade="七年级",
    )

    assert "dimensions" in result
    assert result["weighted_score"] == 3.05
    assert result["difficulty_level"] == "中等偏难"


@pytest.mark.asyncio
@patch("app.services.validation_service.structured_chat")
async def test_assess_difficulty_json_error(mock_structured_chat):
    """测试难度评估 JSON 解析失败."""
    mock_response = MagicMock()
    mock_response.content = "invalid json"
    mock_structured_chat.return_value = mock_response

    svc = ValidationService()
    result = await svc.assess_difficulty(
        content_latex="$x^2$",
        question_type="choice",
        stage="初中",
        grade="七年级",
    )

    assert "error" in result


@pytest.mark.asyncio
async def test_check_paper_quality_valid():
    """测试整卷质量检查 - 合格."""
    svc = ValidationService()
    questions = [
        {"difficulty": 2.0, "knowledge_points": ["代数", "方程"]},
        {"difficulty": 3.0, "knowledge_points": ["几何", "三角形"]},
        {"difficulty": 2.5, "knowledge_points": ["代数", "函数"]},
    ]

    result = await svc.check_paper_quality(
        questions=questions,
        expected_difficulty=2.5,
    )

    assert result["is_valid"] is True
    assert result["issues"] == []
    assert result["stats"]["total_questions"] == 3
    assert result["stats"]["knowledge_points_covered"] == 5


@pytest.mark.asyncio
async def test_check_paper_quality_difficulty_mismatch():
    """测试整卷质量检查 - 难度偏差大."""
    svc = ValidationService()
    questions = [
        {"difficulty": 1.0, "knowledge_points": ["代数"]},
        {"difficulty": 1.5, "knowledge_points": ["几何"]},
    ]

    result = await svc.check_paper_quality(
        questions=questions,
        expected_difficulty=4.0,
    )

    assert len(result["warnings"]) > 0
    assert "偏差" in result["warnings"][0]


@pytest.mark.asyncio
async def test_check_paper_quality_empty():
    """测试整卷质量检查 - 空试卷."""
    svc = ValidationService()

    result = await svc.check_paper_quality(
        questions=[],
        expected_difficulty=3.0,
    )

    assert result["is_valid"] is True
    assert result["stats"]["total_questions"] == 0
    assert result["stats"]["avg_difficulty"] == 0


@pytest.mark.asyncio
@patch("app.services.validation_service.structured_chat")
async def test_verify_answer_with_options(mock_structured_chat):
    """测试带选项的答案验证."""
    mock_response = MagicMock()
    mock_response.content = '{"final_answer": "C", "confidence": 0.9, "solution_steps": ["分析选项A", "分析选项B", "选C"], "reasoning": "排除法"}'
    mock_structured_chat.return_value = mock_response

    svc = ValidationService()
    result = await svc.verify_answer(
        content_latex="下列哪个是质数？",
        options=[
            {"label": "A", "content_latex": "4"},
            {"label": "B", "content_latex": "6"},
            {"label": "C", "content_latex": "7"},
        ],
        question_type="choice",
        stage="初中",
        grade="七年级",
        expected_answer="C",
    )

    assert result["is_correct"] is True
    assert result["llm_answer"] == "C"


@pytest.mark.asyncio
@patch("app.services.validation_service.structured_chat")
async def test_verify_answer_case_insensitive(mock_structured_chat):
    """测试答案大小写不敏感."""
    mock_response = MagicMock()
    mock_response.content = '{"final_answer": "b", "confidence": 0.9, "solution_steps": [], "reasoning": ""}'
    mock_structured_chat.return_value = mock_response

    svc = ValidationService()
    result = await svc.verify_answer(
        content_latex="test",
        options=None,
        question_type="choice",
        stage="初中",
        grade="七年级",
        expected_answer="B",
    )

    assert result["is_correct"] is True
