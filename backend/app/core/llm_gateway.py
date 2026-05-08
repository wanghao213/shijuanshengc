"""LiteLLM 封装的统一 LLM 调用入口.

所有 AI 调用必须通过此模块，禁止直接调用 anthropic/openai SDK。
"""

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

import litellm
import structlog

from app.config import settings
from app.core.exceptions import LLMError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

# 并发控制
_semaphore = asyncio.Semaphore(settings.litellm_max_concurrent)

# 重试配置
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # 秒


@dataclass
class LLMResponse:
    """LLM 响应."""

    content: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """估算调用成本（简化版，实际应查 LiteLLM 的 cost 表）."""
    if "claude" in model.lower():
        return (input_tokens * 3 + output_tokens * 15) / 1_000_000
    if "deepseek" in model.lower():
        return (input_tokens * 0.14 + output_tokens * 0.28) / 1_000_000
    if "gpt-4" in model.lower():
        return (input_tokens * 10 + output_tokens * 30) / 1_000_000
    if "gpt-3.5" in model.lower():
        return (input_tokens * 0.5 + output_tokens * 1.5) / 1_000_000
    return 0.0


async def _record_usage(
    session: "AsyncSession | None",
    model: str,
    operation: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    latency_ms: int,
    success: bool,
    error_detail: str | None = None,
    generation_log_id: int | None = None,
) -> None:
    """记录 AI 调用到 AIUsageLog 表."""
    if session is None:
        return
    try:
        from app.models.generation_log import AIUsageLog

        log = AIUsageLog(
            generation_log_id=generation_log_id,
            model=model,
            operation=operation,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            success=success,
            error_detail=error_detail,
        )
        session.add(log)
        await session.flush()
    except Exception as e:
        logger.warning("usage_log_failed", error=str(e))


async def _retry_with_backoff(coro_func, *args, **kwargs):
    """指数退避重试，最多 MAX_RETRIES 次."""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            return await coro_func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "llm_retry",
                    attempt=attempt + 1,
                    delay=delay,
                    error=str(e),
                )
                await asyncio.sleep(delay)
    raise LLMError(f"LLM 调用在 {MAX_RETRIES} 次重试后仍然失败: {last_error}") from last_error


async def chat(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    stream: bool = False,
    response_format: dict | None = None,
    tools: list[dict] | None = None,
    session: "AsyncSession | None" = None,
    generation_log_id: int | None = None,
) -> LLMResponse | AsyncIterator[str]:
    """统一的 LLM 对话调用.

    Args:
        session: 可选的数据库会话，用于记录 AIUsageLog
        generation_log_id: 可选的生成日志 ID
        stream: 是否流式输出
        tools: 工具定义列表（function calling）

    Returns:
        LLMResponse 或 AsyncIterator[str]（流式时）
    """
    model = model or settings.default_chat_model
    start = time.perf_counter()

    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
    }
    if response_format:
        kwargs["response_format"] = response_format
    if tools:
        kwargs["tools"] = tools

    if stream:
        return _stream_chat(kwargs, model, session, generation_log_id, start)

    async with _semaphore:
        try:
            response = await _retry_with_backoff(litellm.acompletion, **kwargs)
        except LLMError:
            raise
        except Exception as e:
            latency_ms = int((time.perf_counter() - start) * 1000)
            await _record_usage(
                session, model, "chat", 0, 0, 0.0, latency_ms,
                False, str(e), generation_log_id,
            )
            logger.error("llm_chat_error", model=model, error=str(e))
            raise LLMError(f"LLM 调用失败: {e}") from e

    latency_ms = int((time.perf_counter() - start) * 1000)
    usage = response.usage
    input_tokens = usage.prompt_tokens if usage else 0
    output_tokens = usage.completion_tokens if usage else 0
    cost_usd = _estimate_cost(model, input_tokens, output_tokens)

    logger.info(
        "llm_chat",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
    )

    await _record_usage(
        session, model, "chat", input_tokens, output_tokens,
        cost_usd, latency_ms, True, None, generation_log_id,
    )

    return LLMResponse(
        content=response.choices[0].message.content or "",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
    )


async def _stream_chat(
    kwargs: dict,
    model: str,
    session: "AsyncSession | None",
    generation_log_id: int | None,
    start: float,
) -> AsyncIterator[str]:
    """流式输出的内部实现."""
    kwargs["stream"] = True
    output_tokens = 0
    full_content = ""

    async with _semaphore:
        try:
            response = await _retry_with_backoff(litellm.acompletion, **kwargs)
        except LLMError:
            raise
        except Exception as e:
            logger.error("llm_stream_error", model=model, error=str(e))
            raise LLMError(f"LLM 流式调用失败: {e}") from e

        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                full_content += delta.content
                output_tokens += 1  # Approximate: 1 token per chunk
                yield delta.content

    latency_ms = int((time.perf_counter() - start) * 1000)
    estimated_input = sum(len(m.get("content", "")) // 4 for m in kwargs.get("messages", []))
    cost_usd = _estimate_cost(model, estimated_input, output_tokens)
    await _record_usage(
        session, model, "chat_stream", estimated_input, output_tokens,
        cost_usd, latency_ms, True, None, generation_log_id,
    )


async def embed(
    texts: list[str],
    model: str | None = None,
    session: "AsyncSession | None" = None,
    generation_log_id: int | None = None,
) -> list[list[float]]:
    """统一的 Embedding 调用."""
    model = model or settings.default_embedding_model
    start = time.perf_counter()

    async with _semaphore:
        try:
            response = await _retry_with_backoff(
                litellm.aembedding, model=model, input=texts,
            )
        except LLMError:
            raise
        except Exception as e:
            latency_ms = int((time.perf_counter() - start) * 1000)
            await _record_usage(
                session, model, "embed", 0, 0, 0.0, latency_ms,
                False, str(e), generation_log_id,
            )
            logger.error("llm_embed_error", model=model, error=str(e))
            raise LLMError(f"Embedding 调用失败: {e}") from e

    latency_ms = int((time.perf_counter() - start) * 1000)
    # embedding 调用通常不返回 token 使用量，估算
    estimated_tokens = sum(len(t) // 4 for t in texts)
    cost_usd = _estimate_cost(model, estimated_tokens, 0)

    await _record_usage(
        session, model, "embed", estimated_tokens, 0,
        cost_usd, latency_ms, True, None, generation_log_id,
    )

    return [item["embedding"] for item in response.data]


async def structured_chat(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    session: "AsyncSession | None" = None,
    generation_log_id: int | None = None,
) -> LLMResponse:
    """强制 JSON 输出的 LLM 调用."""
    return await chat(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        session=session,
        generation_log_id=generation_log_id,
    )
