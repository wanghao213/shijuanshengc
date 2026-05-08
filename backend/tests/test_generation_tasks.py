"""generation_tasks 单元测试."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tasks.generation_tasks import (
    _broadcast_progress,
    _ws_connections,
    register_ws,
    run_generation_pipeline,
    unregister_ws,
)


def test_register_ws():
    """测试注册 WebSocket 连接."""
    ws = MagicMock()
    register_ws(1, ws)
    assert ws in _ws_connections[1]
    # Cleanup
    _ws_connections.pop(1, None)


def test_unregister_ws():
    """测试注销 WebSocket 连接."""
    ws = MagicMock()
    _ws_connections[2] = [ws]
    unregister_ws(2, ws)
    assert 2 not in _ws_connections


def test_unregister_ws_not_found():
    """测试注销不存在的连接."""
    ws = MagicMock()
    unregister_ws(999, ws)  # Should not raise


@pytest.mark.asyncio
async def test_broadcast_progress_no_connections():
    """测试无连接时广播."""
    await _broadcast_progress(999, "running", "step", 50.0)


@pytest.mark.asyncio
async def test_broadcast_progress_with_connection():
    """测试有连接时广播."""
    ws = AsyncMock()
    _ws_connections[3] = [ws]

    await _broadcast_progress(3, "running", "step", 50.0, {"detail": "test"})

    ws.send_text.assert_called_once()
    _ws_connections.pop(3, None)


@pytest.mark.asyncio
async def test_broadcast_progress_removes_broken_connection():
    """测试广播时移除断开的连接."""
    ws = AsyncMock()
    ws.send_text.side_effect = Exception("Connection closed")
    _ws_connections[4] = [ws]

    await _broadcast_progress(4, "running", "step", 50.0)

    # Connection is removed from the list (list becomes empty)
    assert len(_ws_connections.get(4, [])) == 0


@pytest.mark.asyncio
@patch("app.tasks.generation_tasks.async_session_factory")
@patch("app.tasks.generation_tasks.GenerationService")
async def test_run_generation_pipeline_success(mock_service_cls, mock_factory):
    """测试生成管线成功执行."""
    mock_session = AsyncMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_service = AsyncMock()
    mock_service.generate_paper.return_value = {"paper_id": 1, "stats": {}}
    mock_service_cls.return_value = mock_service

    from app.schemas.generation import GenerationRequest
    request = GenerationRequest(template_id=1)

    await run_generation_pipeline(1, request)

    mock_service.generate_paper.assert_called_once()


@pytest.mark.asyncio
@patch("app.tasks.generation_tasks.async_session_factory")
@patch("app.tasks.generation_tasks.GenerationService")
async def test_run_generation_pipeline_error(mock_service_cls, mock_factory):
    """测试生成管线执行出错."""
    mock_session = AsyncMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_service = AsyncMock()
    mock_service.generate_paper.return_value = {"error": "模板不存在"}
    mock_service_cls.return_value = mock_service

    from app.schemas.generation import GenerationRequest
    request = GenerationRequest(template_id=999)

    await run_generation_pipeline(1, request)


@pytest.mark.asyncio
@patch("app.tasks.generation_tasks.async_session_factory")
@patch("app.tasks.generation_tasks.GenerationService")
async def test_run_generation_pipeline_exception(mock_service_cls, mock_factory):
    """测试生成管线抛出异常."""
    mock_session = AsyncMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_service = AsyncMock()
    mock_service.generate_paper.side_effect = Exception("Unexpected error")
    mock_service_cls.return_value = mock_service

    from app.schemas.generation import GenerationRequest
    request = GenerationRequest(template_id=1)

    # Should not raise
    await run_generation_pipeline(1, request)
