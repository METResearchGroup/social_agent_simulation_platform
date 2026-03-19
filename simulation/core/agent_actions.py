"""Action generation helpers for simulation agents."""

from __future__ import annotations

from lib.run_rng import get_turn_rng
from simulation.core.action_generators import (
    get_comment_generator,
    get_follow_generator,
    get_like_generator,
)
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.posts import Post


def generate_likes(
    candidates: list[Post],
    *,
    run_id: str,
    run_seed: int,
    turn_number: int,
    agent_handle: str,
) -> list[GeneratedLike]:
    if not candidates:
        return []
    rng = get_turn_rng(run_seed=run_seed, turn_number=turn_number)
    generator = get_like_generator()
    return generator.generate(
        candidates=candidates,
        run_id=run_id,
        turn_number=turn_number,
        agent_handle=agent_handle,
        rng=rng,
    )


def generate_comments(
    candidates: list[Post],
    *,
    run_id: str,
    run_seed: int,
    turn_number: int,
    agent_handle: str,
) -> list[GeneratedComment]:
    if not candidates:
        return []
    rng = get_turn_rng(run_seed=run_seed, turn_number=turn_number)
    generator = get_comment_generator()
    return generator.generate(
        candidates=candidates,
        run_id=run_id,
        turn_number=turn_number,
        agent_handle=agent_handle,
        rng=rng,
    )


def generate_follows(
    candidates: list[Post],
    *,
    run_id: str,
    run_seed: int,
    turn_number: int,
    agent_handle: str,
) -> list[GeneratedFollow]:
    if not candidates:
        return []
    rng = get_turn_rng(run_seed=run_seed, turn_number=turn_number)
    generator = get_follow_generator()
    return generator.generate(
        candidates=candidates,
        run_id=run_id,
        turn_number=turn_number,
        agent_handle=agent_handle,
        rng=rng,
    )
