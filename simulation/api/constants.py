"""Shared constants for the simulation API.

Keep API defaults as named constants so behavior is explicit and can be reused
across routes, services, and tests.
"""

from simulation.api.schemas.simulation import DefaultConfigSchema

DEFAULT_AGENT_LIST_LIMIT: int = 100
MAX_AGENT_LIST_LIMIT: int = 500
DEFAULT_AGENT_LIST_OFFSET: int = 0

DEFAULT_SIMULATION_CONFIG: DefaultConfigSchema = DefaultConfigSchema(
    num_agents=5,
    num_turns=10,
)
