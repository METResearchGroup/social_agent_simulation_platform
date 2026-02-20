"""Read-side CQRS service for simulation agent lookup APIs."""

from simulation.api.dummy_data import DUMMY_AGENTS
from simulation.api.schemas.simulation import AgentSchema


def list_agents_dummy() -> list[AgentSchema]:
    """Return deterministic dummy agent list for UI integration, sorted by handle."""
    return sorted(DUMMY_AGENTS, key=lambda a: a.handle)
