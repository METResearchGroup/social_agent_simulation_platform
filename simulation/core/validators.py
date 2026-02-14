from db.exceptions import RunNotFoundError
from simulation.core.exceptions import InsufficientAgentsError
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.runs import Run, RunConfig

MAX_RATIO_OF_EMPTY_FEEDS = 0.25


def validate_run_id(run_id: str):
    if not run_id or not run_id.strip():
        raise ValueError("run_id is invalid")

def validate_turn_number(turn_number: int):
    if turn_number is None or turn_number < 0:
        raise ValueError("turn_number is invalid")

# TODO: should consolidate this and validate_run_id
# to a single validate_run function.
def validate_run(run: Run | None, run_id: str):
    if run is None:
        raise RunNotFoundError(run_id)


def validate_agents(
    agents: list[SocialMediaAgent],
    config: RunConfig,
    run_id: str
):
    _validate_insufficient_agents(agents, config, run_id)
    _validate_duplicate_agent_handles(agents)


def validate_agents_without_feeds(
    agent_handles: set[str],
    agents_with_feeds: set[str],
):
    """Validate that the number of empty feeds is not too high."""
    agents_without_feeds = agent_handles - agents_with_feeds
    if len(agents_without_feeds) / len(agent_handles) > MAX_RATIO_OF_EMPTY_FEEDS:
        raise ValueError(
            f"Too many empty feeds: {len(agents_without_feeds)}/{len(agent_handles)}. "
            f"This is greater than the maximum ratio of empty feeds: {MAX_RATIO_OF_EMPTY_FEEDS}. "
            "All feeds must be non-empty."
        )


def _validate_insufficient_agents(
    agents: list[SocialMediaAgent], config: RunConfig, run_id: str
):
    """Validate that the number of agents is sufficient."""
    if len(agents) < config.num_agents:
        raise InsufficientAgentsError(
            requested=config.num_agents,
            available=len(agents),
            run_id=run_id,
        )

def _validate_duplicate_agent_handles(agents: list[SocialMediaAgent]):
    """Validate that the agent handles are unique."""
    handles = [agent.handle for agent in agents]
    if len(handles) != len(set(handles)):
        duplicates = [h for h in handles if handles.count(h) > 1]
        raise ValueError(
            f"Duplicate agent handles found: {set(duplicates)}. "
            "All agent handles must be unique."
        )
