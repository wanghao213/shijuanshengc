"""
Domain Infrastructure: LLM Provider Strategies.

This module defines the abstraction for Large Language Model providers,
allowing seamless switching between Cloud APIs (OpenAI, Claude) and 
Local GPU-accelerated models (vLLM, Ollama) via the Strategy Pattern.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Optional, Dict, Any
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class LLMMessage(BaseModel):
    """Standardized message structure for LLM interactions."""
    role: str
    content: str
    # Optional metadata for tool calls or specific model parameters
    metadata: Optional[Dict[str, Any]] = None


class LLMResponse(BaseModel):
    """Standardized response wrapper."""
    content: str
    model: str
    usage: Dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    finish_reason: Optional[str] = None


class BaseLLMProvider(ABC):
    """
    Abstract Base Class for LLM Providers.
    
    Implements the Strategy interface for interacting with different 
    LLM backends. All implementations must adhere to this contract.
    """

    def __init__(self, model_name: str, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.model_name = model_name
        self.base_url = base_url
        self.api_key = api_key
        self._validate_config()

    @abstractmethod
    def _validate_config(self) -> None:
        """Validate provider-specific configuration."""
        pass

    @abstractmethod
    async def generate_completion(
        self, 
        messages: List[LLMMessage], 
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a single completion response.
        
        Args:
            messages: List of conversation messages.
            temperature: Sampling temperature.
            max_tokens: Max tokens to generate.
            **kwargs: Provider-specific extra arguments.
            
        Returns:
            LLMResponse object containing the generated text and metadata.
        """
        pass

    @abstractmethod
    async def generate_stream(
        self, 
        messages: List[LLMMessage], 
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream a completion response token by token.
        
        Useful for real-time UI updates during long generation tasks.
        """
        pass

    async def generate_with_retry(
        self, 
        messages: List[LLMMessage], 
        retries: int = 3, 
        **kwargs
    ) -> LLMResponse:
        """
        Wrapper with built-in retry logic for transient failures.
        
        Implements exponential backoff strategy to handle rate limits
        and temporary network issues gracefully.
        """
        import asyncio
        
        last_exception = None
        for attempt in range(retries):
            try:
                return await self.generate_completion(messages, **kwargs)
            except Exception as e:
                last_exception = e
                logger.warning(f"LLM Generation failed (attempt {attempt + 1}/{retries}): {str(e)}")
                if attempt < retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    await asyncio.sleep(wait_time)
        
        raise RuntimeError(f"LLM Generation failed after {retries} attempts") from last_exception
