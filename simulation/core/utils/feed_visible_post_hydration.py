"""Hydrate feed-visible post IDs from ``run_posts`` and ``turn_posts``.

Lookup order: ``run_posts`` first (run-scoped snapshot), then ``turn_posts`` for
IDs not found. IDs missing from both are omitted from the returned map.
"""

from __future__ import annotations

from collections.abc import Iterable

from db.repositories.interfaces import (
    RunPostCommentRepository,
    RunPostLikeRepository,
    RunPostRepository,
    TurnPostRepository,
)
from simulation.core.models.posts import (
    Post,
    run_post_snapshot_to_post,
    turn_post_snapshot_to_post,
)


def hydrate_feed_visible_posts_for_run(
    run_id: str,
    post_ids: Iterable[str],
    *,
    run_post_repo: RunPostRepository,
    turn_post_repo: TurnPostRepository,
    run_post_like_repo: RunPostLikeRepository,
    run_post_comment_repo: RunPostCommentRepository,
) -> dict[str, Post]:
    """Build ``post_id`` -> :class:`Post` for mixed run + turn post IDs.

    Engagement counts for run snapshots come from ``run_post_like_repo`` /
    ``run_post_comment_repo``. Turn-authored posts use zero like/reply counts
    until turn-scoped engagement storage exists.
    """
    unique_ids = list(dict.fromkeys(post_ids))
    if not unique_ids:
        return {}

    run_snaps = run_post_repo.read_run_posts_by_ids(run_id, unique_ids)
    found_run_ids = {s.run_post_id for s in run_snaps}
    like_counts = run_post_like_repo.count_likes_by_run_post_ids(
        run_id, list(found_run_ids)
    )
    reply_counts = run_post_comment_repo.count_comments_by_run_post_ids(
        run_id, list(found_run_ids)
    )

    remaining = [pid for pid in unique_ids if pid not in found_run_ids]
    turn_snaps = (
        turn_post_repo.read_turn_posts_by_ids(run_id, remaining) if remaining else []
    )

    out: dict[str, Post] = {}
    for s in run_snaps:
        out[s.run_post_id] = run_post_snapshot_to_post(
            s,
            like_count=like_counts.get(s.run_post_id, 0),
            reply_count=reply_counts.get(s.run_post_id, 0),
        )
    for s in turn_snaps:
        tid = s.turn_post_id
        if tid not in out:
            out[tid] = turn_post_snapshot_to_post(s)
    return out


def ordered_posts_from_hydration(
    post_ids: Iterable[str], mapping: dict[str, Post]
) -> list[Post]:
    """Preserve caller order; skip IDs not present in ``mapping``."""
    return [mapping[pid] for pid in post_ids if pid in mapping]
