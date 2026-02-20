"""Abstract interfaces for feed generation algorithms."""

from typing import Any, TypedDict


class FeedAlgorithmMetadata(TypedDict, total=False):
    """Metadata for a feed algorithm, exposed to the API and UI."""

    display_name: str
    description: str
    config_schema: dict[str, Any] | None


# Feed generators are callables with signature:
# (candidate_posts: list[BlueskyFeedPost], agent: SocialMediaAgent, **kwargs) -> dict
# Return dict must have: feed_id, agent_handle, post_uris
