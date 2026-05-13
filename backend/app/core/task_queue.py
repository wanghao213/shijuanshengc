"""异步任务队列管理 - ARQ 集成.

基于 ARQ (Async Redis Queue) 实现长耗时任务的彻底解耦，
防止 FastAPI 主进程被阻塞。支持任务生命周期管理、重试机制和优先级队列。
"""

import asyncio
import json
import traceback
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable

import structlog
from arq import Worker
from arq.connections import ArqRedis, RedisSettings
from arq.jobs import Job
from pydantic import BaseModel

logger = structlog.get_logger()


class TaskPriority(int, Enum):
    """任务优先级."""

    LOW = 0
    NORMAL = 50
    HIGH = 100
    CRITICAL = 200


class TaskStatus(str, Enum):
    """任务状态."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class TaskMetadata(BaseModel):
    """任务元数据."""

    task_id: str
    log_id: int
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retry_count: int = 0
    max_retries: int = 3
    agent_state: dict[str, Any] | None = None
    error_stack: str | None = None


class TaskQueueManager:
    """ARQ 任务队列管理器.

    提供任务提交、状态查询、取消和重试功能。
    """

    def __init__(self, redis_settings: RedisSettings | None = None):
        """初始化任务队列管理器.

        Args:
            redis_settings: Redis 连接配置，默认使用 localhost:6379
        """
        self.redis_settings = redis_settings or RedisSettings(
            host="localhost",
            port=6379,
            database=0,
        )
        self._redis: ArqRedis | None = None
        self._task_metadata: dict[str, TaskMetadata] = {}

    async def connect(self) -> None:
        """连接到 Redis."""
        self._redis = await ArqRedis(self.redis_settings)
        logger.info("task_queue_connected", settings=self.redis_settings)

    async def disconnect(self) -> None:
        """断开 Redis 连接."""
        if self._redis:
            await self._redis.close()
            logger.info("task_queue_disconnected")

    async def submit_task(
        self,
        task_id: str,
        log_id: int,
        request_data: dict,
        priority: TaskPriority = TaskPriority.NORMAL,
        delay_seconds: int = 0,
    ) -> Job:
        """提交生成任务到队列.

        Args:
            task_id: 任务唯一标识
            log_id: 生成日志 ID
            request_data: 请求数据（序列化后的 GenerationRequest）
            priority: 任务优先级
            delay_seconds: 延迟执行时间（秒）

        Returns:
            ARQ Job 对象
        """
        if not self._redis:
            await self.connect()

        # 创建任务元数据
        metadata = TaskMetadata(
            task_id=task_id,
            log_id=log_id,
            priority=priority,
            created_at=datetime.now(),
            max_retries=3,
        )
        self._task_metadata[task_id] = metadata

        # 准备任务参数
        task_args = {
            "task_id": task_id,
            "log_id": log_id,
            "request_data": request_data,
            "metadata": metadata.model_dump(mode="json"),
        }

        # 根据优先级选择队列
        queue_name = self._get_queue_name(priority)

        # 提交任务
        job = await self._redis.enqueue_job(
            "run_generation_pipeline",
            **task_args,
            queue_name=queue_name,
            job_timeout=timedelta(seconds=3600),  # 1 小时超时
            job_try_limit=metadata.max_retries,
        )

        logger.info(
            "task_submitted",
            task_id=task_id,
            log_id=log_id,
            priority=priority.value,
            queue=queue_name,
            job_id=job.job_id,
        )

        return job

    def _get_queue_name(self, priority: TaskPriority) -> str:
        """根据优先级获取队列名称."""
        if priority >= TaskPriority.CRITICAL:
            return "critical"
        elif priority >= TaskPriority.HIGH:
            return "high"
        elif priority >= TaskPriority.NORMAL:
            return "default"
        else:
            return "low"

    async def get_task_status(self, task_id: str) -> dict:
        """获取任务状态.

        Args:
            task_id: 任务 ID

        Returns:
            包含状态、进度和错误信息的字典
        """
        if not self._redis:
            await self.connect()

        job = Job(task_id, redis=self._redis)
        info = await job.info()

        metadata = self._task_metadata.get(task_id)

        status_map = {
            "queued": TaskStatus.QUEUED,
            "complete": TaskStatus.COMPLETED,
            "failed": TaskStatus.FAILED,
        }

        current_status = status_map.get(info.result_type, TaskStatus.RUNNING)

        result = {
            "task_id": task_id,
            "status": current_status.value,
            "progress_pct": 0.0,
            "agent_state": metadata.agent_state if metadata else None,
            "error_stack": metadata.error_stack if metadata else None,
            "retry_count": metadata.retry_count if metadata else 0,
        }

        # 如果任务已完成，获取结果
        if info.result_type == "complete" and info.result:
            try:
                result_data = json.loads(info.result)
                result["result"] = result_data
                result["progress_pct"] = 100.0
            except (json.JSONDecodeError, TypeError):
                result["result"] = info.result

        # 如果任务失败，获取错误信息
        if info.result_type == "failed" and info.result:
            result["error_stack"] = str(info.result)
            if metadata:
                metadata.error_stack = str(info.result)

        return result

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务.

        Args:
            task_id: 任务 ID

        Returns:
            是否成功取消
        """
        if not self._redis:
            await self.connect()

        job = Job(task_id, redis=self._redis)
        cancelled = await job.abort(timeout=5)

        if cancelled:
            if task_id in self._task_metadata:
                self._task_metadata[task_id].agent_state = {"status": "cancelled"}
            logger.info("task_cancelled", task_id=task_id)

        return cancelled

    async def retry_task(self, task_id: str) -> bool:
        """重试失败的任务.

        Args:
            task_id: 任务 ID

        Returns:
            是否成功提交重试
        """
        if not self._redis:
            await self.connect()

        metadata = self._task_metadata.get(task_id)
        if not metadata:
            logger.warning("task_metadata_not_found", task_id=task_id)
            return False

        if metadata.retry_count >= metadata.max_retries:
            logger.warning(
                "task_max_retries_exceeded",
                task_id=task_id,
                retry_count=metadata.retry_count,
            )
            return False

        metadata.retry_count += 1
        metadata.started_at = None
        metadata.completed_at = None
        metadata.error_stack = None

        # 重新提交任务
        job = await self._redis.enqueue_job(
            "run_generation_pipeline",
            task_id=task_id,
            log_id=metadata.log_id,
            request_data={},  # 需要从其他地方获取原始请求
            metadata=metadata.model_dump(mode="json"),
            job_try_limit=metadata.max_retries - metadata.retry_count,
        )

        logger.info(
            "task_retried",
            task_id=task_id,
            retry_count=metadata.retry_count,
            job_id=job.job_id,
        )

        return True

    def update_agent_state(self, task_id: str, agent_state: dict) -> None:
        """更新 Agent 状态（用于错误追踪）.

        Args:
            task_id: 任务 ID
            agent_state: Agent 当前状态
        """
        if task_id in self._task_metadata:
            self._task_metadata[task_id].agent_state = agent_state

    def record_error(self, task_id: str, error: Exception) -> None:
        """记录错误堆栈.

        Args:
            task_id: 任务 ID
            error: 异常对象
        """
        if task_id in self._task_metadata:
            self._task_metadata[task_id].error_stack = traceback.format_exc()
            logger.error(
                "task_error_recorded",
                task_id=task_id,
                error=str(error),
                stack=self._task_metadata[task_id].error_stack,
            )


# ARQ Worker 设置
async def run_generation_pipeline(
    ctx: dict,
    task_id: str,
    log_id: int,
    request_data: dict,
    metadata: dict,
) -> dict:
    """ARQ 工作器执行的生成管线函数.

    这是实际在后台进程中运行的任务，与 FastAPI 主进程完全解耦。

    Args:
        ctx: ARQ 上下文（包含 Redis 连接等）
        task_id: 任务 ID
        log_id: 生成日志 ID
        request_data: 序列化的 GenerationRequest
        metadata: 任务元数据

    Returns:
        生成结果
    """
    from app.db.session import async_session_factory
    from app.schemas.generation import GenerationRequest
    from app.services.generation_service import GenerationService
    from app.tasks.websocket_manager import WebSocketManager

    logger.info(
        "arq_task_started",
        task_id=task_id,
        log_id=log_id,
        worker_id=ctx.get("worker_name", "unknown"),
    )

    ws_manager = WebSocketManager()
    await ws_manager.connect_redis(ctx["redis"])

    try:
        # 反序列化请求
        request = GenerationRequest(**request_data)

        async with async_session_factory() as session:
            service = GenerationService(session)

            # 定义进度回调
            async def progress_callback(
                log_id: int,
                status: str,
                step: str,
                pct: float,
                detail: dict | None = None,
            ) -> None:
                """推送进度到 WebSocket."""
                # 更新 Redis 中的任务状态
                await ctx["redis"].hset(
                    f"task:{task_id}",
                    mapping={
                        "status": status,
                        "step": step,
                        "progress": pct,
                        "detail": json.dumps(detail) if detail else "",
                    },
                )

                # 推送 WebSocket 消息
                await ws_manager.broadcast_progress(log_id, status, step, pct, detail)

            # 执行生成管线
            result = await service.generate_paper(
                log_id=log_id,
                request=request,
                progress_callback=progress_callback,
            )

            logger.info(
                "arq_task_completed",
                task_id=task_id,
                log_id=log_id,
                has_error="error" in result,
            )

            return result

    except Exception as e:
        error_stack = traceback.format_exc()
        logger.error(
            "arq_task_failed",
            task_id=task_id,
            log_id=log_id,
            error=str(e),
            stack=error_stack,
        )

        # 推送错误到 WebSocket
        await ws_manager.broadcast_error(
            log_id,
            str(e),
            error_stack,
        )

        # 抛出异常让 ARQ 处理重试
        raise


# ARQ Worker 配置
class WorkerSettings:
    """ARQ Worker 配置类."""

    functions = [run_generation_pipeline]
    redis_settings = RedisSettings(host="localhost", port=6379, database=0)
    job_timeout = timedelta(seconds=3600)
    job_try_limit = 3
    retry_jobs = True
    burst = False
    listen_queues = ["critical", "high", "default", "low"]

    # 钩子函数
    async def on_start_job(self, **kwargs) -> None:
        """任务开始前的钩子."""
        logger.debug("arq_job_starting", job_id=kwargs.get("job_id"))

    async def on_end_job(self, **kwargs) -> None:
        """任务结束后的钩子."""
        logger.debug("arq_job_ended", job_id=kwargs.get("job_id"))
