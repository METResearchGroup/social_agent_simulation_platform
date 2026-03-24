"""Proposal inventory of agent-key columns for head-state migration verification."""

from __future__ import annotations

import re
import sqlite3
from typing import NamedTuple

from lib.agent_id import is_canonical_agent_id

# Full proposal inventory (strategy_planning/2026-03-20_agent_id_migration/proposal.md).
AGENT_KEY_COLUMNS: tuple[tuple[str, str], ...] = (
    ("agent", "agent_id"),
    ("agent_persona_bios", "agent_id"),
    ("user_agent_profile_metadata", "agent_id"),
    ("agent_follow_edges", "follower_agent_id"),
    ("agent_follow_edges", "target_agent_id"),
    ("agent_posts", "agent_id"),
    ("agent_post_likes", "liker_agent_id"),
    ("agent_post_comments", "author_agent_id"),
    ("run_agents", "agent_id"),
    ("run_posts", "author_agent_id"),
    ("run_post_likes", "liker_agent_id"),
    ("run_post_comments", "author_agent_id"),
    ("run_follow_edges", "follower_agent_id"),
    ("run_follow_edges", "target_agent_id"),
    ("turn_likes", "agent_id"),
    ("turn_comments", "agent_id"),
    ("turn_follows", "agent_id"),
    ("turn_follows", "target_agent_id"),
    ("turn_generated_feeds", "agent_id"),
)

_UUID_HYPHENATED = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_UUID_PLAIN_32 = re.compile(r"^[0-9a-fA-F]{32}$")


class AgentKeyViolation(NamedTuple):
    table: str
    column: str
    value: str


def is_legacy_shaped_agent_id(value: str) -> bool:
    """True when *value* looks like a pre-migration ID shape (not necessarily 16-char hex).

    Canonical IDs are checked separately via ``is_canonical_agent_id``; this covers
    negative patterns from the proposal: ``did:*``, ``agent_*``, UUID-like, handle-like.
    """
    if not isinstance(value, str) or not value:
        return False
    if value.startswith("did:"):
        return True
    if value.startswith("agent_"):
        return True
    if _UUID_HYPHENATED.match(value):
        return True
    if _UUID_PLAIN_32.match(value):
        return True
    # Handle-shaped (e.g. alice.bsky.social) — canonical storage never contains dots.
    return "." in value and "@" not in value


def collect_non_canonical_agent_key_values(
    conn: sqlite3.Connection,
) -> list[AgentKeyViolation]:
    """Return (table, column, value) for every non-null agent-key value that is not canonical."""
    bad: list[AgentKeyViolation] = []
    for table, column in AGENT_KEY_COLUMNS:
        cur = conn.execute(
            f'SELECT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL'
        )
        for (raw,) in cur.fetchall():
            if not isinstance(raw, str):
                bad.append(
                    AgentKeyViolation(table, column, repr(raw)),
                )
                continue
            if not is_canonical_agent_id(raw):
                bad.append(AgentKeyViolation(table, column, raw))
    return bad


def collect_legacy_shaped_agent_key_values(
    conn: sqlite3.Connection,
) -> list[AgentKeyViolation]:
    """Return rows where a legacy-shaped ID appears in an agent-key column."""
    bad: list[AgentKeyViolation] = []
    for table, column in AGENT_KEY_COLUMNS:
        cur = conn.execute(
            f'SELECT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL'
        )
        for (raw,) in cur.fetchall():
            if isinstance(raw, str) and is_legacy_shaped_agent_id(raw):
                bad.append(AgentKeyViolation(table, column, raw))
    return bad


def assert_agent_key_inventory_tables_exist(conn: sqlite3.Connection) -> None:
    """Fail fast with a clear message if the head schema is missing an inventoried table."""
    for table, _ in AGENT_KEY_COLUMNS:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
            (table,),
        ).fetchone()
        if row is None:
            msg = f"Head-state verifier: expected table {table!r} to exist"
            raise AssertionError(msg)
