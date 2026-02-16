"""Registry for LLM providers."""

from typing import Type

from ml_tooling.llm.providers.base import LLMProviderProtocol
from ml_tooling.llm.providers.gemini_provider import GeminiProvider
from ml_tooling.llm.providers.groq_provider import GroqProvider
from ml_tooling.llm.providers.openai_provider import OpenAIProvider


class LLMProviderRegistry:
    """Registry for LLM providers."""

    _providers: dict[str, Type[LLMProviderProtocol]] = {}
    _instances: dict[str, LLMProviderProtocol] = {}

    @classmethod
    def register(cls, provider_class: Type[LLMProviderProtocol]) -> None:
        """Register a provider class."""
        provider_instance = provider_class()
        provider_name = provider_instance.provider_name
        cls._providers[provider_name] = provider_class
        cls._instances[provider_name] = provider_instance

    @classmethod
    def get_provider(cls, model: str) -> LLMProviderProtocol:
        """Get provider for a given model.

        Args:
            model: Model identifier (e.g., 'gpt-4o-mini', 'groq/llama3-8b-8192')

        Returns:
            Provider instance that supports the given model

        Raises:
            ValueError: If no provider supports the given model
        """
        for _, provider_instance in cls._instances.items():
            # assumes only one provider supports a given model
            # (which makes sense).
            if provider_instance.supports_model(model):
                return provider_instance
        raise ValueError(f"No provider found for model {model}")

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered providers."""
        return list(cls._providers.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear all registered providers."""
        cls._providers.clear()
        cls._instances.clear()


# Auto-register default providers on import
# NOTE: choosing to do this here instead of __init__ so that we can use the
# classmethods while assuming that the providers are already imported.
LLMProviderRegistry.register(OpenAIProvider)
LLMProviderRegistry.register(GroqProvider)
LLMProviderRegistry.register(GeminiProvider)
