"""Transactional deletion of a simulation run and all dependent SQLite rows.

Delete order respects foreign keys (children before parents). Table list matches
``db/schema.py`` at repository HEAD.
"""

from __future__ import annotations

import sqlite3

_DELETE_STATEMENTS_ORDERED: tuple[str, ...] = (
    "DELETE FROM turn_generated_feeds WHERE run_id = ?",
    "DELETE FROM turn_metrics WHERE run_id = ?",
    "DELETE FROM turn_likes WHERE run_id = ?",
    "DELETE FROM turn_comments WHERE run_id = ?",
    "DELETE FROM turn_follows WHERE run_id = ?",
    "DELETE FROM turn_posts WHERE run_id = ?",
    "DELETE FROM run_post_comments WHERE run_id = ?",
    "DELETE FROM run_post_likes WHERE run_id = ?",
    "DELETE FROM run_follow_edges WHERE run_id = ?",
    "DELETE FROM run_posts WHERE run_id = ?",
    "DELETE FROM turns WHERE run_id = ?",
    "DELETE FROM run_metrics WHERE run_id = ?",
    "DELETE FROM run_agents WHERE run_id = ?",
    "DELETE FROM runs WHERE run_id = ?",
)


def delete_run_and_dependents(conn: sqlite3.Connection, run_id: str) -> int:
    """Delete all rows for ``run_id`` in one transaction.

    Args:
        conn: SQLite connection with ``PRAGMA foreign_keys = ON``.
        run_id: Run primary key.

    Returns:
        Number of rows deleted from ``runs`` (0 if the run did not exist, 1 on success).
    """
    deleted_from_runs = 0
    for sql in _DELETE_STATEMENTS_ORDERED:
        cur = conn.execute(sql, (run_id,))
        if sql.startswith("DELETE FROM runs"):
            deleted_from_runs = cur.rowcount
    return deleted_from_runs
