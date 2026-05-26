"""SimulationDatabase facade wiring connection, schema, and repositories."""

from __future__ import annotations

from pathlib import Path

from simulation_v2.db.connection import transaction
from simulation_v2.db.repositories import SimulationRepositories
from simulation_v2.db.schema import create_schema


class SimulationDatabase:
    def __init__(self, db_path: Path | str) -> None:
        self._db_path = db_path
        self._repos = SimulationRepositories()

    def initialize(self) -> None:
        with transaction(self._db_path) as conn:
            create_schema(conn)

    @property
    def repos(self) -> SimulationRepositories:
        return self._repos
