"""Most-liked feed plugin."""

from __future__ import annotations

import random

from simulation_v2.config import FeedConfig
from simulation_v2.db.models import FeedPostView
from simulation_v2.feeds.interfaces import hydrate_feed_post_view, post_like_counts
from simulation_v2.worker.state import TurnStateSnapshot


class MostLikedFeedGenerator:
    name = "most_liked"

    def generate(
        self,
        snapshot: TurnStateSnapshot,
        user_id: str,
        config: FeedConfig,
    ) -> list[FeedPostView]:
        like_counts = post_like_counts(snapshot)
        candidates = sorted(
            snapshot.posts.values(),
            key=lambda post: (like_counts.get(post.post_id, 0), post.post_id),
            reverse=True,
        )

        feed: list[FeedPostView] = []
        for post in candidates:
            if len(feed) >= config.max_posts:
                break
            if post.author_id == user_id:
                continue
            if random.random() < config.include_probability:  # noqa: S311
                feed.append(
                    hydrate_feed_post_view(
                        post,
                        like_count=like_counts.get(post.post_id, 0),
                    )
                )
        return feed
