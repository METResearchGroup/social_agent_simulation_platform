"""Tests for SimulationRepositories.update_agent_memory."""

from __future__ import annotations

from pathlib import Path

from simulation_v2.db.connection import transaction
from simulation_v2.db.database import SimulationDatabase
from tests.simulation_v2.db import factories


def test_update_agent_memory_changes_episodic_and_updated_at(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "test.sqlite3"
    db = SimulationDatabase(db_path)
    db.initialize()
    run = factories.RunRecordFactory.create()
    memory = factories.AgentMemoryRecordFactory.create(
        run_id=run.run_id,
        user_id="u1",
        episodic="",
        personalized="",
        social="",
        updated_at="old-ts",
    )

    with transaction(db_path) as conn:
        db.repos.insert_run(run, conn)
        db.repos.insert_agent_memory(memory, conn)
        updated = memory.model_copy(
            update={
                "episodic": "Turn 1: liked post p1",
                "updated_at": "new-ts",
            }
        )
        db.repos.update_agent_memory(updated, conn)
        loaded = db.repos.get_agent_memory(run.run_id, "u1", conn)

    assert loaded is not None
    assert loaded.episodic == "Turn 1: liked post p1"
    assert loaded.updated_at == "new-ts"
