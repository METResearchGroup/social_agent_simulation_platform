"""Integration tests for db.repositories.agent_post_like_repository module."""

import sqlite3

import pytest

from db.repositories.agent_post_like_repository import (
    create_sqlite_agent_post_like_repository,
)
from simulation.core.models.agent_post_likes import AgentPostLike
from simulation.core.models.agent_posts import AgentPost
from tests.factories import AgentRecordFactory


def _seed_agent(agent_repo, *, agent_id: str, handle: str) -> None:
    agent_repo.create_or_update_agent(
        AgentRecordFactory.create(
            agent_id=agent_id,
            handle=handle,
            display_name=handle,
            created_at="2026-03-17T00:00:00Z",
            updated_at="2026-03-17T00:00:00Z",
        )
    )


def _seed_agent_post(*, agent_post_repo, agent_post_id: str, agent_id: str) -> None:
    agent_post_repo.write_agent_posts(
        [
            AgentPost(
                agent_post_id=agent_post_id,
                agent_id=agent_id,
                body_text="Post body",
                published_at="2026-03-17T10:00:00Z",
                created_at="2026-03-17T10:00:00Z",
                updated_at="2026-03-17T10:00:00Z",
            )
        ]
    )


class TestSQLiteAgentPostLikeRepositoryIntegration:
    def test_write_and_list_round_trips_in_deterministic_order(
        self,
        agent_repo,
        agent_post_repo,
        sqlite_tx,
    ) -> None:
        like_repo = create_sqlite_agent_post_like_repository(
            transaction_provider=sqlite_tx
        )

        _seed_agent(agent_repo, agent_id="did:plc:agent1", handle="agent1.bsky.social")
        _seed_agent(agent_repo, agent_id="did:plc:agent2", handle="agent2.bsky.social")

        _seed_agent_post(
            agent_post_repo=agent_post_repo,
            agent_post_id="ap1",
            agent_id="did:plc:agent1",
        )
        _seed_agent_post(
            agent_post_repo=agent_post_repo,
            agent_post_id="ap2",
            agent_id="did:plc:agent2",
        )

        rows = [
            AgentPostLike(
                agent_post_like_id="apl_1",
                agent_post_id="ap1",
                liker_agent_id="did:plc:agent1",
                created_at="2026-03-17T00:00:00Z",
            ),
            AgentPostLike(
                agent_post_like_id="apl_2",
                agent_post_id="ap1",
                liker_agent_id="did:plc:agent2",
                created_at="2026-03-17T00:00:01Z",
            ),
            AgentPostLike(
                agent_post_like_id="apl_3",
                agent_post_id="ap2",
                liker_agent_id="did:plc:agent1",
                created_at="2026-03-17T00:00:02Z",
            ),
        ]

        like_repo.write_agent_post_likes(rows)

        result = like_repo.list_likes_for_agent_post_ids(["ap2", "ap1"])

        assert [(row.agent_post_id, row.liker_agent_id) for row in result] == [
            ("ap1", "did:plc:agent1"),
            ("ap1", "did:plc:agent2"),
            ("ap2", "did:plc:agent1"),
        ]
        assert [row.agent_post_like_id for row in result] == ["apl_1", "apl_2", "apl_3"]

    def test_duplicate_seed_like_is_ignored_by_unique_constraint(
        self,
        agent_repo,
        agent_post_repo,
        sqlite_tx,
    ) -> None:
        like_repo = create_sqlite_agent_post_like_repository(
            transaction_provider=sqlite_tx
        )

        _seed_agent(agent_repo, agent_id="did:plc:agent1", handle="agent1.bsky.social")
        _seed_agent_post(
            agent_post_repo=agent_post_repo,
            agent_post_id="ap1",
            agent_id="did:plc:agent1",
        )

        first = AgentPostLike(
            agent_post_like_id="apl_1",
            agent_post_id="ap1",
            liker_agent_id="did:plc:agent1",
            created_at="2026-03-17T00:00:00Z",
        )
        like_repo.write_agent_post_likes([first])

        # Same (liker_agent_id, agent_post_id) => unique conflict.
        second = AgentPostLike(
            agent_post_like_id="apl_1_DUP",
            agent_post_id="ap1",
            liker_agent_id="did:plc:agent1",
            created_at="2026-03-17T00:00:01Z",
        )
        like_repo.write_agent_post_likes([second])

        result = like_repo.list_likes_for_agent_post_ids(["ap1"])
        assert len(result) == 1
        assert result[0].agent_post_like_id == "apl_1"

    def test_db_constraint_failure_rolls_back_batch(
        self,
        agent_repo,
        agent_post_repo,
        sqlite_tx,
    ) -> None:
        like_repo = create_sqlite_agent_post_like_repository(
            transaction_provider=sqlite_tx
        )

        _seed_agent(agent_repo, agent_id="did:plc:agent1", handle="agent1.bsky.social")
        _seed_agent_post(
            agent_post_repo=agent_post_repo,
            agent_post_id="ap1",
            agent_id="did:plc:agent1",
        )

        valid_row = AgentPostLike(
            agent_post_like_id="apl_valid",
            agent_post_id="ap1",
            liker_agent_id="did:plc:agent1",
            created_at="2026-03-17T00:00:00Z",
        )
        invalid_row = AgentPostLike(
            agent_post_like_id="apl_invalid",
            agent_post_id="ap1",
            liker_agent_id="did:plc:missing",
            created_at="2026-03-17T00:00:01Z",
        )

        with pytest.raises(sqlite3.IntegrityError):
            like_repo.write_agent_post_likes([valid_row, invalid_row])

        assert like_repo.list_likes_for_agent_post_ids(["ap1"]) == []
