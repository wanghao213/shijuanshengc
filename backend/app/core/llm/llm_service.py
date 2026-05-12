"""
LLM Provider Factory and Service Registry.

Implements the Factory Pattern to create appropriate LLM provider instances
based on configuration, enabling seamless switching between cloud and local models.
"""

from typing import Optional, Dict, Type
import logging
from enum import Enum

from .providers.base import BaseLLMProvider
from .providers.openai_provider import OpenAIProvider
from .providers.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)


class LLMProviderType(str, Enum):
    """Enumeration of supported LLM provider types."""
    OPENAI = "openai"
    OLLAMA = "ollama"
    # Future providers can be added here
    # AZURE = "azure"
    # ANTHROPIC = "anthropic"
    # VLLM = "vllm"


class LLMProviderFactory:
    """
    Factory for creating LLM provider instances.
    
    Centralizes the logic for instantiating the correct provider
    based on configuration parameters. Follows the Factory Pattern
    to decouple client code from concrete provider implementations.
    
    Example:
        >>> factory = LLMProviderFactory()
        >>> provider = factory.create_provider(
        ...     provider_type=LLMProviderType.OLLAMA,
        ...     model_name="qwen2.5:7b",
        ...     base_url="http://localhost:11434"
        ... )
    """
    
    # Registry of provider classes
    _provider_registry: Dict[LLMProviderType, Type[BaseLLMProvider]] = {
        LLMProviderType.OPENAI: OpenAIProvider,
        LLMProviderType.OLLAMA: OllamaProvider,
    }
    
    @classmethod
    def register_provider(cls, provider_type: LLMProviderType, provider_class: Type[BaseLLMProvider]):
        """
        Register a new provider type dynamically.
        
        Allows extending the system with custom providers without
        modifying the factory code (Open/Closed Principle).
        """
        cls._provider_registry[provider_type] = provider_class
        logger.info(f"Registered provider: {provider_type.value} -> {provider_class.__name__}")
    
    def create_provider(
        self,
        provider_type: LLMProviderType,
        model_name: str,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ) -> BaseLLMProvider:
        """
        Create an LLM provider instance.
        
        Args:
            provider_type: The type of provider to create.
            model_name: The model identifier/name.
            base_url: Optional base URL for the API endpoint.
            api_key: Optional API key for authentication.
            **kwargs: Additional provider-specific arguments.
            
        Returns:
            Configured LLM provider instance.
            
        Raises:
            ValueError: If provider_type is not registered.
        """
        if provider_type not in self._provider_registry:
            available = ", ".join(pt.value for pt in self._provider_registry.keys())
            raise ValueError(
                f"Unknown provider type: {provider_type}. "
                f"Available providers: {available}"
            )
        
        provider_class = self._provider_registry[provider_type]
        logger.info(f"Creating {provider_type.value} provider for model: {model_name}")
        
        return provider_class(
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
            **kwargs
        )


class LLMService:
    """
    High-level LLM service facade.
    
    Provides a unified interface for LLM operations, abstracting away
    the underlying provider selection and management. This is the main
    entry point for application code to interact with LLMs.
    
    Features:
    - Automatic provider selection based on config
    - Provider pooling/caching for efficiency
    - Health checking and failover support (future)
    """
    
    def __init__(self):
        self._factory = LLMProviderFactory()
        self._providers: Dict[str, BaseLLMProvider] = {}
    
    def get_provider(
        self,
        provider_type: LLMProviderType,
        model_name: str,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> BaseLLMProvider:
        """
        Get or create a cached provider instance.
        
        Uses a cache key to reuse provider instances when possible,
        reducing initialization overhead.
        """
        cache_key = f"{provider_type.value}:{model_name}:{base_url}"
        
        if cache_key not in self._providers:
            self._providers[cache_key] = self._factory.create_provider(
                provider_type=provider_type,
                model_name=model_name,
                base_url=base_url,
                api_key=api_key,
            )
        
        return self._providers[cache_key]
    
    async def health_check(self, provider_type: LLMProviderType, model_name: str) -> bool:
        """
        Check if a provider/model combination is healthy.
        
        For local providers (Ollama), this verifies the server is running
        and the model is available. For cloud providers, it checks API connectivity.
        """
        try:
            provider = self.get_provider(provider_type, model_name)
            
            # Check if provider has health check method
            if hasattr(provider, 'check_health'):
                return await provider.check_health()
            
            # Default: assume healthy if we can instantiate it
            return True
        except Exception as e:
            logger.error(f"Health check failed for {provider_type.value}/{model_name}: {e}")
            return False
    
    def list_available_providers(self) -> list[str]:
        """List all registered provider types."""
        return [pt.value for pt in LLMProviderFactory._provider_registry.keys()]


# Singleton instance for global access
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get the global LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
