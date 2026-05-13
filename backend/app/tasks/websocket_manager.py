"""WebSocket 管理器 - 高可用长连接设计.

实现健壮的心跳检测（Ping/Pong）、断线缓冲堆积重传机制，
确保在复杂网络环境下稳定推送生成进度。
"""

import asyncio
import json
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog
from fastapi import WebSocket, WebSocketDisconnect

logger = structlog.get_logger()


@dataclass
class BufferedMessage:
    """缓冲的消息."""

    message: str
    timestamp: float
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class ClientConnection:
    """客户端连接信息."""

    websocket: WebSocket
    log_id: int
    connected_at: float
    last_pong: float
    heartbeat_interval: float = 15.0  # 15 秒心跳间隔
    message_buffer: deque[BufferedMessage] = field(default_factory=lambda: deque(maxlen=100))
    is_alive: bool = True


class WebSocketManager:
    """高可用 WebSocket 管理器.

    功能：
    - 心跳检测（Ping/Pong）
    - 断线缓冲与重传
    - 多客户端广播
    - Redis 集成（用于多进程/多实例场景）
    """

    def __init__(self):
        """初始化 WebSocket 管理器."""
        self._connections: dict[int, list[ClientConnection]] = {}
        self._redis = None
        self._heartbeat_tasks: dict[int, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def connect_redis(self, redis_client) -> None:
        """连接到 Redis（用于多实例同步）.

        Args:
            redis_client: ARQ Redis 客户端
        """
        self._redis = redis_client
        logger.info("websocket_redis_connected")

    async def register_connection(self, log_id: int, websocket: WebSocket) -> None:
        """注册 WebSocket 连接.

        Args:
            log_id: 生成日志 ID
            websocket: WebSocket 连接对象
        """
        async with self._lock:
            now = time.time()
            connection = ClientConnection(
                websocket=websocket,
                log_id=log_id,
                connected_at=now,
                last_pong=now,
            )

            if log_id not in self._connections:
                self._connections[log_id] = []

            self._connections[log_id].append(connection)

            # 启动心跳检测任务
            heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(connection)
            )
            self._heartbeat_tasks[id(websocket)] = heartbeat_task

            logger.info(
                "websocket_registered",
                log_id=log_id,
                connection_id=id(websocket),
            )

    async def unregister_connection(self, log_id: int, websocket: WebSocket) -> None:
        """注销 WebSocket 连接.

        Args:
            log_id: 生成日志 ID
            websocket: WebSocket 连接对象
        """
        async with self._lock:
            connections = self._connections.get(log_id, [])
            connection_to_remove = None

            for conn in connections:
                if conn.websocket == websocket:
                    connection_to_remove = conn
                    break

            if connection_to_remove:
                connections.remove(connection_to_remove)

                # 取消心跳任务
                heartbeat_task = self._heartbeat_tasks.pop(id(websocket), None)
                if heartbeat_task:
                    heartbeat_task.cancel()
                    try:
                        await heartbeat_task
                    except asyncio.CancelledError:
                        pass

                # 清理空列表
                if not connections:
                    del self._connections[log_id]

                logger.info(
                    "websocket_unregistered",
                    log_id=log_id,
                    connection_id=id(websocket),
                )

    async def _heartbeat_loop(self, connection: ClientConnection) -> None:
        """心跳检测循环.

        定期发送 Ping 并等待 Pong，超时则标记为断开。
        """
        while connection.is_alive:
            try:
                await asyncio.sleep(connection.heartbeat_interval)

                if not connection.is_alive:
                    break

                # 检查上次 Pong 的时间
                now = time.time()
                time_since_pong = now - connection.last_pong

                if time_since_pong > connection.heartbeat_interval * 2:
                    logger.warning(
                        "websocket_heartbeat_timeout",
                        log_id=connection.log_id,
                        time_since_pong=time_since_pong,
                    )
                    connection.is_alive = False
                    await self._handle_disconnect(connection)
                    break

                # 发送 Ping
                try:
                    await connection.websocket.send_json({
                        "type": "ping",
                        "timestamp": datetime.now().isoformat(),
                    })
                except Exception as e:
                    logger.warning(
                        "websocket_ping_failed",
                        log_id=connection.log_id,
                        error=str(e),
                    )
                    connection.is_alive = False
                    await self._handle_disconnect(connection)
                    break

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "websocket_heartbeat_error",
                    log_id=connection.log_id,
                    error=str(e),
                )
                connection.is_alive = False
                await self._handle_disconnect(connection)
                break

    async def handle_pong(self, log_id: int, websocket: WebSocket) -> None:
        """处理 Pong 响应.

        Args:
            log_id: 生成日志 ID
            websocket: WebSocket 连接对象
        """
        async with self._lock:
            connections = self._connections.get(log_id, [])
            for conn in connections:
                if conn.websocket == websocket:
                    conn.last_pong = time.time()
                    break

    async def _handle_disconnect(self, connection: ClientConnection) -> None:
        """处理断线事件.

        尝试重传缓冲的消息，然后关闭连接。
        """
        log_id = connection.log_id
        websocket = connection.websocket

        logger.warning(
            "websocket_disconnected",
            log_id=log_id,
            buffer_size=len(connection.message_buffer),
        )

        # 尝试重传缓冲消息
        if connection.message_buffer:
            await self._replay_buffered_messages(connection)

        # 从注册表中移除
        await self.unregister_connection(log_id, websocket)

        # 尝试关闭 WebSocket
        try:
            await websocket.close(code=1001, reason="heartbeat_timeout")
        except Exception:
            pass

    async def _replay_buffered_messages(self, connection: ClientConnection) -> None:
        """重传缓冲的消息.

        Args:
            connection: 客户端连接
        """
        while connection.message_buffer:
            buffered = connection.message_buffer.popleft()

            if buffered.retry_count >= buffered.max_retries:
                logger.warning(
                    "message_max_retries_exceeded",
                    log_id=connection.log_id,
                    message=buffered.message[:100],
                )
                continue

            try:
                await connection.websocket.send_text(buffered.message)
            except Exception as e:
                buffered.retry_count += 1
                connection.message_buffer.appendleft(buffered)
                logger.warning(
                    "message_replay_failed",
                    log_id=connection.log_id,
                    retry_count=buffered.retry_count,
                    error=str(e),
                )
                break

    async def broadcast_progress(
        self,
        log_id: int,
        status: str,
        step: str,
        pct: float,
        detail: dict | None = None,
    ) -> None:
        """广播进度到所有连接的客户端.

        Args:
            log_id: 生成日志 ID
            status: 状态
            step: 当前步骤
            pct: 进度百分比
            detail: 详细信息
        """
        from app.schemas.generation import GenerationWsMessage

        message = GenerationWsMessage(
            task_id=str(log_id),
            status=status,
            current_step=step,
            progress_pct=pct,
            detail=detail,
            timestamp=datetime.now(),
        )
        data = message.model_dump_json()

        async with self._lock:
            connections = self._connections.get(log_id, [])

            if not connections:
                # 没有连接的客户端，缓冲消息
                if self._redis:
                    # 存储到 Redis 以便后续重放
                    await self._redis.lpush(
                        f"ws:buffer:{log_id}",
                        data,
                    )
                    # 限制缓冲大小
                    await self._redis.ltrim(f"ws:buffer:{log_id}", 0, 99)
                return

            disconnected = []

            for conn in connections:
                try:
                    await conn.websocket.send_text(data)
                    # 发送成功，更新 Pong 时间
                    conn.last_pong = time.time()
                except WebSocketDisconnect:
                    disconnected.append(conn)
                except Exception as e:
                    logger.warning(
                        "broadcast_failed",
                        log_id=log_id,
                        connection_id=id(conn.websocket),
                        error=str(e),
                    )
                    # 加入缓冲队列
                    conn.message_buffer.append(BufferedMessage(
                        message=data,
                        timestamp=time.time(),
                    ))
                    disconnected.append(conn)

            # 清理断开的连接
            for conn in disconnected:
                conn.is_alive = False
                await self.unregister_connection(log_id, conn.websocket)

    async def broadcast_error(
        self,
        log_id: int,
        error_message: str,
        error_stack: str | None = None,
    ) -> None:
        """广播错误信息到所有连接的客户端.

        Args:
            log_id: 生成日志 ID
            error_message: 错误消息
            error_stack: 错误堆栈（可选）
        """
        from app.schemas.generation import GenerationWsMessage

        message = GenerationWsMessage(
            task_id=str(log_id),
            status="failed",
            current_step="生成失败",
            progress_pct=0.0,
            detail={
                "error": error_message,
                "stack_trace": error_stack,
            },
            timestamp=datetime.now(),
        )
        data = message.model_dump_json()

        await self.broadcast_progress(
            log_id,
            "failed",
            "生成失败",
            0.0,
            {"error": error_message, "stack_trace": error_stack},
        )

    async def replay_buffered_messages(self, log_id: int, websocket: WebSocket) -> None:
        """重放 Redis 中缓冲的消息.

        当客户端重新连接时，回放之前错过的消息。

        Args:
            log_id: 生成日志 ID
            websocket: WebSocket 连接对象
        """
        if not self._redis:
            return

        try:
            buffered = await self._redis.lrange(f"ws:buffer:{log_id}", 0, -1)
            for msg in buffered:
                await websocket.send_text(msg.decode("utf-8"))
            logger.info(
                "buffered_messages_replayed",
                log_id=log_id,
                count=len(buffered),
            )
        except Exception as e:
            logger.error(
                "buffer_replay_failed",
                log_id=log_id,
                error=str(e),
            )

    def get_connection_count(self, log_id: int) -> int:
        """获取指定任务的连接数.

        Args:
            log_id: 生成日志 ID

        Returns:
            连接数
        """
        return len(self._connections.get(log_id, []))

    def get_all_connections(self) -> dict[int, int]:
        """获取所有任务的连接数统计.

        Returns:
            {log_id: connection_count} 字典
        """
        return {log_id: len(conns) for log_id, conns in self._connections.items()}


# 全局单例
_ws_manager: WebSocketManager | None = None


def get_websocket_manager() -> WebSocketManager:
    """获取 WebSocket 管理器单例."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager
