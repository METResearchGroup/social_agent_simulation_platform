"""Rewrite legacy agent primary keys and FKs to canonical hex ids.

Revision ID: c3d5e7f9a0b2
Revises: b2c4d6e8f0a1
Create Date: 2026-03-20 14:00:00.000000

Data migration only (no DDL). For every row in ``agent``, compute::

    stable_source = stable_source_for_agent_row(
        handle=agent.handle,
        legacy_agent_id=agent.agent_id,
        bluesky_did=bluesky_profiles.did via LEFT JOIN on handle,
    )
    new_id = canonical_agent_id(stable_source)

**Precedence (frozen)** matches ``scripts/migrations/agent_id_migration.py`` / strategy doc:

1. Bluesky DID when non-empty after strip (from joined ``bluesky_profiles``).
2. Else trimmed ``agent.handle``; if empty, fall through.
3. Else stripped ``agent.agent_id`` (legacy UUID / DID / ``agent_*`` string).

**Collision policy:** abort the upgrade if two legacy ``agent_id`` values map to
the same ``new_id`` (see ``AgentIdMigrationCollisionError``).

**Rewrite order (composite FKs):** direct children of ``agent`` → run-scoped
tables pointing at ``(run_id, agent_id)`` in ``run_agents`` → ``run_agents`` →
``agent`` (PK swap last).

SQLite enables ``PRAGMA foreign_keys=OFF`` for the update batch. Rewrites use a
two-phase temp-id strategy (``migtmp_<uuid>``) so chains like ``A→B, B→C`` do
not collide on ``agent.agent_id`` / composite keys. After ``PRAGMA
foreign_keys=ON``, ``PRAGMA foreign_key_check`` runs before canonical-format
validation.

Downgrade is intentionally unsupported (restore from backup).
"""

import logging
import uuid
from typing import Mapping, Sequence, cast

from alembic import op
from sqlalchemy import text

from lib.agent_id import is_canonical_agent_id
from scripts.migrations.agent_id_migration import (
    agent_rows_from_mappings,
    build_old_to_new_map,
    migration_pairs,
)

revision: str = "c3d5e7f9a0b2"
down_revision: str | Sequence[str] | None = "b2c4d6e8f0a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_AGENT_FK_COLUMNS: tuple[tuple[str, str], ...] = (
    ("agent_persona_bios", "agent_id"),
    ("user_agent_profile_metadata", "agent_id"),
    ("agent_follow_edges", "follower_agent_id"),
    ("agent_follow_edges", "target_agent_id"),
    ("agent_posts", "agent_id"),
    ("agent_post_likes", "liker_agent_id"),
    ("agent_post_comments", "author_agent_id"),
)

_RUN_AGENT_FK_COLUMNS: tuple[tuple[str, str], ...] = (
    ("run_posts", "author_agent_id"),
    ("run_post_likes", "liker_agent_id"),
    ("run_post_comments", "author_agent_id"),
    ("run_follow_edges", "follower_agent_id"),
    ("run_follow_edges", "target_agent_id"),
)

_LOG = logging.getLogger(__name__)


def _unique_migration_temp_ids(count: int, reserved: set[str]) -> list[str]:
    """Return ``count`` distinct temp ids that cannot collide with ``reserved``."""
    out: list[str] = []
    while len(out) < count:
        # Prefix keeps these outside the 16-char canonical agent_id space and schema TEXT.
        candidate = f"migtmp_{uuid.uuid4().hex}"
        if candidate in reserved:
            continue
        reserved.add(candidate)
        out.append(candidate)
    return out


def _rewrite_agent_id_everywhere(connection, old_id: str, new_id: str) -> None:
    """Rewrite ``old_id`` to ``new_id`` across all FK paths (FKs may be OFF)."""
    for table, column in _AGENT_FK_COLUMNS:
        connection.execute(
            text(
                f"UPDATE {table} SET {column} = :new_id WHERE {column} = :old_id"  # nosec B608
            ),
            {"new_id": new_id, "old_id": old_id},
        )
    for table, column in _RUN_AGENT_FK_COLUMNS:
        connection.execute(
            text(
                f"UPDATE {table} SET {column} = :new_id WHERE {column} = :old_id"  # nosec B608
            ),
            {"new_id": new_id, "old_id": old_id},
        )
    connection.execute(
        text("UPDATE run_agents SET agent_id = :new_id WHERE agent_id = :old_id"),
        {"new_id": new_id, "old_id": old_id},
    )
    connection.execute(
        text("UPDATE agent SET agent_id = :new_id WHERE agent_id = :old_id"),
        {"new_id": new_id, "old_id": old_id},
    )


def _apply_rewrites(connection, old_to_new: dict[str, str]) -> None:
    """Two-phase rewrite so chains like A→B, B→C never hit PK/UNIQUE conflicts."""
    pairs = migration_pairs(old_to_new)
    if not pairs:
        return

    reserved: set[str] = set(old_to_new.keys()) | set(old_to_new.values())
    temp_ids = _unique_migration_temp_ids(len(pairs), reserved)
    trios = list(
        zip(temp_ids, [p[0] for p in pairs], [p[1] for p in pairs], strict=True)
    )

    for temp_id, old_id, _new_id in trios:
        _rewrite_agent_id_everywhere(connection, old_id, temp_id)
    for temp_id, _old_id, new_id in trios:
        _rewrite_agent_id_everywhere(connection, temp_id, new_id)


def _validate_agent_fk_columns(connection) -> None:
    checks: tuple[tuple[str, str], ...] = _AGENT_FK_COLUMNS + _RUN_AGENT_FK_COLUMNS
    checks += (("run_agents", "agent_id"), ("agent", "agent_id"))
    seen: set[tuple[str, str]] = set()
    for table, column in checks:
        key = (table, column)
        if key in seen:
            continue
        seen.add(key)
        for row in connection.execute(
            text(f"SELECT DISTINCT {column} FROM {table}")  # nosec B608
        ):
            value = row[0]
            if value is None:
                continue
            if not is_canonical_agent_id(str(value)):
                raise ValueError(
                    f"post-migration validation failed: {table}.{column}="
                    f"{value!r} is not a canonical agent_id"
                )


def _assert_foreign_key_integrity(connection) -> None:
    """Run SQLite referential integrity check; raise if any FK violations exist."""
    rows = connection.execute(text("PRAGMA foreign_key_check")).fetchall()
    if not rows:
        return
    for row in rows:
        _LOG.error("PRAGMA foreign_key_check violation: %s", row)
    raise ValueError(
        f"post-migration PRAGMA foreign_key_check reported {len(rows)} violation(s): {rows!r}"
    )


def upgrade() -> None:
    conn = op.get_bind()
    row_maps = (
        conn.execute(
            text(
                "SELECT a.agent_id AS agent_id, a.handle AS handle, bp.did AS did "
                "FROM agent a "
                "LEFT JOIN bluesky_profiles bp ON bp.handle = a.handle "
                "ORDER BY a.agent_id"
            )
        )
        .mappings()
        .all()
    )
    agent_rows = agent_rows_from_mappings(
        cast(Sequence[Mapping[str, str | None]], row_maps)
    )
    old_to_new = build_old_to_new_map(agent_rows)

    conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
    try:
        _apply_rewrites(conn, old_to_new)
    finally:
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")

    _assert_foreign_key_integrity(conn)
    _validate_agent_fk_columns(conn)


def downgrade() -> None:
    raise NotImplementedError(
        "Rewriting agent primary keys is a one-way data migration; restore from backup."
    )
