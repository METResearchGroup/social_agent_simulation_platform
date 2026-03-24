"""Unit tests for mixed run/turn post hydration helper."""

from unittest.mock import Mock

from db.repositories.interfaces import (
    RunPostCommentRepository,
    RunPostLikeRepository,
    RunPostRepository,
    TurnPostRepository,
)
from simulation.core.models.posts import (
    run_post_snapshot_to_post,
    turn_post_snapshot_to_post,
)
from simulation.core.utils.feed_visible_post_hydration import (
    hydrate_feed_visible_posts_for_run,
    ordered_posts_from_hydration,
)
from tests.factories import RunPostSnapshotFactory, TurnPostSnapshotFactory


class TestFeedVisiblePostHydration:
    def test_hydrate_run_wins_when_same_id_in_both_tables(self) -> None:
        """If an ID exists in run_posts, turn_posts is not used for that ID."""
        shared_id = "same_id"
        run_snap = RunPostSnapshotFactory.create(
            run_post_id=shared_id,
            body_text_at_start="from run",
        )
        run_repo = Mock(spec=RunPostRepository)
        run_repo.read_run_posts_by_ids.return_value = [run_snap]
        turn_repo = Mock(spec=TurnPostRepository)
        like_repo = Mock(spec=RunPostLikeRepository)
        like_repo.count_likes_by_run_post_ids.return_value = {}
        comment_repo = Mock(spec=RunPostCommentRepository)
        comment_repo.count_comments_by_run_post_ids.return_value = {}

        mapping = hydrate_feed_visible_posts_for_run(
            "run_1",
            [shared_id],
            run_post_repo=run_repo,
            turn_post_repo=turn_repo,
            run_post_like_repo=like_repo,
            run_post_comment_repo=comment_repo,
        )

        assert mapping[shared_id].text == "from run"
        turn_repo.read_turn_posts_by_ids.assert_not_called()

    def test_ordered_posts_from_hydration_skips_missing(self) -> None:
        a = RunPostSnapshotFactory.create(run_post_id="a")
        b = TurnPostSnapshotFactory.create(turn_post_id="b")
        mapping = {
            "a": run_post_snapshot_to_post(a),
            "b": turn_post_snapshot_to_post(b),
        }
        ordered = ordered_posts_from_hydration(["a", "ghost", "b"], mapping)
        assert [p.post_id for p in ordered] == ["a", "b"]
