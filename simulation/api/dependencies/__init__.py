"""FastAPI dependencies for simulation API."""

from simulation.api.dependencies.auth import require_auth

__all__ = ["require_auth"]
