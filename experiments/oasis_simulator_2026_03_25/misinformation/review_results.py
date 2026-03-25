"""Inspect OASIS `simulation.db` (SQLite) and print per-table stats and row previews.

OASIS stores the simulated social platform state in SQLite: users/agents, posts,
follows, likes, traces of actions, recommendations, etc. See the upstream project:
https://github.com/camel-ai/oasis

Run from repo root:

    uv run python experiments/oasis_simulator_2026_03_25/misinformation/review_results.py

Or with a custom DB path:

    uv run python .../review_results.py --db /path/to/simulation.db
"""

# ruff: noqa: T201, S608
# CLI tool: prints summaries; SQL identifiers come only from sqlite_master + PRAGMA.

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pandas as pd


def _table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cur = conn.execute(f'PRAGMA table_info("{table}")')
    return [row[1] for row in cur.fetchall()]


def _quote_ident(table: str) -> str:
    return '"' + table.replace('"', '""') + '"'


def _distinct_agents_sql(table: str, columns: list[str]) -> str | None:
    """Return SQL for a single scalar: distinct agent-like identities in this table."""
    t = _quote_ident(table)
    cset = {name.lower(): name for name in columns}

    if "agent_id" in cset:
        col = cset["agent_id"]
        return f"SELECT COUNT(DISTINCT {_quote_ident(col)}) FROM {t} WHERE {_quote_ident(col)} IS NOT NULL"

    if table.lower() == "user" and "user_id" in cset:
        return f"SELECT COUNT(*) FROM {t}"

    if "follower_id" in cset and "followee_id" in cset:
        cf, ce = cset["follower_id"], cset["followee_id"]
        return (
            f"SELECT COUNT(*) FROM ("
            f"SELECT {_quote_ident(cf)} AS aid FROM {t} WHERE {_quote_ident(cf)} IS NOT NULL "
            f"UNION SELECT {_quote_ident(ce)} AS aid FROM {t} WHERE {_quote_ident(ce)} IS NOT NULL)"
        )

    if "muter_id" in cset and "mutee_id" in cset:
        cm, ce = cset["muter_id"], cset["mutee_id"]
        return (
            f"SELECT COUNT(*) FROM ("
            f"SELECT {_quote_ident(cm)} AS aid FROM {t} WHERE {_quote_ident(cm)} IS NOT NULL "
            f"UNION SELECT {_quote_ident(ce)} AS aid FROM {t} WHERE {_quote_ident(ce)} IS NOT NULL)"
        )

    if "user_id" in cset:
        col = cset["user_id"]
        return f"SELECT COUNT(DISTINCT {_quote_ident(col)}) FROM {t} WHERE {_quote_ident(col)} IS NOT NULL"

    if "sender_id" in cset:
        col = cset["sender_id"]
        return f"SELECT COUNT(DISTINCT {_quote_ident(col)}) FROM {t} WHERE {_quote_ident(col)} IS NOT NULL"

    return None


def _list_user_tables(conn: sqlite3.Connection) -> list[str]:
    df = pd.read_sql(
        """
        SELECT name FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """,
        conn,
    )
    return df["name"].astype(str).tolist()


def main() -> None:
    default_db = Path(__file__).resolve().parent / "data" / "simulation.db"
    parser = argparse.ArgumentParser(
        description="Summarize OASIS simulation.db tables."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=default_db,
        help=f"Path to SQLite DB (default: {default_db})",
    )
    args = parser.parse_args()
    db_path: Path = args.db

    if not db_path.is_file():
        raise SystemExit(f"Database file not found: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        tables = _list_user_tables(conn)
        summary_rows: list[dict[str, object]] = []

        print(f"Database: {db_path}\n")
        print(
            "OASIS persists agents, posts, edges, and action traces in SQLite "
            "(see https://github.com/camel-ai/oasis).\n"
        )

        for table in tables:
            tq = _quote_ident(table)
            total = int(conn.execute(f"SELECT COUNT(*) FROM {tq}").fetchone()[0])
            cols = _table_columns(conn, table)
            agents_sql = _distinct_agents_sql(table, cols)
            if agents_sql is None:
                total_agents: int | str = "n/a"
            else:
                total_agents = int(conn.execute(agents_sql).fetchone()[0])

            summary_rows.append(
                {
                    "table": table,
                    "row_count": total,
                    "total_agents": total_agents,
                }
            )

        summary_df = pd.DataFrame(summary_rows)
        print("=== Summary (all tables) ===")
        print(summary_df.to_string(index=False))
        print()

        for table in tables:
            tq = _quote_ident(table)
            print(f"=== Table: {table} ===")
            peek = pd.read_sql(f"SELECT * FROM {tq} LIMIT 5", conn)
            print(peek.to_string(index=False))
            print()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
