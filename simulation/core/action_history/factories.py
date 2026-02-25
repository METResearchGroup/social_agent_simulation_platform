"""Factories for action history dependencies."""

from __future__ import annotations

from collections.abc import Callable

from simulation.core.action_history.interfaces import ActionHistoryStore
from simulation.core.action_history.stores import InMemoryActionHistoryStore


def create_default_action_history_store_factory() -> Callable[[], ActionHistoryStore]:
    """Create the default run-scoped action history store factory."""

    # Returning the class keeps callsites simple and supports DI overrides.
    return InMemoryActionHistoryStore
