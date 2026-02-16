"""Groq provider implementation."""

from typing import Any

from pydantic import BaseModel

from ml_tooling.llm._env import get_env_var
from ml_tooling.llm.providers.base import LLMProviderProtocol


class GroqProvider(LLMProviderProtocol):
    """Groq provider implementation.

    Handles Groq-specific logic:
    - API key management
    - Structured output format (json_object mode)
    - Model identifier normalization
    """

    def __init__(self):
        self._initialized = False
        self._api_key: str | None = None

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def supported_models(self) -> list[str]:
        return [
            "groq/llama3-8b-8192",
            "groq/llama3-70b-8192",
        ]

    @property
    def api_key(self) -> str:
        if self._api_key is None:
            raise RuntimeError(
                "GroqProvider has not been initialized with an API key. "
                "Call initialize() before making LiteLLM requests."
            )
        return self._api_key

    def initialize(self, api_key: str | None = None) -> None:
        if api_key is None:
            api_key = get_env_var("GROQ_API_KEY", required=True)
        if not self._initialized:
            self._api_key = api_key
            self._initialized = True

    def supports_model(self, model_name: str) -> bool:
        return model_name in self.supported_models

    def format_structured_output(
        self,
        response_model: type[BaseModel],
        model_config: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Format Groq's structured output format."""
        raise NotImplementedError(
            "We'll revisit this later when actively working with Groq models."
        )

    def prepare_completion_kwargs(
        self,
        model: str,
        messages: list[dict],
        response_format: dict[str, Any] | None,
        model_config: dict[str, Any],
        **kwargs,
    ) -> dict[str, Any]:
        """Prepare Groq-specific completion kwargs."""
        raise NotImplementedError(
            "We'll revisit this later when actively working with Groq models."
        )
