"""Gemini provider implementation."""

import os
from typing import Any

from pydantic import BaseModel

from ml_tooling.llm._env import get_env_var
from ml_tooling.llm.providers.base import LLMProviderProtocol

DEFAULT_GEMINI_SAFETY_SETTINGS = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE",
    },
]


class GeminiProvider(LLMProviderProtocol):
    """Gemini provider implementation.

    Handles Gemini-specific logic:
    - API key management (uses GOOGLE_AI_STUDIO_KEY -> GEMINI_API_KEY)
    - Safety settings configuration
    - Model identifier normalization
    """

    def __init__(self):
        self._initialized = False
        self._api_key: str | None = None

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def supported_models(self) -> list[str]:
        return [
            "gemini/gemini-1.0-pro-latest",
            "gemini/gemini-1.5-pro-latest",
        ]

    @property
    def api_key(self) -> str:
        if self._api_key is None:
            raise RuntimeError(
                "GeminiProvider has not been initialized with an API key. "
                "Call initialize() before making LiteLLM requests."
            )
        return self._api_key

    def initialize(self, api_key: str | None = None) -> None:
        if api_key is None:
            api_key = get_env_var("GOOGLE_AI_STUDIO_KEY", required=True)
        if not self._initialized:
            self._api_key = api_key
            os.environ["GEMINI_API_KEY"] = api_key  # type: ignore
            self._initialized = True

    def supports_model(self, model_name: str) -> bool:
        return model_name in self.supported_models

    def format_structured_output(
        self,
        response_model: type[BaseModel],
        model_config: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Format Gemini's structured output format."""
        raise NotImplementedError(
            "We'll revisit this later when actively working with Gemini models."
        )

    def prepare_completion_kwargs(
        self,
        model: str,
        messages: list[dict],
        response_format: dict[str, Any] | None,
        model_config: dict[str, Any],
        **kwargs,
    ) -> dict[str, Any]:
        """Prepare Gemini-specific completion kwargs."""
        if not self._initialized:
            self.initialize()

        # Merge model_config defaults with user kwargs (user kwargs take precedence)
        merged_kwargs = {**model_config.get("kwargs", {}), **kwargs}

        # Ensure safety_settings are included (default if not provided)
        if "safety_settings" not in merged_kwargs:
            merged_kwargs["safety_settings"] = DEFAULT_GEMINI_SAFETY_SETTINGS

        completion_kwargs = {
            "model": model,
            "messages": messages,
            **merged_kwargs,
        }

        return completion_kwargs
