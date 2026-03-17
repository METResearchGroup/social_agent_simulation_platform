"""Integration tests for db.repositories.agent_post_repository module."""

import sqlite3

import pytest

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


class TestSQLiteAgentPostRepositoryIntegration:
    def test_upsert_imported_agent_posts_is_idempotent_when_data_unchanged(
        self,
        agent_repo,
        agent_post_repo,
    ):
        _seed_agent(
            agent_repo,
            agent_id="did:plc:agent1",
            handle="agent1.bsky.social",
        )

        first = AgentPost(
            agent_post_id="agent_post_1",
            agent_id="did:plc:agent1",
            body_text="hello",
            published_at="2026-03-17T00:00:00Z",
            created_at="2026-03-17T01:00:00Z",
            updated_at="2026-03-17T01:00:00Z",
            source_post_id="bluesky:at://post/1",
            source="bluesky",
            source_uri="at://post/1",
        )
        agent_post_repo.upsert_imported_agent_posts([first])

        # Rerun with only timestamps changed; should not update because idempotent
        # comparisons exclude created_at/updated_at.
        second = AgentPost(
            agent_post_id="agent_post_1",
            agent_id="did:plc:agent1",
            body_text="hello",
            published_at="2026-03-17T00:00:00Z",
            created_at="2026-03-17T02:00:00Z",
            updated_at="2026-03-17T02:00:00Z",
            source_post_id="bluesky:at://post/1",
            source="bluesky",
            source_uri="at://post/1",
        )
        agent_post_repo.upsert_imported_agent_posts([second])

        assert agent_post_repo.count_all_posts() == 1
        posts = agent_post_repo.list_posts_for_agent_ids(["did:plc:agent1"])
        assert posts[0].body_text == "hello"
        assert posts[0].created_at == "2026-03-17T01:00:00Z"
        assert posts[0].updated_at == "2026-03-17T01:00:00Z"

    def test_upsert_imported_agent_posts_updates_when_body_changes(
        self,
        agent_repo,
        agent_post_repo,
    ):
        _seed_agent(
            agent_repo,
            agent_id="did:plc:agent1",
            handle="agent1.bsky.social",
        )

        agent_post_repo.upsert_imported_agent_posts(
            [
                AgentPost(
                    agent_post_id="agent_post_1",
                    agent_id="did:plc:agent1",
                    body_text="hello",
                    published_at="2026-03-17T00:00:00Z",
                    created_at="2026-03-17T01:00:00Z",
                    updated_at="2026-03-17T01:00:00Z",
                    source_post_id="bluesky:at://post/1",
                    source="bluesky",
                    source_uri="at://post/1",
                )
            ]
        )

        agent_post_repo.upsert_imported_agent_posts(
            [
                AgentPost(
                    agent_post_id="agent_post_1",
                    agent_id="did:plc:agent1",
                    body_text="hello updated",
                    published_at="2026-03-17T00:00:00Z",
                    created_at="2026-03-17T02:00:00Z",
                    updated_at="2026-03-17T02:00:00Z",
                    source_post_id="bluesky:at://post/1",
                    source="bluesky",
                    source_uri="at://post/1",
                )
            ]
        )

        posts = agent_post_repo.list_posts_for_agent_ids(["did:plc:agent1"])
        assert posts[0].body_text == "hello updated"
        assert posts[0].created_at == "2026-03-17T01:00:00Z"
        assert posts[0].updated_at == "2026-03-17T02:00:00Z"

    def test_count_posts_by_agent_ids_includes_zeros(self, agent_repo, agent_post_repo):
        _seed_agent(
            agent_repo,
            agent_id="did:plc:agent1",
            handle="agent1.bsky.social",
        )
        _seed_agent(
            agent_repo,
            agent_id="did:plc:agent2",
            handle="agent2.bsky.social",
        )

        agent_post_repo.upsert_imported_agent_posts(
            [
                AgentPost(
                    agent_post_id="agent_post_1",
                    agent_id="did:plc:agent1",
                    body_text="hello",
                    published_at="2026-03-17T00:00:00Z",
                    created_at="2026-03-17T01:00:00Z",
                    updated_at="2026-03-17T01:00:00Z",
                    source_post_id="bluesky:at://post/1",
                    source="bluesky",
                )
            ]
        )

        counts = agent_post_repo.count_posts_by_agent_ids(
            ["did:plc:agent1", "did:plc:agent2"]
        )

        assert counts == {"did:plc:agent1": 1, "did:plc:agent2": 0}

    def test_fk_failure_rolls_back_batch(self, temp_db, agent_repo, agent_post_repo):
        _seed_agent(
            agent_repo,
            agent_id="did:plc:agent1",
            handle="agent1.bsky.social",
        )

        with sqlite3.connect(temp_db) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("BEGIN")
            with pytest.raises(sqlite3.IntegrityError):
                agent_post_repo.upsert_imported_agent_posts(
                    [
                        AgentPost(
                            agent_post_id="agent_post_1",
                            agent_id="did:plc:agent1",
                            body_text="hello",
                            published_at="2026-03-17T00:00:00Z",
                            created_at="2026-03-17T01:00:00Z",
                            updated_at="2026-03-17T01:00:00Z",
                            source_post_id="bluesky:at://post/1",
                            source="bluesky",
                        ),
                        AgentPost(
                            agent_post_id="agent_post_2",
                            agent_id="did:plc:missing",
                            body_text="bad",
                            published_at="2026-03-17T00:00:00Z",
                            created_at="2026-03-17T01:00:00Z",
                            updated_at="2026-03-17T01:00:00Z",
                            source_post_id="bluesky:at://post/2",
                            source="bluesky",
                        ),
                    ],
                    conn=conn,
                )
            conn.execute("ROLLBACK")

        assert agent_post_repo.count_all_posts() == 0
