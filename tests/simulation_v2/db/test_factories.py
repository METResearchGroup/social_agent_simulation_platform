"""Smoke tests for simulation_v2 db factories."""

from __future__ import annotations

from tests.simulation_v2.db import factories


class TestFactories:
    def test_run_record_factory(self) -> None:
        record = factories.RunRecordFactory.create()
        assert record.run_id
        assert record.config_json

    def test_turn_record_factory(self) -> None:
        record = factories.TurnRecordFactory.create()
        assert record.turn_number >= 1

    def test_social_factories(self) -> None:
        assert factories.UserRecordFactory.create().username
        assert factories.PostRecordFactory.create().content
        assert factories.LikeRecordFactory.create().like_id
        assert factories.FollowRecordFactory.create().follow_id
        assert factories.CommentRecordFactory.create().comment_id

    def test_memory_factories(self) -> None:
        assert factories.AgentMemoryRecordFactory.create().user_id
        assert factories.MemoryDiffRecordFactory.create().memory_type

    def test_feed_factories(self) -> None:
        feed = factories.GeneratedFeedRecordFactory.create()
        assert feed.feed_posts
        assert feed.feed_post_ids

    def test_action_factories(self) -> None:
        assert factories.GenerationRecordFactory.create().generation_id
        assert factories.LlmProposedActionRecordFactory.create().llm_proposed_action_id
        assert factories.ProposedActionRecordFactory.create().action_id

    def test_eval_factories(self) -> None:
        assert factories.EvalRunRecordFactory.create().eval_run_id
        assert factories.EvalMetricRecordFactory.create().eval_metric_id
