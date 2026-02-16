"""Factory for creating the default action history store factory."""

from collections.abc import Callable

from simulation.core.action_history import (
    ActionHistoryStore,
    InMemoryActionHistoryStore,
)


def create_default_action_history_store_factory() -> (
    Callable[[], ActionHistoryStore]
):
    """Create the default run-scoped action history store factory."""
    return InMemoryActionHistoryStore
