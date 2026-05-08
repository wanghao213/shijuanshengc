"""试卷生成端点."""

from fastapi import APIRouter, BackgroundTasks, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.common import UnifiedResponse
from app.schemas.generation import GenerationRequest, GenerationTaskStatus
from app.services.generation_service import GenerationService
from app.tasks.generation_tasks import (
    register_ws,
    run_generation_pipeline,
    unregister_ws,
)

router = APIRouter()


@router.post("/generate")
async def start_generation(
    request: GenerationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """发起生成任务."""
    service = GenerationService(db)
    log = await service.start_generation(request)
    await db.commit()

    background_tasks.add_task(run_generation_pipeline, log.id, request)

    return UnifiedResponse(
        data=GenerationTaskStatus(
            task_id=str(log.id),
            status=log.status,
            current_step=log.current_step,
            progress_pct=log.progress_pct,
            created_at=log.created_at,
        ).model_dump()
    )


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """查询任务状态."""
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
    """WebSocket 实时进度推送."""
    await websocket.accept()
    register_ws(task_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        unregister_ws(task_id, websocket)
