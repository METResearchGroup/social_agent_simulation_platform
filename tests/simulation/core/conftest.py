"""Shared pytest fixtures for simulation core tests."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from db.repositories.feed_post_repository import FeedPostRepository
from db.repositories.generated_bio_repository import GeneratedBioRepository
from db.repositories.generated_feed_repository import GeneratedFeedRepository
from db.repositories.interfaces import (
    CommentRepository,
    FollowRepository,
    LikeRepository,
    MetricsRepository,
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

    return {
        "run_repo": Mock(spec=RunRepository),
        "metrics_repo": Mock(spec=MetricsRepository),
        "profile_repo": Mock(spec=ProfileRepository),
        "feed_post_repo": Mock(spec=FeedPostRepository),
        "generated_bio_repo": Mock(spec=GeneratedBioRepository),
        "generated_feed_repo": Mock(spec=GeneratedFeedRepository),
        "like_repo": like_repo,
        "comment_repo": comment_repo,
        "follow_repo": follow_repo,
    }


@pytest.fixture
def deps(mock_repos):
    return mock_repos


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
