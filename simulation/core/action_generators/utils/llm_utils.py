"""Shared LLM utilities for naive LLM action generators."""

from __future__ import annotations

import json

from simulation.core.models.posts import Post


def _posts_to_minimal_json(posts: list[Post]) -> str:
    """Serialize posts to minimal JSON for the prompt."""
    items = [
        {
            "id": p.post_id,
            "text": p.text,
            "author_handle": p.author_handle,
            "like_count": p.like_count,
        }
        for p in posts
    ]
    return json.dumps(items, indent=2)


def _resolve_model_used() -> str | None:
    """Get the default model identifier for metadata, or None if unavailable."""
    try:
        from ml_tooling.llm.config.model_registry import ModelConfigRegistry

        return ModelConfigRegistry.get_default_model()
    except (ValueError, FileNotFoundError, KeyError):
        return None
