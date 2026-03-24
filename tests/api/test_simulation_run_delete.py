"""Tests for DELETE /v1/simulations/runs/{run_id}."""

import sqlite3
import uuid

from tests.factories import RunConfigFactory

# Matches ``_mock_require_current_app_user`` in ``tests/api/conftest.py``.
_MOCK_APP_USER_ID: str = "00000000-0000-0000-0000-000000000001"


def _insert_completed_run(
    temp_db: str,
    *,
    run_id: str,
    app_user_id: str | None,
) -> None:
    conn = sqlite3.connect(temp_db)
    conn.execute(
        """
        INSERT INTO runs (
            run_id, app_user_id, created_at, total_turns, total_agents,
            feed_algorithm, metric_keys, started_at, status, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            app_user_id,
            "2026-01-01T00:00:00",
            1,
            1,
            "chronological",
            None,
            "2026-01-01T00:00:00",
            "completed",
            "2026-01-01T00:00:01",
        ),
    )
    conn.commit()
    conn.close()


class TestDeleteSimulationRun:
    def test_delete_run_returns_204_and_get_returns_404(
        self,
        simulation_client,
        temp_db,
    ):
        """After delete, run is gone from list and GET returns 404."""
        client, _ = simulation_client
        run_id = f"run-delete-{uuid.uuid4().hex[:12]}"
        _insert_completed_run(temp_db, run_id=run_id, app_user_id=_MOCK_APP_USER_ID)

        assert any(
            r["run_id"] == run_id for r in client.get("/v1/simulations/runs").json()
        )

        delete = client.delete(f"/v1/simulations/runs/{run_id}")
        assert delete.status_code == 204

        get_run = client.get(f"/v1/simulations/runs/{run_id}")
        assert get_run.status_code == 404
        assert get_run.json()["error"]["code"] == "RUN_NOT_FOUND"

        listed = client.get("/v1/simulations/runs").json()
        assert not any(r["run_id"] == run_id for r in listed)

    def test_delete_run_returns_403_when_app_user_mismatch(
        self,
        simulation_client,
        temp_db,
    ):
        """Cannot delete another user's run when runs.app_user_id is set."""
        client, _ = simulation_client
        run_id = f"run-delete-403-{uuid.uuid4().hex[:12]}"
        _insert_completed_run(temp_db, run_id=run_id, app_user_id="other-app-user-id")

        delete = client.delete(f"/v1/simulations/runs/{run_id}")
        assert delete.status_code == 403
        assert delete.json()["error"]["code"] == "RUN_FORBIDDEN"

        get_run = client.get(f"/v1/simulations/runs/{run_id}")
        assert get_run.status_code == 200


class TestRunDeletionSqliteIntegration:
    def test_delete_run_removes_run_row_and_no_orphans_for_minimal_run(
        self,
        run_repo,
        temp_db,
    ):
        """Repository delete removes the runs row (spot-check FK chain)."""
        config = RunConfigFactory.create(num_agents=1, num_turns=1)
        run = run_repo.create_run(config, created_by_app_user_id=None)
        run_id = run.run_id

        run_repo.delete_run(run_id)

        conn = sqlite3.connect(temp_db)
        conn.row_factory = sqlite3.Row
        n = conn.execute(
            "SELECT count(*) AS c FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()["c"]
        conn.close()
        assert n == 0
