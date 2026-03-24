"""Simple deterministic turn post generation (no LLM)."""

from __future__ import annotations

import json
from collections import defaultdict
from uuid import UUID, uuid5

from simulation.core.models.agents import SimulationAgent
from simulation.core.models.turn_posts import TurnPostSnapshot

# Stable namespace for deterministic ``turn_post_id`` (uuid5); not a security secret.
_TURN_POST_ID_NAMESPACE = UUID("a1b2c3d4-e5f6-4789-a012-3456789abcde")

_POLICY = "simple_deterministic"
_EXPLANATION = "Deterministic post text for simulation (v1)."


def _stable_turn_post_id(
    *, run_id: str, turn_number: int, author_agent_id: str, seq: int
) -> str:
    payload = f"simple_deterministic|{run_id}|{turn_number}|{author_agent_id}|{seq}"
    return f"tp_{uuid5(_TURN_POST_ID_NAMESPACE, payload).hex}"


def generate_turn_post_snapshots(
    *,
    agents: list[SimulationAgent],
    run_id: str,
    turn_number: int,
    max_per_author: int,
    sim_timestamp: str,
) -> list[TurnPostSnapshot]:
    """Emit up to ``max_per_author`` posts per author for this turn.

    IDs and timestamps are derived from ``sim_timestamp`` and stable inputs so
    repeated calls with the same arguments produce identical snapshots.
    """
    per_author: dict[str, int] = defaultdict(int)
    out: list[TurnPostSnapshot] = []
    for agent in agents:
        if agent.agent_id is None:
            continue
        if per_author[agent.agent_id] >= max_per_author:
            continue
        handle = agent.handle
        display = agent.display_name or handle
        seq = per_author[agent.agent_id]
        turn_post_id = _stable_turn_post_id(
            run_id=run_id,
            turn_number=turn_number,
            author_agent_id=agent.agent_id,
            seq=seq,
        )
        body = f"[turn {turn_number}] post from {handle}"
        out.append(
            TurnPostSnapshot(
                turn_post_id=turn_post_id,
                run_id=run_id,
                turn_number=turn_number,
                author_agent_id=agent.agent_id,
                author_handle_at_time=handle,
                author_display_name_at_time=display,
                body_text=body,
                created_at=sim_timestamp,
                explanation=_EXPLANATION,
                model_used=None,
                generation_metadata_json=json.dumps({"policy": _POLICY}),
                generation_created_at=sim_timestamp,
            )
        )
        per_author[agent.agent_id] += 1
    return out
