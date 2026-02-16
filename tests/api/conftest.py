"""Shared fixtures for API tests."""

from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from simulation.api.main import app


@pytest.fixture
def simulation_client():
    """TestClient for simulation API. Saves and restores app.state.engine after each test."""
    original_engine = getattr(app.state, "engine", None)
    with TestClient(app=app) as client:
        fastapi_app = cast(FastAPI, client.app)
        yield client, fastapi_app
    app.state.engine = original_engine
