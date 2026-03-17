"""Integration tests for db.repositories.agent_follow_edge_repository module."""

import pytest

from simulation.core.models.agent_follow_edge import AgentFollowEdge
from simulation.core.utils.exceptions import DuplicateAgentFollowEdgeError
from tests.factories import AgentRecordFactory


def _seed_agents(agent_repo) -> None:
    for agent_id, handle in [
        ("agent_a", "@alice.bsky.social"),
        ("agent_b", "@bob.bsky.social"),
        ("agent_c", "@charlie.bsky.social"),
    ]:
        agent_repo.create_or_update_agent(
            AgentRecordFactory.create(
                agent_id=agent_id,
                handle=handle,
                display_name=handle,
                created_at="2026-03-17T00:00:00Z",
                updated_at="2026-03-17T00:00:00Z",
            )
        )


def _build_edge(
    *,
    edge_id: str,
    follower_agent_id: str,
    target_agent_id: str,
) -> AgentFollowEdge:
    return AgentFollowEdge(
        agent_follow_edge_id=edge_id,
        follower_agent_id=follower_agent_id,
        target_agent_id=target_agent_id,
        created_at="2026-03-17T00:00:00Z",
    )


class TestSQLiteAgentFollowEdgeRepositoryIntegration:
    def test_create_list_count_and_paginate_edges(
        self,
        agent_repo,
        agent_follow_edge_repo,
    ) -> None:
        _seed_agents(agent_repo)
        agent_follow_edge_repo.create_edge(
            _build_edge(
                edge_id="edge_2",
                follower_agent_id="agent_a",
                target_agent_id="agent_c",
            )
        )
        agent_follow_edge_repo.create_edge(
            _build_edge(
                edge_id="edge_1",
                follower_agent_id="agent_a",
                target_agent_id="agent_b",
            )
        )

        result = agent_follow_edge_repo.list_edges_by_follower_agent_id(
            "agent_a",
            limit=10,
            offset=0,
        )
        expected_result = {
            "edge_ids": ["edge_1", "edge_2"],
            "targets": ["agent_b", "agent_c"],
            "follower_count": 2,
            "target_b_count": 1,
            "target_c_count": 1,
        }
        assert [edge.agent_follow_edge_id for edge in result] == expected_result[
            "edge_ids"
        ]
        assert [edge.target_agent_id for edge in result] == expected_result["targets"]
        assert (
            agent_follow_edge_repo.count_edges_by_follower_agent_id("agent_a")
            == expected_result["follower_count"]
        )
        assert (
            agent_follow_edge_repo.count_edges_by_target_agent_id("agent_b")
            == expected_result["target_b_count"]
        )
        assert (
            agent_follow_edge_repo.count_edges_by_target_agent_id("agent_c")
            == expected_result["target_c_count"]
        )

        paged = agent_follow_edge_repo.list_edges_by_follower_agent_id(
            "agent_a",
            limit=1,
            offset=1,
        )
        expected_paged_edge_ids = ["edge_2"]
        assert [edge.agent_follow_edge_id for edge in paged] == expected_paged_edge_ids

        edge_page = agent_follow_edge_repo.get_edge_page_by_follower_agent_id(
            "agent_a",
            limit=1,
            offset=1,
        )
        expected_page = {
            "total": 2,
            "edge_ids": ["edge_2"],
            "target_handles": ["@charlie.bsky.social"],
        }
        assert edge_page.total == expected_page["total"]
        assert [edge.agent_follow_edge_id for edge in edge_page.items] == expected_page[
            "edge_ids"
        ]
        assert [edge.target_handle for edge in edge_page.items] == expected_page[
            "target_handles"
        ]

    def test_duplicate_edge_raises_integrity_error(
        self,
        agent_repo,
        agent_follow_edge_repo,
    ) -> None:
        _seed_agents(agent_repo)
        edge = _build_edge(
            edge_id="edge_1",
            follower_agent_id="agent_a",
            target_agent_id="agent_b",
        )
        agent_follow_edge_repo.create_edge(edge)

        with pytest.raises(DuplicateAgentFollowEdgeError):
            agent_follow_edge_repo.create_edge(
                _build_edge(
                    edge_id="edge_2",
                    follower_agent_id="agent_a",
                    target_agent_id="agent_b",
                )
            )

    def test_delete_edge_and_delete_edges_for_agent(
        self,
        agent_repo,
        agent_follow_edge_repo,
    ) -> None:
        _seed_agents(agent_repo)
        agent_follow_edge_repo.create_edge(
            _build_edge(
                edge_id="edge_1",
                follower_agent_id="agent_a",
                target_agent_id="agent_b",
            )
        )
        agent_follow_edge_repo.create_edge(
            _build_edge(
                edge_id="edge_2",
                follower_agent_id="agent_c",
                target_agent_id="agent_a",
            )
        )

        deleted = agent_follow_edge_repo.delete_edge("agent_a", "agent_b")
        expected_deleted = True
        assert deleted is expected_deleted
        assert agent_follow_edge_repo.delete_edge("agent_a", "agent_b") is False

        connected_agent_ids = agent_follow_edge_repo.list_connected_agent_ids("agent_a")
        expected_connected_agent_ids = ["agent_c"]
        assert connected_agent_ids == expected_connected_agent_ids

        agent_follow_edge_repo.delete_edges_for_agent("agent_a")
        expected_counts = {
            "follower_count": 0,
            "target_count": 0,
        }
        assert (
            agent_follow_edge_repo.count_edges_by_follower_agent_id("agent_c")
            == expected_counts["follower_count"]
        )
        assert (
            agent_follow_edge_repo.count_edges_by_target_agent_id("agent_a")
            == expected_counts["target_count"]
        )
