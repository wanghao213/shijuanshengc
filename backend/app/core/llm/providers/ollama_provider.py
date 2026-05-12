"""
Ollama LLM Provider for Local GPU Deployments.

Optimized for WSL environments with GPU passthrough, supporting
local models like DeepSeek, Qwen, Llama3 via Ollama runtime.
"""

from typing import AsyncIterator, List, Optional
import logging
import httpx

from .base import BaseLLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """
    Ollama API Provider for local model deployments.
    
    Designed for WSL + GPU scenarios where models run locally
    via Ollama (ollama.ai). Supports streaming and custom parameters.
    """

    def __init__(
        self, 
        model_name: str = "qwen2.5:7b", 
        base_url: str = "http://localhost:11434",
        api_key: Optional[str] = None  # Ollama doesn't require API key by default
    ):
        super().__init__(model_name=model_name, base_url=base_url, api_key=api_key)
        self._http_client = None

    def _validate_config(self) -> None:
        """Validate Ollama-specific configuration."""
        if not self.base_url:
            self.base_url = "http://localhost:11434"
        
        logger.info(f"Ollama provider configured: {self.model_name} @ {self.base_url}")

    def _get_http_client(self) -> httpx.AsyncClient:
        """Lazy initialization of HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(120.0, connect=10.0)  # Longer timeout for local GPU
            )
        return self._http_client

    async def generate_completion(
        self, 
        messages: List[LLMMessage], 
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate completion using Ollama API.
        
        Args:
            messages: Conversation history.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional Ollama-specific parameters.
            
        Returns:
            LLMResponse with generated content.
        """
        client = self._get_http_client()
        
        # Convert messages to Ollama format
        ollama_messages = [
            {"role": msg.role, "content": msg.content} 
            for msg in messages
        ]
        
        payload = {
            "model": self.model_name,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens or 2048,
                **kwargs.get("options", {})
            }
        }
        
        try:
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            
            return LLMResponse(
                content=data["message"]["content"],
                model=self.model_name,
                usage={
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                },
                finish_reason="stop"
            )
            
        except httpx.HTTPError as e:
            logger.error(f"Ollama API error: {str(e)}")
            raise RuntimeError(f"Ollama request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error calling Ollama: {str(e)}")
            raise

    async def generate_stream(
        self, 
        messages: List[LLMMessage], 
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream completion from Ollama.
        
        Yields:
            String chunks of the generated response.
        """
        client = self._get_http_client()
        
        ollama_messages = [
            {"role": msg.role, "content": msg.content} 
            for msg in messages
        ]
        
        payload = {
            "model": self.model_name,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens or 2048,
                **kwargs.get("options", {})
            }
        }
        
        async with client.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    import json
                    chunk = json.loads(line)
                    if "message" in chunk and "content" in chunk["message"]:
                        yield chunk["message"]["content"]

    async def check_health(self) -> bool:
        """Check if Ollama server is running and model is available."""
        client = self._get_http_client()
        try:
            response = await client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            models = [m["name"] for m in data.get("models", [])]
            return self.model_name in models or any(self.model_name in m for m in models)
        except Exception:
            return False
