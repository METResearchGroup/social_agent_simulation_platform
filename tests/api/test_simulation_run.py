"""Tests for POST /v1/simulations/run endpoint."""

from unittest.mock import MagicMock

from lib.timestamp_utils import get_current_timestamp
from simulation.core.exceptions import SimulationRunFailure
from simulation.core.models.actions import TurnAction
from simulation.core.models.runs import Run, RunStatus
from simulation.core.models.turns import TurnMetadata


def test_post_simulations_run_success_returns_completed_and_likes(simulation_client):
    """Success run returns 200 with status completed and likes per turn."""
    client, fastapi_app = simulation_client
    run = Run(
        run_id="run-success-1",
        created_at=get_current_timestamp(),
        total_turns=1,
        total_agents=1,
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
    mock_engine = MagicMock()
    mock_engine.execute_run.return_value = run
    mock_engine.list_turn_metadata.return_value = metadata_list
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
    assert data["likes_per_turn"] == [{"turn_number": 0, "likes": 0}]
    assert data["total_likes"] == 0


def test_post_simulations_run_defaults_num_turns_and_feed_algorithm(simulation_client):
    """Request with only num_agents uses default num_turns=10 and feed_algorithm=chronological."""
    client, fastapi_app = simulation_client
    run = Run(
        run_id="run-defaults-1",
        created_at=get_current_timestamp(),
        total_turns=10,
        total_agents=1,
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
    mock_engine = MagicMock()
    mock_engine.execute_run.return_value = run
    mock_engine.list_turn_metadata.return_value = metadata_list
    fastapi_app.state.engine = mock_engine
    response = client.post(
        "/v1/simulations/run",
        json={"num_agents": 1},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["num_turns"] == 10
    assert data["status"] == "completed"
    assert len(data["likes_per_turn"]) == 10


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


def test_post_simulations_run_partial_failure_returns_200_with_partial_likes(
    simulation_client,
):
    """Mid-run failure returns 200 with status failed and partial likes_per_turn."""
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
    mock_engine = MagicMock()
    mock_engine.execute_run.side_effect = SimulationRunFailure(
        message="Run failed during execution",
        run_id="run-partial-1",
        cause=RuntimeError("turn 1 failed"),
    )
    mock_engine.list_turn_metadata.return_value = partial_metadata
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
        "likes_per_turn": [{"turn_number": 0, "likes": 3}],
        "total_likes": 3,
    }
    assert data["run_id"] == expected_result["run_id"]
    assert data["status"] == expected_result["status"]
    assert data["num_agents"] == expected_result["num_agents"]
    assert data["num_turns"] == expected_result["num_turns"]
    assert data["likes_per_turn"] == expected_result["likes_per_turn"]
    assert data["total_likes"] == expected_result["total_likes"]
    assert data["error"] is not None
    assert data["error"]["code"] == "SIMULATION_FAILED"
    assert data["error"]["message"] == "Run failed during execution"
    assert data["error"]["detail"] is None
