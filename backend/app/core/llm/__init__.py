"""
Core LLM Module.

Unified interface for Large Language Model interactions,
supporting multiple providers via Strategy and Factory patterns.
"""

from .llm_service import LLMService, LLMProviderFactory, LLMProviderType, get_llm_service
from .gateway_adapter import LLMGatewayAdapter, get_gateway_adapter
from .providers import (
    BaseLLMProvider,
    LLMMessage,
    LLMResponse,
    OpenAIProvider,
    OllamaProvider,
)

__all__ = [
    # Service Layer
    "LLMService",
    "LLMProviderFactory", 
    "LLMProviderType",
    "get_llm_service",
    
    # Adapter for Legacy Compatibility
    "LLMGatewayAdapter",
    "get_gateway_adapter",
    
    # Provider Abstractions
    "BaseLLMProvider",
    "LLMMessage",
    "LLMResponse",
    
    # Concrete Providers
    "OpenAIProvider",
    "OllamaProvider",
]
