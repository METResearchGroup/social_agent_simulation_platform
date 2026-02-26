"""Tests for action history recording helpers."""

from simulation.core.action_history.recording import record_action_targets
from simulation.core.action_history.stores import InMemoryActionHistoryStore


def test_records_like_comment_follow_targets() -> None:
    history = InMemoryActionHistoryStore()

    record_action_targets(
        run_id="run_123",
        agent_handle="agent1.bsky.social",
        like_post_ids=["post_1"],
        comment_post_ids=["post_2"],
        follow_user_ids=["user_3"],
        action_history_store=history,
    )

    assert history.has_liked("run_123", "agent1.bsky.social", "post_1")
    assert history.has_commented("run_123", "agent1.bsky.social", "post_2")
    assert history.has_followed("run_123", "agent1.bsky.social", "user_3")
