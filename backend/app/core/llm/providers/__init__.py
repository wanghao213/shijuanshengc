"""
Core LLM Provider Infrastructure.

This package implements the Strategy Pattern for LLM providers,
supporting both Cloud APIs and Local GPU-accelerated deployments.
"""

from .base import BaseLLMProvider, LLMMessage, LLMResponse
from .openai_provider import OpenAIProvider
from .ollama_provider import OllamaProvider

__all__ = [
    "BaseLLMProvider", 
    "LLMMessage", 
    "LLMResponse",
    "OpenAIProvider",
    "OllamaProvider"
]
