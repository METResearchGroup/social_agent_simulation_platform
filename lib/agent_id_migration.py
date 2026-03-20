"""Deterministic agent_id migration mapping (data backfill helpers).

Used by Alembic to rewrite legacy ``agent.agent_id`` and dependent foreign keys
to canonical 16-char hex IDs. Mapping rules must stay aligned with
``strategy_planning/2026-03-20_agent_id_migration/proposal.md``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from lib.agent_id import canonical_agent_id, is_canonical_agent_id


class AgentIdMigrationCollisionError(ValueError):
    """Raised when two legacy ``agent_id`` values map to the same canonical id."""

    def __init__(self, new_id: str, old_ids: list[str]) -> None:
        joined = ", ".join(sorted(old_ids))
        super().__init__(
            f"agent_id migration collision: canonical id {new_id!r} "
            f"produced from multiple legacy agent_id values: {joined}"
        )
        self.new_id = new_id
        self.old_ids = old_ids


def stable_source_for_agent_row(
    *,
    handle: str,
    legacy_agent_id: str,
    bluesky_did: str | None,
) -> str:
    """Return the stable string used to compute the canonical agent id for a row.

    Precedence (frozen):
    1. Bluesky DID when present and non-empty after strip.
    2. Else ``handle`` trimmed; if empty after trim, fall through.
    3. Else ``legacy_agent_id`` stripped.
    """
    if bluesky_did is not None and bluesky_did.strip():
        return bluesky_did.strip()
    trimmed_handle = handle.strip()
    if trimmed_handle:
        return trimmed_handle
    return legacy_agent_id.strip()


def new_agent_id_for_agent_row(
    *,
    handle: str,
    legacy_agent_id: str,
    bluesky_did: str | None,
) -> str:
    """Return ``canonical_agent_id(stable_source)`` for this agent row."""
    stable = stable_source_for_agent_row(
        handle=handle,
        legacy_agent_id=legacy_agent_id,
        bluesky_did=bluesky_did,
    )
    return canonical_agent_id(stable)


def build_old_to_new_map(
    agent_rows: Sequence[tuple[str, str, str | None]],
) -> dict[str, str]:
    """Build ``old_agent_id -> new_agent_id`` for each agent row.

    ``agent_rows`` items are ``(agent_id, handle, bluesky_did)`` where ``bluesky_did``
    is the joined DID from ``bluesky_profiles`` (or ``None``).

    Raises:
        AgentIdMigrationCollisionError: if two legacy ids map to the same new id.
        ValueError: if a derived new id is not canonical (defensive).
    """
    old_to_new: dict[str, str] = {}
    new_to_olds: dict[str, list[str]] = {}

    for legacy_id, handle, did in agent_rows:
        new_id = new_agent_id_for_agent_row(
            handle=handle,
            legacy_agent_id=legacy_id,
            bluesky_did=did,
        )
        if not is_canonical_agent_id(new_id):
            raise ValueError(
                f"derived agent_id {new_id!r} for agent {legacy_id!r} is not canonical"
            )
        old_to_new[legacy_id] = new_id
        bucket = new_to_olds.setdefault(new_id, [])
        if legacy_id not in bucket:
            bucket.append(legacy_id)

    for new_id, olds in new_to_olds.items():
        if len(olds) > 1:
            raise AgentIdMigrationCollisionError(new_id, olds)

    return old_to_new


def migration_pairs(old_to_new: Mapping[str, str]) -> list[tuple[str, str]]:
    """Return ``(old_id, new_id)`` pairs where the id actually changes."""
    return [(old, new) for old, new in old_to_new.items() if old != new]


def agent_rows_from_mappings(
    rows: Iterable[Mapping[str, str | None]],
) -> list[tuple[str, str, str | None]]:
    """Normalize SQLAlchemy row mappings to ``build_old_to_new_map`` input."""
    out: list[tuple[str, str, str | None]] = []
    for row in rows:
        agent_id = row["agent_id"]
        handle = row["handle"]
        did = row.get("did")
        if not isinstance(agent_id, str) or not isinstance(handle, str):
            raise TypeError("agent_id and handle must be str")
        if did is not None and not isinstance(did, str):
            raise TypeError("did must be str or None")
        out.append((agent_id, handle, did))
    return out
