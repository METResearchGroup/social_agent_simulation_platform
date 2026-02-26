"""Smoke tests for tests.factories.* factories."""

from tests.factories import (
    AgentFactory,
    CommentFactory,
    FollowFactory,
    GeneratedBioFactory,
    GeneratedCommentFactory,
    GeneratedFollowFactory,
    GeneratedLikeFactory,
    GenerationMetadataFactory,
    LikeFactory,
    PersistedCommentFactory,
    PersistedFollowFactory,
    PersistedLikeFactory,
    PostFactory,
    RunConfigFactory,
    RunFactory,
    RunMetricsFactory,
    TurnMetadataFactory,
    TurnMetricsFactory,
)


def test_post_factory_smoke():
    assert PostFactory.create().uri


def test_generation_metadata_factory_smoke():
    assert GenerationMetadataFactory.create().created_at


def test_generated_bio_factory_smoke():
    assert GeneratedBioFactory.create().handle


def test_action_factories_smoke():
    assert LikeFactory.create().like_id
    assert CommentFactory.create().comment_id
    assert FollowFactory.create().follow_id


def test_generated_action_factories_smoke():
    assert GeneratedLikeFactory.create().like.like_id
    assert GeneratedCommentFactory.create().comment.comment_id
    assert GeneratedFollowFactory.create().follow.follow_id


def test_persisted_action_factories_smoke():
    assert PersistedLikeFactory.create().like_id
    assert PersistedCommentFactory.create().comment_id
    assert PersistedFollowFactory.create().follow_id


def test_agent_factory_smoke():
    assert AgentFactory.create().handle


def test_run_factories_smoke():
    assert RunConfigFactory.create().feed_algorithm == "chronological"
    assert RunFactory.create().run_id


def test_turn_factories_smoke():
    assert TurnMetadataFactory.create().run_id
    assert TurnMetricsFactory.create().run_id
    assert RunMetricsFactory.create().run_id


def test_like_factory_uses_agent_and_post_in_like_id():
    like = LikeFactory.create(agent_id="agent_1", post_id="post_1")
    assert like.like_id == "like_agent_1_post_1"


def test_create_batch_sizes_match():
    posts = PostFactory.create_batch(3)
    assert len(posts) == 3
