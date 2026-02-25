"""Shared test factories for building domain models."""

from __future__ import annotations

from simulation.core.models.posts import BlueskyFeedPost


def make_post(
    *,
    uri: str,
    text: str = "content",
    author_handle: str = "test.author",
    author_display_name: str = "Test Author",
    like_count: int = 0,
    bookmark_count: int = 0,
    quote_count: int = 0,
    reply_count: int = 0,
    repost_count: int = 0,
    created_at: str = "2026-01-01T00:00:00.000Z",
) -> BlueskyFeedPost:
    """Build a BlueskyFeedPost for tests with sensible defaults.

    id is set from uri by the model when not provided.
    """
    return BlueskyFeedPost(
        id=uri,
        uri=uri,
        author_handle=author_handle,
        author_display_name=author_display_name,
        text=text,
        like_count=like_count,
        bookmark_count=bookmark_count,
        quote_count=quote_count,
        reply_count=reply_count,
        repost_count=repost_count,
        created_at=created_at,
    )
