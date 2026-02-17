from typing import Iterable

from lib.validation_utils import (
    validate_non_empty_iterable,
    validate_non_empty_string,
    validate_nonnegative_value,
    validate_not_none,
    validate_turn_number,  # noqa: F401
    validate_value_in_set,
)
from simulation.core.exceptions import (
    InsufficientAgentsError,
    InvalidTransitionError,
    RunNotFoundError,
)
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.posts import BlueskyFeedPost
from simulation.core.models.runs import Run, RunStatus

MAX_RATIO_OF_EMPTY_FEEDS = 0.25


def validate_run_id(run_id: str) -> str:
    """Validate that run_id is a non-empty string. Returns stripped value."""
    return validate_non_empty_string(run_id, "run_id")


def validate_num_agents(num_agents: int) -> int:
    """Validate that num_agents is a positive integer."""
    return validate_nonnegative_value(num_agents, "num_agents", ok_equals_zero=False)


def validate_num_turns(num_turns: int | None) -> int | None:
    """Validate that num_turns, when provided, is a positive integer."""
    if num_turns is not None:
        validate_nonnegative_value(num_turns, "num_turns", ok_equals_zero=False)
    return num_turns


def validate_feed_algorithm(feed_algorithm: str | None) -> str | None:
    """Validate that feed_algorithm, when provided, is a registered algorithm."""
    if feed_algorithm is None:
        return None
    from feeds.feed_generator import _FEED_ALGORITHMS

    return validate_value_in_set(
        feed_algorithm,
        "feed_algorithm",
        _FEED_ALGORITHMS,
        allowed_display_name="registered feed algorithms",
    )


def validate_run_exists(run: Run | None, run_id: str) -> Run:
    if run is None:
        raise RunNotFoundError(run_id)
    return run


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


def validate_insufficient_agents(agents: list[SocialMediaAgent], requested_agents: int):
    """Validate that the number of agents is sufficient."""
    if len(agents) < requested_agents:
        raise InsufficientAgentsError(
            requested=requested_agents,
            available=len(agents),
        )


def validate_handle_exists(handle: str) -> str:
    """Validate that handle is a non-empty string. Returns stripped value."""
    return validate_non_empty_string(handle, "handle")


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


def validate_uri_exists(uri: str) -> str:
    """Validate that uri is a non-empty string. Returns stripped value."""
    return validate_non_empty_string(uri, "uri")


def validate_uris_exist(uris: Iterable[str]) -> Iterable[str]:
    """Validate that uris is not None and not empty."""
    return validate_non_empty_iterable(uris, "uris")


def validate_posts_exist(posts: list[BlueskyFeedPost] | None) -> list[BlueskyFeedPost]:
    """Validate that posts is not None."""
    return validate_not_none(posts, "posts")
