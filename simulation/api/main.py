"""FastAPI application entrypoint.

Run from repository root with PYTHONPATH set to project root, e.g.:
    PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from db.adapters.sqlite.sqlite import initialize_database
from simulation.core.factories import create_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and simulation engine on startup."""
    await asyncio.to_thread(initialize_database)
    app.state.engine = await asyncio.to_thread(create_engine)
    yield


app = FastAPI(
    title="Agent Simulation Platform API",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    """Health check endpoint. Returns 200 when the service is up."""
    return {"status": "ok"}
