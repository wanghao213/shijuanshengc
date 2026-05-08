"""试卷生成管线 - 后台任务执行器.

使用 FastAPI BackgroundTasks（V1 阶段）执行生成管线。
通过 GenerationService.generate_paper 编排 5 个 Agent。
"""

from datetime import datetime

import structlog

from app.db.session import async_session_factory
from app.schemas.generation import GenerationRequest, GenerationWsMessage
from app.services.generation_service import GenerationService

logger = structlog.get_logger()

# WebSocket 连接管理
_ws_connections: dict[int, list] = {}


def register_ws(log_id: int, ws) -> None:
    """注册 WebSocket 连接."""
    _ws_connections.setdefault(log_id, []).append(ws)


def unregister_ws(log_id: int, ws) -> None:
    """注销 WebSocket 连接."""
    conns = _ws_connections.get(log_id, [])
    if ws in conns:
        conns.remove(ws)
    if not conns:
        _ws_connections.pop(log_id, None)


async def _broadcast_progress(
    log_id: int,
    status: str,
    step: str,
    pct: float,
    detail: dict | None = None,
) -> None:
    """广播进度到所有连接的 WebSocket."""
    conns = _ws_connections.get(log_id, [])
    if not conns:
        return

    message = GenerationWsMessage(
        task_id=str(log_id),
        status=status,
        current_step=step,
        progress_pct=pct,
        detail=detail,
        timestamp=datetime.now(),
    )
    data = message.model_dump_json()

    for ws in conns[:]:
        try:
            await ws.send_text(data)
        except Exception:
            conns.remove(ws)


async def run_generation_pipeline(
    log_id: int,
    request: GenerationRequest,
) -> None:
    """执行完整的试卷生成管线.

    包装 GenerationService.generate_paper，通过 WebSocket 推送进度。
    """
    async with async_session_factory() as session:
        try:
            service = GenerationService(session)
            result = await service.generate_paper(
                log_id=log_id,
                request=request,
                progress_callback=_broadcast_progress,
            )

            if "error" in result:
                logger.error(
                    "generation_pipeline_error",
                    log_id=log_id,
                    error=result["error"],
                )
            else:
                logger.info(
                    "generation_pipeline_done",
                    log_id=log_id,
                    paper_id=result.get("paper_id"),
                )

        except Exception as e:
            logger.error("generation_pipeline_exception", log_id=log_id, error=str(e), exc_info=True)
            # 异常时广播失败状态
            await _broadcast_progress(
                log_id, "failed", f"生成失败: {str(e)}", 0.0
            )
