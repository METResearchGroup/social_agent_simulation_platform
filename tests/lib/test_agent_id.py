import re

from lib.agent_id import canonical_agent_id, is_canonical_agent_id


class TestCanonicalAgentId:
    def test_deterministic_for_same_source(self):
        source = "did:plc:alice"
        assert canonical_agent_id(source) == canonical_agent_id(source)

    def test_strips_source_before_hashing(self):
        assert canonical_agent_id("did:plc:alice") == canonical_agent_id(
            "  did:plc:alice  "
        )

    def test_differs_for_different_sources(self):
        assert canonical_agent_id("did:plc:alice") != canonical_agent_id("did:plc:bob")

    def test_without_source_matches_canonical_shape(self):
        value = canonical_agent_id()
        assert len(value) == 16
        assert re.fullmatch(r"[0-9a-f]{16}", value)
        assert is_canonical_agent_id(value)

    def test_without_source_is_not_constant(self):
        first = canonical_agent_id()
        second = canonical_agent_id()
        assert first != second


class TestIsCanonicalAgentId:
    def test_accepts_valid_values(self):
        assert is_canonical_agent_id("0123456789abcdef")
        assert is_canonical_agent_id(canonical_agent_id("did:plc:alice"))

    def test_rejects_invalid_values(self):
        invalid_values = [
            "ABCDEF0123456789",
            "0123456789abcde",
            "0123456789abcdef0",
            "g123456789abcdef",
            "did:plc:alice",
            "agent_123",
            "550e8400-e29b-41d4-a716-446655440000",
            "",
            "   ",
        ]
        for value in invalid_values:
            assert not is_canonical_agent_id(value)

    def test_non_string_values_return_false(self):
        assert not is_canonical_agent_id(None)  # type: ignore[arg-type]
        assert not is_canonical_agent_id(123)  # type: ignore[arg-type]
        assert not is_canonical_agent_id(object())  # type: ignore[arg-type]
