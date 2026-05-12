"""
OpenAI-Compatible LLM Provider.

Supports OpenAI API, Azure OpenAI, and any OpenAI-compatible endpoints
including local deployments like vLLM with OpenAI-compatible server.
"""

from typing import AsyncIterator, List, Optional, Dict, Any
import logging

from .base import BaseLLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI API Provider implementation.
    
    Handles communication with OpenAI's API or compatible endpoints.
    Supports streaming, function calling, and comprehensive error handling.
    """

    def __init__(
        self, 
        model_name: str = "gpt-4o", 
        base_url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        super().__init__(model_name=model_name, base_url=base_url, api_key=api_key)
        self._client = None

    def _validate_config(self) -> None:
        """Validate OpenAI-specific configuration."""
        if not self.api_key:
            logger.warning("OpenAI API key not provided. Set OPENAI_API_KEY env var.")
        
        # Lazy validation - client will be created on first use
        pass

    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url  # Can be None for official API
                )
            except ImportError:
                raise ImportError("openai package required. Install with: pip install openai")
        return self._client

    async def generate_completion(
        self, 
        messages: List[LLMMessage], 
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate completion using OpenAI API.
        
        Args:
            messages: Conversation history.
            temperature: Sampling temperature (0.0 to 2.0).
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional OpenAI-specific parameters.
            
        Returns:
            LLMResponse with generated content and usage stats.
        """
        client = self._get_client()
        
        # Convert our standard messages to OpenAI format
        openai_messages = [
            {"role": msg.role, "content": msg.content} 
            for msg in messages
        ]
        
        try:
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            choice = response.choices[0]
            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                finish_reason=choice.finish_reason
            )
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise

    async def generate_stream(
        self, 
        messages: List[LLMMessage], 
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream completion token by token.
        
        Yields:
            String chunks of the generated response.
        """
        client = self._get_client()
        
        openai_messages = [
            {"role": msg.role, "content": msg.content} 
            for msg in messages
        ]
        
        stream = await client.chat.completions.create(
            model=self.model_name,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
