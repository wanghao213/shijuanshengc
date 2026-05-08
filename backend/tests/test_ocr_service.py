"""OcrService 单元测试."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ValidationError
from app.services.ocr_service import ExtractedQuestion, OcrService


@pytest.mark.asyncio
@patch("app.services.ocr_service.structured_chat")
async def test_process_document_raw_text(mock_structured_chat):
    """测试手动输入模式处理文档."""
    session = AsyncMock()

    # mock _llm_cleanup response
    cleanup_response = MagicMock()
    cleanup_response.content = '{"cleaned_text": "1. 计算 1+1", "corrections": [], "confidence": 0.9, "notes": ""}'

    # mock _structured_extract response
    extract_response = MagicMock()
    extract_response.content = '{"questions": [{"number": "1", "content_latex": "$1+1=2$", "question_type": "short_answer", "answer_latex": "2", "knowledge_points": ["算术"], "estimated_difficulty": 1.0}]}'

    mock_structured_chat.side_effect = [cleanup_response, extract_response]

    svc = OcrService(session)
    result = await svc.process_document(raw_text="1. 计算 $1+1$ 的值。")

    assert result.status == "success"
    assert len(result.questions) == 1
    assert result.questions[0].number == "1"
    assert result.questions[0].content_latex == "$1+1=2$"


@pytest.mark.asyncio
async def test_process_document_no_input():
    """测试无输入时的处理."""
    session = AsyncMock()

    svc = OcrService(session)
    with pytest.raises(ValidationError):
        await svc.process_document()


@pytest.mark.asyncio
@patch("app.services.ocr_service.structured_chat")
async def test_process_document_empty_extract(mock_structured_chat):
    """测试提取结果为空."""
    session = AsyncMock()

    cleanup_response = MagicMock()
    cleanup_response.content = '{"cleaned_text": "文本", "corrections": [], "confidence": 0.5, "notes": ""}'

    extract_response = MagicMock()
    extract_response.content = '{"questions": []}'

    mock_structured_chat.side_effect = [cleanup_response, extract_response]

    svc = OcrService(session)
    result = await svc.process_document(raw_text="无法识别的文本")

    assert result.status == "partial"
    assert len(result.questions) == 0


@pytest.mark.asyncio
@patch("app.services.ocr_service.structured_chat")
async def test_llm_cleanup_success(mock_structured_chat):
    """测试 LLM 清洗成功."""
    session = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = '{"cleaned_text": "清洗后文本", "corrections": [{"original": "错字", "corrected": "正字"}], "confidence": 0.85, "notes": "修正了错别字"}'
    mock_structured_chat.return_value = mock_response

    svc = OcrService(session)
    result = await svc._llm_cleanup("原始文本")

    assert result["cleaned_text"] == "清洗后文本"
    assert len(result["corrections"]) == 1
    assert result["confidence"] == 0.85


@pytest.mark.asyncio
@patch("app.services.ocr_service.structured_chat")
async def test_llm_cleanup_json_error(mock_structured_chat):
    """测试 LLM 清洗 JSON 解析失败."""
    session = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = "not json"
    mock_structured_chat.return_value = mock_response

    svc = OcrService(session)
    result = await svc._llm_cleanup("原始文本")

    # 应该回退到原始文本
    assert result["cleaned_text"] == "原始文本"
    assert result["confidence"] == 0.3


@pytest.mark.asyncio
@patch("app.services.ocr_service.structured_chat")
async def test_structured_extract_success(mock_structured_chat):
    """测试结构化提取成功."""
    session = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = '{"questions": [{"number": "1", "content_latex": "$x+1=0$", "question_type": "short_answer"}]}'
    mock_structured_chat.return_value = mock_response

    svc = OcrService(session)
    result = await svc._structured_extract("1. 解方程 x+1=0")

    assert len(result["questions"]) == 1


@pytest.mark.asyncio
@patch("app.services.ocr_service.structured_chat")
async def test_structured_extract_json_error(mock_structured_chat):
    """测试结构化提取 JSON 解析失败."""
    session = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = "invalid"
    mock_structured_chat.return_value = mock_response

    svc = OcrService(session)
    result = await svc._structured_extract("文本")

    assert result["questions"] == []


def test_latex_to_plain():
    """测试 LaTeX 转纯文本."""
    assert "frac" not in OcrService._latex_to_plain("\\frac{1}{2}")
    assert "1" in OcrService._latex_to_plain("\\frac{1}{2}")
    assert "2" in OcrService._latex_to_plain("\\frac{1}{2}")


def test_latex_to_plain_sqrt():
    """测试 sqrt 转换."""
    result = OcrService._latex_to_plain("\\sqrt{4}")
    assert "sqrt" not in result
    assert "4" in result


def test_latex_to_plain_textbf():
    """测试 textbf 转换."""
    result = OcrService._latex_to_plain("\\textbf{重要}")
    assert "textbf" not in result
    assert "重要" in result


def test_latex_to_plain_complex():
    """测试复杂 LaTeX 转换."""
    result = OcrService._latex_to_plain("$x^2 + \\frac{a}{b} = 0$")
    assert "$" not in result
    assert "x" in result


@pytest.mark.asyncio
@patch("app.services.ocr_service.structured_chat")
async def test_llm_cleanup_exception(mock_structured_chat):
    """测试 LLM 清洗抛出异常."""
    session = AsyncMock()
    mock_structured_chat.side_effect = Exception("LLM unavailable")

    svc = OcrService(session)
    result = await svc._llm_cleanup("原始文本")

    assert result["cleaned_text"] == "原始文本"
    assert "LLM" in result["notes"]


@pytest.mark.asyncio
@patch("app.services.ocr_service.structured_chat")
async def test_structured_extract_exception(mock_structured_chat):
    """测试结构化提取抛出异常."""
    session = AsyncMock()
    mock_structured_chat.side_effect = Exception("LLM error")

    svc = OcrService(session)
    result = await svc._structured_extract("文本")

    assert result["questions"] == []


@pytest.mark.asyncio
@patch("app.services.ocr_service.structured_chat")
async def test_process_and_save(mock_structured_chat):
    """测试处理并保存到数据库."""
    session = AsyncMock()

    cleanup_response = MagicMock()
    cleanup_response.content = '{"cleaned_text": "1. 计算", "corrections": [], "confidence": 0.9, "notes": ""}'

    extract_response = MagicMock()
    extract_response.content = '{"questions": [{"number": "1", "content_latex": "$1+1$", "question_type": "short_answer", "answer_latex": "2", "knowledge_points": [], "estimated_difficulty": 1.5}]}'

    annotate_response = MagicMock()
    annotate_response.content = '{"knowledge_points": ["算术"], "difficulty": 1.5}'

    mock_structured_chat.side_effect = [cleanup_response, extract_response, annotate_response]

    # Mock KnowledgeNode query for auto_annotate
    mock_kp_result = MagicMock()
    mock_kp_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_kp_result

    svc = OcrService(session)
    result = await svc.process_and_save(raw_text="1. 计算 $1+1$")

    assert result.status == "success"
    assert len(result.saved_question_ids) == 1
    session.add.assert_called()


@pytest.mark.asyncio
@patch("app.services.ocr_service.structured_chat")
async def test_process_and_save_failed(mock_structured_chat):
    """测试处理失败时不保存."""
    session = AsyncMock()

    cleanup_response = MagicMock()
    cleanup_response.content = '{"cleaned_text": "", "corrections": [], "confidence": 0.1, "notes": ""}'

    extract_response = MagicMock()
    extract_response.content = '{"questions": []}'

    mock_structured_chat.side_effect = [cleanup_response, extract_response]

    svc = OcrService(session)
    result = await svc.process_and_save(raw_text="  ")

    assert result.status == "partial"
    assert result.saved_question_ids == []


@pytest.mark.asyncio
@patch("app.services.ocr_service.settings")
async def test_run_mineru_disabled(mock_settings):
    """测试 MinerU 禁用时返回 None."""
    mock_settings.mineru_enabled = False

    session = AsyncMock()
    svc = OcrService(session)
    result = await svc._run_mineru("/fake/path.pdf")

    assert result is None


@pytest.mark.asyncio
@patch("app.services.ocr_service.settings")
async def test_run_mineru_file_not_found(mock_settings):
    """测试 MinerU 文件不存在."""
    mock_settings.mineru_enabled = True

    session = AsyncMock()
    svc = OcrService(session)

    with pytest.raises(ValidationError):
        await svc._run_mineru("/nonexistent/file.pdf")


@pytest.mark.asyncio
@patch("app.services.ocr_service.structured_chat")
async def test_llm_annotate_success(mock_structured_chat):
    """测试 LLM 标注成功."""
    session = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = '{"knowledge_points": ["代数"], "difficulty": 3.0}'
    mock_structured_chat.return_value = mock_response

    from app.models.question import Question
    question = MagicMock(spec=Question)
    question.content_latex = "$x^2 + 1 = 0$"
    question.question_type = "short_answer"

    svc = OcrService(session)
    result = await svc._llm_annotate(question, ["代数", "几何"])

    assert result["knowledge_points"] == ["代数"]
    assert result["difficulty"] == 3.0


@pytest.mark.asyncio
@patch("app.services.ocr_service.structured_chat")
async def test_llm_annotate_exception(mock_structured_chat):
    """测试 LLM 标注异常."""
    session = AsyncMock()
    mock_structured_chat.side_effect = Exception("LLM error")

    from app.models.question import Question
    question = MagicMock(spec=Question)
    question.content_latex = "$x^2$"
    question.question_type = "choice"

    svc = OcrService(session)
    result = await svc._llm_annotate(question, ["代数"])

    assert result["knowledge_points"] == []
    assert result["difficulty"] == 3.0


def test_collect_mineru_output_empty():
    """测试 MinerU 输出目录为空."""
    import tempfile

    session = AsyncMock()
    svc = OcrService(session)

    with tempfile.TemporaryDirectory() as tmpdir:
        result = svc._collect_mineru_output(tmpdir)
        assert result == ""


def test_collect_mineru_output_with_files():
    """测试 MinerU 输出目录有文件."""
    import os
    import tempfile

    session = AsyncMock()
    svc = OcrService(session)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a markdown file
        md_file = os.path.join(tmpdir, "output.md")
        with open(md_file, "w", encoding="utf-8") as f:
            f.write("# 测试内容\n\n数学公式 $x^2$")

        # Create a txt file
        txt_file = os.path.join(tmpdir, "output.txt")
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write("纯文本内容")

        result = svc._collect_mineru_output(tmpdir)
        assert "测试内容" in result
        assert "纯文本内容" in result


@pytest.mark.asyncio
@patch("app.services.ocr_service.structured_chat")
async def test_process_and_save_with_options(mock_structured_chat):
    """测试处理带选项的题目."""
    session = AsyncMock()

    cleanup_response = MagicMock()
    cleanup_response.content = '{"cleaned_text": "选择题", "corrections": [], "confidence": 0.9, "notes": ""}'

    extract_response = MagicMock()
    extract_response.content = '{"questions": [{"number": "1", "content_latex": "1+1=?", "question_type": "choice", "options": [{"label": "A", "content_latex": "1"}, {"label": "B", "content_latex": "2"}], "answer_latex": "B", "knowledge_points": [], "estimated_difficulty": 1.0}]}'

    mock_structured_chat.side_effect = [cleanup_response, extract_response]

    mock_kp_result = MagicMock()
    mock_kp_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_kp_result

    svc = OcrService(session)
    result = await svc.process_and_save(raw_text="1. 1+1=?\nA. 1\nB. 2")

    assert result.status == "success"
    assert len(result.saved_question_ids) == 1


@pytest.mark.asyncio
@patch("app.services.ocr_service.structured_chat")
async def test_process_document_with_options(mock_structured_chat):
    """测试处理带选项的文档."""
    session = AsyncMock()

    cleanup_response = MagicMock()
    cleanup_response.content = '{"cleaned_text": "选择题", "corrections": [], "confidence": 0.9, "notes": ""}'

    extract_response = MagicMock()
    extract_response.content = '{"questions": [{"number": "1", "content_latex": "1+1=?", "question_type": "choice", "options": [{"label": "A", "content_latex": "1"}, {"label": "B", "content_latex": "2"}], "answer_latex": "B"}]}'

    mock_structured_chat.side_effect = [cleanup_response, extract_response]

    svc = OcrService(session)
    result = await svc.process_document(raw_text="1. 1+1=?")

    assert result.questions[0].options is not None
    assert len(result.questions[0].options) == 2


@pytest.mark.asyncio
@patch("app.services.ocr_service.structured_chat")
async def test_process_and_save_failed_status(mock_structured_chat):
    """测试 process_and_save 处理失败状态时直接返回."""
    session = AsyncMock()

    # Make process_document return a failed result
    cleanup_response = MagicMock()
    cleanup_response.content = '{"cleaned_text": "", "corrections": [], "confidence": 0.0, "notes": ""}'

    extract_response = MagicMock()
    extract_response.content = '{"questions": []}'

    # First call for process_document's _llm_cleanup
    # Second call for process_document's _structured_extract
    mock_structured_chat.side_effect = [cleanup_response, extract_response]

    svc = OcrService(session)
    # Use raw_text with actual content so process_document doesn't raise
    result = await svc.process_and_save(raw_text="test")

    # partial status because no questions extracted
    assert result.status == "partial"


@pytest.mark.asyncio
@patch("app.services.ocr_service.structured_chat")
async def test_auto_annotate_fuzzy_match(mock_structured_chat):
    """测试 _auto_annotate 模糊匹配知识点."""
    session = AsyncMock()

    # Mock LLM annotation response
    annotate_response = MagicMock()
    annotate_response.content = '{"knowledge_points": ["代数方程"], "difficulty": 2.5}'
    mock_structured_chat.return_value = annotate_response

    # Mock knowledge nodes with a similar name
    mock_kp = MagicMock()
    mock_kp.name = "代数方程与不等式"
    mock_kp.id = 1

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_kp]
    session.execute.return_value = mock_result

    from app.models.question import Question

    question = MagicMock(spec=Question)
    question.id = 1
    question.content_latex = "$x+1=0$"
    question.question_type = "short_answer"
    question.difficulty = 3.0

    extracted = ExtractedQuestion(
        number="1",
        content_latex="$x+1=0$",
        knowledge_points=["代数方程"],
        estimated_difficulty=3.0,
    )

    svc = OcrService(session)
    await svc._auto_annotate(question, extracted)

    # Should have matched via fuzzy matching
    assert session.add.called
