"""AI 调用成本统计中间件."""

import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()


class CostMiddleware(BaseHTTPMiddleware):
    """记录 API 请求的成本相关指标（目前仅记录耗时，后续可扩展 token 统计）."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        # 仅对 AI 相关接口记录成本日志
        if request.url.path.startswith("/api/v1/generation"):
            logger.info(
                "ai_request_cost",
                path=request.url.path,
                method=request.method,
                duration_ms=duration_ms,
                status_code=response.status_code,
            )

        return response
