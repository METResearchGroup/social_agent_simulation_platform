"""Deterministic factories for simulation_v2 db record models."""

from __future__ import annotations

from typing import Any

from faker import Faker

from simulation_v2 import ids
from simulation_v2.config import LocalSimulationConfig
from simulation_v2.db.models import (
    AgentMemoryRecord,
    CommentRecord,
    EvalMetricRecord,
    EvalRunRecord,
    FeedPostView,
    FollowRecord,
    GeneratedFeedRecord,
    GenerationRecord,
    LikeRecord,
    LlmProposedActionRecord,
    MemoryDiffRecord,
    PostRecord,
    ProposedActionRecord,
    RunRecord,
    TurnRecord,
    UserRecord,
)
from simulation_v2.time import get_current_timestamp


def _faker() -> Faker:
    return Faker()


class RunRecordFactory:
    @staticmethod
    def create(**overrides: Any) -> RunRecord:
        defaults: dict[str, Any] = {
            "run_id": ids.new_run_id(),
            "status": "queued",
            "config_json": LocalSimulationConfig.default().model_dump(mode="json"),
            "seed_metadata_json": {"source": "test"},
            "created_at": get_current_timestamp(),
        }
        defaults.update(overrides)
        return RunRecord.model_validate(defaults)


class TurnRecordFactory:
    @staticmethod
    def create(**overrides: Any) -> TurnRecord:
        defaults: dict[str, Any] = {
            "turn_id": ids.new_turn_id(),
            "run_id": ids.new_run_id(),
            "turn_number": 1,
            "status": "pending",
            "created_at": get_current_timestamp(),
        }
        defaults.update(overrides)
        return TurnRecord.model_validate(defaults)


class UserRecordFactory:
    @staticmethod
    def create(**overrides: Any) -> UserRecord:
        faker = _faker()
        defaults: dict[str, Any] = {
            "user_id": ids.new_user_id(),
            "run_id": ids.new_run_id(),
            "name": faker.name(),
            "email": faker.email(),
            "username": faker.user_name(),
            "profile_json": {"bio": faker.sentence()},
            "created_at": get_current_timestamp(),
        }
        defaults.update(overrides)
        return UserRecord.model_validate(defaults)


class PostRecordFactory:
    @staticmethod
    def create(**overrides: Any) -> PostRecord:
        faker = _faker()
        defaults: dict[str, Any] = {
            "post_id": ids.new_post_id(),
            "run_id": ids.new_run_id(),
            "author_id": ids.new_user_id(),
            "content": faker.sentence(),
            "created_at": get_current_timestamp(),
            "created_at_turn": 0,
        }
        defaults.update(overrides)
        return PostRecord.model_validate(defaults)


class LikeRecordFactory:
    @staticmethod
    def create(**overrides: Any) -> LikeRecord:
        defaults: dict[str, Any] = {
            "like_id": ids.new_like_id(),
            "run_id": ids.new_run_id(),
            "post_id": ids.new_post_id(),
            "author_id": ids.new_user_id(),
            "created_at": get_current_timestamp(),
            "created_at_turn": 1,
        }
        defaults.update(overrides)
        return LikeRecord.model_validate(defaults)


class FollowRecordFactory:
    @staticmethod
    def create(**overrides: Any) -> FollowRecord:
        defaults: dict[str, Any] = {
            "follow_id": ids.new_follow_id(),
            "run_id": ids.new_run_id(),
            "follower_id": ids.new_user_id(),
            "followee_id": ids.new_user_id(),
            "created_at": get_current_timestamp(),
            "created_at_turn": 1,
        }
        defaults.update(overrides)
        return FollowRecord.model_validate(defaults)


class CommentRecordFactory:
    @staticmethod
    def create(**overrides: Any) -> CommentRecord:
        faker = _faker()
        defaults: dict[str, Any] = {
            "comment_id": ids.new_comment_id(),
            "run_id": ids.new_run_id(),
            "parent_post_id": ids.new_post_id(),
            "author_id": ids.new_user_id(),
            "content": faker.sentence(),
            "created_at": get_current_timestamp(),
            "created_at_turn": 1,
        }
        defaults.update(overrides)
        return CommentRecord.model_validate(defaults)


class AgentMemoryRecordFactory:
    @staticmethod
    def create(**overrides: Any) -> AgentMemoryRecord:
        faker = _faker()
        defaults: dict[str, Any] = {
            "run_id": ids.new_run_id(),
            "user_id": ids.new_user_id(),
            "preferences_json": {"theme": "dark"},
            "episodic": faker.sentence(),
            "personalized": faker.sentence(),
            "social": faker.sentence(),
            "updated_at": get_current_timestamp(),
        }
        defaults.update(overrides)
        return AgentMemoryRecord.model_validate(defaults)


class MemoryDiffRecordFactory:
    @staticmethod
    def create(**overrides: Any) -> MemoryDiffRecord:
        faker = _faker()
        defaults: dict[str, Any] = {
            "memory_diff_id": ids.new_memory_diff_id(),
            "run_id": ids.new_run_id(),
            "turn_id": ids.new_turn_id(),
            "user_id": ids.new_user_id(),
            "memory_type": "episodic",
            "content": faker.sentence(),
            "created_at": get_current_timestamp(),
        }
        defaults.update(overrides)
        return MemoryDiffRecord.model_validate(defaults)


class FeedPostViewFactory:
    @staticmethod
    def create(**overrides: Any) -> FeedPostView:
        faker = _faker()
        defaults: dict[str, Any] = {
            "post_id": ids.new_post_id(),
            "author_id": ids.new_user_id(),
            "content": faker.sentence(),
            "created_at": get_current_timestamp(),
        }
        defaults.update(overrides)
        return FeedPostView.model_validate(defaults)


class GeneratedFeedRecordFactory:
    @staticmethod
    def create(**overrides: Any) -> GeneratedFeedRecord:
        post = FeedPostViewFactory.create()
        defaults: dict[str, Any] = {
            "feed_id": ids.new_feed_id(),
            "run_id": ids.new_run_id(),
            "turn_id": ids.new_turn_id(),
            "user_id": ids.new_user_id(),
            "algorithm": "most_liked",
            "feed_post_ids": [post.post_id],
            "feed_posts": [post],
            "created_at": get_current_timestamp(),
        }
        defaults.update(overrides)
        return GeneratedFeedRecord.model_validate(defaults)


class GenerationRecordFactory:
    @staticmethod
    def create(**overrides: Any) -> GenerationRecord:
        defaults: dict[str, Any] = {
            "generation_id": ids.new_generation_id(),
            "run_id": ids.new_run_id(),
            "turn_id": ids.new_turn_id(),
            "user_id": ids.new_user_id(),
            "action_type": "like",
            "parsed_response_json": {"post_ids": ["p1"]},
            "raw_response_json": {"text": "ok"},
            "status": "completed",
            "latency_ms": 12.5,
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "cost_usd": 0.001,
            "created_at": get_current_timestamp(),
        }
        defaults.update(overrides)
        return GenerationRecord.model_validate(defaults)


class LlmProposedActionRecordFactory:
    @staticmethod
    def create(**overrides: Any) -> LlmProposedActionRecord:
        defaults: dict[str, Any] = {
            "llm_proposed_action_id": ids.new_llm_proposed_action_id(),
            "generation_id": ids.new_generation_id(),
            "run_id": ids.new_run_id(),
            "turn_id": ids.new_turn_id(),
            "user_id": ids.new_user_id(),
            "action_type": "like",
            "target_type": "post",
            "target_id": ids.new_post_id(),
            "target_content": None,
            "metadata_json": {"source": "llm"},
            "created_at": get_current_timestamp(),
        }
        defaults.update(overrides)
        return LlmProposedActionRecord.model_validate(defaults)


class ProposedActionRecordFactory:
    @staticmethod
    def create(**overrides: Any) -> ProposedActionRecord:
        defaults: dict[str, Any] = {
            "action_id": ids.new_action_id(),
            "record_kind": "validated",
            "generation_id": ids.new_generation_id(),
            "run_id": ids.new_run_id(),
            "turn_id": ids.new_turn_id(),
            "user_id": ids.new_user_id(),
            "action_type": "like",
            "target_type": "post",
            "target_id": ids.new_post_id(),
            "created_at": get_current_timestamp(),
        }
        defaults.update(overrides)
        return ProposedActionRecord.model_validate(defaults)


class EvalRunRecordFactory:
    @staticmethod
    def create(**overrides: Any) -> EvalRunRecord:
        defaults: dict[str, Any] = {
            "eval_run_id": ids.new_eval_run_id(),
            "run_id": ids.new_run_id(),
            "turn_id": ids.new_turn_id(),
            "scope": "turn",
            "plugin_name": "action_counts",
            "status": "completed",
            "created_at": get_current_timestamp(),
        }
        defaults.update(overrides)
        return EvalRunRecord.model_validate(defaults)


class EvalMetricRecordFactory:
    @staticmethod
    def create(**overrides: Any) -> EvalMetricRecord:
        defaults: dict[str, Any] = {
            "eval_metric_id": ids.new_eval_metric_id(),
            "eval_run_id": ids.new_eval_run_id(),
            "run_id": ids.new_run_id(),
            "turn_id": ids.new_turn_id(),
            "plugin_name": "action_counts",
            "metric_name": "likes",
            "metric_value": 1.0,
            "metadata_json": {"unit": "count"},
            "created_at": get_current_timestamp(),
        }
        defaults.update(overrides)
        return EvalMetricRecord.model_validate(defaults)
