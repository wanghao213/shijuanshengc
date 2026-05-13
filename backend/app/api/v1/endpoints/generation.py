"""试卷生成端点 - 集成 ARQ 任务队列与高可用 WebSocket.

支持：
- 通过 ARQ 提交异步任务（彻底解耦）
- WebSocket 实时进度推送（心跳检测、断线重传）
- 完整错误堆栈返回
"""

import json

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.task_queue import TaskQueueManager, TaskPriority
from app.dependencies import get_db
from app.schemas.common import UnifiedResponse
from app.schemas.generation import GenerationRequest, GenerationTaskStatus
from app.services.generation_service import GenerationService
from app.tasks.websocket_manager import get_websocket_manager

logger = structlog.get_logger()

router = APIRouter()

# 任务队列管理器（单例）
_task_queue: TaskQueueManager | None = None


def get_task_queue() -> TaskQueueManager:
    """获取任务队列管理器单例."""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueueManager()
    return _task_queue


@router.post("/generate")
async def start_generation(
    request: GenerationRequest,
    db: AsyncSession = Depends(get_db),
):
    """发起生成任务 - 通过 ARQ 队列异步执行.

    支持优先级参数：
    - priority: "low" | "normal" | "high" | "critical"
    """
    service = GenerationService(db)
    log = await service.start_generation(request)
    await db.commit()

    # 获取任务队列并提交任务
    task_queue = get_task_queue()
    await task_queue.connect()

    # 解析优先级
    priority_map = {
        "low": TaskPriority.LOW,
        "normal": TaskPriority.NORMAL,
        "high": TaskPriority.HIGH,
        "critical": TaskPriority.CRITICAL,
    }
    priority = priority_map.get(getattr(request, "priority", "normal"), TaskPriority.NORMAL)

    # 提交到 ARQ 队列
    job = await task_queue.submit_task(
        task_id=str(log.id),
        log_id=log.id,
        request_data=request.model_dump(),
        priority=priority,
    )

    logger.info(
        "generation_task_queued",
        task_id=log.id,
        job_id=job.job_id,
        priority=priority.value,
    )

    return UnifiedResponse(
        data=GenerationTaskStatus(
            task_id=str(log.id),
            status="queued",
            current_step="等待执行",
            progress_pct=0.0,
            created_at=log.created_at,
        ).model_dump()
    )


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """查询任务状态 - 支持 ARQ 队列状态."""
    # 先尝试从 ARQ 获取实时状态
    task_queue = get_task_queue()
    await task_queue.connect()

    try:
        arq_status = await task_queue.get_task_status(str(task_id))
        if arq_status["status"] in ["queued", "running"]:
            return UnifiedResponse(data=arq_status)
    except Exception:
        pass

    # 回退到数据库查询
    service = GenerationService(db)
    log = await service.get_task(task_id)
    if not log:
        return UnifiedResponse(code=404, message="任务不存在")

    return UnifiedResponse(
        data=GenerationTaskStatus(
            task_id=str(log.id),
            status=log.status,
            current_step=log.current_step,
            progress_pct=log.progress_pct,
            paper_id=log.paper_id,
            error_message=log.error_message,
            created_at=log.created_at,
        ).model_dump()
    )


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: int,
):
    """取消正在执行的任务."""
    task_queue = get_task_queue()
    await task_queue.connect()

    cancelled = await task_queue.cancel_task(str(task_id))
    if cancelled:
        return UnifiedResponse(message="任务已取消")
    else:
        return UnifiedResponse(code=404, message="任务不存在或已完成")


@router.post("/tasks/{task_id}/retry")
async def retry_task(
    task_id: int,
):
    """重试失败的任务."""
    task_queue = get_task_queue()
    await task_queue.connect()

    retried = await task_queue.retry_task(str(task_id))
    if retried:
        return UnifiedResponse(message="任务已重新提交")
    else:
        return UnifiedResponse(code=400, message="无法重试任务（可能未达到最大重试次数）")


@router.get("/tasks")
async def list_tasks(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """任务列表."""
    service = GenerationService(db)
    logs, total = await service.list_tasks(page=page, page_size=page_size)

    return UnifiedResponse(
        data=[
            GenerationTaskStatus(
                task_id=str(log.id),
                status=log.status,
                current_step=log.current_step,
                progress_pct=log.progress_pct,
                paper_id=log.paper_id,
                created_at=log.created_at,
            ).model_dump()
            for log in logs
        ],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.websocket("/ws/{task_id}")
async def generation_ws(websocket: WebSocket, task_id: int):
    """WebSocket 实时进度推送 - 高可用设计.

    功能：
    - 心跳检测（Ping/Pong）
    - 断线缓冲与重传
    - 完整错误堆栈返回
    """
    ws_manager = get_websocket_manager()

    await websocket.accept()
    await ws_manager.register_connection(task_id, websocket)

    # 重放缓冲的消息
    await ws_manager.replay_buffered_messages(task_id, websocket)

    try:
        while True:
            # 等待客户端消息（主要是 Pong 响应）
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "pong":
                    await ws_manager.handle_pong(task_id, websocket)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        logger.info("websocket_disconnected", task_id=task_id)
    except Exception as e:
        logger.error(
            "websocket_error",
            task_id=task_id,
            error=str(e),
            exc_info=True,
        )
    finally:
        await ws_manager.unregister_connection(task_id, websocket)

