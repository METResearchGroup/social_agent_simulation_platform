"""Shared pytest fixtures for simulation core tests."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import Mock

import pytest

from db.adapters.base import TransactionProvider
from db.repositories.generated_feed_repository import GeneratedFeedRepository
from db.repositories.interfaces import (
    AgentBioRepository,
    AgentFollowEdgeRepository,
    AgentPostCommentRepository,
    AgentPostLikeRepository,
    AgentPostRepository,
    AgentRepository,
    CommentRepository,
    FollowRepository,
    LikeRepository,
    MetricsRepository,
    RunAgentRepository,
    RunFollowEdgeRepository,
    RunPostCommentRepository,
    RunPostLikeRepository,
    RunPostRepository,
    UserAgentProfileMetadataRepository,
)
from db.repositories.profile_repository import ProfileRepository
from db.repositories.run_repository import RunRepository
from simulation.core.models.runs import Run, RunStatus


@pytest.fixture
def mock_repos():
    like_repo = Mock(spec=LikeRepository)
    like_repo.read_likes_by_run_turn.return_value = []
    comment_repo = Mock(spec=CommentRepository)
    comment_repo.read_comments_by_run_turn.return_value = []
    follow_repo = Mock(spec=FollowRepository)
    follow_repo.read_follows_by_run_turn.return_value = []
    agent_follow_edge_repo = Mock(spec=AgentFollowEdgeRepository)
    agent_follow_edge_repo.list_edges_for_follower_agent_ids.return_value = []
    run_follow_edge_repo = Mock(spec=RunFollowEdgeRepository)
    run_follow_edge_repo.list_run_follow_edges.return_value = []

    run_post_repo = Mock(spec=RunPostRepository)
    run_post_repo.read_run_posts_by_ids.return_value = []
    run_post_repo.list_run_posts.return_value = []
    run_post_repo.write_run_posts.return_value = None

    agent_post_repo = Mock(spec=AgentPostRepository)
    agent_post_repo.list_posts_for_agent_ids.return_value = []

    agent_post_like_repo = Mock(spec=AgentPostLikeRepository)
    agent_post_like_repo.list_likes_for_agent_post_ids.return_value = []

    agent_post_comment_repo = Mock(spec=AgentPostCommentRepository)
    agent_post_comment_repo.list_comments_for_agent_post_ids.return_value = []

    run_post_like_repo = Mock(spec=RunPostLikeRepository)
    run_post_like_repo.write_run_post_likes.return_value = None
    run_post_like_repo.count_likes_by_run_post_ids.return_value = {}

    run_post_comment_repo = Mock(spec=RunPostCommentRepository)
    run_post_comment_repo.write_run_post_comments.return_value = None
    run_post_comment_repo.count_comments_by_run_post_ids.return_value = {}

    feed_post_repo = Mock()
    feed_post_repo.list_all_feed_posts.return_value = []
    feed_post_repo.read_feed_posts_by_ids.return_value = []

    return {
        "run_repo": Mock(spec=RunRepository),
        "metrics_repo": Mock(spec=MetricsRepository),
        "profile_repo": Mock(spec=ProfileRepository),
        "feed_post_repo": feed_post_repo,
        "run_post_repo": run_post_repo,
        "generated_feed_repo": Mock(spec=GeneratedFeedRepository),
        "agent_repo": Mock(spec=AgentRepository),
        "agent_bio_repo": Mock(spec=AgentBioRepository),
        "agent_follow_edge_repo": agent_follow_edge_repo,
        "user_agent_profile_metadata_repo": Mock(
            spec=UserAgentProfileMetadataRepository
        ),
        "run_agent_repo": Mock(spec=RunAgentRepository),
        "run_follow_edge_repo": run_follow_edge_repo,
        "agent_post_repo": agent_post_repo,
        "agent_post_like_repo": agent_post_like_repo,
        "agent_post_comment_repo": agent_post_comment_repo,
        "run_post_like_repo": run_post_like_repo,
        "run_post_comment_repo": run_post_comment_repo,
        "like_repo": like_repo,
        "comment_repo": comment_repo,
        "follow_repo": follow_repo,
    }


@pytest.fixture
def deps(mock_repos):
    return mock_repos


@pytest.fixture
def mock_transaction_provider():
    provider = Mock(spec=TransactionProvider)
    mock_conn = Mock()

    @contextmanager
    def _run_transaction():
        yield mock_conn

    provider.run_transaction.side_effect = _run_transaction
    provider.mock_conn = mock_conn
    return provider


@pytest.fixture
def sample_run(request):
    overrides = getattr(request.module, "SAMPLE_RUN_OVERRIDES", {})
    return Run(
        run_id="run_123",
        created_at="2024_01_01-12:00:00",
        total_turns=overrides.get("total_turns", 2),
        total_agents=overrides.get("total_agents", 2),
        feed_algorithm="chronological",
        metric_keys=[
            "run.actions.total",
            "run.actions.total_by_type",
            "turn.actions.counts_by_type",
            "turn.actions.total",
        ],
        started_at="2024_01_01-12:00:00",
        status=RunStatus.RUNNING,
        completed_at=None,
    )
