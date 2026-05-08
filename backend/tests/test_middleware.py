"""中间件测试."""

from unittest.mock import MagicMock, patch

import pytest
from starlette.requests import Request
from starlette.responses import Response

from app.middleware.cost_middleware import CostMiddleware
from app.middleware.logging_middleware import LoggingMiddleware


def _make_mock_request(path: str = "/api/v1/test", method: str = "GET"):
    """创建 mock Request."""
    request = MagicMock(spec=Request)
    request.url = MagicMock()
    request.url.path = path
    request.method = method
    return request


def _make_mock_response(status_code: int = 200):
    """创建 mock Response."""
    response = MagicMock(spec=Response)
    response.status_code = status_code
    return response


@pytest.mark.asyncio
@patch("app.middleware.cost_middleware.logger")
async def test_cost_middleware_non_ai_path(mock_logger):
    """测试 CostMiddleware 对非 AI 路径不记录."""
    request = _make_mock_request("/api/v1/questions/")
    response = _make_mock_response(200)

    async def mock_call_next(req):
        return response

    middleware = CostMiddleware(app=None)
    result = await middleware.dispatch(request, mock_call_next)

    assert result == response
    # 非 AI 路径不应记录日志
    mock_logger.info.assert_not_called()


@pytest.mark.asyncio
@patch("app.middleware.cost_middleware.logger")
async def test_cost_middleware_ai_path(mock_logger):
    """测试 CostMiddleware 对 AI 路径记录日志."""
    request = _make_mock_request("/api/v1/generation/generate", "POST")
    response = _make_mock_response(200)

    async def mock_call_next(req):
        return response

    middleware = CostMiddleware(app=None)
    result = await middleware.dispatch(request, mock_call_next)

    assert result == response
    mock_logger.info.assert_called_once()
    call_args = mock_logger.info.call_args
    assert call_args[0][0] == "ai_request_cost"


@pytest.mark.asyncio
@patch("app.middleware.cost_middleware.logger")
async def test_cost_middleware_ai_tasks_path(mock_logger):
    """测试 CostMiddleware 对 tasks 路径记录日志."""
    request = _make_mock_request("/api/v1/generation/tasks/1")
    response = _make_mock_response(200)

    async def mock_call_next(req):
        return response

    middleware = CostMiddleware(app=None)
    result = await middleware.dispatch(request, mock_call_next)

    assert result == response
    mock_logger.info.assert_called_once()


@pytest.mark.asyncio
@patch("app.middleware.logging_middleware.logger")
async def test_logging_middleware(mock_logger):
    """测试 LoggingMiddleware 记录请求日志."""
    request = _make_mock_request("/api/v1/test", "GET")
    response = _make_mock_response(200)

    async def mock_call_next(req):
        return response

    middleware = LoggingMiddleware(app=None)
    result = await middleware.dispatch(request, mock_call_next)

    assert result == response
    mock_logger.info.assert_called_once()
    call_args = mock_logger.info.call_args
    assert call_args[0][0] == "request"
    assert call_args[1]["method"] == "GET"
    assert call_args[1]["path"] == "/api/v1/test"
    assert call_args[1]["status_code"] == 200
    assert "duration_ms" in call_args[1]


@pytest.mark.asyncio
@patch("app.middleware.logging_middleware.logger")
async def test_logging_middleware_post(mock_logger):
    """测试 LoggingMiddleware 记录 POST 请求."""
    request = _make_mock_request("/api/v1/questions/", "POST")
    response = _make_mock_response(201)

    async def mock_call_next(req):
        return response

    middleware = LoggingMiddleware(app=None)
    result = await middleware.dispatch(request, mock_call_next)

    assert result == response
    call_args = mock_logger.info.call_args
    assert call_args[1]["method"] == "POST"
    assert call_args[1]["status_code"] == 201


@pytest.mark.asyncio
@patch("app.middleware.logging_middleware.logger")
async def test_logging_middleware_error_response(mock_logger):
    """测试 LoggingMiddleware 记录错误响应."""
    request = _make_mock_request("/api/v1/test", "GET")
    response = _make_mock_response(500)

    async def mock_call_next(req):
        return response

    middleware = LoggingMiddleware(app=None)
    result = await middleware.dispatch(request, mock_call_next)

    assert result == response
    call_args = mock_logger.info.call_args
    assert call_args[1]["status_code"] == 500


@pytest.mark.asyncio
@patch("app.middleware.logging_middleware.logger")
async def test_logging_middleware_duration(mock_logger):
    """测试 LoggingMiddleware 记录耗时."""
    request = _make_mock_request()
    response = _make_mock_response(200)

    async def mock_call_next(req):
        return response

    middleware = LoggingMiddleware(app=None)
    await middleware.dispatch(request, mock_call_next)

    call_args = mock_logger.info.call_args
    duration = call_args[1]["duration_ms"]
    assert isinstance(duration, float)
    assert duration >= 0
