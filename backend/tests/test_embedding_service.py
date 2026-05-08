"""EmbeddingService 单元测试."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.embedding_service import EmbeddingService


@pytest.mark.asyncio
@patch("app.services.embedding_service.embed")
async def test_generate_embedding_success(mock_embed):
    """测试成功生成 embedding."""
    session = AsyncMock()

    # mock content query
    row = MagicMock()
    row.__getitem__ = MagicMock(return_value="x squared plus one equals zero")
    query_result = MagicMock()
    query_result.first.return_value = row
    session.execute = AsyncMock(return_value=query_result)
    session.flush = AsyncMock()

    # mock embed
    mock_embed.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5]]

    svc = EmbeddingService(session)
    embedding = await svc.generate_embedding(question_id=1)

    assert embedding == [0.1, 0.2, 0.3, 0.4, 0.5]
    mock_embed.assert_called_once()
    session.flush.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.embedding_service.embed")
async def test_generate_embedding_not_found(mock_embed):
    """测试题目不存在时生成 embedding."""
    session = AsyncMock()
    query_result = MagicMock()
    query_result.first.return_value = None
    session.execute = AsyncMock(return_value=query_result)

    svc = EmbeddingService(session)
    embedding = await svc.generate_embedding(question_id=999)

    assert embedding == []
    mock_embed.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.embedding_service.embed")
async def test_generate_embedding_empty_result(mock_embed):
    """测试 embed 返回空结果."""
    session = AsyncMock()

    row = MagicMock()
    row.__getitem__ = MagicMock(return_value="test content")
    query_result = MagicMock()
    query_result.first.return_value = row
    session.execute = AsyncMock(return_value=query_result)

    mock_embed.return_value = []

    svc = EmbeddingService(session)
    embedding = await svc.generate_embedding(question_id=1)

    assert embedding == []


@pytest.mark.asyncio
@patch("app.services.embedding_service.EmbeddingService.generate_embedding")
async def test_batch_generate_embeddings_with_ids(mock_generate):
    """测试批量生成 embedding（指定 IDs）."""
    session = AsyncMock()
    mock_generate.return_value = [0.1, 0.2]

    svc = EmbeddingService(session)
    count = await svc.batch_generate_embeddings(
        question_ids=[1, 2, 3],
        batch_size=2,
    )

    assert count == 3
    assert mock_generate.call_count == 3


@pytest.mark.asyncio
@patch("app.services.embedding_service.EmbeddingService.generate_embedding")
async def test_batch_generate_embeddings_partial_failure(mock_generate):
    """测试批量生成 embedding（部分失败）."""
    session = AsyncMock()
    mock_generate.side_effect = [
        [0.1, 0.2],
        Exception("API error"),
        [0.3, 0.4],
    ]

    svc = EmbeddingService(session)
    count = await svc.batch_generate_embeddings(
        question_ids=[1, 2, 3],
        batch_size=10,
    )

    assert count == 2  # 2 succeeded, 1 failed


@pytest.mark.asyncio
@patch("app.services.embedding_service.EmbeddingService.generate_embedding")
async def test_batch_generate_embeddings_auto_discover(mock_generate):
    """测试批量生成 embedding（自动发现无 embedding 的题目）."""
    session = AsyncMock()

    # mock query for IDs
    id_result = MagicMock()
    id_result.__iter__ = MagicMock(return_value=iter([(1,), (2,)]))
    session.execute = AsyncMock(return_value=id_result)

    mock_generate.return_value = [0.1, 0.2]

    svc = EmbeddingService(session)
    await svc.batch_generate_embeddings(
        question_ids=None,
        skip_existing=True,
    )

    # generate_embedding is called for each discovered ID
    # but session.execute is also called for the discovery query
    assert mock_generate.call_count == 2


@pytest.mark.asyncio
@patch("app.services.embedding_service.EmbeddingService.generate_embedding")
async def test_batch_generate_embeddings_empty(mock_generate):
    """测试批量生成 embedding（空列表）."""
    session = AsyncMock()

    svc = EmbeddingService(session)
    count = await svc.batch_generate_embeddings(question_ids=[])

    assert count == 0
    mock_generate.assert_not_called()
