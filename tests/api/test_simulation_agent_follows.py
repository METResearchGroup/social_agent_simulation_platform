"""Tests for simulation agent follow-edge API endpoints."""

from simulation.core.models.agent_follow_edge import AgentFollowEdge
from tests.factories import AgentRecordFactory, UserAgentProfileMetadataFactory


def _seed_agent(
    agent_repo,
    user_agent_profile_metadata_repo,
    *,
    agent_id: str,
    handle: str,
) -> None:
    agent_repo.create_or_update_agent(
        AgentRecordFactory.create(
            agent_id=agent_id,
            handle=handle,
            display_name=handle,
            created_at="2026-03-17T00:00:00Z",
            updated_at="2026-03-17T00:00:00Z",
        )
    )
    user_agent_profile_metadata_repo.create_or_update_metadata(
        UserAgentProfileMetadataFactory.create(
            metadata_id=f"meta_{agent_id}",
            agent_id=agent_id,
            followers_count=0,
            follows_count=0,
            posts_count=0,
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


def _list_agents_by_handle(client) -> dict[str, dict]:
    response = client.get("/v1/simulations/agents?limit=100&offset=0")
    assert response.status_code == 200
    payload = response.json()
    return {agent["handle"]: agent for agent in payload}


class TestSimulationAgentFollows:
    def test_get_simulation_agent_follows_returns_empty_page(
        self,
        simulation_client,
        agent_repo,
        user_agent_profile_metadata_repo,
    ) -> None:
        _seed_agent(
            agent_repo,
            user_agent_profile_metadata_repo,
            agent_id="agent_a",
            handle="@alice.bsky.social",
        )

        client, _ = simulation_client
        response = client.get(
            "/v1/simulations/agents/@alice.bsky.social/follows?limit=10&offset=0"
        )

        expected_result = {"status_code": 200, "total": 0, "items": []}
        assert response.status_code == expected_result["status_code"]
        assert response.json() == {
            "total": expected_result["total"],
            "items": expected_result["items"],
        }

    def test_get_simulation_agent_follows_paginates_deterministically(
        self,
        simulation_client,
        agent_repo,
        user_agent_profile_metadata_repo,
        agent_follow_edge_repo,
    ) -> None:
        _seed_agent(
            agent_repo,
            user_agent_profile_metadata_repo,
            agent_id="agent_a",
            handle="@alice.bsky.social",
        )
        _seed_agent(
            agent_repo,
            user_agent_profile_metadata_repo,
            agent_id="agent_b",
            handle="@bob.bsky.social",
        )
        _seed_agent(
            agent_repo,
            user_agent_profile_metadata_repo,
            agent_id="agent_c",
            handle="@charlie.bsky.social",
        )
        agent_follow_edge_repo.create_edge(
            edge=_build_edge(
                edge_id="edge_2",
                follower_agent_id="agent_a",
                target_agent_id="agent_c",
            )
        )
        agent_follow_edge_repo.create_edge(
            edge=_build_edge(
                edge_id="edge_1",
                follower_agent_id="agent_a",
                target_agent_id="agent_b",
            )
        )

        client, _ = simulation_client
        response = client.get(
            "/v1/simulations/agents/@alice.bsky.social/follows?limit=1&offset=1"
        )

        expected_result = {
            "status_code": 200,
            "payload": {
                "total": 2,
                "items": [
                    {
                        "agent_follow_edge_id": "edge_2",
                        "follower_handle": "@alice.bsky.social",
                        "target_handle": "@charlie.bsky.social",
                        "created_at": "2026-03-17T00:00:00Z",
                    }
                ],
            },
        }
        assert response.status_code == expected_result["status_code"]
        assert response.json() == expected_result["payload"]

    def test_post_simulation_agent_follow_creates_edge_and_syncs_counts(
        self,
        simulation_client,
        agent_repo,
        user_agent_profile_metadata_repo,
    ) -> None:
        _seed_agent(
            agent_repo,
            user_agent_profile_metadata_repo,
            agent_id="agent_a",
            handle="@alice.bsky.social",
        )
        _seed_agent(
            agent_repo,
            user_agent_profile_metadata_repo,
            agent_id="agent_b",
            handle="@bob.bsky.social",
        )

        client, _ = simulation_client
        response = client.post(
            "/v1/simulations/agents/@alice.bsky.social/follows",
            json={"target_handle": "@bob.bsky.social"},
        )

        expected_result = {
            "status_code": 201,
            "follower_handle": "@alice.bsky.social",
            "target_handle": "@bob.bsky.social",
        }
        assert response.status_code == expected_result["status_code"]
        payload = response.json()
        assert payload["follower_handle"] == expected_result["follower_handle"]
        assert payload["target_handle"] == expected_result["target_handle"]
        assert payload["agent_follow_edge_id"]
        assert payload["created_at"]

        follows_response = client.get(
            "/v1/simulations/agents/@alice.bsky.social/follows?limit=10&offset=0"
        )
        expected_follows = {"status_code": 200, "total": 1}
        assert follows_response.status_code == expected_follows["status_code"]
        follows_payload = follows_response.json()
        assert follows_payload["total"] == expected_follows["total"]
        assert [item["target_handle"] for item in follows_payload["items"]] == [
            "@bob.bsky.social"
        ]

        agents_by_handle = _list_agents_by_handle(client)
        expected_counts = {
            "@alice.bsky.social": {"following": 1, "followers": 0},
            "@bob.bsky.social": {"following": 0, "followers": 1},
        }
        assert (
            agents_by_handle["@alice.bsky.social"]["following"]
            == expected_counts["@alice.bsky.social"]["following"]
        )
        assert (
            agents_by_handle["@alice.bsky.social"]["followers"]
            == expected_counts["@alice.bsky.social"]["followers"]
        )
        assert (
            agents_by_handle["@bob.bsky.social"]["following"]
            == expected_counts["@bob.bsky.social"]["following"]
        )
        assert (
            agents_by_handle["@bob.bsky.social"]["followers"]
            == expected_counts["@bob.bsky.social"]["followers"]
        )

    def test_post_simulation_agent_follow_duplicate_returns_409(
        self,
        simulation_client,
        agent_repo,
        user_agent_profile_metadata_repo,
    ) -> None:
        _seed_agent(
            agent_repo,
            user_agent_profile_metadata_repo,
            agent_id="agent_a",
            handle="@alice.bsky.social",
        )
        _seed_agent(
            agent_repo,
            user_agent_profile_metadata_repo,
            agent_id="agent_b",
            handle="@bob.bsky.social",
        )

        client, _ = simulation_client
        client.post(
            "/v1/simulations/agents/@alice.bsky.social/follows",
            json={"target_handle": "@bob.bsky.social"},
        )
        response = client.post(
            "/v1/simulations/agents/@alice.bsky.social/follows",
            json={"target_handle": "@bob.bsky.social"},
        )

        expected_result = {
            "status_code": 409,
            "error_code": "FOLLOW_EDGE_ALREADY_EXISTS",
        }
        assert response.status_code == expected_result["status_code"]
        assert response.json()["error"]["code"] == expected_result["error_code"]

    def test_post_simulation_agent_follow_self_follow_returns_422(
        self,
        simulation_client,
        agent_repo,
        user_agent_profile_metadata_repo,
    ) -> None:
        _seed_agent(
            agent_repo,
            user_agent_profile_metadata_repo,
            agent_id="agent_a",
            handle="@alice.bsky.social",
        )

        client, _ = simulation_client
        response = client.post(
            "/v1/simulations/agents/@alice.bsky.social/follows",
            json={"target_handle": "@alice.bsky.social"},
        )

        expected_result = {
            "status_code": 422,
            "error_code": "SELF_FOLLOW_NOT_ALLOWED",
        }
        assert response.status_code == expected_result["status_code"]
        assert response.json()["error"]["code"] == expected_result["error_code"]

    def test_post_simulation_agent_follow_missing_agents_return_404(
        self,
        simulation_client,
        agent_repo,
        user_agent_profile_metadata_repo,
    ) -> None:
        _seed_agent(
            agent_repo,
            user_agent_profile_metadata_repo,
            agent_id="agent_a",
            handle="@alice.bsky.social",
        )

        client, _ = simulation_client
        missing_source = client.post(
            "/v1/simulations/agents/@missing.bsky.social/follows",
            json={"target_handle": "@alice.bsky.social"},
        )
        expected_missing_source = {
            "status_code": 404,
            "error_code": "AGENT_NOT_FOUND",
        }
        assert missing_source.status_code == expected_missing_source["status_code"]
        assert (
            missing_source.json()["error"]["code"]
            == expected_missing_source["error_code"]
        )

        missing_target = client.post(
            "/v1/simulations/agents/@alice.bsky.social/follows",
            json={"target_handle": "@missing.bsky.social"},
        )
        expected_missing_target = {
            "status_code": 404,
            "error_code": "TARGET_AGENT_NOT_FOUND",
        }
        assert missing_target.status_code == expected_missing_target["status_code"]
        assert (
            missing_target.json()["error"]["code"]
            == expected_missing_target["error_code"]
        )

    def test_delete_simulation_agent_follow_returns_204_and_syncs_counts(
        self,
        simulation_client,
        agent_repo,
        user_agent_profile_metadata_repo,
    ) -> None:
        _seed_agent(
            agent_repo,
            user_agent_profile_metadata_repo,
            agent_id="agent_a",
            handle="@alice.bsky.social",
        )
        _seed_agent(
            agent_repo,
            user_agent_profile_metadata_repo,
            agent_id="agent_b",
            handle="@bob.bsky.social",
        )

        client, _ = simulation_client
        create_response = client.post(
            "/v1/simulations/agents/@alice.bsky.social/follows",
            json={"target_handle": "@bob.bsky.social"},
        )
        assert create_response.status_code == 201

        delete_response = client.delete(
            "/v1/simulations/agents/@alice.bsky.social/follows/@bob.bsky.social"
        )
        expected_delete = {"status_code": 204}
        assert delete_response.status_code == expected_delete["status_code"]

        follows_response = client.get(
            "/v1/simulations/agents/@alice.bsky.social/follows?limit=10&offset=0"
        )
        expected_follows = {"status_code": 200, "payload": {"total": 0, "items": []}}
        assert follows_response.status_code == expected_follows["status_code"]
        assert follows_response.json() == expected_follows["payload"]

        agents_by_handle = _list_agents_by_handle(client)
        expected_counts = {
            "@alice.bsky.social": {"following": 0, "followers": 0},
            "@bob.bsky.social": {"following": 0, "followers": 0},
        }
        assert (
            agents_by_handle["@alice.bsky.social"]["following"]
            == expected_counts["@alice.bsky.social"]["following"]
        )
        assert (
            agents_by_handle["@bob.bsky.social"]["followers"]
            == expected_counts["@bob.bsky.social"]["followers"]
        )

    def test_delete_simulation_agent_follow_missing_edge_returns_404(
        self,
        simulation_client,
        agent_repo,
        user_agent_profile_metadata_repo,
    ) -> None:
        _seed_agent(
            agent_repo,
            user_agent_profile_metadata_repo,
            agent_id="agent_a",
            handle="@alice.bsky.social",
        )
        _seed_agent(
            agent_repo,
            user_agent_profile_metadata_repo,
            agent_id="agent_b",
            handle="@bob.bsky.social",
        )

        client, _ = simulation_client
        response = client.delete(
            "/v1/simulations/agents/@alice.bsky.social/follows/@bob.bsky.social"
        )

        expected_result = {
            "status_code": 404,
            "error_code": "FOLLOW_EDGE_NOT_FOUND",
        }
        assert response.status_code == expected_result["status_code"]
        assert response.json()["error"]["code"] == expected_result["error_code"]
