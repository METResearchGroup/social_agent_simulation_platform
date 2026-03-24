"""Action generation helpers for simulation agents."""

from __future__ import annotations

from simulation.core.action_generators import (
    get_comment_generator,
    get_follow_generator,
    get_like_generator,
)
from simulation.core.action_generators.post.algorithms.simple_deterministic import (
    generate_turn_post_snapshots,
)
from simulation.core.models.agents import SimulationAgent
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.posts import Post
from simulation.core.models.turn_posts import TurnPostSnapshot

MAX_AUTHORED_POSTS_PER_TURN: int = 5


def generate_likes(
    candidates: list[Post],
    *,
    run_id: str,
    turn_number: int,
    agent_handle: str,
    agent_id: str,
) -> list[GeneratedLike]:
    if not candidates:
        return []
    generator = get_like_generator()
    return generator.generate(
        candidates=candidates,
        run_id=run_id,
        turn_number=turn_number,
        agent_handle=agent_handle,
        agent_id=agent_id,
    )


def generate_comments(
    candidates: list[Post],
    *,
    run_id: str,
    turn_number: int,
    agent_handle: str,
    agent_id: str,
) -> list[GeneratedComment]:
    if not candidates:
        return []
    generator = get_comment_generator()
    return generator.generate(
        candidates=candidates,
        run_id=run_id,
        turn_number=turn_number,
        agent_handle=agent_handle,
        agent_id=agent_id,
    )


def generate_follows(
    candidates: list[Post],
    *,
    run_id: str,
    turn_number: int,
    agent_handle: str,
    agent_id: str,
) -> list[GeneratedFollow]:
    if not candidates:
        return []
    generator = get_follow_generator()
    return generator.generate(
        candidates=candidates,
        run_id=run_id,
        turn_number=turn_number,
        agent_handle=agent_handle,
        agent_id=agent_id,
    )


def generate_posts(
    *,
    agents: list[SimulationAgent],
    run_id: str,
    turn_number: int,
    sim_timestamp: str,
) -> list[TurnPostSnapshot]:
    """Generate turn-authored post snapshots (capped per author)."""
    return generate_turn_post_snapshots(
        agents=agents,
        run_id=run_id,
        turn_number=turn_number,
        max_per_author=MAX_AUTHORED_POSTS_PER_TURN,
        sim_timestamp=sim_timestamp,
    )
