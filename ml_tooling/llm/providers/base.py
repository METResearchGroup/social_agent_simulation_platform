"""Base protocol for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class LLMProviderProtocol(ABC):
    """Protocol for LLM provider implementations.

    Each provider (OpenAI, Gemini, Groq, etc.) implements this interface
    to handle provider-specific logic: API key management, response formatting,
    structured output handling, retry logic, etc.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'openai', 'gemini', 'groq')."""
        ...

    @property
    @abstractmethod
    def supported_models(self) -> list[str]:
        """Return list of model identifiers this provider supports.

        Examples: ['gpt-4o-mini', 'gpt-4'] for OpenAI,
        ['gemini/gemini-1.5-pro-latest'] for Gemini.
        """
        ...

    @property
    @abstractmethod
    def api_key(self) -> str:
        """Return the API key for this provider instance.

        This is used to avoid mutating global LiteLLM state (e.g. litellm.api_key).
        Providers should store the key on the instance during initialize() and
        callers should pass api_key=provider.api_key on each LiteLLM call.
        """
        ...

    @abstractmethod
    def initialize(self, api_key: str | None = None) -> None:
        """Initialize the provider with the given API key.

        Args:
            api_key: The API key for the provider.
        """
        ...

    @abstractmethod
    def supports_model(self, model_name: str) -> bool:
        """Check if the provider supports the given model.

        Args:
            model_name: The name of the model to check.
        """
        ...

    @abstractmethod
    def format_structured_output(
        self,
        response_model: type[BaseModel],
        model_config: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Format response_format parameter for structured outputs.

        Different providers have different structured output formats:
        - OpenAI: json_schema with strict mode
        - Groq: json_object mode
        - Gemini: May not support structured outputs at all

        Args:
            response_model: Pydantic model class to parse response into
            model_config: Model-specific configuration from registry

        Returns:
            Provider-specific response_format dict, or None if provider
            doesn't support structured outputs for this model
        """
        ...

    @abstractmethod
    def prepare_completion_kwargs(
        self,
        model: str,
        messages: list[dict],
        response_format: dict[str, Any] | None,
        model_config: dict[str, Any],
        **kwargs,
    ) -> dict[str, Any]:
        """Prepare kwargs for litellm.completion call.

        Provider-specific parameter preparation (safety settings, API base URLs, etc.)

        Args:
            model: Model identifier
            messages: Chat messages
            response_format: Formatted response_format dict (from format_structured_output)
            model_config: Model-specific configuration
            **kwargs: Additional parameters passed by user

        Returns:
            Complete kwargs dict ready for litellm.completion
        """
        ...
