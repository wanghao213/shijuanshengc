"""LLM Gateway 测试."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.llm_gateway import (
    LLMResponse,
    _estimate_cost,
    chat,
    embed,
    structured_chat,
)


def test_estimate_cost_claude():
    """测试 Claude 模型成本估算."""
    cost = _estimate_cost("claude-sonnet-4-20250514", 1000, 500)
    expected = (1000 * 3 + 500 * 15) / 1_000_000
    assert cost == pytest.approx(expected)


def test_estimate_cost_deepseek():
    """测试 DeepSeek 模型成本估算."""
    cost = _estimate_cost("deepseek-chat", 1000, 500)
    expected = (1000 * 0.14 + 500 * 0.28) / 1_000_000
    assert cost == pytest.approx(expected)


def test_estimate_cost_gpt4():
    """测试 GPT-4 模型成本估算."""
    cost = _estimate_cost("gpt-4", 1000, 500)
    expected = (1000 * 10 + 500 * 30) / 1_000_000
    assert cost == pytest.approx(expected)


def test_estimate_cost_unknown():
    """测试未知模型成本估算."""
    cost = _estimate_cost("unknown-model", 1000, 500)
    assert cost == 0.0


@pytest.mark.asyncio
@patch("app.core.llm_gateway.litellm.acompletion")
async def test_chat_success(mock_acompletion):
    """测试成功的 chat 调用."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello, world!"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_acompletion.return_value = mock_response

    response = await chat(
        messages=[{"role": "user", "content": "Hello"}],
        model="test-model",
    )

    assert isinstance(response, LLMResponse)
    assert response.content == "Hello, world!"
    assert response.model == "test-model"
    assert response.input_tokens == 100
    assert response.output_tokens == 50
    assert response.latency_ms >= 0
    mock_acompletion.assert_called_once()


@pytest.mark.asyncio
@patch("app.core.llm_gateway.litellm.acompletion")
async def test_chat_failure(mock_acompletion):
    """测试 chat 调用失败."""
    mock_acompletion.side_effect = Exception("API Error")

    with pytest.raises(Exception, match="API Error"):
        await chat(
            messages=[{"role": "user", "content": "Hello"}],
            model="test-model",
        )


@pytest.mark.asyncio
@patch("app.core.llm_gateway.litellm.aembedding")
async def test_embed_success(mock_aembedding):
    """测试成功的 embed 调用."""
    mock_response = MagicMock()
    mock_response.data = [{"embedding": [0.1, 0.2, 0.3]}]
    mock_aembedding.return_value = mock_response

    result = await embed(texts=["test text"], model="test-embedding-model")

    assert len(result) == 1
    assert result[0] == [0.1, 0.2, 0.3]
    mock_aembedding.assert_called_once()


@pytest.mark.asyncio
@patch("app.core.llm_gateway.litellm.aembedding")
async def test_embed_multiple(mock_aembedding):
    """测试批量 embed 调用."""
    mock_response = MagicMock()
    mock_response.data = [
        {"embedding": [0.1, 0.2]},
        {"embedding": [0.3, 0.4]},
    ]
    mock_aembedding.return_value = mock_response

    result = await embed(texts=["text1", "text2"], model="test-model")

    assert len(result) == 2
    assert result[0] == [0.1, 0.2]
    assert result[1] == [0.3, 0.4]


@pytest.mark.asyncio
@patch("app.core.llm_gateway.litellm.acompletion")
async def test_structured_chat(mock_acompletion):
    """测试 structured_chat 调用."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"key": "value"}'
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 50
    mock_response.usage.completion_tokens = 20
    mock_acompletion.return_value = mock_response

    response = await structured_chat(
        messages=[{"role": "user", "content": "Return JSON"}],
        model="test-model",
    )

    assert isinstance(response, LLMResponse)
    assert response.content == '{"key": "value"}'
    # 验证传入了 response_format
    call_kwargs = mock_acompletion.call_args[1]
    assert call_kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
@patch("app.core.llm_gateway.litellm.acompletion")
async def test_chat_with_tools(mock_acompletion):
    """测试带 tools 参数的 chat 调用."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "I'll use the tool"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_acompletion.return_value = mock_response

    tools = [{"type": "function", "function": {"name": "search", "description": "Search"}}]
    response = await chat(
        messages=[{"role": "user", "content": "Search for something"}],
        model="test-model",
        tools=tools,
    )

    assert isinstance(response, LLMResponse)
    call_kwargs = mock_acompletion.call_args[1]
    assert call_kwargs["tools"] == tools


@pytest.mark.asyncio
@patch("app.core.llm_gateway.litellm.acompletion")
async def test_chat_records_usage(mock_acompletion):
    """测试 chat 调用记录 AIUsageLog."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Response"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_acompletion.return_value = mock_response

    mock_session = AsyncMock()

    await chat(
        messages=[{"role": "user", "content": "Hello"}],
        model="test-model",
        session=mock_session,
    )

    # 验证 session.add 被调用（记录 AIUsageLog）
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()
