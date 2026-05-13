"""弹性 LLM 客户端测试 - 验证重试、熔断和降级机制."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import LLMError
from app.core.llm_gateway import LLMResponse
from app.core.resilience import (
    ResilientLLMClient,
    CircuitBreaker,
    CircuitBreakerConfig,
    RetryConfig,
    CircuitState,
    LRUCache,
)


class TestLRUCache:
    """LRU 缓存测试."""

    def test_cache_put_get(self):
        """测试基本存取."""
        cache = LRUCache(max_size=3)
        
        response = LLMResponse(
            content="test",
            model="test-model",
            input_tokens=10,
            output_tokens=5,
            cost_usd=0.001,
            latency_ms=100,
        )
        
        cache.put("key1", response)
        result = cache.get("key1")
        
        assert result is not None
        assert result.content == "test"
        # 检查缓存条目中的 hits (通过访问内部 cache dict)
        entry = cache.cache["key1"]
        assert entry.hits == 1

    def test_cache_lru_eviction(self):
        """测试 LRU 淘汰策略."""
        cache = LRUCache(max_size=2)
        
        responses = [
            LLMResponse(content=f"content{i}", model="test", input_tokens=10,
                       output_tokens=5, cost_usd=0.001, latency_ms=100)
            for i in range(3)
        ]
        
        cache.put("key1", responses[0])
        cache.put("key2", responses[1])
        cache.put("key3", responses[2])  # 应该淘汰 key1
        
        assert cache.get("key1") is None
        assert cache.get("key2") is not None
        assert cache.get("key3") is not None

    def test_cache_access_updates_order(self):
        """测试访问更新顺序."""
        cache = LRUCache(max_size=2)
        
        responses = [
            LLMResponse(content=f"content{i}", model="test", input_tokens=10,
                       output_tokens=5, cost_usd=0.001, latency_ms=100)
            for i in range(3)
        ]
        
        cache.put("key1", responses[0])
        cache.put("key2", responses[1])
        cache.get("key1")  # 访问 key1，使其变为最近使用
        cache.put("key3", responses[2])  # 应该淘汰 key2
        
        assert cache.get("key1") is not None
        assert cache.get("key2") is None
        assert cache.get("key3") is not None


class TestCircuitBreaker:
    """熔断器测试."""

    @pytest.mark.asyncio
    async def test_circuit_closed_normal_operation(self):
        """测试正常操作下熔断器保持关闭."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(config)
        
        async def success_func():
            return "success"
        
        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self):
        """测试失败达到阈值后熔断器打开."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(config)
        
        async def failing_func():
            raise LLMError("Test error")
        
        # 连续失败 3 次
        for _ in range(3):
            with pytest.raises(LLMError):
                await breaker.call(failing_func)
        
        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 3

    @pytest.mark.asyncio
    async def test_circuit_rejects_when_open(self):
        """测试熔断器打开时拒绝请求."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=60)
        breaker = CircuitBreaker(config)
        
        async def failing_func():
            raise LLMError("Test error")
        
        # 触发熔断
        for _ in range(2):
            with pytest.raises(LLMError):
                await breaker.call(failing_func)
        
        assert breaker.state == CircuitState.OPEN
        
        # 尝试调用应该被拒绝
        async def success_func():
            return "success"
        
        with pytest.raises(LLMError, match="熔断器开启"):
            await breaker.call(success_func)

    @pytest.mark.asyncio
    async def test_circuit_half_open_after_timeout(self):
        """测试超时后进入半开状态."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.1  # 100ms 快速测试
        )
        breaker = CircuitBreaker(config)
        
        async def failing_func():
            raise LLMError("Test error")
        
        # 触发熔断
        for _ in range(2):
            with pytest.raises(LLMError):
                await breaker.call(failing_func)
        
        assert breaker.state == CircuitState.OPEN
        
        # 等待恢复时间
        await asyncio.sleep(0.15)
        
        # 下次请求应该允许 (进入半开状态)
        async def success_func():
            return "success"
        
        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED  # 成功后关闭

    @pytest.mark.asyncio
    async def test_circuit_reopens_on_half_open_failure(self):
        """测试半开状态失败后重新打开."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.1
        )
        breaker = CircuitBreaker(config)
        
        async def failing_func():
            raise LLMError("Test error")
        
        # 触发熔断
        for _ in range(2):
            with pytest.raises(LLMError):
                await breaker.call(failing_func)
        
        await asyncio.sleep(0.15)
        
        # 半开状态失败
        with pytest.raises(LLMError):
            await breaker.call(failing_func)
        
        assert breaker.state == CircuitState.OPEN


class TestResilientLLMClient:
    """弹性 LLM 客户端测试."""

    @pytest.fixture
    def mock_llm_response(self):
        """模拟 LLM 响应."""
        return LLMResponse(
            content="Test response",
            model="test-model",
            input_tokens=10,
            output_tokens=5,
            cost_usd=0.001,
            latency_ms=100,
        )

    @pytest.mark.asyncio
    async def test_client_success_no_retry(self, mock_llm_response):
        """测试成功调用无需重试."""
        client = ResilientLLMClient()
        
        messages = [{"role": "user", "content": "Hello"}]
        
        with patch('app.core.resilience.llm_chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_llm_response
            
            response = await client.chat(messages, model="test-model")
            
            assert response.content == "Test response"
            mock_chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_client_retry_on_failure(self, mock_llm_response):
        """测试失败时自动重试."""
        client = ResilientLLMClient(
            retry_config=RetryConfig(max_retries=2, base_delay=0.01)
        )
        
        messages = [{"role": "user", "content": "Hello"}]
        
        with patch('app.core.resilience.llm_chat', new_callable=AsyncMock) as mock_chat:
            # 前两次失败，第三次成功
            mock_chat.side_effect = [
                LLMError("First failure"),
                LLMError("Second failure"),
                mock_llm_response,
            ]
            
            response = await client.chat(messages, model="test-model")
            
            assert response.content == "Test response"
            assert mock_chat.call_count == 3

    @pytest.mark.asyncio
    async def test_client_fallback_on_exhausted_retries(self, mock_llm_response):
        """测试重试耗尽后切换到备用模型."""
        client = ResilientLLMClient(
            retry_config=RetryConfig(max_retries=1, base_delay=0.01),
            fallback_models=["fallback-model-1", "fallback-model-2"]
        )
        
        messages = [{"role": "user", "content": "Hello"}]
        
        call_sequence = [
            LLMError("Primary failed"),  # 主模型第一次调用失败
            LLMError("Primary failed after retry"),  # 主模型重试失败
            mock_llm_response,  # 备用模型成功
        ]
        
        with patch('app.core.resilience.llm_chat', new_callable=AsyncMock) as mock_chat:
            # 主模型失败，备用模型 1 成功
            mock_chat.side_effect = call_sequence
            
            response = await client.chat(messages, model="primary-model")
            
            assert response.content == "Test response"
            # 验证调用了 3 次：主模型 2 次 (含重试) + 备用模型 1 次
            assert mock_chat.call_count == 3
            # 验证最后一次调用了备用模型
            calls = [call[1]['model'] for call in mock_chat.call_args_list]
            assert "fallback-model-1" in calls

    @pytest.mark.asyncio
    async def test_client_cache_hit(self, mock_llm_response):
        """测试缓存命中."""
        client = ResilientLLMClient(cache_enabled=True)
        
        messages = [{"role": "user", "content": "Hello"}]
        
        with patch('app.core.resilience.llm_chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_llm_response
            
            # 第一次调用
            await client.chat(messages, model="test-model")
            assert mock_chat.call_count == 1
            
            # 第二次调用应该命中缓存
            await client.chat(messages, model="test-model")
            assert mock_chat.call_count == 1  # 没有新的调用

    @pytest.mark.asyncio
    async def test_client_circuit_breaker_integration(self, mock_llm_response):
        """测试熔断器集成."""
        client = ResilientLLMClient(
            circuit_config=CircuitBreakerConfig(failure_threshold=2),
            retry_config=RetryConfig(max_retries=0),  # 禁用重试以便快速触发熔断
        )
        
        messages = [{"role": "user", "content": "Hello"}]
        
        with patch('app.core.resilience.llm_chat', new_callable=AsyncMock) as mock_chat:
            # 连续失败触发熔断
            mock_chat.side_effect = LLMError("Service unavailable")
            
            # 第一次失败
            with pytest.raises(LLMError):
                await client.chat(messages, model="test-model")
            
            # 第二次失败
            with pytest.raises(LLMError):
                await client.chat(messages, model="test-model")
            
            # 熔断后应该快速失败
            with pytest.raises(LLMError, match="熔断器开启"):
                await client.chat(messages, model="test-model")

    @pytest.mark.asyncio
    async def test_client_status(self, mock_llm_response):
        """测试状态查询."""
        client = ResilientLLMClient(
            fallback_models=["fallback-1"],
            cache_enabled=True,
        )
        
        status = client.get_status()
        
        assert status["circuit_state"] == "CLOSED"
        assert status["fallback_models"] == ["fallback-1"]
        assert status["cache_size"] == 0

    @pytest.mark.asyncio
    async def test_client_reset(self, mock_llm_response):
        """测试重置功能."""
        client = ResilientLLMClient(
            circuit_config=CircuitBreakerConfig(failure_threshold=2),
            retry_config=RetryConfig(max_retries=0),
        )
        
        messages = [{"role": "user", "content": "Hello"}]
        
        with patch('app.core.resilience.llm_chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.side_effect = LLMError("Error")
            
            # 触发熔断
            for _ in range(2):
                with pytest.raises(LLMError):
                    await client.chat(messages, model="test-model")
            
            assert client.circuit_breaker.state == CircuitState.OPEN
            
            # 重置
            client.reset()
            
            assert client.circuit_breaker.state == CircuitState.CLOSED
            assert client.circuit_breaker.failure_count == 0


class TestIntegrationScenarios:
    """集成场景测试."""

    @pytest.mark.asyncio
    async def test_realistic_failure_recovery(self):
        """测试真实故障恢复场景 - 无备用模型情况下熔断器工作正常."""
        mock_response = LLMResponse(
            content="Recovered response",
            model="recovered-model",
            input_tokens=10,
            output_tokens=5,
            cost_usd=0.001,
            latency_ms=100,
        )
        
        # 不配置备用模型，以便测试熔断器本身的行为
        client = ResilientLLMClient(
            circuit_config=CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=0.2
            ),
            retry_config=RetryConfig(max_retries=0, base_delay=0.01),  # 禁用重试以便快速触发熔断
            fallback_models=[],  # 无备用模型
        )
        
        messages = [{"role": "user", "content": "Test"}]
        
        with patch('app.core.resilience.llm_chat', new_callable=AsyncMock) as mock_chat:
            # 场景：主模型暂时不可用，然后恢复
            call_count = 0
            
            async def dynamic_response(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                
                if call_count <= 3:  # 前 3 次失败触发熔断
                    raise LLMError("Service temporarily unavailable")
                # 第 4 次及以后成功（模拟恢复）
                return mock_response
            
            mock_chat.side_effect = dynamic_response
            
            # 前 3 次会失败并触发熔断
            for i in range(3):
                with pytest.raises(LLMError):
                    await client.chat(messages, model="primary")
            
            # 验证熔断器已打开
            assert client.circuit_breaker.state == CircuitState.OPEN
            
            # 等待恢复时间，让熔断器进入半开状态
            await asyncio.sleep(0.25)
            
            # 恢复后应该成功 (半开状态测试请求通过后关闭熔断器)
            response = await client.chat(messages, model="primary")
            assert response.content == "Recovered response"
            
            # 验证熔断器已关闭
            assert client.circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_fallback_model_on_primary_failure(self):
        """测试备用模型降级策略."""
        mock_response = LLMResponse(
            content="Fallback response",
            model="backup-model",
            input_tokens=10,
            output_tokens=5,
            cost_usd=0.001,
            latency_ms=100,
        )
        
        client = ResilientLLMClient(
            circuit_config=CircuitBreakerConfig(failure_threshold=2),
            retry_config=RetryConfig(max_retries=0, base_delay=0.01),
            fallback_models=["backup-model"],
        )
        
        messages = [{"role": "user", "content": "Test"}]
        
        with patch('app.core.resilience.llm_chat', new_callable=AsyncMock) as mock_chat:
            # 主模型失败，但备用模型成功
            # 注意：当有备用模型时，主模型失败后会尝试备用模型
            # 所以第一次调用就会触发备用模型并成功返回
            mock_chat.side_effect = [
                LLMError("Primary failed"),  # 主模型第一次失败
                mock_response,  # 备用模型成功
            ]
            
            # 第一次调用：主模型失败后切换到备用模型并成功
            response = await client.chat(messages, model="primary")
            assert response.content == "Fallback response"
            assert response.model == "backup-model"
            
            # 验证已调用 2 次：主模型 1 次 + 备用模型 1 次
            assert mock_chat.call_count == 2
