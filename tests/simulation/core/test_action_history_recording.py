"""Tests for action history recording helpers."""

from lib.agent_id import canonical_agent_id
from simulation.core.action_history.recording import record_action_targets
from simulation.core.action_history.stores import InMemoryActionHistoryStore


class TestActionHistoryRecording:
    def test_records_like_comment_follow_targets(self) -> None:
        history = InMemoryActionHistoryStore()

        actor_id = canonical_agent_id("agent1.bsky.social")
        target = canonical_agent_id("user_3")
        record_action_targets(
            run_id="run_123",
            agent_id=actor_id,
            like_post_ids=["post_1"],
            comment_post_ids=["post_2"],
            follow_target_agent_ids=[target],
            action_history_store=history,
        )

        assert history.has_liked("run_123", actor_id, "post_1")
        assert history.has_commented("run_123", actor_id, "post_2")
        assert history.has_followed("run_123", actor_id, target)
