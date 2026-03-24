"""SQLite read/write path for turn-authored posts."""

import sqlite3
from collections.abc import Iterable

from db.adapters.base import TurnPostDatabaseAdapter
from db.adapters.sqlite.schema_utils import required_column_names
from db.adapters.sqlite.sqlite import validate_required_fields
from db.schema import turn_posts as turn_posts_table
from simulation.core.models.turn_posts import TurnPostSnapshot

TURN_POST_REQUIRED_FIELDS = required_column_names(turn_posts_table)


def _build_read_turn_posts_by_ids_sql(num_ids: int) -> str:
    placeholders = ", ".join("?" for _ in range(num_ids))
    return f"SELECT * FROM turn_posts WHERE run_id = ? AND turn_post_id IN ({placeholders})"  # nosec B608


class SQLiteTurnPostAdapter(TurnPostDatabaseAdapter):
    """SQLite implementation of TurnPostDatabaseAdapter."""

    def _validate_turn_post_row(self, row: sqlite3.Row) -> None:
        validate_required_fields(row, TURN_POST_REQUIRED_FIELDS)

    def _row_to_turn_post_snapshot(self, row: sqlite3.Row) -> TurnPostSnapshot:
        return TurnPostSnapshot(
            turn_post_id=row["turn_post_id"],
            run_id=row["run_id"],
            turn_number=row["turn_number"],
            author_agent_id=row["author_agent_id"],
            author_handle_at_time=row["author_handle_at_time"],
            author_display_name_at_time=row["author_display_name_at_time"],
            body_text=row["body_text"],
            created_at=row["created_at"],
            explanation=row["explanation"],
            model_used=row["model_used"],
            generation_metadata_json=row["generation_metadata_json"],
            generation_created_at=row["generation_created_at"],
        )

    def read_turn_posts_by_ids(
        self,
        run_id: str,
        post_ids: Iterable[str],
        *,
        conn: sqlite3.Connection,
    ) -> list[TurnPostSnapshot]:
        post_ids_list = list(post_ids)
        if not post_ids_list:
            return []
        sql = _build_read_turn_posts_by_ids_sql(len(post_ids_list))
        params: tuple[object, ...] = (run_id, *post_ids_list)
        rows = conn.execute(sql, params).fetchall()
        row_by_id = {row["turn_post_id"]: row for row in rows}
        result: list[TurnPostSnapshot] = []
        for pid in post_ids_list:
            if pid in row_by_id:
                row = row_by_id[pid]
                self._validate_turn_post_row(row)
                result.append(self._row_to_turn_post_snapshot(row))
        return result

    def list_turn_posts_for_run_before_turn(
        self, run_id: str, before_turn_number: int, *, conn: sqlite3.Connection
    ) -> list[TurnPostSnapshot]:
        rows = conn.execute(
            """
            SELECT * FROM turn_posts
            WHERE run_id = ? AND turn_number < ?
            ORDER BY turn_number, turn_post_id
            """,
            (run_id, before_turn_number),
        ).fetchall()
        result: list[TurnPostSnapshot] = []
        for r in rows:
            self._validate_turn_post_row(r)
            result.append(self._row_to_turn_post_snapshot(r))
        return result

    def list_turn_posts_for_run_at_turn(
        self, run_id: str, turn_number: int, *, conn: sqlite3.Connection
    ) -> list[TurnPostSnapshot]:
        rows = conn.execute(
            """
            SELECT * FROM turn_posts
            WHERE run_id = ? AND turn_number = ?
            ORDER BY turn_post_id
            """,
            (run_id, turn_number),
        ).fetchall()
        result: list[TurnPostSnapshot] = []
        for r in rows:
            self._validate_turn_post_row(r)
            result.append(self._row_to_turn_post_snapshot(r))
        return result

    def write_turn_posts(
        self,
        run_id: str,
        turn_number: int,
        rows: Iterable[TurnPostSnapshot],
        *,
        conn: sqlite3.Connection,
    ) -> None:
        for snap in rows:
            if snap.run_id != run_id or snap.turn_number != turn_number:
                raise ValueError(
                    "TurnPostSnapshot run_id/turn_number must match write_turn_posts"
                )
            conn.execute(
                """
                INSERT INTO turn_posts (
                    turn_post_id, run_id, turn_number, author_agent_id,
                    author_handle_at_time, author_display_name_at_time,
                    body_text, created_at, explanation, model_used,
                    generation_metadata_json, generation_created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snap.turn_post_id,
                    snap.run_id,
                    snap.turn_number,
                    snap.author_agent_id,
                    snap.author_handle_at_time,
                    snap.author_display_name_at_time,
                    snap.body_text,
                    snap.created_at,
                    snap.explanation,
                    snap.model_used,
                    snap.generation_metadata_json,
                    snap.generation_created_at,
                ),
            )
