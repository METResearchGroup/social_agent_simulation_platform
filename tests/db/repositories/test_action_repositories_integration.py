"""Integration tests for like, comment, and follow action repositories.

Uses a real SQLite database. Requires a run to exist for FK (run_id).
"""

from __future__ import annotations

from simulation.core.models.generated.base import GenerationMetadata
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.runs import RunConfig


def _make_run(run_repo) -> str:
    """Create a run and return run_id."""
    config = RunConfig(num_agents=1, num_turns=2, feed_algorithm="chronological")
    run = run_repo.create_run(config)
    return run.run_id


class TestSQLiteLikeRepositoryIntegration:
    """Integration tests for LikeRepository."""

    def test_write_and_read_likes_by_run_turn(self, run_repo, like_repo) -> None:
        """write_likes then read_likes_by_run_turn round-trips."""
        run_id = _make_run(run_repo)
        turn_number = 0
        from simulation.core.models.actions import Like

        likes = [
            GeneratedLike(
                like=Like(
                    like_id="like_1",
                    agent_id="alice.bsky.social",
                    post_id="at://did:plc:post1",
                    created_at="2026-02-24T12:00:00Z",
                ),
                explanation="Great post",
                metadata=GenerationMetadata(
                    model_used=None,
                    generation_metadata=None,
                    created_at="2026-02-24T12:00:00Z",
                ),
            ),
        ]
        like_repo.write_likes(run_id, turn_number, likes)

        result = like_repo.read_likes_by_run_turn(run_id, turn_number)
        assert len(result) == 1
        assert result[0].like_id == "like_1"
        assert result[0].agent_handle == "alice.bsky.social"
        assert result[0].post_id == "at://did:plc:post1"
        assert result[0].run_id == run_id
        assert result[0].turn_number == turn_number

    def test_read_likes_empty_when_none_persisted(self, run_repo, like_repo) -> None:
        """read_likes_by_run_turn returns empty list when no likes for that turn."""
        run_id = _make_run(run_repo)
        result = like_repo.read_likes_by_run_turn(run_id, 0)
        assert result == []


class TestSQLiteCommentRepositoryIntegration:
    """Integration tests for CommentRepository."""

    def test_write_and_read_comments_by_run_turn(self, run_repo, comment_repo) -> None:
        """write_comments then read_comments_by_run_turn round-trips."""
        run_id = _make_run(run_repo)
        turn_number = 0
        from simulation.core.models.actions import Comment

        comments = [
            GeneratedComment(
                comment=Comment(
                    comment_id="comment_1",
                    agent_id="bob.bsky.social",
                    post_id="at://did:plc:post2",
                    text="Nice one!",
                    created_at="2026-02-24T12:01:00Z",
                ),
                explanation="Relevant",
                metadata=GenerationMetadata(
                    model_used=None,
                    generation_metadata=None,
                    created_at="2026-02-24T12:01:00Z",
                ),
            ),
        ]
        comment_repo.write_comments(run_id, turn_number, comments)

        result = comment_repo.read_comments_by_run_turn(run_id, turn_number)
        assert len(result) == 1
        assert result[0].comment_id == "comment_1"
        assert result[0].agent_handle == "bob.bsky.social"
        assert result[0].post_id == "at://did:plc:post2"
        assert result[0].text == "Nice one!"
        assert result[0].run_id == run_id
        assert result[0].turn_number == turn_number


class TestSQLiteFollowRepositoryIntegration:
    """Integration tests for FollowRepository."""

    def test_write_and_read_follows_by_run_turn(self, run_repo, follow_repo) -> None:
        """write_follows then read_follows_by_run_turn round-trips."""
        run_id = _make_run(run_repo)
        turn_number = 0
        from simulation.core.models.actions import Follow

        follows = [
            GeneratedFollow(
                follow=Follow(
                    follow_id="follow_1",
                    agent_id="alice.bsky.social",
                    user_id="charlie.bsky.social",
                    created_at="2026-02-24T12:02:00Z",
                ),
                explanation="Interesting account",
                metadata=GenerationMetadata(
                    model_used=None,
                    generation_metadata=None,
                    created_at="2026-02-24T12:02:00Z",
                ),
            ),
        ]
        follow_repo.write_follows(run_id, turn_number, follows)

        result = follow_repo.read_follows_by_run_turn(run_id, turn_number)
        assert len(result) == 1
        assert result[0].follow_id == "follow_1"
        assert result[0].agent_handle == "alice.bsky.social"
        assert result[0].user_id == "charlie.bsky.social"
        assert result[0].run_id == run_id
        assert result[0].turn_number == turn_number
