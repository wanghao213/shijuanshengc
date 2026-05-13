"""LiteLLM 封装的统一 LLM 调用入口.

所有 AI 调用必须通过此模块，禁止直接调用 anthropic/openai SDK。

支持:
- vLLM 本地部署 (PageAttention KV Cache 优化)
- AWQ 4-bit 量化模型 (Qwen/DeepSeek 等)
- LiteLLM 统一协议转换
- WSL 容器网络桥接配置
- OpenAI 接口格式对齐
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

# vLLM 配置 (用于本地 8GB 显存设备如 RTX 4060)
VLLM_CONFIG = {
    "max_model_len": 4096,  # 上下文长度限制
    "gpu_memory_utilization": 0.85,  # 显存利用率 (8GB * 0.85 ≈ 6.8GB)
    "tensor_parallel_size": 1,  # 单卡
    "block_size": 16,  # PageAttention block size
    "swap_space": 4,  # CPU swap space (GB)
}

# AWQ 量化模型映射 (4-bit 量化，大幅降低显存占用)
AWQ_MODEL_MAP = {
    "qwen-7b-awq": "huggingface/BAAI/Qwen-7B-AWQ",
    "qwen-14b-awq": "huggingface/BAAI/Qwen-14B-AWQ",
    "deepseek-coder-6.7b-awq": "huggingface/TheBloke/deepseek-coder-6.7B-base-AWQ",
    "mistral-7b-awq": "huggingface/TheBloke/Mistral-7B-Instruct-v0.2-AWQ",
}

# 本地模型端点配置 (WSL 网络桥接)
LOCAL_MODEL_ENDPOINTS = {
    "vllm": "http://localhost:8000/v1",  # vLLM 默认端口
    "ollama": "http://localhost:11434",
    "lmstudio": "http://localhost:1234/v1",
}


@dataclass
class LLMResponse:
    """LLM 响应."""

    content: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    model_type: str = "cloud"  # cloud | vllm | ollama | lmstudio
    quantization: str | None = None  # awq-4bit | gptq-4bit | none


def _estimate_cost(model: str, input_tokens: int, output_tokens: int, model_type: str = "cloud") -> float:
    """估算调用成本（简化版，实际应查 LiteLLM 的 cost 表）.
    
    Args:
        model: 模型名称
        input_tokens: 输入 token 数
        output_tokens: 输出 token 数
        model_type: 模型类型 (cloud|vllm|ollama|lmstudio)
    
    Returns:
        成本 (USD)，本地模型返回 0.0
    """
    # 本地部署模型无 API 成本
    if model_type != "cloud":
        return 0.0
    
    if "claude" in model.lower():
        return (input_tokens * 3 + output_tokens * 15) / 1_000_000
    if "deepseek" in model.lower():
        return (input_tokens * 0.14 + output_tokens * 0.28) / 1_000_000
    if "gpt-4" in model.lower():
        return (input_tokens * 10 + output_tokens * 30) / 1_000_000
    if "gpt-3.5" in model.lower():
        return (input_tokens * 0.5 + output_tokens * 1.5) / 1_000_000
    return 0.0


def _detect_model_type(model: str) -> tuple[str, str | None]:
    """检测模型类型和量化格式.
    
    Args:
        model: 模型名称或路径
        
    Returns:
        (model_type, quantization)
        - model_type: cloud | vllm | ollama | lmstudio
        - quantization: awq-4bit | gptq-4bit | none
    """
    model_lower = model.lower()
    
    # 检查 AWQ 量化
    if "awq" in model_lower or "4bit" in model_lower:
        if any(name in model_lower for name in ["qwen", "deepseek", "mistral", "llama"]):
            return "vllm", "awq-4bit"
    
    # 检查 GPTQ 量化
    if "gptq" in model_lower:
        return "vllm", "gptq-4bit"
    
    # 检查 Ollama
    if "ollama" in model_lower or model.startswith("ollama/"):
        return "ollama", None
    
    # 检查 LM Studio
    if "lmstudio" in model_lower:
        return "lmstudio", None
    
    # 检查 vLLM (通过模型路径判断)
    if "huggingface" in model_lower or model_lower.startswith("/"):
        return "vllm", None
    
    # 默认为云服务
    if any(cloud in model_lower for cloud in ["gpt-", "claude", "gemini"]):
        return "cloud", None
    
    return "cloud", None


def _configure_litellm_for_local(model: str) -> dict:
    """配置 LiteLLM 以支持本地模型部署.
    
    Args:
        model: 模型名称
        
    Returns:
        LiteLLM 配置字典
    """
    model_type, quantization = _detect_model_type(model)
    
    config = {
        "model": model,
        "api_base": None,
        "api_key": "not-needed",  # 本地模型通常不需要 API key
    }
    
    if model_type == "vllm":
        config["api_base"] = LOCAL_MODEL_ENDPOINTS["vllm"]
        # vLLM 使用 OpenAI 兼容接口
        config["model"] = model.split("/")[-1] if "/" in model else model
    elif model_type == "ollama":
        config["api_base"] = LOCAL_MODEL_ENDPOINTS["ollama"]
        config["model"] = model.replace("ollama/", "")
    elif model_type == "lmstudio":
        config["api_base"] = LOCAL_MODEL_ENDPOINTS["lmstudio"]
    
    return config


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
    
    支持模型类型:
        - 云服务：gpt-4, claude-3, gemini 等
        - vLLM 本地部署：huggingface/Qwen-7B-AWQ, /models/qwen-14b-awq
        - Ollama: ollama/qwen2.5, ollama/deepseek-coder
        - LM Studio: lmstudio/local-model
    """
    model = model or settings.default_chat_model
    start = time.perf_counter()

    # 检测模型类型并配置 LiteLLM
    model_type, quantization = _detect_model_type(model)
    litellm_config = _configure_litellm_for_local(model)
    
    kwargs = {
        "model": litellm_config["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
    }
    
    # 添加 API base 和 key (本地模型需要)
    if litellm_config["api_base"]:
        kwargs["api_base"] = litellm_config["api_base"]
    if litellm_config["api_key"]:
        kwargs["api_key"] = litellm_config["api_key"]
    
    if response_format:
        kwargs["response_format"] = response_format
    if tools:
        kwargs["tools"] = tools

    if stream:
        return _stream_chat(kwargs, model, model_type, quantization, session, generation_log_id, start)

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
    cost_usd = _estimate_cost(model, input_tokens, output_tokens, model_type)

    logger.info(
        "llm_chat",
        model=model,
        model_type=model_type,
        quantization=quantization,
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
        model_type=model_type,
        quantization=quantization,
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
