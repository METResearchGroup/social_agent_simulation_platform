"""Integration tests for db.repositories.agent_post_comment_repository module."""

import sqlite3

import pytest

from db.repositories.agent_post_comment_repository import (
    create_sqlite_agent_post_comment_repository,
)
from simulation.core.models.agent_post_comments import AgentPostComment
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


class TestSQLiteAgentPostCommentRepositoryIntegration:
    def test_write_and_list_round_trips_in_deterministic_order(
        self,
        agent_repo,
        agent_post_repo,
        sqlite_tx,
    ) -> None:
        comment_repo = create_sqlite_agent_post_comment_repository(
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
            AgentPostComment(
                agent_post_comment_id="apc_1",
                agent_post_id="ap1",
                author_agent_id="did:plc:agent1",
                body_text="First",
                published_at="2026-03-17T00:00:00Z",
                created_at="2026-03-17T00:00:00Z",
                updated_at="2026-03-17T00:00:00Z",
            ),
            AgentPostComment(
                agent_post_comment_id="apc_2",
                agent_post_id="ap1",
                author_agent_id="did:plc:agent2",
                body_text="Second",
                published_at="2026-03-17T00:00:01Z",
                created_at="2026-03-17T00:00:01Z",
                updated_at="2026-03-17T00:00:01Z",
            ),
            AgentPostComment(
                agent_post_comment_id="apc_3",
                agent_post_id="ap2",
                author_agent_id="did:plc:agent1",
                body_text="Third",
                published_at="2026-03-17T00:00:02Z",
                created_at="2026-03-17T00:00:02Z",
                updated_at="2026-03-17T00:00:02Z",
            ),
        ]

        comment_repo.write_agent_post_comments(rows)

        result = comment_repo.list_comments_for_agent_post_ids(["ap2", "ap1"])

        assert [(row.agent_post_id, row.author_agent_id) for row in result] == [
            ("ap1", "did:plc:agent1"),
            ("ap1", "did:plc:agent2"),
            ("ap2", "did:plc:agent1"),
        ]
        assert [row.agent_post_comment_id for row in result] == [
            "apc_1",
            "apc_2",
            "apc_3",
        ]

    def test_duplicate_primary_key_is_ignored_by_insert_or_ignore(
        self,
        agent_repo,
        agent_post_repo,
        sqlite_tx,
    ) -> None:
        comment_repo = create_sqlite_agent_post_comment_repository(
            transaction_provider=sqlite_tx
        )

        _seed_agent(agent_repo, agent_id="did:plc:agent1", handle="agent1.bsky.social")
        _seed_agent_post(
            agent_post_repo=agent_post_repo,
            agent_post_id="ap1",
            agent_id="did:plc:agent1",
        )

        first = AgentPostComment(
            agent_post_comment_id="apc_1",
            agent_post_id="ap1",
            author_agent_id="did:plc:agent1",
            body_text="Hello",
            published_at="2026-03-17T00:00:00Z",
            created_at="2026-03-17T00:00:00Z",
            updated_at="2026-03-17T00:00:00Z",
        )
        comment_repo.write_agent_post_comments([first])

        second = AgentPostComment(
            agent_post_comment_id="apc_1",
            agent_post_id="ap1",
            author_agent_id="did:plc:agent1",
            body_text="Different body",
            published_at="2026-03-17T00:00:01Z",
            created_at="2026-03-17T00:00:01Z",
            updated_at="2026-03-17T00:00:01Z",
        )
        comment_repo.write_agent_post_comments([second])

        result = comment_repo.list_comments_for_agent_post_ids(["ap1"])
        assert len(result) == 1
        assert result[0].body_text == "Hello"

    def test_db_constraint_failure_rolls_back_batch(
        self,
        agent_repo,
        agent_post_repo,
        sqlite_tx,
    ) -> None:
        comment_repo = create_sqlite_agent_post_comment_repository(
            transaction_provider=sqlite_tx
        )

        _seed_agent(agent_repo, agent_id="did:plc:agent1", handle="agent1.bsky.social")
        _seed_agent_post(
            agent_post_repo=agent_post_repo,
            agent_post_id="ap1",
            agent_id="did:plc:agent1",
        )

        valid_row = AgentPostComment(
            agent_post_comment_id="apc_valid",
            agent_post_id="ap1",
            author_agent_id="did:plc:agent1",
            body_text="ok",
            published_at="2026-03-17T00:00:00Z",
            created_at="2026-03-17T00:00:00Z",
            updated_at="2026-03-17T00:00:00Z",
        )
        invalid_row = AgentPostComment(
            agent_post_comment_id="apc_invalid",
            agent_post_id="ap1",
            author_agent_id="did:plc:missing",
            body_text="bad",
            published_at="2026-03-17T00:00:01Z",
            created_at="2026-03-17T00:00:01Z",
            updated_at="2026-03-17T00:00:01Z",
        )

        with pytest.raises(sqlite3.IntegrityError):
            comment_repo.write_agent_post_comments([valid_row, invalid_row])

        assert comment_repo.list_comments_for_agent_post_ids(["ap1"]) == []
