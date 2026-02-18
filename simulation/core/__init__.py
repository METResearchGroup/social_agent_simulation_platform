from simulation.core.exceptions import InsufficientAgentsError, SimulationError
from simulation.core.models.turns import TurnResult


# Lazy import to avoid circular dependency
def __getattr__(name: str):
    if name == "SimulationEngine":
        from simulation.core.engine import SimulationEngine

        return SimulationEngine
    if name == "create_engine":
        from simulation.core.factories import create_engine

        return create_engine
    if name == "SimulationQueryService":
        from simulation.core.query_service import SimulationQueryService

        return SimulationQueryService
    if name == "SimulationCommandService":
        from simulation.core.command_service import SimulationCommandService

        return SimulationCommandService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "SimulationEngine",  # type: ignore[attr-defined]  # Lazy-loaded via __getattr__
    "TurnResult",
    "SimulationError",
    "InsufficientAgentsError",
    "create_engine",  # type: ignore[attr-defined]  # Lazy-loaded via __getattr__
    "SimulationQueryService",  # type: ignore[attr-defined]  # Lazy-loaded via __getattr__
    "SimulationCommandService",  # type: ignore[attr-defined]  # Lazy-loaded via __getattr__
]
