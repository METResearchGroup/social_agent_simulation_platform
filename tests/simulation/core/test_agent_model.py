import pytest
from pydantic import ValidationError

from simulation.core.models.agent import Agent, PersonaSource


def _agent_payload(agent_id: str) -> dict[str, object]:
    return {
        "agent_id": agent_id,
        "handle": "test.bsky.social",
        "persona_source": PersonaSource.SYNC_BLUESKY,
        "display_name": "Test User",
        "created_at": "2026_03_20-10:00:00",
        "updated_at": "2026_03_20-10:00:00",
    }


class TestAgentModel:
    def test_agent_accepts_canonical_id_in_default_mode(self):
        agent = Agent.model_validate(_agent_payload("0123456789abcdef"))
        assert agent.agent_id == "0123456789abcdef"

    def test_agent_accepts_legacy_did_in_default_mode_for_rollout_safety(self):
        legacy_id = "did:plc:test123"
        agent = Agent.model_validate(_agent_payload(legacy_id))
        assert agent.agent_id == legacy_id

    def test_agent_rejects_non_canonical_id_in_strict_mode(self):
        with pytest.raises(
            ValidationError, match=r"agent_id must match \^\[0-9a-f\]\{16\}\$"
        ):
            Agent.model_validate(
                _agent_payload("did:plc:test123"),
                context={"enforce_canonical_agent_id": True},
            )

    def test_agent_accepts_canonical_id_in_strict_mode(self):
        agent = Agent.model_validate(
            _agent_payload("abcdef0123456789"),
            context={"enforce_canonical_agent_id": True},
        )
        assert agent.agent_id == "abcdef0123456789"

    def test_agent_rejects_empty_agent_id_in_all_modes(self):
        with pytest.raises(ValidationError, match="value cannot be empty"):
            Agent.model_validate(_agent_payload("   "))
        with pytest.raises(ValidationError, match="value cannot be empty"):
            Agent.model_validate(
                _agent_payload("   "),
                context={"enforce_canonical_agent_id": True},
            )

    def test_agent_strips_whitespace_before_canonical_check(self):
        agent = Agent.model_validate(
            _agent_payload("  abcdef0123456789  "),
            context={"enforce_canonical_agent_id": True},
        )
        assert agent.agent_id == "abcdef0123456789"
