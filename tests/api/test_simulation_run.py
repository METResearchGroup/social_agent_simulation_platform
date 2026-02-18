"""Tests for POST /v1/simulations/run endpoint."""

from unittest.mock import MagicMock

from lib.timestamp_utils import get_current_timestamp
from simulation.api.dummy_data import DUMMY_RUNS, DUMMY_TURNS
from simulation.core.exceptions import SimulationRunFailure
from simulation.core.models.actions import TurnAction
from simulation.core.models.metrics import RunMetrics, TurnMetrics
from simulation.core.models.runs import Run, RunStatus
from simulation.core.models.turns import TurnMetadata


def test_post_simulations_run_success_returns_completed_and_metrics(simulation_client):
    """Success run returns 200 with status completed and per-turn metrics."""
    client, fastapi_app = simulation_client
    run = Run(
        run_id="run-success-1",
        created_at=get_current_timestamp(),
        total_turns=1,
        total_agents=1,
        feed_algorithm="chronological",
        started_at=get_current_timestamp(),
        status=RunStatus.COMPLETED,
        completed_at=get_current_timestamp(),
    )
    metadata_list = [
        TurnMetadata(
            run_id=run.run_id,
            turn_number=0,
            total_actions={
                TurnAction.LIKE: 0,
                TurnAction.COMMENT: 0,
                TurnAction.FOLLOW: 0,
            },
            created_at=run.created_at,
        ),
    ]
    turn_metrics_list = [
        TurnMetrics(
            run_id=run.run_id,
            turn_number=0,
            metrics={"turn.actions.total": 0},
            created_at=run.created_at,
        )
    ]
    run_metrics = RunMetrics(
        run_id=run.run_id,
        metrics={"run.actions.total": 0},
        created_at=run.created_at,
    )
    mock_engine = MagicMock()
    mock_engine.execute_run.return_value = run
    mock_engine.list_turn_metadata.return_value = metadata_list
    mock_engine.list_turn_metrics.return_value = turn_metrics_list
    mock_engine.get_run_metrics.return_value = run_metrics
    fastapi_app.state.engine = mock_engine
    response = client.post(
        "/v1/simulations/run",
        json={"num_agents": 1, "num_turns": 1},
    )
    assert response.status_code == 200
    data = response.json()
    expected_result = {
        "status": "completed",
        "num_agents": 1,
        "num_turns": 1,
        "error": None,
    }
    assert data["status"] == expected_result["status"]
    assert data["num_agents"] == expected_result["num_agents"]
    assert data["num_turns"] == expected_result["num_turns"]
    assert data["error"] is expected_result["error"]
    assert data["run_id"] == run.run_id
    assert data["turns"] == [
        {
            "turn_number": 0,
            "created_at": run.created_at,
            "total_actions": {"like": 0, "comment": 0, "follow": 0},
            "metrics": {"turn.actions.total": 0},
        }
    ]
    assert data["run_metrics"] == {"run.actions.total": 0}


def test_post_simulations_run_defaults_num_turns_and_feed_algorithm(simulation_client):
    """Request with only num_agents uses default num_turns=10 and feed_algorithm=chronological."""
    client, fastapi_app = simulation_client
    run = Run(
        run_id="run-defaults-1",
        created_at=get_current_timestamp(),
        total_turns=10,
        total_agents=1,
        feed_algorithm="chronological",
        started_at=get_current_timestamp(),
        status=RunStatus.COMPLETED,
        completed_at=get_current_timestamp(),
    )
    metadata_list = [
        TurnMetadata(
            run_id=run.run_id,
            turn_number=i,
            total_actions={
                TurnAction.LIKE: 0,
                TurnAction.COMMENT: 0,
                TurnAction.FOLLOW: 0,
            },
            created_at=run.created_at,
        )
        for i in range(10)
    ]
    turn_metrics_list = [
        TurnMetrics(
            run_id=run.run_id,
            turn_number=i,
            metrics={"turn.actions.total": 0},
            created_at=run.created_at,
        )
        for i in range(10)
    ]
    run_metrics = RunMetrics(
        run_id=run.run_id,
        metrics={"run.actions.total": 0},
        created_at=run.created_at,
    )
    mock_engine = MagicMock()
    mock_engine.execute_run.return_value = run
    mock_engine.list_turn_metadata.return_value = metadata_list
    mock_engine.list_turn_metrics.return_value = turn_metrics_list
    mock_engine.get_run_metrics.return_value = run_metrics
    fastapi_app.state.engine = mock_engine
    response = client.post(
        "/v1/simulations/run",
        json={"num_agents": 1},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["num_turns"] == 10
    assert data["status"] == "completed"
    assert len(data["turns"]) == 10


def test_post_simulations_run_validation_num_agents_zero(simulation_client):
    """Invalid num_agents returns 422."""
    client, _ = simulation_client
    response = client.post(
        "/v1/simulations/run",
        json={"num_agents": 0},
    )
    assert response.status_code == 422


def test_post_simulations_run_validation_num_agents_missing(simulation_client):
    """Missing num_agents returns 422."""
    client, _ = simulation_client
    response = client.post(
        "/v1/simulations/run",
        json={},
    )
    assert response.status_code == 422


def test_post_simulations_run_validation_invalid_feed_algorithm(simulation_client):
    """Invalid feed_algorithm returns 422."""
    client, _ = simulation_client
    response = client.post(
        "/v1/simulations/run",
        json={"num_agents": 1, "feed_algorithm": "invalid_algo"},
    )
    assert response.status_code == 422


def test_post_simulations_run_pre_create_failure_returns_500(simulation_client):
    """Failure before run creation returns 500 with error payload."""
    client, fastapi_app = simulation_client
    mock_engine = MagicMock()
    mock_engine.execute_run.side_effect = SimulationRunFailure(
        message="Run creation or status update failed",
        run_id=None,
        cause=RuntimeError("db error"),
    )
    fastapi_app.state.engine = mock_engine
    response = client.post(
        "/v1/simulations/run",
        json={"num_agents": 2, "num_turns": 2},
    )
    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "RUN_CREATION_FAILED"
    assert data["error"]["message"] == "Run creation or status update failed"
    assert data["error"]["detail"] is None


def test_post_simulations_run_partial_failure_returns_200_with_partial_metrics(
    simulation_client,
):
    """Mid-run failure returns 200 with status failed and partial per-turn metrics."""
    client, fastapi_app = simulation_client
    partial_metadata = [
        TurnMetadata(
            run_id="run-partial-1",
            turn_number=0,
            total_actions={
                TurnAction.LIKE: 3,
                TurnAction.COMMENT: 0,
                TurnAction.FOLLOW: 0,
            },
            created_at="2026-01-01T00:00:00",
        ),
    ]
    partial_turn_metrics = [
        TurnMetrics(
            run_id="run-partial-1",
            turn_number=0,
            metrics={"turn.actions.total": 3},
            created_at="2026-01-01T00:00:00",
        )
    ]
    mock_engine = MagicMock()
    mock_engine.execute_run.side_effect = SimulationRunFailure(
        message="Run failed during execution",
        run_id="run-partial-1",
        cause=RuntimeError("turn 1 failed"),
    )
    mock_engine.list_turn_metadata.return_value = partial_metadata
    mock_engine.list_turn_metrics.return_value = partial_turn_metrics
    mock_engine.get_run_metrics.return_value = None
    fastapi_app.state.engine = mock_engine
    response = client.post(
        "/v1/simulations/run",
        json={"num_agents": 2, "num_turns": 2},
    )
    assert response.status_code == 200
    data = response.json()
    expected_result = {
        "run_id": "run-partial-1",
        "status": "failed",
        "num_agents": 2,
        "num_turns": 2,
        "turns": [
            {
                "turn_number": 0,
                "created_at": "2026-01-01T00:00:00",
                "total_actions": {"like": 3, "comment": 0, "follow": 0},
                "metrics": {"turn.actions.total": 3},
            }
        ],
        "run_metrics": None,
    }
    assert data["run_id"] == expected_result["run_id"]
    assert data["status"] == expected_result["status"]
    assert data["num_agents"] == expected_result["num_agents"]
    assert data["num_turns"] == expected_result["num_turns"]
    assert data["turns"] == expected_result["turns"]
    assert data["run_metrics"] is expected_result["run_metrics"]
    assert data["error"] is not None
    assert data["error"]["code"] == "SIMULATION_FAILED"
    assert data["error"]["message"] == "Run failed during execution"
    assert data["error"]["detail"] is None


def test_get_simulations_runs_returns_dummy_run_list(simulation_client):
    """GET /v1/simulations/runs returns dummy run summaries from backend."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/runs")

    assert response.status_code == 200
    data = response.json()
    sorted_run_ids = [
        run.run_id
        for run in sorted(
            DUMMY_RUNS,
            key=lambda run: run.created_at,
            reverse=True,
        )
    ]
    expected_result = {
        "count": len(DUMMY_RUNS),
        "first_run_id": sorted_run_ids[0],
    }
    assert len(data) == expected_result["count"]
    assert data[0]["run_id"] == expected_result["first_run_id"]
    assert "total_turns" in data[0]
    assert "total_agents" in data[0]


def test_get_simulations_run_turns_returns_turn_map(simulation_client):
    """GET /v1/simulations/runs/{run_id}/turns returns turn payload map."""
    client, _ = simulation_client
    run_id = DUMMY_RUNS[0].run_id
    response = client.get(f"/v1/simulations/runs/{run_id}/turns")

    assert response.status_code == 200
    data = response.json()
    expected_result = {
        "turn_count": len(DUMMY_TURNS[run_id]),
        "first_turn_key": "0",
    }
    assert len(data) == expected_result["turn_count"]
    assert expected_result["first_turn_key"] in data
    assert "turn_number" in data[expected_result["first_turn_key"]]
    assert "agent_feeds" in data[expected_result["first_turn_key"]]
    assert "agent_actions" in data[expected_result["first_turn_key"]]


def test_get_simulations_run_turns_missing_run_returns_404(simulation_client):
    """Unknown run_id for turns endpoint returns stable RUN_NOT_FOUND payload."""
    client, _ = simulation_client
    response = client.get("/v1/simulations/runs/missing-run-id/turns")

    assert response.status_code == 404
    data = response.json()
    expected_result = {
        "code": "RUN_NOT_FOUND",
        "message": "Run not found",
    }
    assert data["error"]["code"] == expected_result["code"]
    assert data["error"]["message"] == expected_result["message"]
