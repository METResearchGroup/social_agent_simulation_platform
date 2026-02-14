from typing import Iterable
from db.exceptions import InvalidTransitionError, RunNotFoundError
from simulation.core.exceptions import InsufficientAgentsError
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.posts import BlueskyFeedPost
from simulation.core.models.runs import Run, RunStatus

MAX_RATIO_OF_EMPTY_FEEDS = 0.25


from simulation.core.models.validators import validate_turn_number


def validate_run_id(run_id: str):
    if not run_id or not run_id.strip():
        raise ValueError("run_id is invalid")


def validate_run_exists(run: Run | None, run_id: str):
    if run is None:
        raise RunNotFoundError(run_id)

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


def validate_insufficient_agents(
    agents: list[SocialMediaAgent], requested_agents: int
):
    """Validate that the number of agents is sufficient."""
    if len(agents) < requested_agents:
        raise InsufficientAgentsError(
            requested=requested_agents, available=len(agents),
        )

def validate_handle_exists(handle: str):
    if not handle or not handle.strip():
        raise ValueError("handle cannot be empty")

def validate_duplicate_agent_handles(agents: list[SocialMediaAgent]):
    """Validate that the agent handles are unique."""
    handles = [agent.handle for agent in agents]
    if len(handles) != len(set(handles)):
        duplicates = [h for h in handles if handles.count(h) > 1]
        raise ValueError(
            f"Duplicate agent handles found: {set(duplicates)}. "
            "All agent handles must be unique."
        )

def validate_turn_number_less_than_max_turns(turn_number: int, max_turns: int):
    if turn_number >= max_turns:
        raise ValueError(
            f"Turn number {turn_number} is greater than the maximum number of turns: {max_turns}. "
            "Turn number must be less than the maximum number of turns."
        )


def validate_run_status_transition(
    *,
    run_id: str,
    current_status: RunStatus,
    target_status: RunStatus,
    valid_transitions: dict[RunStatus, set[RunStatus]],
):
    """Check to see if a run status transition is valid.
    
    For example, a run can only transition from RUNNING to COMPLETED or FAILED.
    A run cannot transition from COMPLETED or FAILED to RUNNING.

    Args:
        run_id: The ID of the run
        current_status: The current status of the run
        target_status: The target status of the run
        valid_transitions: A dictionary of valid transitions for each status
    """
    if target_status == current_status:
        return

    valid_next_states = valid_transitions.get(current_status, set())
    if target_status not in valid_next_states:
        valid_transitions_list = (
            [status.value for status in valid_next_states]
            if valid_next_states
            else None
        )
        raise InvalidTransitionError(
            run_id=run_id,
            current_status=current_status.value,
            target_status=target_status.value,
            valid_transitions=valid_transitions_list,
        )


def validate_uri_exists(uri: str):
    if not uri or not uri.strip():
        raise ValueError("uri cannot be empty")

def validate_uris_exist(uris: Iterable[str]):
    if not uris:
        raise ValueError("uris cannot be empty")

def validate_posts_exist(posts: list[BlueskyFeedPost] | None):
    if posts is None:
        raise ValueError("posts cannot be None")
