"""Integration tests for db.repositories.agent_follow_edge_repository module."""

from db.repositories.agent_follow_edge_repository import DuplicateAgentFollowEdgeError
from simulation.core.models.agent import PersonaSource
from tests.factories import AgentFollowEdgeFactory, AgentRecordFactory


class TestSQLiteAgentFollowEdgeRepositoryIntegration:
    """Integration tests for AgentFollowEdgeRepository using a real database."""

    def test_create_and_get_agent_follow_edge(self, agent_follow_edge_repo, agent_repo):
        follower_agent_id = "did:plc:follower"
        target_agent_id = "did:plc:target"
        _seed_agent(
            agent_repo=agent_repo,
            agent_id=follower_agent_id,
            handle="@follower.bsky.social",
        )
        _seed_agent(
            agent_repo=agent_repo,
            agent_id=target_agent_id,
            handle="@target.bsky.social",
        )

        edge = AgentFollowEdgeFactory.create(
            agent_follow_edge_id="edge_1",
            follower_agent_id=follower_agent_id,
            target_agent_id=target_agent_id,
            created_at="2026_03_13-10:00:00",
        )

        created = agent_follow_edge_repo.create_agent_follow_edge(edge)
        retrieved = agent_follow_edge_repo.get_agent_follow_edge(
            follower_agent_id,
            target_agent_id,
        )

        assert created.agent_follow_edge_id == "edge_1"
        assert retrieved is not None
        assert retrieved.agent_follow_edge_id == "edge_1"
        assert retrieved.follower_agent_id == follower_agent_id
        assert retrieved.target_agent_id == target_agent_id

    def test_list_agent_follow_edges_by_follower_agent_id_is_paginated_and_deterministic(
        self, agent_follow_edge_repo, agent_repo
    ):
        follower_agent_id = "did:plc:follower"
        _seed_agent(
            agent_repo=agent_repo,
            agent_id=follower_agent_id,
            handle="@follower.bsky.social",
        )
        for target_agent_id, handle, edge_id in [
            ("did:plc:ccc", "@ccc.bsky.social", "edge_c"),
            ("did:plc:aaa", "@aaa.bsky.social", "edge_a"),
            ("did:plc:bbb", "@bbb.bsky.social", "edge_b"),
        ]:
            _seed_agent(agent_repo=agent_repo, agent_id=target_agent_id, handle=handle)
            agent_follow_edge_repo.create_agent_follow_edge(
                AgentFollowEdgeFactory.create(
                    agent_follow_edge_id=edge_id,
                    follower_agent_id=follower_agent_id,
                    target_agent_id=target_agent_id,
                    created_at="2026_03_13-10:00:00",
                )
            )

        page0 = agent_follow_edge_repo.list_agent_follow_edges_by_follower_agent_id(
            follower_agent_id,
            limit=2,
            offset=0,
        )
        page1 = agent_follow_edge_repo.list_agent_follow_edges_by_follower_agent_id(
            follower_agent_id,
            limit=2,
            offset=2,
        )

        assert [edge.target_agent_id for edge in page0] == [
            "did:plc:aaa",
            "did:plc:bbb",
        ]
        assert [edge.target_agent_id for edge in page1] == ["did:plc:ccc"]

    def test_count_methods_reflect_current_edges(
        self, agent_follow_edge_repo, agent_repo
    ):
        _seed_agent(
            agent_repo=agent_repo,
            agent_id="did:plc:a",
            handle="@a.bsky.social",
        )
        _seed_agent(
            agent_repo=agent_repo,
            agent_id="did:plc:b",
            handle="@b.bsky.social",
        )
        _seed_agent(
            agent_repo=agent_repo,
            agent_id="did:plc:c",
            handle="@c.bsky.social",
        )

        agent_follow_edge_repo.create_agent_follow_edge(
            AgentFollowEdgeFactory.create(
                agent_follow_edge_id="edge_ab",
                follower_agent_id="did:plc:a",
                target_agent_id="did:plc:b",
                created_at="2026_03_13-10:00:00",
            )
        )
        agent_follow_edge_repo.create_agent_follow_edge(
            AgentFollowEdgeFactory.create(
                agent_follow_edge_id="edge_ac",
                follower_agent_id="did:plc:a",
                target_agent_id="did:plc:c",
                created_at="2026_03_13-10:00:00",
            )
        )

        assert (
            agent_follow_edge_repo.count_agent_follow_edges_by_follower_agent_id(
                "did:plc:a"
            )
            == 2
        )
        assert (
            agent_follow_edge_repo.count_agent_follow_edges_by_target_agent_id(
                "did:plc:b"
            )
            == 1
        )

    def test_delete_agent_follow_edge_returns_true_only_when_row_exists(
        self, agent_follow_edge_repo, agent_repo
    ):
        follower_agent_id = "did:plc:follower"
        target_agent_id = "did:plc:target"
        _seed_agent(
            agent_repo=agent_repo,
            agent_id=follower_agent_id,
            handle="@follower.bsky.social",
        )
        _seed_agent(
            agent_repo=agent_repo,
            agent_id=target_agent_id,
            handle="@target.bsky.social",
        )
        agent_follow_edge_repo.create_agent_follow_edge(
            AgentFollowEdgeFactory.create(
                agent_follow_edge_id="edge_delete",
                follower_agent_id=follower_agent_id,
                target_agent_id=target_agent_id,
                created_at="2026_03_13-10:00:00",
            )
        )

        assert (
            agent_follow_edge_repo.delete_agent_follow_edge(
                follower_agent_id,
                target_agent_id,
            )
            is True
        )
        assert (
            agent_follow_edge_repo.delete_agent_follow_edge(
                follower_agent_id,
                target_agent_id,
            )
            is False
        )

    def test_create_duplicate_agent_follow_edge_raises_repository_error(
        self, agent_follow_edge_repo, agent_repo
    ):
        follower_agent_id = "did:plc:follower"
        target_agent_id = "did:plc:target"
        _seed_agent(
            agent_repo=agent_repo,
            agent_id=follower_agent_id,
            handle="@follower.bsky.social",
        )
        _seed_agent(
            agent_repo=agent_repo,
            agent_id=target_agent_id,
            handle="@target.bsky.social",
        )

        edge = AgentFollowEdgeFactory.create(
            agent_follow_edge_id="edge_dup",
            follower_agent_id=follower_agent_id,
            target_agent_id=target_agent_id,
            created_at="2026_03_13-10:00:00",
        )
        agent_follow_edge_repo.create_agent_follow_edge(edge)

        try:
            agent_follow_edge_repo.create_agent_follow_edge(
                AgentFollowEdgeFactory.create(
                    agent_follow_edge_id="edge_dup_2",
                    follower_agent_id=follower_agent_id,
                    target_agent_id=target_agent_id,
                    created_at="2026_03_13-10:00:01",
                )
            )
        except DuplicateAgentFollowEdgeError:
            pass
        else:
            raise AssertionError(
                "Expected DuplicateAgentFollowEdgeError for duplicate follow edge"
            )


def _seed_agent(*, agent_repo, agent_id: str, handle: str) -> None:
    agent_repo.create_or_update_agent(
        AgentRecordFactory.create(
            agent_id=agent_id,
            handle=handle,
            persona_source=PersonaSource.SYNC_BLUESKY,
            display_name=handle,
            created_at="2026_03_13-10:00:00",
            updated_at="2026_03_13-10:00:00",
        )
    )
