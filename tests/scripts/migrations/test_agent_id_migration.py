import pytest

from lib.agent_id import canonical_agent_id, is_canonical_agent_id
from scripts.migrations.agent_id_migration import (
    AgentIdMigrationCollisionError,
    build_old_to_new_map,
    migration_pairs,
    new_agent_id_for_agent_row,
    stable_source_for_agent_row,
)


class TestStableSourceForAgentRow:
    def test_bluesky_did_wins_over_handle(self):
        assert (
            stable_source_for_agent_row(
                handle="alice.bsky.social",
                legacy_agent_id="550e8400-e29b-41d4-a716-446655440000",
                bluesky_did="did:plc:aaa",
            )
            == "did:plc:aaa"
        )

    def test_whitespace_did_is_ignored(self):
        assert (
            stable_source_for_agent_row(
                handle="alice.bsky.social",
                legacy_agent_id="legacy",
                bluesky_did="   \n\t  ",
            )
            == "alice.bsky.social"
        )

    def test_handle_when_no_did(self):
        assert (
            stable_source_for_agent_row(
                handle="  bob.bsky.social  ",
                legacy_agent_id="legacy",
                bluesky_did=None,
            )
            == "bob.bsky.social"
        )

    def test_legacy_when_handle_blank(self):
        assert (
            stable_source_for_agent_row(
                handle="   ",
                legacy_agent_id="  uuid-or-did-fallback  ",
                bluesky_did=None,
            )
            == "uuid-or-did-fallback"
        )

    def test_none_did_falls_through_to_handle(self):
        assert (
            stable_source_for_agent_row(
                handle="carol",
                legacy_agent_id="x",
                bluesky_did=None,
            )
            == "carol"
        )


class TestBuildOldToNewMap:
    def test_produces_canonical_hex_ids(self):
        m = build_old_to_new_map(
            [
                ("old-a", "alice", "did:plc:aa"),
            ]
        )
        assert len(m) == 1
        assert is_canonical_agent_id(m["old-a"])

    def test_collision_two_legacy_same_canonical(self):
        same_did = "did:plc:shared"
        with pytest.raises(AgentIdMigrationCollisionError) as excinfo:
            build_old_to_new_map(
                [
                    ("legacy-1", "one.bsky", same_did),
                    ("legacy-2", "two.bsky", same_did),
                ]
            )
        err = excinfo.value
        assert err.new_id == canonical_agent_id(same_did)
        assert set(err.old_ids) == {"legacy-1", "legacy-2"}

    def test_migration_pairs_excludes_identity_mappings(self):
        canonical = canonical_agent_id("only-handle")
        pairs = migration_pairs({canonical: canonical, "legacy-uuid": canonical})
        assert pairs == [("legacy-uuid", canonical)]


class TestNewAgentIdForAgentRow:
    def test_matches_canonical_agent_id_of_stable_source(self):
        handle = "dave.bsky.social"
        legacy = "550e8400-e29b-41d4-a716-446655440000"
        expected = canonical_agent_id(handle)
        assert (
            new_agent_id_for_agent_row(
                handle=handle,
                legacy_agent_id=legacy,
                bluesky_did=None,
            )
            == expected
        )
