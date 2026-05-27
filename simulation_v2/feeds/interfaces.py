"""Feed generator protocol, registry, and snapshot helpers."""

from __future__ import annotations

from typing import Protocol

from simulation_v2.config import FeedConfig
from simulation_v2.db.models import FeedPostView, PostRecord
from simulation_v2.worker.state import TurnStateSnapshot


class FeedGenerator(Protocol):
    name: str

    def generate(
        self,
        snapshot: TurnStateSnapshot,
        user_id: str,
        config: FeedConfig,
    ) -> list[FeedPostView]: ...


def get_feed_generator(algorithm: str) -> FeedGenerator:
    from simulation_v2.feeds.most_liked import MostLikedFeedGenerator
    from simulation_v2.feeds.reverse_chronological import (
        ReverseChronologicalFeedGenerator,
    )

    generators: dict[str, FeedGenerator] = {
        "most_liked": MostLikedFeedGenerator(),
        "reverse_chronological": ReverseChronologicalFeedGenerator(),
    }
    try:
        return generators[algorithm]
    except KeyError as exc:
        raise ValueError(f"unknown feed algorithm: {algorithm!r}") from exc


def post_like_counts(snapshot: TurnStateSnapshot) -> dict[str, int]:
    counts: dict[str, int] = {}
    for like in snapshot.likes:
        counts[like.post_id] = counts.get(like.post_id, 0) + 1
    return counts


def hydrate_feed_post_view(post: PostRecord, *, like_count: int) -> FeedPostView:
    metadata = dict(post.metadata_json or {})
    metadata["num_likes"] = like_count
    return FeedPostView(
        post_id=post.post_id,
        author_id=post.author_id,
        content=post.content,
        created_at=post.created_at,
        metadata=metadata,
    )
