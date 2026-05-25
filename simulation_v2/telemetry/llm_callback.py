"""LangChain callback for local LLM latency and token metrics."""

from __future__ import annotations

import time
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult


class LlmMetricsCallbackHandler(BaseCallbackHandler):
    """Capture latency and token usage from LangChain LLM callbacks.

    Reads token counts from ``response.llm_output["token_usage"]`` when present,
    otherwise from ``response.generations[0][0].message.usage_metadata``.
    """

    def __init__(self) -> None:
        self._start_time: float | None = None
        self.latency_ms: float = 0.0
        self.prompt_tokens: int | None = None
        self.completion_tokens: int | None = None
        self.total_tokens: int | None = None
        self.cost_usd: float | None = None

    def on_llm_start(
        self,
        _serialized: dict[str, Any],
        _prompts: list[str],
        **_kwargs: Any,
    ) -> None:
        self._start_time = time.perf_counter()

    def on_llm_end(self, response: LLMResult, **_kwargs: Any) -> None:
        if self._start_time is not None:
            self.latency_ms = (time.perf_counter() - self._start_time) * 1000

        llm_output = response.llm_output or {}
        token_usage = llm_output.get("token_usage")
        if isinstance(token_usage, dict):
            self._apply_token_usage(token_usage)
            return

        for generation_group in response.generations:
            for generation in generation_group:
                message = getattr(generation, "message", None)
                usage_metadata = getattr(message, "usage_metadata", None)
                if isinstance(usage_metadata, dict):
                    self._apply_token_usage(usage_metadata)
                    return

    def _apply_token_usage(self, token_usage: dict[str, Any]) -> None:
        prompt_tokens = token_usage.get("prompt_tokens")
        completion_tokens = token_usage.get("completion_tokens")
        total_tokens = token_usage.get("total_tokens")

        if isinstance(prompt_tokens, int):
            self.prompt_tokens = prompt_tokens
        if isinstance(completion_tokens, int):
            self.completion_tokens = completion_tokens
        if isinstance(total_tokens, int):
            self.total_tokens = total_tokens

    def get_metrics(self) -> dict[str, float | int | None]:
        return {
            "latency_ms": self.latency_ms,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
        }
