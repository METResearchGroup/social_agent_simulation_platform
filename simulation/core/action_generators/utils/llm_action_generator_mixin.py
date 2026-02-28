"""Shared scaffolding for naive LLM action generators."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TypeVar

from ml_tooling.llm.llm_service import LLMService

T = TypeVar("T")


class LLMActionGeneratorMixin:
    """Lightweight mixin that centralizes LLM call + dedupe helpers."""

    def __init__(self, *, llm_service: LLMService) -> None:
        self._llm = llm_service

    def _call_llm(self, *, prompt: str, response_model: type[T]) -> T:
        """Call the shared LLM service with the provided prompt."""
        return self._llm.structured_completion(
            messages=[{"role": "user", "content": prompt}],
            response_model=response_model,
        )

    @staticmethod
    def _filter_and_dedupe_ids(
        response_ids: Iterable[str], valid_ids: set[str]
    ) -> list[str]:
        """Return response IDs that are valid and deduplicated (first occurrence)."""
        seen: set[str] = set()
        filtered: list[str] = []
        for entry_id in response_ids:
            if entry_id in seen or entry_id not in valid_ids:
                continue
            seen.add(entry_id)
            filtered.append(entry_id)
        return filtered

    @staticmethod
    def _filter_and_dedupe_items(
        items: Iterable[T],
        valid_ids: set[str],
        item_id: Callable[[T], str],
    ) -> list[T]:
        """Return items whose IDs are valid, deduplicated in first-occurrence order."""
        seen: set[str] = set()
        filtered: list[T] = []
        for item in items:
            identifier = item_id(item)
            if identifier in seen or identifier not in valid_ids:
                continue
            seen.add(identifier)
            filtered.append(item)
        return filtered
