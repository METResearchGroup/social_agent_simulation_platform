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

SQLite enables ``PRAGMA foreign_keys=OFF`` for the update batch, then restores
FK enforcement for validation.

Downgrade is intentionally unsupported (restore from backup).
"""

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


def _apply_rewrites(connection, old_to_new: dict[str, str]) -> None:
    pairs = migration_pairs(old_to_new)
    if not pairs:
        return

    for old_id, new_id in pairs:
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


def upgrade() -> None:
    conn = op.get_bind()
    row_maps = (
        conn.execute(
            text(
                "SELECT a.agent_id AS agent_id, a.handle AS handle, bp.did AS did "
                "FROM agent a "
                "LEFT JOIN bluesky_profiles bp ON bp.handle = a.handle"
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

    _validate_agent_fk_columns(conn)


def downgrade() -> None:
    raise NotImplementedError(
        "Rewriting agent primary keys is a one-way data migration; restore from backup."
    )
