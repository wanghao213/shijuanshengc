"""检索服务测试."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.retrieval_service import RetrievalService


def _make_mock_row(**kwargs):
    """创建模拟的数据库行."""
    row = MagicMock()
    row._mapping = kwargs
    return row


@pytest.fixture
def mock_session():
    """创建模拟的数据库会话."""
    session = AsyncMock()
    return session


@pytest.fixture
def retrieval_service(mock_session):
    """创建 RetrievalService 实例."""
    return RetrievalService(session=mock_session)


@pytest.mark.asyncio
async def test_structured_search_basic(retrieval_service, mock_session):
    """测试基本结构化检索."""
    mock_rows = [
        _make_mock_row(
            id=1, content_latex="$x^2$", content_plain="x^2",
            question_type="choice", difficulty=2.0, score=3,
            answer_latex="A", options=None, source="test",
        ),
    ]
    mock_result = MagicMock()
    mock_result.__iter__ = MagicMock(return_value=iter(mock_rows))
    mock_session.execute.return_value = mock_result

    results = await retrieval_service.structured_search(question_type="choice")

    assert len(results) == 1
    assert results[0]["id"] == 1
    assert results[0]["question_type"] == "choice"
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_structured_search_with_filters(retrieval_service, mock_session):
    """测试带过滤条件的结构化检索."""
    mock_result = MagicMock()
    mock_result.__iter__ = MagicMock(return_value=iter([]))
    mock_session.execute.return_value = mock_result

    await retrieval_service.structured_search(
        question_type="fill_blank",
        difficulty_min=2.0,
        difficulty_max=4.0,
        limit=10,
    )

    call_args = mock_session.execute.call_args
    query_text = call_args[0][0].text
    assert "question_type" in query_text
    assert "difficulty >=" in query_text
    assert "difficulty <=" in query_text


@pytest.mark.asyncio
@patch("app.services.retrieval_service.embed")
async def test_semantic_search(mock_embed, retrieval_service, mock_session):
    """测试语义检索."""
    mock_embed.return_value = [[0.1, 0.2, 0.3]]

    mock_rows = [
        _make_mock_row(
            id=1, content_latex="$x^2$", content_plain="x^2",
            question_type="choice", difficulty=2.0, score=3,
            answer_latex="A", options=None, source="test", similarity=0.95,
        ),
    ]
    mock_result = MagicMock()
    mock_result.__iter__ = MagicMock(return_value=iter(mock_rows))
    mock_session.execute.return_value = mock_result

    results = await retrieval_service.semantic_search("二次函数")

    assert len(results) == 1
    assert results[0]["similarity"] == 0.95
    mock_embed.assert_called_once_with(["二次函数"])


@pytest.mark.asyncio
@patch("app.services.retrieval_service.embed")
async def test_hybrid_search_rrf(mock_embed, retrieval_service, mock_session):
    """测试混合检索 RRF 融合."""
    mock_embed.return_value = [[0.1, 0.2, 0.3]]

    # 全文检索返回结果
    fulltext_rows = [
        _make_mock_row(
            id=1, content_latex="q1", content_plain="q1",
            question_type="choice", difficulty=2.0, score=3,
            answer_latex=None, options=None, source=None, rank=0.8,
        ),
        _make_mock_row(
            id=2, content_latex="q2", content_plain="q2",
            question_type="choice", difficulty=3.0, score=3,
            answer_latex=None, options=None, source=None, rank=0.6,
        ),
    ]

    # 语义检索返回结果
    semantic_rows = [
        _make_mock_row(
            id=2, content_latex="q2", content_plain="q2",
            question_type="choice", difficulty=3.0, score=3,
            answer_latex=None, options=None, source=None, similarity=0.9,
        ),
        _make_mock_row(
            id=3, content_latex="q3", content_plain="q3",
            question_type="choice", difficulty=4.0, score=3,
            answer_latex=None, options=None, source=None, similarity=0.8,
        ),
    ]

    # Mock 两次 execute 调用（fulltext 和 semantic）
    mock_result_ft = MagicMock()
    mock_result_ft.__iter__ = MagicMock(return_value=iter(fulltext_rows))
    mock_result_sem = MagicMock()
    mock_result_sem.__iter__ = MagicMock(return_value=iter(semantic_rows))

    mock_session.execute.side_effect = [mock_result_ft, mock_result_sem]

    results = await retrieval_service.hybrid_search("测试查询")

    # id=2 出现在两路结果中，应排在最前
    assert len(results) > 0
    assert results[0]["id"] == 2  # 两路都有，RRF 分数最高


@pytest.mark.asyncio
async def test_find_similar_questions(retrieval_service, mock_session):
    """测试相似题目查找."""
    mock_rows = [
        _make_mock_row(
            id=2, content_latex="similar", question_type="choice",
            difficulty=2.0, similarity=0.95,
        ),
    ]
    mock_result = MagicMock()
    mock_result.__iter__ = MagicMock(return_value=iter(mock_rows))
    mock_session.execute.return_value = mock_result

    results = await retrieval_service.find_similar_questions(question_id=1, threshold=0.9)

    assert len(results) == 1
    assert results[0]["similarity"] == 0.95


@pytest.mark.asyncio
async def test_apply_filters(retrieval_service):
    """测试后过滤功能."""
    results = [
        {"id": 1, "question_type": "choice", "difficulty": 2.0},
        {"id": 2, "question_type": "fill_blank", "difficulty": 3.0},
        {"id": 3, "question_type": "choice", "difficulty": 4.0},
    ]

    filtered = retrieval_service._apply_filters(results, {"question_type": "choice"})
    assert len(filtered) == 2
    assert all(r["question_type"] == "choice" for r in filtered)

    filtered = retrieval_service._apply_filters(results, {"difficulty_min": 3.0})
    assert len(filtered) == 2
    assert all(r["difficulty"] >= 3.0 for r in filtered)

    filtered = retrieval_service._apply_filters(results, {"difficulty_max": 2.5})
    assert len(filtered) == 1
    assert filtered[0]["difficulty"] <= 2.5
