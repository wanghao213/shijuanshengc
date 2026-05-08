"""QuestionService 单元测试."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import NotFoundError
from app.schemas.question import QuestionCreate, QuestionUpdate
from app.services.question_service import QuestionService


def _make_mock_question(**kwargs):
    """创建 mock Question 对象."""
    q = MagicMock()
    q.id = kwargs.get("id", 1)
    q.content_latex = kwargs.get("content_latex", "$x^2$")
    q.content_plain = kwargs.get("content_plain", "x^2")
    q.question_type = kwargs.get("question_type", "choice")
    q.difficulty = kwargs.get("difficulty", 3.0)
    q.score = kwargs.get("score", 5.0)
    q.answer_latex = kwargs.get("answer_latex", "A")
    q.solution_steps = kwargs.get("solution_steps")
    q.options = kwargs.get("options")
    q.source = kwargs.get("source")
    q.source_year = kwargs.get("source_year")
    q.region = kwargs.get("region")
    q.exam_type = kwargs.get("exam_type")
    q.is_ai_generated = kwargs.get("is_ai_generated", False)
    q.review_status = kwargs.get("review_status", "pending")
    q.is_deleted = kwargs.get("is_deleted", False)
    q.current_version = kwargs.get("current_version", 1)
    q.knowledge_points = kwargs.get("knowledge_points", [])
    q.versions = kwargs.get("versions", [])
    q.tags = kwargs.get("tags", [])
    return q


@pytest.mark.asyncio
async def test_list_questions_empty():
    """测试空题库列表."""
    session = AsyncMock()
    # count query
    count_result = MagicMock()
    count_result.scalar.return_value = 0
    # list query
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = []

    session.execute = AsyncMock(side_effect=[count_result, list_result])

    svc = QuestionService(session)
    questions, total = await svc.list_questions()

    assert questions == []
    assert total == 0


@pytest.mark.asyncio
async def test_list_questions_with_data():
    """测试有数据的列表."""
    session = AsyncMock()
    q1 = _make_mock_question(id=1)
    q2 = _make_mock_question(id=2)

    count_result = MagicMock()
    count_result.scalar.return_value = 2
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [q1, q2]

    session.execute = AsyncMock(side_effect=[count_result, list_result])

    svc = QuestionService(session)
    questions, total = await svc.list_questions(page=1, page_size=20)

    assert len(questions) == 2
    assert total == 2


@pytest.mark.asyncio
async def test_list_questions_with_filters():
    """测试带过滤条件的列表."""
    session = AsyncMock()
    count_result = MagicMock()
    count_result.scalar.return_value = 1
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [_make_mock_question()]

    session.execute = AsyncMock(side_effect=[count_result, list_result])

    svc = QuestionService(session)
    questions, total = await svc.list_questions(
        question_type="choice", difficulty_min=2.0, difficulty_max=4.0
    )

    assert len(questions) == 1
    assert total == 1


@pytest.mark.asyncio
async def test_get_question_found():
    """测试获取存在的题目."""
    session = AsyncMock()
    mock_q = _make_mock_question(id=42)
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_q
    session.execute = AsyncMock(return_value=result)

    svc = QuestionService(session)
    q = await svc.get_question(42)

    assert q.id == 42


@pytest.mark.asyncio
async def test_get_question_not_found():
    """测试获取不存在的题目."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=result)

    svc = QuestionService(session)
    with pytest.raises(NotFoundError):
        await svc.get_question(999)


@pytest.mark.asyncio
async def test_create_question():
    """测试创建题目."""
    session = AsyncMock()
    # flush 后模拟 question 获得 id
    def set_id(obj):
        if hasattr(obj, 'id') and obj.id is None:
            obj.id = 1

    session.add = MagicMock(side_effect=lambda obj: set_id(obj) if hasattr(obj, 'id') else None)
    session.flush = AsyncMock()

    svc = QuestionService(session)
    data = QuestionCreate(
        content_latex="$x+1=0$",
        content_plain="x+1=0",
        question_type="short_answer",
        difficulty=2.0,
        knowledge_point_ids=[1, 2],
    )
    await svc.create_question(data)

    assert session.add.call_count >= 2  # question + version + associations
    assert session.flush.call_count >= 1


@pytest.mark.asyncio
async def test_update_question():
    """测试更新题目."""
    session = AsyncMock()
    mock_q = _make_mock_question(id=10, current_version=1)

    # get_question -> execute -> scalar_one_or_none
    get_result = MagicMock()
    get_result.scalar_one_or_none.return_value = mock_q
    session.execute = AsyncMock(return_value=get_result)
    session.add = MagicMock()
    session.flush = AsyncMock()

    svc = QuestionService(session)
    data = QuestionUpdate(
        content_latex="$x^2+1=0$",
        change_reason="修正公式",
    )
    await svc.update_question(10, data)

    # update_question uses setattr + flush, not add (versioning is ORM event)
    assert mock_q.content_latex == "$x^2+1=0$"
    assert mock_q._change_reason == "修正公式"
    session.flush.assert_called()


@pytest.mark.asyncio
async def test_batch_import_success():
    """测试批量导入全部成功."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    svc = QuestionService(session)
    data = QuestionCreate(
        content_latex="$a+b$",
        content_plain="a+b",
        question_type="fill_blank",
        difficulty=1.5,
    )
    result = await svc.batch_import([data, data])

    assert result["created"] == 2
    assert result["failed"] == 0
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_batch_import_partial_failure():
    """测试批量导入部分失败."""
    session = AsyncMock()
    call_count = 0

    def side_effect(obj):
        nonlocal call_count
        call_count += 1

    session.add = MagicMock(side_effect=side_effect)

    async def flush_side_effect():
        if call_count > 1:
            raise Exception("DB error")

    session.flush = AsyncMock(side_effect=flush_side_effect)
    session.commit = AsyncMock()

    svc = QuestionService(session)
    data = QuestionCreate(
        content_latex="$x$",
        content_plain="x",
        question_type="choice",
        difficulty=2.0,
    )
    result = await svc.batch_import([data])

    # The first one may succeed or fail depending on flush timing
    assert result["created"] + result["failed"] == 1


@pytest.mark.asyncio
@patch("app.services.question_service.structured_chat")
async def test_auto_tag(mock_structured_chat):
    """测试 AI 自动标注."""
    session = AsyncMock()

    # mock get_question
    mock_q = _make_mock_question(id=5, content_latex="$x^2$", question_type="choice")
    q_result = MagicMock()
    q_result.scalar_one_or_none.return_value = mock_q

    # mock knowledge points query
    kp_result = MagicMock()
    kp_result.__iter__ = MagicMock(return_value=iter([("代数",), ("方程",)]))

    # mock structured_chat response
    mock_response = MagicMock()
    mock_response.content = '{"knowledge_points": ["代数"], "difficulty": 3.5, "tags": [{"tag_type": "解题方法", "tag_value": "因式分解"}]}'
    mock_structured_chat.return_value = mock_response

    # mock knowledge node lookup
    kp_node_result = MagicMock()
    mock_kp_node = MagicMock()
    mock_kp_node.id = 1
    kp_node_result.scalar_one_or_none.return_value = mock_kp_node

    # mock existing association check
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = None

    session.execute = AsyncMock(
        side_effect=[q_result, kp_result, kp_node_result, existing_result]
    )
    session.add = MagicMock()
    session.flush = AsyncMock()

    svc = QuestionService(session)
    result = await svc.auto_tag(5)

    assert result["difficulty"] == 3.5
    assert "代数" in result["knowledge_points"]
    assert len(result["tags"]) == 1


@pytest.mark.asyncio
@patch("app.services.question_service.structured_chat")
async def test_auto_tag_json_error(mock_structured_chat):
    """测试 AI 自动标注 JSON 解析失败."""
    session = AsyncMock()

    mock_q = _make_mock_question(id=5, difficulty=2.5)
    q_result = MagicMock()
    q_result.scalar_one_or_none.return_value = mock_q

    kp_result = MagicMock()
    kp_result.__iter__ = MagicMock(return_value=iter([]))

    mock_response = MagicMock()
    mock_response.content = "not valid json"
    mock_structured_chat.return_value = mock_response

    session.execute = AsyncMock(side_effect=[q_result, kp_result])
    session.add = MagicMock()
    session.flush = AsyncMock()

    svc = QuestionService(session)
    result = await svc.auto_tag(5)

    assert result["knowledge_points"] == []
    assert result["difficulty"] == 2.5  # falls back to original


@pytest.mark.asyncio
async def test_get_statistics():
    """测试统计方法."""
    session = AsyncMock()

    # total count
    total_result = MagicMock()
    total_result.scalar.return_value = 100

    # by type
    type_result = MagicMock()
    type_row = MagicMock()
    type_row.question_type = "choice"
    type_row.count = 50
    type_row.avg_difficulty = 2.5
    type_result.__iter__ = MagicMock(return_value=iter([type_row]))

    # by status
    status_result = MagicMock()
    status_row = MagicMock()
    status_row.review_status = "approved"
    status_row.count = 80
    status_result.__iter__ = MagicMock(return_value=iter([status_row]))

    # by source
    source_result = MagicMock()
    source_row = MagicMock()
    source_row.source = "中考真题"
    source_row.count = 30
    source_result.__iter__ = MagicMock(return_value=iter([source_row]))

    # difficulty
    diff_result = MagicMock()
    diff_row = MagicMock()
    diff_row.avg = 2.8
    diff_row.min = 1.0
    diff_row.max = 5.0
    diff_result.one.return_value = diff_row

    # ai count
    ai_result = MagicMock()
    ai_result.scalar.return_value = 20

    session.execute = AsyncMock(
        side_effect=[total_result, type_result, status_result, source_result, diff_result, ai_result]
    )

    svc = QuestionService(session)
    stats = await svc.get_statistics()

    assert stats["total"] == 100
    assert "choice" in stats["by_type"]
    assert stats["by_status"]["approved"] == 80
    assert stats["by_source"]["中考真题"] == 30
    assert stats["difficulty"]["average"] == 2.8
    assert stats["ai_generated"] == 20
