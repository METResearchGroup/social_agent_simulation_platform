"""Feed validation rules for generated post views."""

from __future__ import annotations

from simulation_v2.db.models import FeedPostView


class FeedValidationError(ValueError):
    """Raised when a generated feed violates invariants."""


def validate_feed(user_id: str, views: list[FeedPostView]) -> None:
    seen_post_ids: set[str] = set()
    for view in views:
        if view.post_id in seen_post_ids:
            raise FeedValidationError(
                f"duplicate post_id {view.post_id!r} in feed for user {user_id!r}"
            )
        seen_post_ids.add(view.post_id)
        if view.author_id == user_id:
            raise FeedValidationError(
                f"self-authored post {view.post_id!r} in feed for user {user_id!r}"
            )
