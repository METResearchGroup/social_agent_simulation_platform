"""Phase 7 head-state audit: full proposal inventory of agent-key columns.

See ``strategy_planning/2026-03-20_agent_id_migration/proposal.md`` (FK graph).
"""

from __future__ import annotations

import re
import sqlite3
from typing import NamedTuple

from lib.agent_id import is_canonical_agent_id

# Every table/column that stores an agent identity key at migration head (proposal minimum).
PHASE7_AGENT_KEY_COLUMNS: tuple[tuple[str, str], ...] = (
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
    ("likes", "agent_id"),
    ("comments", "agent_id"),
    ("follows", "agent_id"),
    ("follows", "target_agent_id"),
    ("generated_feeds", "agent_id"),
)


class AgentKeyViolation(NamedTuple):
    table: str
    column: str
    value: str


_UUID_HEX_NO_DASHES = re.compile(r"^[0-9a-fA-F]{32}$")


def looks_like_legacy_agent_key_value(value: str) -> bool:
    """True when *value* matches legacy shapes the migration was meant to eliminate.

    Canonical 16-char hex IDs are never legacy-shaped. Used for the negative audit pass
    alongside ``is_canonical_agent_id``.
    """
    if not isinstance(value, str) or not value:
        return False
    if value.startswith("did:"):
        return True
    if value.startswith("agent_"):
        return True
    if _UUID_HEX_NO_DASHES.fullmatch(value):
        return True
    # Handle-shaped strings (e.g. alice.bsky.social), not agent keys.
    return bool("." in value and not is_canonical_agent_id(value))


def iter_non_canonical_agent_key_values(
    conn: sqlite3.Connection,
) -> list[AgentKeyViolation]:
    """Return rows where a non-null agent-key column fails ``is_canonical_agent_id``."""
    violations: list[AgentKeyViolation] = []
    for table, column in PHASE7_AGENT_KEY_COLUMNS:
        rows = conn.execute(
            f'SELECT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL'
        ).fetchall()
        for (raw,) in rows:
            if not is_canonical_agent_id(raw):
                violations.append(AgentKeyViolation(table, column, raw))
    return violations


def iter_legacy_shaped_agent_key_values(
    conn: sqlite3.Connection,
) -> list[AgentKeyViolation]:
    """Return rows where a non-null value looks like a legacy DID/agent_/UUID/handle key."""
    violations: list[AgentKeyViolation] = []
    for table, column in PHASE7_AGENT_KEY_COLUMNS:
        rows = conn.execute(
            f'SELECT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL'
        ).fetchall()
        for (raw,) in rows:
            if looks_like_legacy_agent_key_value(raw):
                violations.append(AgentKeyViolation(table, column, raw))
    return violations
