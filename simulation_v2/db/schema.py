"""DDL for simulation_v2 SQLite schema."""

from __future__ import annotations

import sqlite3

TABLE_NAMES: tuple[str, ...] = (
    "runs",
    "turns",
    "users",
    "posts",
    "likes",
    "comments",
    "follows",
    "agent_memories",
    "memory_diffs",
    "generated_feeds",
    "generations",
    "llm_proposed_actions",
    "proposed_actions",
    "eval_runs",
    "eval_metrics",
)

_DDL_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS runs (
        run_id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        config_json TEXT NOT NULL,
        seed_metadata_json TEXT,
        created_at TEXT NOT NULL,
        started_at TEXT,
        finished_at TEXT,
        error TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS turns (
        turn_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        turn_number INTEGER NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        started_at TEXT,
        finished_at TEXT,
        error TEXT,
        FOREIGN KEY (run_id) REFERENCES runs (run_id),
        UNIQUE (run_id, turn_number)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT NOT NULL,
        run_id TEXT NOT NULL,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        username TEXT NOT NULL,
        profile_json TEXT,
        created_at TEXT NOT NULL,
        PRIMARY KEY (run_id, user_id),
        FOREIGN KEY (run_id) REFERENCES runs (run_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS posts (
        post_id TEXT NOT NULL,
        run_id TEXT NOT NULL,
        author_id TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        created_at_turn INTEGER NOT NULL,
        metadata_json TEXT,
        PRIMARY KEY (run_id, post_id),
        FOREIGN KEY (run_id) REFERENCES runs (run_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS likes (
        like_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        post_id TEXT NOT NULL,
        author_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        created_at_turn INTEGER NOT NULL,
        metadata_json TEXT,
        FOREIGN KEY (run_id) REFERENCES runs (run_id),
        UNIQUE (run_id, author_id, post_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS comments (
        comment_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        parent_post_id TEXT NOT NULL,
        author_id TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        created_at_turn INTEGER NOT NULL,
        metadata_json TEXT,
        FOREIGN KEY (run_id) REFERENCES runs (run_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS follows (
        follow_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        follower_id TEXT NOT NULL,
        followee_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        created_at_turn INTEGER NOT NULL,
        metadata_json TEXT,
        FOREIGN KEY (run_id) REFERENCES runs (run_id),
        UNIQUE (run_id, follower_id, followee_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS agent_memories (
        run_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        preferences_json TEXT,
        episodic TEXT,
        personalized TEXT,
        social TEXT,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (run_id, user_id),
        FOREIGN KEY (run_id) REFERENCES runs (run_id),
        UNIQUE (run_id, user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS memory_diffs (
        memory_diff_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        turn_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        memory_type TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (run_id) REFERENCES runs (run_id),
        FOREIGN KEY (turn_id) REFERENCES turns (turn_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS generated_feeds (
        feed_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        turn_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        algorithm TEXT NOT NULL,
        feed_post_ids_json TEXT NOT NULL,
        feed_posts_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (run_id) REFERENCES runs (run_id),
        FOREIGN KEY (turn_id) REFERENCES turns (turn_id),
        UNIQUE (run_id, turn_id, user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS generations (
        generation_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        turn_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        action_type TEXT NOT NULL,
        parsed_response_json TEXT,
        raw_response_json TEXT,
        status TEXT NOT NULL,
        latency_ms REAL,
        prompt_tokens INTEGER,
        completion_tokens INTEGER,
        cost_usd REAL,
        created_at TEXT NOT NULL,
        error TEXT,
        FOREIGN KEY (run_id) REFERENCES runs (run_id),
        FOREIGN KEY (turn_id) REFERENCES turns (turn_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS llm_proposed_actions (
        llm_proposed_action_id TEXT PRIMARY KEY,
        generation_id TEXT NOT NULL,
        run_id TEXT NOT NULL,
        turn_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        action_type TEXT NOT NULL,
        target_type TEXT,
        target_id TEXT,
        target_content TEXT,
        metadata_json TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (generation_id) REFERENCES generations (generation_id),
        FOREIGN KEY (run_id) REFERENCES runs (run_id),
        FOREIGN KEY (turn_id) REFERENCES turns (turn_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS proposed_actions (
        action_id TEXT PRIMARY KEY,
        record_kind TEXT NOT NULL,
        generation_id TEXT,
        run_id TEXT NOT NULL,
        turn_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        action_type TEXT NOT NULL,
        target_type TEXT,
        target_id TEXT,
        target_content TEXT,
        filter_id TEXT,
        filter_reason TEXT,
        rejection_stage TEXT,
        metadata_json TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (generation_id) REFERENCES generations (generation_id),
        FOREIGN KEY (run_id) REFERENCES runs (run_id),
        FOREIGN KEY (turn_id) REFERENCES turns (turn_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS eval_runs (
        eval_run_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        turn_id TEXT,
        scope TEXT NOT NULL,
        plugin_name TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        finished_at TEXT,
        error TEXT,
        FOREIGN KEY (run_id) REFERENCES runs (run_id),
        FOREIGN KEY (turn_id) REFERENCES turns (turn_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS eval_metrics (
        eval_metric_id TEXT PRIMARY KEY,
        eval_run_id TEXT NOT NULL,
        run_id TEXT NOT NULL,
        turn_id TEXT,
        plugin_name TEXT NOT NULL,
        metric_name TEXT NOT NULL,
        metric_value REAL NOT NULL,
        metadata_json TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (eval_run_id) REFERENCES eval_runs (eval_run_id),
        FOREIGN KEY (run_id) REFERENCES runs (run_id),
        FOREIGN KEY (turn_id) REFERENCES turns (turn_id)
    )
    """,
)


def create_schema(conn: sqlite3.Connection) -> None:
    for statement in _DDL_STATEMENTS:
        conn.execute(statement)


def list_table_names(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
    ).fetchall()
    return [row["name"] for row in rows if row["name"] != "sqlite_sequence"]
