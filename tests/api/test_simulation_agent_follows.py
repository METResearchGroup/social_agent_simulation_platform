"""Tests for editable agent follow-edge API endpoints."""

from simulation.core.models.agent import PersonaSource
from tests.factories import AgentRecordFactory, UserAgentProfileMetadataFactory


class TestSimulationAgentFollows:
    def test_get_agent_follows_returns_empty_paginated_response_for_existing_agent(
        self,
        simulation_client,
        agent_repo,
    ):
        _seed_agent(
            agent_repo=agent_repo,
            agent_id="did:plc:alice",
            handle="@alice.bsky.social",
        )

        client, _ = simulation_client
        response = client.get("/v1/simulations/agents/@alice.bsky.social/follows")

        expected_result = {"status_code": 200, "body": {"total": 0, "items": []}}
        assert response.status_code == expected_result["status_code"]
        assert response.json() == expected_result["body"]

    def test_get_agent_follows_returns_404_when_follower_agent_missing(
        self,
        simulation_client,
    ):
        client, _ = simulation_client
        response = client.get("/v1/simulations/agents/@missing.bsky.social/follows")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "AGENT_NOT_FOUND"

    def test_post_agent_follow_creates_edge_and_syncs_cached_counts(
        self,
        simulation_client,
        agent_repo,
        user_agent_profile_metadata_repo,
    ):
        _seed_agent_with_metadata(
            agent_repo=agent_repo,
            metadata_repo=user_agent_profile_metadata_repo,
            agent_id="did:plc:alice",
            handle="@alice.bsky.social",
            followers_count=17,
            follows_count=23,
            posts_count=7,
        )
        _seed_agent_with_metadata(
            agent_repo=agent_repo,
            metadata_repo=user_agent_profile_metadata_repo,
            agent_id="did:plc:bob",
            handle="@bob.tech",
            followers_count=31,
            follows_count=29,
            posts_count=11,
        )

        client, _ = simulation_client
        response = client.post(
            "/v1/simulations/agents/@alice.bsky.social/follows",
            json={"target_handle": "@bob.tech"},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["follower_handle"] == "@alice.bsky.social"
        assert body["target_handle"] == "@bob.tech"
        assert body["agent_follow_edge_id"]

        follow_list = client.get("/v1/simulations/agents/@alice.bsky.social/follows")
        assert follow_list.status_code == 200
        assert follow_list.json()["total"] == 1
        assert follow_list.json()["items"][0]["target_handle"] == "@bob.tech"

        agents_response = client.get("/v1/simulations/agents?limit=10&offset=0")
        assert agents_response.status_code == 200
        agents_by_handle = {agent["handle"]: agent for agent in agents_response.json()}

        assert agents_by_handle["@alice.bsky.social"]["following"] == 1
        assert agents_by_handle["@alice.bsky.social"]["followers"] == 0
        assert agents_by_handle["@alice.bsky.social"]["posts_count"] == 7
        assert agents_by_handle["@bob.tech"]["followers"] == 1
        assert agents_by_handle["@bob.tech"]["following"] == 0
        assert agents_by_handle["@bob.tech"]["posts_count"] == 11

    def test_post_agent_follow_duplicate_returns_409(
        self,
        simulation_client,
        agent_repo,
        user_agent_profile_metadata_repo,
    ):
        _seed_agent_with_metadata(
            agent_repo=agent_repo,
            metadata_repo=user_agent_profile_metadata_repo,
            agent_id="did:plc:alice",
            handle="@alice.bsky.social",
            followers_count=0,
            follows_count=0,
            posts_count=1,
        )
        _seed_agent_with_metadata(
            agent_repo=agent_repo,
            metadata_repo=user_agent_profile_metadata_repo,
            agent_id="did:plc:bob",
            handle="@bob.tech",
            followers_count=0,
            follows_count=0,
            posts_count=1,
        )

        client, _ = simulation_client
        first = client.post(
            "/v1/simulations/agents/@alice.bsky.social/follows",
            json={"target_handle": "@bob.tech"},
        )
        second = client.post(
            "/v1/simulations/agents/@alice.bsky.social/follows",
            json={"target_handle": "@bob.tech"},
        )

        assert first.status_code == 201
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "FOLLOW_EDGE_ALREADY_EXISTS"

    def test_post_agent_follow_self_follow_returns_422(
        self,
        simulation_client,
        agent_repo,
        user_agent_profile_metadata_repo,
    ):
        _seed_agent_with_metadata(
            agent_repo=agent_repo,
            metadata_repo=user_agent_profile_metadata_repo,
            agent_id="did:plc:alice",
            handle="@alice.bsky.social",
            followers_count=0,
            follows_count=0,
            posts_count=1,
        )

        client, _ = simulation_client
        response = client.post(
            "/v1/simulations/agents/@alice.bsky.social/follows",
            json={"target_handle": "@alice.bsky.social"},
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "SELF_FOLLOW_NOT_ALLOWED"

    def test_post_agent_follow_target_missing_returns_404(
        self,
        simulation_client,
        agent_repo,
        user_agent_profile_metadata_repo,
    ):
        _seed_agent_with_metadata(
            agent_repo=agent_repo,
            metadata_repo=user_agent_profile_metadata_repo,
            agent_id="did:plc:alice",
            handle="@alice.bsky.social",
            followers_count=0,
            follows_count=0,
            posts_count=1,
        )

        client, _ = simulation_client
        response = client.post(
            "/v1/simulations/agents/@alice.bsky.social/follows",
            json={"target_handle": "@missing.bsky.social"},
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TARGET_AGENT_NOT_FOUND"

    def test_delete_agent_follow_removes_edge_and_syncs_cached_counts(
        self,
        simulation_client,
        agent_repo,
        user_agent_profile_metadata_repo,
    ):
        _seed_agent_with_metadata(
            agent_repo=agent_repo,
            metadata_repo=user_agent_profile_metadata_repo,
            agent_id="did:plc:alice",
            handle="@alice.bsky.social",
            followers_count=0,
            follows_count=0,
            posts_count=3,
        )
        _seed_agent_with_metadata(
            agent_repo=agent_repo,
            metadata_repo=user_agent_profile_metadata_repo,
            agent_id="did:plc:bob",
            handle="@bob.tech",
            followers_count=0,
            follows_count=0,
            posts_count=4,
        )

        client, _ = simulation_client
        create_response = client.post(
            "/v1/simulations/agents/@alice.bsky.social/follows",
            json={"target_handle": "@bob.tech"},
        )
        assert create_response.status_code == 201

        delete_response = client.delete(
            "/v1/simulations/agents/@alice.bsky.social/follows/@bob.tech"
        )
        assert delete_response.status_code == 204

        follow_list = client.get("/v1/simulations/agents/@alice.bsky.social/follows")
        assert follow_list.status_code == 200
        assert follow_list.json() == {"total": 0, "items": []}

        agents_response = client.get("/v1/simulations/agents?limit=10&offset=0")
        agents_by_handle = {agent["handle"]: agent for agent in agents_response.json()}
        assert agents_by_handle["@alice.bsky.social"]["following"] == 0
        assert agents_by_handle["@bob.tech"]["followers"] == 0

    def test_delete_agent_follow_missing_edge_returns_404(
        self,
        simulation_client,
        agent_repo,
        user_agent_profile_metadata_repo,
    ):
        _seed_agent_with_metadata(
            agent_repo=agent_repo,
            metadata_repo=user_agent_profile_metadata_repo,
            agent_id="did:plc:alice",
            handle="@alice.bsky.social",
            followers_count=0,
            follows_count=0,
            posts_count=1,
        )
        _seed_agent_with_metadata(
            agent_repo=agent_repo,
            metadata_repo=user_agent_profile_metadata_repo,
            agent_id="did:plc:bob",
            handle="@bob.tech",
            followers_count=0,
            follows_count=0,
            posts_count=1,
        )

        client, _ = simulation_client
        response = client.delete(
            "/v1/simulations/agents/@alice.bsky.social/follows/@bob.tech"
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "FOLLOW_EDGE_NOT_FOUND"


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


def _seed_agent_with_metadata(
    *,
    agent_repo,
    metadata_repo,
    agent_id: str,
    handle: str,
    followers_count: int,
    follows_count: int,
    posts_count: int,
) -> None:
    _seed_agent(agent_repo=agent_repo, agent_id=agent_id, handle=handle)
    metadata_repo.create_or_update_metadata(
        UserAgentProfileMetadataFactory.create(
            metadata_id=f"meta_{agent_id}",
            agent_id=agent_id,
            followers_count=followers_count,
            follows_count=follows_count,
            posts_count=posts_count,
            created_at="2026_03_13-10:00:00",
            updated_at="2026_03_13-10:00:00",
        )
    )
