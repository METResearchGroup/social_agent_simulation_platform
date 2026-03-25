"""Health check route for Railway and operators."""

from __future__ import annotations

import os

from fastapi import APIRouter

router = APIRouter(tags=["health"])


def _version_from_env() -> str | None:
    return (
        os.environ.get("FEATURE_EXTRACTION_VERSION")
        or os.environ.get("GIT_COMMIT")
        or os.environ.get("RAILWAY_GIT_COMMIT_SHA")
    )


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness: process is up. Readiness fields may be added in a later phase."""
    body: dict[str, str] = {
        "status": "ok",
        "service": "feature-extraction",
    }
    version = _version_from_env()
    if version:
        body["version"] = version
    return body
