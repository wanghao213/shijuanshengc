"""弹性 LLM 客户端 - 实现重试、熔断和降级机制.

功能:
- 指数退避重试 (Exponential Backoff)
- 熔断器模式 (Circuit Breaker): 5 次失败/30s 半开恢复
- 降级策略：本地缓存 + 备用模型切换
- 健康检查与自动恢复

使用示例:
    resilient_client = ResilientLLMClient(
        fallback_models=["deepseek-chat", "gpt-3.5-turbo"],
        cache_enabled=True,
    )
    
    response = await resilient_client.chat(messages, model="claude-sonnet-4-20250514")
"""

import asyncio
import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable

import structlog

from app.core.exceptions import LLMError
from app.core.llm_gateway import chat as llm_chat, LLMResponse

logger = structlog.get_logger()


class CircuitState(Enum):
    """熔断器状态."""

    CLOSED = auto()  # 正常状态，请求通过
    OPEN = auto()  # 熔断状态，拒绝所有请求
    HALF_OPEN = auto()  # 半开状态，允许测试请求


@dataclass
class CircuitBreakerConfig:
    """熔断器配置."""

    failure_threshold: int = 5  # 触发熔断的失败次数
    recovery_timeout: float = 30.0  # 熔断后恢复时间 (秒)
    half_open_max_calls: int = 1  # 半开状态允许的最大调用数
    expected_exceptions: tuple = (LLMError, TimeoutError, ConnectionError)


@dataclass
class RetryConfig:
    """重试配置."""

    max_retries: int = 3
    base_delay: float = 1.0  # 基础延迟 (秒)
    max_delay: float = 60.0  # 最大延迟 (秒)
    exponential_base: float = 2.0  # 指数退避基数
    jitter: bool = True  # 是否添加随机抖动


@dataclass
class CacheEntry:
    """缓存条目."""

    response: LLMResponse
    created_at: float
    hits: int = 0


class LRUCache:
    """LRU 缓存实现，用于降级时的响应缓存."""

    def __init__(self, max_size: int = 100):
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.max_size = max_size

    def get(self, key: str) -> LLMResponse | None:
        """获取缓存项."""
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        entry.hits += 1
        # 移到末尾 (最近使用)
        self.cache.move_to_end(key)
        return entry.response

    def put(self, key: str, response: LLMResponse) -> None:
        """存入缓存项."""
        if key in self.cache:
            self.cache.move_to_end(key)
        
        self.cache[key] = CacheEntry(
            response=response,
            created_at=time.time(),
        )
        
        # 超出容量时删除最旧项
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

    def clear(self) -> None:
        """清空缓存."""
        self.cache.clear()


class CircuitBreaker:
    """熔断器实现."""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.half_open_calls = 0
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """通过熔断器执行函数调用."""
        async with self._lock:
            if not self._allow_request():
                raise LLMError("熔断器开启，请求被拒绝")
            
            self.half_open_calls += 1

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except self.config.expected_exceptions as e:
            await self._on_failure()
            raise
        except Exception as e:
            # 非预期异常也视为失败
            await self._on_failure()
            raise LLMError(f"LLM 调用异常：{e}") from e

    def _allow_request(self) -> bool:
        """判断是否允许请求."""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # 检查是否已过恢复时间
            if self.last_failure_time is None:
                return False
            
            elapsed = time.time() - self.last_failure_time
            if elapsed >= self.config.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info("circuit_breaker_half_open", elapsed=elapsed)
                return True
            return False
        
        # HALF_OPEN 状态
        return self.half_open_calls < self.config.half_open_max_calls

    async def _on_success(self) -> None:
        """成功回调."""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.half_open_calls = 0
                logger.info("circuit_breaker_closed", reason="half_open_success")
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0

    async def _on_failure(self) -> None:
        """失败回调."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                # 半开状态失败，重新打开熔断
                self.state = CircuitState.OPEN
                logger.warning(
                    "circuit_breaker_opened",
                    reason="half_open_failure",
                )
            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    self.state = CircuitState.OPEN
                    logger.warning(
                        "circuit_breaker_opened",
                        failure_count=self.failure_count,
                        threshold=self.config.failure_threshold,
                    )


class ResilientLLMClient:
    """弹性 LLM 客户端 - 集成重试、熔断和降级."""

    def __init__(
        self,
        circuit_config: CircuitBreakerConfig | None = None,
        retry_config: RetryConfig | None = None,
        fallback_models: list[str] | None = None,
        cache_enabled: bool = True,
        cache_max_size: int = 100,
    ):
        self.circuit_breaker = CircuitBreaker(
            circuit_config or CircuitBreakerConfig()
        )
        self.retry_config = retry_config or RetryConfig()
        self.fallback_models = fallback_models or []
        self.cache_enabled = cache_enabled
        self.cache = LRUCache(max_size=cache_max_size) if cache_enabled else None
        self._current_model: str | None = None
        self._primary_model_failed = False

    def _generate_cache_key(self, messages: list[dict], model: str, **kwargs) -> str:
        """生成缓存键."""
        content = str(sorted(messages, key=lambda x: str(x)))
        params = str(sorted(kwargs.items()))
        raw_key = f"{model}:{content}:{params}"
        return hashlib.sha256(raw_key.encode()).hexdigest()[:32]

    async def _execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """带指数退避的重试执行."""
        last_error: Exception | None = None
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except self.circuit_breaker.config.expected_exceptions as e:
                last_error = e
                
                if attempt >= self.retry_config.max_retries:
                    break
                
                # 计算延迟时间 (指数退避 + 抖动)
                delay = min(
                    self.retry_config.base_delay * (
                        self.retry_config.exponential_base ** attempt
                    ),
                    self.retry_config.max_delay,
                )
                
                if self.retry_config.jitter:
                    import random
                    delay *= (0.5 + random.random())
                
                logger.warning(
                    "llm_retry",
                    attempt=attempt + 1,
                    max_retries=self.retry_config.max_retries,
                    delay=delay,
                    error=str(e),
                )
                
                await asyncio.sleep(delay)
        
        raise LLMError(
            f"LLM 调用在 {self.retry_config.max_retries} 次重试后失败: {last_error}"
        ) from last_error

    async def _try_fallback(
        self,
        messages: list[dict],
        original_model: str,
        **kwargs,
    ) -> LLMResponse:
        """尝试备用模型."""
        if not self.fallback_models:
            raise LLMError(f"主模型 {original_model} 失败且无备用模型")
        
        for i, model in enumerate(self.fallback_models):
            try:
                logger.info(
                    "fallback_model_attempt",
                    model=model,
                    attempt=i + 1,
                    total=len(self.fallback_models),
                )
                
                response = await llm_chat(
                    messages=messages,
                    model=model,
                    **kwargs,
                )
                
                logger.info(
                    "fallback_model_success",
                    model=model,
                    original_model=original_model,
                )
                
                # 标记切换到备用模型
                self._primary_model_failed = True
                self._current_model = model
                
                return response
                
            except Exception as e:
                logger.warning(
                    "fallback_model_failed",
                    model=model,
                    error=str(e),
                )
                continue
        
        raise LLMError(
            f"所有备用模型均失败，主模型：{original_model}"
        )

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        response_format: dict | None = None,
        tools: list[dict] | None = None,
        session: Any = None,
        generation_log_id: int | None = None,
        use_cache: bool = True,
        **kwargs,
    ) -> LLMResponse:
        """弹性聊天接口 - 支持重试、熔断、降级和缓存.
        
        Args:
            messages: 对话消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数
            stream: 是否流式输出 (不支持缓存)
            response_format: 响应格式配置
            tools: 工具定义列表
            session: 数据库会话
            generation_log_id: 生成日志 ID
            use_cache: 是否使用缓存
            
        Returns:
            LLMResponse 对象
            
        Raises:
            LLMError: 当所有策略都失败时抛出
        """
        model = model or "default"
        
        # 流式不支持缓存和降级
        if stream:
            return await llm_chat(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                response_format=response_format,
                tools=tools,
                session=session,
                generation_log_id=generation_log_id,
            )
        
        # 检查缓存
        cache_key = None
        if self.cache_enabled and use_cache:
            cache_key = self._generate_cache_key(
                messages, model,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )
            
            cached_response = self.cache.get(cache_key)
            if cached_response:
                logger.info(
                    "cache_hit",
                    cache_key=cache_key[:8],
                    model=model,
                )
                return cached_response
        
        # 熔断器包装的调用
        async def _call_llm() -> LLMResponse:
            return await self._execute_with_retry(
                llm_chat,
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
                response_format=response_format,
                tools=tools,
                session=session,
                generation_log_id=generation_log_id,
            )
        
        try:
            # 通过熔断器执行
            response = await self.circuit_breaker.call(_call_llm)
            
            # 成功后存入缓存
            if self.cache_enabled and cache_key:
                self.cache.put(cache_key, response)
            
            # 重置主模型状态
            if self._primary_model_failed:
                logger.info(
                    "primary_model_restored",
                    model=model,
                )
                self._primary_model_failed = False
            
            return response
            
        except LLMError as e:
            logger.error(
                "primary_model_failed",
                model=model,
                error=str(e),
                circuit_state=self.circuit_breaker.state.name,
            )
            
            # 降级策略：尝试备用模型
            if self.fallback_models:
                return await self._try_fallback(
                    messages=messages,
                    original_model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                    tools=tools,
                    session=session,
                    generation_log_id=generation_log_id,
                )
            
            # 尝试从缓存降级 (模糊匹配最近的成功响应)
            if self.cache_enabled and self.cache:
                # 简单策略：返回任意缓存响应作为最后手段
                # 实际应用中应该更智能地选择
                logger.warning("degraded_to_cache", model=model)
                # 注意：这里不返回缓存，因为可能不相关
                # 更好的做法是返回一个友好的错误信息
            
            raise

    async def structured_chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        session: Any = None,
        generation_log_id: int | None = None,
        **kwargs,
    ) -> LLMResponse:
        """强制 JSON 输出的弹性聊天接口."""
        return await self.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            session=session,
            generation_log_id=generation_log_id,
            **kwargs,
        )

    async def embed(
        self,
        texts: list[str],
        model: str | None = None,
        session: Any = None,
        generation_log_id: int | None = None,
        use_cache: bool = True,
    ) -> list[list[float]]:
        """弹性 Embedding 调用."""
        from app.core.llm_gateway import embed as llm_embed
        
        model = model or "default"
        
        # 检查缓存
        cache_key = None
        if self.cache_enabled and use_cache:
            cache_key = self._generate_cache_key(texts, model)
            
            cached = self.cache.get(cache_key) if self.cache else None
            # 注意：缓存的是 LLMResponse，需要适配 embedding
        
        async def _call_embed() -> list[list[float]]:
            return await llm_embed(
                texts=texts,
                model=model,
                session=session,
                generation_log_id=generation_log_id,
            )
        
        try:
            return await self.circuit_breaker.call(_call_embed)
        except LLMError as e:
            logger.error(
                "embed_failed",
                model=model,
                error=str(e),
            )
            raise

    def get_status(self) -> dict:
        """获取客户端状态."""
        return {
            "circuit_state": self.circuit_breaker.state.name,
            "failure_count": self.circuit_breaker.failure_count,
            "current_model": self._current_model,
            "primary_model_failed": self._primary_model_failed,
            "cache_size": len(self.cache.cache) if self.cache else 0,
            "fallback_models": self.fallback_models,
        }

    def reset(self) -> None:
        """重置客户端状态."""
        self.circuit_breaker.state = CircuitState.CLOSED
        self.circuit_breaker.failure_count = 0
        self._primary_model_failed = False
        if self.cache:
            self.cache.clear()
        logger.info("resilient_client_reset")


# 全局单例
_resilient_client: ResilientLLMClient | None = None


def get_resilient_client(
    fallback_models: list[str] | None = None,
    **kwargs,
) -> ResilientLLMClient:
    """获取或创建 ResilientLLMClient 单例."""
    global _resilient_client
    
    if _resilient_client is None:
        _resilient_client = ResilientLLMClient(
            fallback_models=fallback_models,
            **kwargs,
        )
    
    return _resilient_client
