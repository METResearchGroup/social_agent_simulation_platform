"""Schema smoke tests for simulation_v2 SQLite."""

from __future__ import annotations

from pathlib import Path

from simulation_v2.db.connection import open_connection
from simulation_v2.db.database import SimulationDatabase
from simulation_v2.db.schema import TABLE_NAMES, list_table_names


class TestSchema:
    def test_initialize_creates_all_tables(self, tmp_path: Path) -> None:
        db_path = tmp_path / "schema.sqlite3"
        db = SimulationDatabase(db_path)
        db.initialize()

        with open_connection(db_path) as conn:
            table_names = list_table_names(conn)

        assert sorted(table_names) == sorted(TABLE_NAMES)

    def test_initialize_is_idempotent(self, tmp_path: Path) -> None:
        db_path = tmp_path / "schema.sqlite3"
        db = SimulationDatabase(db_path)
        db.initialize()

        with open_connection(db_path) as conn:
            first_tables = list_table_names(conn)

        db.initialize()

        with open_connection(db_path) as conn:
            second_tables = list_table_names(conn)

        assert first_tables == second_tables
