"""OpenAI provider implementation."""

import copy
from typing import Any

from pydantic import BaseModel

from ml_tooling.llm._env import get_env_var
from ml_tooling.llm.providers.base import LLMProviderProtocol


class OpenAIProvider(LLMProviderProtocol):
    """OpenAI provider implementation.

    Handles OpenAI-specific logic:
    - API key management
    - Structured output schema formatting (additionalProperties: false requirement)
    - Model identifier normalization
    """

    def __init__(self):
        self._initialized = False
        self._api_key: str | None = None

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def supported_models(self) -> list[str]:
        return [
            "gpt-4o-mini",
            "gpt-4o-mini-2024-07-18",
            "gpt-4",
            "gpt-5-nano",
        ]

    @property
    def api_key(self) -> str:
        if self._api_key is None:
            raise RuntimeError(
                "OpenAIProvider has not been initialized with an API key. "
                "Call initialize() before making LiteLLM requests."
            )
        return self._api_key

    def initialize(self, api_key: str | None = None) -> None:
        if api_key is None:
            api_key = get_env_var("OPENAI_API_KEY", required=True)
        if not self._initialized:
            self._api_key = api_key
            self._initialized = True

    def supports_model(self, model_name: str) -> bool:
        return model_name in self.supported_models

    def format_structured_output(
        self,
        response_model: type[BaseModel],
        model_config: dict[str, Any],
    ) -> dict[str, Any]:
        """Format OpenAI's structured output format.

        OpenAI requires:
        - type: "json_schema"
        - strict: True
        - schema with additionalProperties: false on all objects
        """
        schema = response_model.model_json_schema()
        fixed_schema = self._fix_schema_for_openai(schema)

        return {
            "type": "json_schema",
            "json_schema": {
                "name": response_model.__name__.lower(),
                "strict": True,
                "schema": fixed_schema,
            },
        }

    def prepare_completion_kwargs(
        self,
        model: str,
        messages: list[dict],
        response_format: dict[str, Any] | None,
        model_config: dict[str, Any],
        **kwargs,
    ) -> dict[str, Any]:
        """Prepare OpenAI-specific completion kwargs."""
        if not self._initialized:
            self.initialize()

        # Merge model_config defaults with user kwargs (user kwargs take precedence)
        merged_kwargs = {**model_config.get("kwargs", {}), **kwargs}

        completion_kwargs = {
            "model": model,
            "messages": messages,
            **merged_kwargs,
        }

        if response_format is not None:
            completion_kwargs["response_format"] = response_format

        return completion_kwargs

    def _fix_schema_for_openai(self, schema: dict) -> dict:
        """Recursively add additionalProperties: false to all object definitions.

        This is OpenAI's strict requirement for structured outputs.
        """
        schema_copy = copy.deepcopy(schema)
        self._patch_recursive(schema_copy)
        return schema_copy

    def _patch_recursive(self, obj) -> None:
        """Recursively patch schema, handling dicts and lists."""
        if isinstance(obj, dict):
            if obj.get("type") == "object":
                obj["additionalProperties"] = False
            for value in obj.values():
                self._patch_recursive(value)
        elif isinstance(obj, list):
            for item in obj:
                self._patch_recursive(item)
