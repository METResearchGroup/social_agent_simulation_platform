"""Shared utilities for follow action generators."""

from __future__ import annotations

from lib.agent_id import canonical_agent_id, is_canonical_agent_id
from simulation.core.models.posts import Post


def derive_target_agent_id(post: Post) -> str:
    """Return canonical agent_id for the post author.

    Uses author_agent_id when it is already canonical; otherwise derives from
    author_handle via canonical_agent_id.
    """
    if post.author_agent_id and is_canonical_agent_id(post.author_agent_id):
        return post.author_agent_id
    return canonical_agent_id(post.author_handle)
