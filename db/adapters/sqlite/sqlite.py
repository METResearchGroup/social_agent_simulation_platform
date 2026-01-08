"""SQLite database infrastructure.

This module provides SQLite-specific infrastructure functions:
- Database connection management
- Database initialization
- Database path configuration
"""

import os
import sqlite3


DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "db.sqlite")


def get_connection() -> sqlite3.Connection:
    """Get a database connection.

    Returns:
        SQLite connection to db.sqlite
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database() -> None:
    """Initialize the database by creating tables if they don't exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bluesky_profiles (
                handle TEXT PRIMARY KEY,
                did TEXT NOT NULL,
                display_name TEXT NOT NULL,
                bio TEXT NOT NULL,
                followers_count INTEGER NOT NULL,
                follows_count INTEGER NOT NULL,
                posts_count INTEGER NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS bluesky_feed_posts (
                uri TEXT PRIMARY KEY,
                author_display_name TEXT NOT NULL,
                author_handle TEXT NOT NULL,
                text TEXT NOT NULL,
                bookmark_count INTEGER NOT NULL,
                like_count INTEGER NOT NULL,
                quote_count INTEGER NOT NULL,
                reply_count INTEGER NOT NULL,
                repost_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_bios (
                handle TEXT PRIMARY KEY,
                generated_bio TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS generated_feeds (
                feed_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                turn_number INTEGER NOT NULL,
                agent_handle TEXT NOT NULL,
                post_uris TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (agent_handle, run_id, turn_number)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                total_turns INTEGER NOT NULL CHECK (total_turns > 0),
                total_agents INTEGER NOT NULL CHECK (total_agents > 0),
                started_at TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('running', 'completed', 'failed')),
                completed_at TEXT NULL,
                CHECK (
                    (status = 'completed' AND completed_at IS NOT NULL AND completed_at >= started_at) OR
                    (status != 'completed' AND completed_at IS NULL)
                )
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS turn_metadata (
                run_id TEXT NOT NULL REFERENCES runs(run_id),
                turn_number INTEGER NOT NULL CHECK (turn_number >= 0),
                total_actions TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (run_id, turn_number)
            )
        """)

        # Create indexes for frequently queried columns
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at DESC)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_bluesky_feed_posts_author_handle 
            ON bluesky_feed_posts(author_handle)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_turn_metadata_run_id ON turn_metadata(run_id)
        """)

        conn.commit()
