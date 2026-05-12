"""
LLM Gateway Adapter for Legacy Compatibility.

This module provides a compatibility layer between the existing llm_gateway.py
and the new Provider-based architecture, ensuring backward compatibility
during the refactoring transition.
"""

from typing import AsyncIterator, List, Optional, Dict, Any
import logging

from .providers.base import BaseLLMProvider, LLMMessage, LLMResponse as ProviderLLMResponse
from .llm_service import get_llm_service, LLMProviderType

logger = logging.getLogger(__name__)


class LLMGatewayAdapter:
    """
    Adapter that wraps the new Provider architecture to match
    the legacy llm_gateway.py interface.
    
    This allows gradual migration - existing code can continue using
    the old interface while new code uses the Provider pattern directly.
    
    Example:
        >>> adapter = LLMGatewayAdapter()
        >>> response = await adapter.chat(
        ...     messages=[{"role": "user", "content": "Hello"}],
        ...     model="gpt-4o",
        ...     provider_type=LLMProviderType.OPENAI
        ... )
    """
    
    def __init__(self):
        self._service = get_llm_service()
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        response_format: Optional[Dict[str, str]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        provider_type: LLMProviderType = LLMProviderType.OPENAI,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> ProviderLLMResponse | AsyncIterator[str]:
        """
        Chat completion with legacy-compatible interface.
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            model: Model name/identifier.
            temperature: Sampling temperature.
            max_tokens: Max tokens to generate.
            stream: Whether to stream the response.
            response_format: Response format hint (e.g., {"type": "json_object"}).
            tools: Tool definitions for function calling.
            provider_type: Which provider to use.
            base_url: Optional custom base URL.
            api_key: Optional API key.
            
        Returns:
            LLMResponse or async iterator of strings (if streaming).
        """
        provider = self._service.get_provider(
            provider_type=provider_type,
            model_name=model,
            base_url=base_url,
            api_key=api_key,
        )
        
        # Convert dict messages to LLMMessage objects
        llm_messages = [
            LLMMessage(role=msg["role"], content=msg["content"])
            for msg in messages
        ]
        
        # Build kwargs for provider
        kwargs = {}
        if response_format:
            kwargs["response_format"] = response_format
        if tools:
            kwargs["tools"] = tools
        
        if stream:
            return self._stream_chat(provider, llm_messages, temperature, max_tokens, **kwargs)
        
        response = await provider.generate_with_retry(
            messages=llm_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        return response
    
    async def _stream_chat(
        self,
        provider: BaseLLMProvider,
        messages: List[LLMMessage],
        temperature: float,
        max_tokens: Optional[int],
        **kwargs
    ) -> AsyncIterator[str]:
        """Internal streaming implementation."""
        async for chunk in provider.generate_stream(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        ):
            yield chunk
    
    async def structured_chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o",
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        provider_type: LLMProviderType = LLMProviderType.OPENAI,
        **kwargs
    ) -> ProviderLLMResponse:
        """
        Chat with forced JSON output.
        
        Automatically sets response_format to JSON for structured outputs.
        """
        return await self.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            provider_type=provider_type,
            **kwargs
        )
    
    async def health_check(
        self, 
        provider_type: LLMProviderType, 
        model_name: str
    ) -> bool:
        """Check if a provider/model is healthy."""
        return await self._service.health_check(provider_type, model_name)
    
    def list_providers(self) -> List[str]:
        """List available provider types."""
        return self._service.list_available_providers()


# Singleton instance for convenience
_gateway_adapter: Optional[LLMGatewayAdapter] = None


def get_gateway_adapter() -> LLMGatewayAdapter:
    """Get the global gateway adapter singleton."""
    global _gateway_adapter
    if _gateway_adapter is None:
        _gateway_adapter = LLMGatewayAdapter()
    return _gateway_adapter
