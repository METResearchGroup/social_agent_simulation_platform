"""FastAPI entrypoint for the Feature Extraction API."""

from __future__ import annotations

from fastapi import FastAPI

from ml_tooling.api.routes.health import router as health_router

app = FastAPI(
    title="Feature Extraction API",
    version="0.1.0",
    description="HTTP API for feature extraction (health and future model endpoints).",
)
app.include_router(health_router)
