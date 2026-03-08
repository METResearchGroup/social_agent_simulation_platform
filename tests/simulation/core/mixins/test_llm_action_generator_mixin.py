"""Unit tests for helpers in LLMActionGeneratorMixin."""

from __future__ import annotations

from pydantic import BaseModel

from simulation.core.action_generators.mixins.llm_action_generator_mixin import (
    LLMActionGeneratorMixin,
)


class _DummyItem(BaseModel):
    """Items used to exercise mixin helpers."""

    post_id: str
    external_ref: str


class TestFilterAndDedupeIds:
    """Verify `_filter_and_dedupe_ids` enforces validity and deduplication."""

    def test_keeps_first_valid_id_only(self) -> None:
        """Only the first occurrence of a valid ID survives."""
        valid_ids = {"valid-1", "valid-2"}
        response_ids = ["valid-1", "valid-1", "valid-2", "unknown"]

        filtered = LLMActionGeneratorMixin._filter_and_dedupe_ids(
            response_ids=response_ids,
            valid_ids=valid_ids,
        )

        assert filtered == ["valid-1", "valid-2"]

    def test_returns_empty_for_empty_input(self) -> None:
        """No IDs yields an empty result without errors."""
        filtered = LLMActionGeneratorMixin._filter_and_dedupe_ids(
            response_ids=[],
            valid_ids={"anything"},
        )

        assert filtered == []


class TestFilterAndDedupeItems:
    """Exercise `_filter_and_dedupe_items` for default and override flows."""

    def test_defaults_to_item_id_for_validation(self) -> None:
        """The default validator matches the supplied item_id extractor."""
        valid_ids = {"local-1"}
        items = [
            _DummyItem(post_id="local-1", external_ref="ext-A"),
            _DummyItem(post_id="local-1", external_ref="ext-A"),
            _DummyItem(post_id="local-2", external_ref="ext-B"),
        ]

        filtered = LLMActionGeneratorMixin._filter_and_dedupe_items(
            items=items,
            valid_ids=valid_ids,
            item_id=lambda item: item.post_id,
        )

        assert [item.post_id for item in filtered] == ["local-1"]

    def test_respects_validation_id_override(self) -> None:
        """A custom validation_id can differ from the dedupe key."""
        valid_ids = {"ext-1"}
        items = [
            _DummyItem(post_id="local-1", external_ref="ext-1"),
            _DummyItem(post_id="local-1", external_ref="ext-1"),
            _DummyItem(post_id="local-2", external_ref="ext-2"),
            _DummyItem(post_id="local-3", external_ref="ext-1"),
        ]

        filtered = LLMActionGeneratorMixin._filter_and_dedupe_items(
            items=items,
            valid_ids=valid_ids,
            item_id=lambda item: item.post_id,
            validation_id=lambda item: item.external_ref,
        )

        assert [item.post_id for item in filtered] == ["local-1", "local-3"]

    def test_seen_scopes_to_item_id(self) -> None:
        """Even if validation_ids differ, only the first item_id survives."""
        valid_ids = {"ext-1", "ext-2"}
        items = [
            _DummyItem(post_id="local-dup", external_ref="ext-1"),
            _DummyItem(post_id="local-dup", external_ref="ext-2"),
        ]

        filtered = LLMActionGeneratorMixin._filter_and_dedupe_items(
            items=items,
            valid_ids=valid_ids,
            item_id=lambda item: item.post_id,
            validation_id=lambda item: item.external_ref,
        )

        assert [item.external_ref for item in filtered] == ["ext-1"]
