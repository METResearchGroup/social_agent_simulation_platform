"""Action and feed tables: ID-first columns and generated_feeds PK.

Revision ID: d4f8a1c3e5b7
Revises: c3d5e7f9a0b2
Create Date: 2026-03-20 16:00:00.000000

Renames misleading columns on run-scoped action tables, adds FKs to ``agent``,
rebuilds ``generated_feeds`` so the primary key is ``(agent_id, run_id, turn_number)``,
and backfills canonical ``agent_id`` values from ``agent`` using normalized handle
equality (strip, compare case-insensitively, ignore a single leading ``@``).

Downgrade is intentionally unsupported (restore from backup).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

from lib.agent_id import is_canonical_agent_id

revision: str = "d4f8a1c3e5b7"
down_revision: Union[str, Sequence[str], None] = "c3d5e7f9a0b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _norm_handle(value: str) -> str:
    t = (value or "").strip()
    if t.startswith("@"):
        t = t[1:]
    return t.strip().lower()


def _build_handle_to_agent_id_map(
    conn: sa.Connection,
) -> tuple[dict[str, str], set[str]]:
    """Build normalized_handle -> agent_id map. Returns (map, canonical_ids_in_agent)."""
    rows = conn.execute(text("SELECT agent_id, handle FROM agent")).fetchall()
    handle_to_id: dict[str, str] = {}
    canonical_ids: set[str] = set()
    for agent_id, handle in rows:
        canonical_ids.add(str(agent_id))
        if handle:
            norm = _norm_handle(handle)
            if norm in handle_to_id and handle_to_id[norm] != str(agent_id):
                raise ValueError(
                    f"action_feed_id_semantics migration: normalized handle collision "
                    f"for {norm!r} -> agent_ids {handle_to_id[norm]!r} and {agent_id!r}"
                )
            handle_to_id[norm] = str(agent_id)
    return handle_to_id, canonical_ids


def _resolve_agent_id(
    raw: str,
    handle_to_id: dict[str, str],
    canonical_ids: set[str],
) -> str:
    if is_canonical_agent_id(raw):
        if raw not in canonical_ids:
            raise ValueError(
                f"action_feed_id_semantics migration: canonical id {raw!r} not in agent table"
            )
        return raw
    want = _norm_handle(raw)
    if want in handle_to_id:
        return handle_to_id[want]
    raise ValueError(
        f"action_feed_id_semantics migration: cannot resolve agent row for handle/id {raw!r}"
    )


def _backfill_agent_id_column(
    conn: sa.Connection,
    table: str,
    column: str,
    handle_to_id: dict[str, str],
    canonical_ids: set[str],
) -> None:
    pk_col = (
        "like_id"
        if table == "likes"
        else "comment_id"
        if table == "comments"
        else "follow_id"
    )
    rows = conn.execute(
        text(f"SELECT {pk_col}, {column} FROM {table}")  # nosec B608
    ).fetchall()
    for pk, current in rows:
        if current is None:
            raise ValueError(f"{table}.{column} is NULL for {pk_col}={pk!r}")
        if is_canonical_agent_id(current):
            _resolve_agent_id(current, handle_to_id, canonical_ids)
            continue
        resolved = _resolve_agent_id(current, handle_to_id, canonical_ids)
        conn.execute(
            text(f"UPDATE {table} SET {column} = :nid WHERE {pk_col} = :pk"),  # nosec B608
            {"nid": resolved, "pk": pk},
        )


def _backfill_follow_target(
    conn: sa.Connection,
    handle_to_id: dict[str, str],
    canonical_ids: set[str],
) -> None:
    rows = conn.execute(
        text("SELECT follow_id, target_agent_id FROM follows")
    ).fetchall()
    for follow_id, current in rows:
        if current is None:
            raise ValueError(
                f"follows.target_agent_id is NULL for follow_id={follow_id!r}"
            )
        if is_canonical_agent_id(current):
            _resolve_agent_id(current, handle_to_id, canonical_ids)
            continue
        resolved = _resolve_agent_id(current, handle_to_id, canonical_ids)
        conn.execute(
            text("UPDATE follows SET target_agent_id = :nid WHERE follow_id = :fid"),
            {"nid": resolved, "fid": follow_id},
        )


def upgrade() -> None:
    conn = op.get_bind()
    assert isinstance(conn, sa.Connection)  # nosec B101
    handle_to_id, canonical_ids = _build_handle_to_agent_id_map(conn)
    conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
    try:
        # --- likes ---
        op.drop_index("idx_likes_run_turn_agent", table_name="likes")
        with op.batch_alter_table("likes", schema=None) as batch_op:
            batch_op.drop_constraint("uq_likes_run_turn_agent_post", type_="unique")
        conn.execute(
            sa.text("ALTER TABLE likes RENAME COLUMN agent_handle TO agent_id")
        )
        _backfill_agent_id_column(
            conn, "likes", "agent_id", handle_to_id, canonical_ids
        )
        with op.batch_alter_table("likes", schema=None) as batch_op:
            batch_op.create_unique_constraint(
                "uq_likes_run_turn_agent_post",
                ["run_id", "turn_number", "agent_id", "post_id"],
            )
            batch_op.create_foreign_key(
                "fk_likes_agent_id", "agent", ["agent_id"], ["agent_id"]
            )
        op.create_index(
            "idx_likes_run_turn_agent",
            "likes",
            ["run_id", "turn_number", "agent_id"],
        )

        # --- comments ---
        op.drop_index("idx_comments_run_turn_agent", table_name="comments")
        with op.batch_alter_table("comments", schema=None) as batch_op:
            batch_op.drop_constraint("uq_comments_run_turn_agent_post", type_="unique")
        conn.execute(
            sa.text("ALTER TABLE comments RENAME COLUMN agent_handle TO agent_id")
        )
        _backfill_agent_id_column(
            conn, "comments", "agent_id", handle_to_id, canonical_ids
        )
        with op.batch_alter_table("comments", schema=None) as batch_op:
            batch_op.create_unique_constraint(
                "uq_comments_run_turn_agent_post",
                ["run_id", "turn_number", "agent_id", "post_id"],
            )
            batch_op.create_foreign_key(
                "fk_comments_agent_id", "agent", ["agent_id"], ["agent_id"]
            )
        op.create_index(
            "idx_comments_run_turn_agent",
            "comments",
            ["run_id", "turn_number", "agent_id"],
        )

        # --- follows ---
        op.drop_index("idx_follows_run_turn_agent", table_name="follows")
        with op.batch_alter_table("follows", schema=None) as batch_op:
            batch_op.drop_constraint("uq_follows_run_turn_agent_user", type_="unique")
        conn.execute(
            sa.text("ALTER TABLE follows RENAME COLUMN agent_handle TO agent_id")
        )
        conn.execute(
            sa.text("ALTER TABLE follows RENAME COLUMN user_id TO target_agent_id")
        )
        _backfill_agent_id_column(
            conn, "follows", "agent_id", handle_to_id, canonical_ids
        )
        _backfill_follow_target(conn, handle_to_id, canonical_ids)
        with op.batch_alter_table("follows", schema=None) as batch_op:
            batch_op.create_unique_constraint(
                "uq_follows_run_turn_agent_target",
                ["run_id", "turn_number", "agent_id", "target_agent_id"],
            )
            batch_op.create_foreign_key(
                "fk_follows_agent_id", "agent", ["agent_id"], ["agent_id"]
            )
            batch_op.create_foreign_key(
                "fk_follows_target_agent_id",
                "agent",
                ["target_agent_id"],
                ["agent_id"],
            )
        op.create_index(
            "idx_follows_run_turn_agent",
            "follows",
            ["run_id", "turn_number", "agent_id"],
        )

        # --- generated_feeds (rebuild) ---
        conn.execute(
            sa.text(
                """
                CREATE TABLE generated_feeds_new (
                    feed_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    turn_number INTEGER NOT NULL,
                    agent_id TEXT NOT NULL,
                    agent_handle TEXT,
                    post_ids TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (agent_id, run_id, turn_number),
                    FOREIGN KEY (run_id) REFERENCES runs (run_id),
                    FOREIGN KEY (agent_id) REFERENCES agent (agent_id)
                )
                """
            )
        )
        old_rows = conn.execute(text("SELECT * FROM generated_feeds")).fetchall()
        cols = [
            d[1]
            for d in conn.execute(text("PRAGMA table_info(generated_feeds)")).fetchall()
        ]
        for row in old_rows:
            rowd = dict(zip(cols, row, strict=True))
            ah = rowd["agent_handle"]
            aid = _resolve_agent_id(ah, handle_to_id, canonical_ids)
            conn.execute(
                text(
                    """
                    INSERT INTO generated_feeds_new (
                      feed_id, run_id, turn_number, agent_id, agent_handle, post_ids, created_at
                    ) VALUES (:feed_id, :run_id, :turn_number, :agent_id, :agent_handle, :post_ids, :created_at)
                    """
                ),
                {
                    "feed_id": rowd["feed_id"],
                    "run_id": rowd["run_id"],
                    "turn_number": rowd["turn_number"],
                    "agent_id": aid,
                    "agent_handle": ah,
                    "post_ids": rowd["post_ids"],
                    "created_at": rowd["created_at"],
                },
            )
        op.drop_table("generated_feeds")
        op.rename_table("generated_feeds_new", "generated_feeds")
    finally:
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")

    # Validate canonical ids for touched tables (migration must not leave unresolved handles).
    for table, col in (
        ("likes", "agent_id"),
        ("comments", "agent_id"),
        ("follows", "agent_id"),
        ("follows", "target_agent_id"),
        ("generated_feeds", "agent_id"),
    ):
        rows = conn.execute(text(f"SELECT {col} FROM {table}")).fetchall()  # nosec B608
        for (value,) in rows:
            if not is_canonical_agent_id(value):
                raise ValueError(
                    f"Post-migration validation failed: {table}.{col} has non-canonical value {value!r}"
                )


def downgrade() -> None:
    raise NotImplementedError("Downgrade unsupported; restore from backup.")
