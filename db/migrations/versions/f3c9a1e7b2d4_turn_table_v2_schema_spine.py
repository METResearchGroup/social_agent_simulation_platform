"""Turn table v2 schema spine: turns parent, turn_* tables, migrate legacy rows.

Revision ID: f3c9a1e7b2d4
Revises: e7f3a9c2d1b4
Create Date: 2026-03-22 12:00:00.000000

Introduces ``turns`` as the canonical parent for per-turn history, renames
``turn_metadata`` -> ``turns``, renames ``generated_feeds`` / ``likes`` /
``comments`` / ``follows`` to ``turn_*`` tables, reparents ``turn_metrics`` onto
``turns(run_id, turn_number)``, and adds empty ``turn_posts`` (foundation only).

Legacy rows are copied forward with create/copy/drop so composite foreign keys and
index names are intentional.

Downgrade is intentionally unsupported (restore from backup).
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# Placeholder parent row for legacy DBs that have per-turn rows without turn_metadata.
_ORPHAN_TURNS_ACTIONS_JSON = '{"like": 0, "comment": 0, "follow": 0}'
_ORPHAN_TURNS_CREATED_AT = "1970_01_01-00:00:00"

revision: str = "f3c9a1e7b2d4"
down_revision: Union[str, Sequence[str], None] = "e7f3a9c2d1b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # SQLite: batch DDL with FK enforcement temporarily disabled.
    conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
    try:
        conn.exec_driver_sql(
            """
            CREATE TABLE turns (
                run_id TEXT NOT NULL,
                turn_number INTEGER NOT NULL,
                total_actions TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (run_id, turn_number),
                FOREIGN KEY (run_id) REFERENCES runs (run_id),
                CHECK (turn_number >= 0)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX idx_turns_run_id ON turns (run_id)")
        conn.exec_driver_sql(
            "INSERT INTO turns SELECT * FROM turn_metadata",
        )
        conn.execute(
            text(
                """
                INSERT OR IGNORE INTO turns (run_id, turn_number, total_actions, created_at)
                SELECT u.run_id, u.turn_number, :actions, :created
                FROM (
                    SELECT run_id, turn_number FROM generated_feeds
                    UNION SELECT run_id, turn_number FROM likes
                    UNION SELECT run_id, turn_number FROM comments
                    UNION SELECT run_id, turn_number FROM follows
                    UNION SELECT run_id, turn_number FROM turn_metrics
                ) AS u
                """
            ),
            {
                "actions": _ORPHAN_TURNS_ACTIONS_JSON,
                "created": _ORPHAN_TURNS_CREATED_AT,
            },
        )

        conn.exec_driver_sql("DROP INDEX IF EXISTS idx_turn_metadata_run_id")
        conn.exec_driver_sql("DROP TABLE turn_metadata")

        conn.exec_driver_sql(
            """
            CREATE TABLE turn_metrics_new (
                run_id TEXT NOT NULL,
                turn_number INTEGER NOT NULL,
                metrics TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (run_id, turn_number),
                FOREIGN KEY (run_id, turn_number) REFERENCES turns (run_id, turn_number),
                CHECK (turn_number >= 0)
            )
            """
        )
        conn.exec_driver_sql(
            "INSERT INTO turn_metrics_new SELECT * FROM turn_metrics",
        )
        conn.exec_driver_sql("DROP TABLE turn_metrics")
        conn.exec_driver_sql("ALTER TABLE turn_metrics_new RENAME TO turn_metrics")
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_turn_metrics_run_id ON turn_metrics (run_id)"
        )

        conn.exec_driver_sql(
            """
            CREATE TABLE turn_generated_feeds (
                feed_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                turn_number INTEGER NOT NULL,
                agent_id TEXT NOT NULL,
                agent_handle TEXT,
                post_ids TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (agent_id, run_id, turn_number),
                FOREIGN KEY (run_id) REFERENCES runs (run_id),
                FOREIGN KEY (agent_id) REFERENCES agent (agent_id),
                FOREIGN KEY (run_id, turn_number) REFERENCES turns (run_id, turn_number)
            )
            """
        )
        conn.exec_driver_sql(
            "INSERT INTO turn_generated_feeds SELECT * FROM generated_feeds",
        )
        conn.exec_driver_sql("DROP TABLE generated_feeds")

        conn.exec_driver_sql("DROP INDEX IF EXISTS idx_likes_run_turn_agent")
        conn.exec_driver_sql(
            """
            CREATE TABLE turn_likes (
                like_id TEXT NOT NULL PRIMARY KEY,
                run_id TEXT NOT NULL,
                turn_number INTEGER NOT NULL,
                agent_id TEXT NOT NULL,
                post_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                explanation TEXT,
                model_used TEXT,
                generation_metadata_json TEXT,
                generation_created_at TEXT,
                FOREIGN KEY (run_id) REFERENCES runs (run_id),
                FOREIGN KEY (agent_id) REFERENCES agent (agent_id),
                FOREIGN KEY (run_id, turn_number) REFERENCES turns (run_id, turn_number),
                CHECK (turn_number >= 0),
                CONSTRAINT uq_turn_likes_run_turn_agent_post UNIQUE (run_id, turn_number, agent_id, post_id)
            )
            """
        )
        conn.exec_driver_sql(
            """
            INSERT INTO turn_likes SELECT
                like_id, run_id, turn_number, agent_id, post_id,
                created_at, explanation, model_used,
                generation_metadata_json, generation_created_at
            FROM likes
            """
        )
        conn.exec_driver_sql("DROP TABLE likes")
        conn.exec_driver_sql(
            "CREATE INDEX idx_turn_likes_run_turn_agent "
            "ON turn_likes (run_id, turn_number, agent_id)"
        )

        conn.exec_driver_sql("DROP INDEX IF EXISTS idx_comments_run_turn_agent")
        conn.exec_driver_sql(
            """
            CREATE TABLE turn_comments (
                comment_id TEXT NOT NULL PRIMARY KEY,
                run_id TEXT NOT NULL,
                turn_number INTEGER NOT NULL,
                agent_id TEXT NOT NULL,
                post_id TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                explanation TEXT,
                model_used TEXT,
                generation_metadata_json TEXT,
                generation_created_at TEXT,
                FOREIGN KEY (run_id) REFERENCES runs (run_id),
                FOREIGN KEY (agent_id) REFERENCES agent (agent_id),
                FOREIGN KEY (run_id, turn_number) REFERENCES turns (run_id, turn_number),
                CHECK (turn_number >= 0),
                CONSTRAINT uq_turn_comments_run_turn_agent_post UNIQUE (run_id, turn_number, agent_id, post_id)
            )
            """
        )
        conn.exec_driver_sql(
            """
            INSERT INTO turn_comments SELECT
                comment_id, run_id, turn_number, agent_id, post_id, text,
                created_at, explanation, model_used,
                generation_metadata_json, generation_created_at
            FROM comments
            """
        )
        conn.exec_driver_sql("DROP TABLE comments")
        conn.exec_driver_sql(
            "CREATE INDEX idx_turn_comments_run_turn_agent "
            "ON turn_comments (run_id, turn_number, agent_id)"
        )

        conn.exec_driver_sql("DROP INDEX IF EXISTS idx_follows_run_turn_agent")
        conn.exec_driver_sql(
            """
            CREATE TABLE turn_follows (
                follow_id TEXT NOT NULL PRIMARY KEY,
                run_id TEXT NOT NULL,
                turn_number INTEGER NOT NULL,
                agent_id TEXT NOT NULL,
                target_agent_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                explanation TEXT,
                model_used TEXT,
                generation_metadata_json TEXT,
                generation_created_at TEXT,
                FOREIGN KEY (run_id) REFERENCES runs (run_id),
                FOREIGN KEY (agent_id) REFERENCES agent (agent_id),
                FOREIGN KEY (target_agent_id) REFERENCES agent (agent_id),
                FOREIGN KEY (run_id, turn_number) REFERENCES turns (run_id, turn_number),
                CHECK (turn_number >= 0),
                CONSTRAINT ck_turn_follows_no_self_follow CHECK (agent_id != target_agent_id),
                CONSTRAINT uq_turn_follows_run_turn_agent_target UNIQUE (run_id, turn_number, agent_id, target_agent_id)
            )
            """
        )
        conn.exec_driver_sql(
            """
            INSERT INTO turn_follows SELECT
                follow_id, run_id, turn_number, agent_id, target_agent_id,
                created_at, explanation, model_used,
                generation_metadata_json, generation_created_at
            FROM follows
            """
        )
        conn.exec_driver_sql("DROP TABLE follows")
        conn.exec_driver_sql(
            "CREATE INDEX idx_turn_follows_run_turn_agent "
            "ON turn_follows (run_id, turn_number, agent_id)"
        )

        conn.exec_driver_sql(
            """
            CREATE TABLE turn_posts (
                turn_post_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                turn_number INTEGER NOT NULL,
                author_agent_id TEXT NOT NULL,
                author_handle_at_time TEXT NOT NULL,
                author_display_name_at_time TEXT NOT NULL,
                body_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                explanation TEXT,
                model_used TEXT,
                generation_metadata_json TEXT,
                generation_created_at TEXT,
                PRIMARY KEY (turn_post_id),
                FOREIGN KEY (run_id, turn_number) REFERENCES turns (run_id, turn_number),
                FOREIGN KEY (run_id, author_agent_id) REFERENCES run_agents (run_id, agent_id),
                CHECK (turn_number >= 0)
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX idx_turn_posts_run_turn_author "
            "ON turn_posts (run_id, turn_number, author_agent_id)"
        )
    finally:
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")


def downgrade() -> None:
    raise NotImplementedError("Downgrade unsupported; restore from backup.")
