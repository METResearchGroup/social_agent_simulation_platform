"""Format run completion summaries for simulation_v2 main entrypoint."""

from __future__ import annotations

import sqlite3
from typing import Any

from simulation_v2.db.models import RunRecord, TurnRecord

_NON_TERMINAL_EVAL_STATUSES = frozenset({"queued", "running", "pending", "in_progress"})
_TERMINAL_EVAL_STATUSES = frozenset({"passed", "failed"})


def format_entity_delta(initial: int, final: int) -> str:
    """Format a final count with delta vs initial, e.g. ``52 (+2)``."""
    delta = final - initial
    if delta == 0:
        return str(final)
    sign = "+" if delta > 0 else ""
    return f"{final} ({sign}{delta})"


def format_eval_summary(run_id: str, conn: sqlite3.Connection) -> str:
    """One-line summary of persisted eval runs for a completed simulation."""
    rows = conn.execute(
        """
        SELECT scope, plugin_name, status
        FROM eval_runs
        WHERE run_id = ?
        ORDER BY scope DESC, plugin_name
        """,
        (run_id,),
    ).fetchall()
    if not rows:
        return "Evals: none recorded"

    metric_count = int(
        conn.execute(
            "SELECT COUNT(*) AS count FROM eval_metrics WHERE run_id = ?",
            (run_id,),
        ).fetchone()["count"]
    )
    turn_count = sum(1 for row in rows if row["scope"] == "turn")
    run_count = sum(1 for row in rows if row["scope"] == "run")
    failed = [row["plugin_name"] for row in rows if row["status"] == "failed"]
    incomplete = [
        f"{row['plugin_name']}={row['status']}"
        for row in rows
        if row["status"] in _NON_TERMINAL_EVAL_STATUSES
        or row["status"] not in _TERMINAL_EVAL_STATUSES
    ]
    run_scope = ", ".join(
        f"{row['plugin_name']}={row['status']}" for row in rows if row["scope"] == "run"
    )

    summary = (
        f"Evals: {len(rows)} plugin runs "
        f"({turn_count} turn + {run_count} run scope), {metric_count} metrics"
    )
    if incomplete:
        return f"{summary}; incomplete: {', '.join(incomplete)}. Run-scope: {run_scope}"
    if failed:
        return f"{summary}; failed: {', '.join(failed)}"
    return f"{summary}; all completed. Run-scope: {run_scope}"


def format_run_summary(
    run: RunRecord,
    turns: list[TurnRecord],
    seed_meta: dict[str, Any] | None,
    totals: dict[str, int],
    eval_summary: str,
) -> list[str]:
    """Build printable summary lines for a completed run."""
    completed_count = sum(1 for turn in turns if turn.status == "completed")
    meta = seed_meta or {}

    initial_posts = int(meta.get("post_count", 0))
    initial_likes = int(meta.get("like_count", 0))
    initial_follows = int(meta.get("follow_count", 0))
    initial_comments = 0

    return [
        (
            f"Run complete: run_id={run.run_id} status={run.status} "
            f"completed_turns={completed_count}/{len(turns)}"
        ),
        (
            "Entities: "
            f"users={totals['user_count']} "
            f"posts={format_entity_delta(initial_posts, totals['post_count'])} "
            f"likes={format_entity_delta(initial_likes, totals['like_count'])} "
            f"follows={format_entity_delta(initial_follows, totals['follow_count'])} "
            f"comments={format_entity_delta(initial_comments, totals['comment_count'])}"
        ),
        (
            "Pipeline: "
            f"generations={totals['generation_count']} "
            f"proposed_actions={totals['proposed_action_count']} "
            f"generated_feeds={totals['generated_feed_count']} "
            f"eval_runs={totals['eval_run_count']} "
            f"eval_metrics={totals['eval_metric_count']}"
        ),
        eval_summary,
    ]
