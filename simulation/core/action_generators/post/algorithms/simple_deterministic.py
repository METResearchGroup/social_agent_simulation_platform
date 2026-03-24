"""Simple deterministic turn post generation (no LLM)."""

from __future__ import annotations

import json
from collections import defaultdict
from uuid import uuid4

from lib.timestamp_utils import get_current_timestamp
from simulation.core.models.agents import SimulationAgent
from simulation.core.models.turn_posts import TurnPostSnapshot

_POLICY = "simple_deterministic"
_EXPLANATION = "Deterministic post text for simulation (v1)."


def generate_turn_post_snapshots(
    *,
    agents: list[SimulationAgent],
    run_id: str,
    turn_number: int,
    max_per_author: int,
) -> list[TurnPostSnapshot]:
    """Emit up to ``max_per_author`` posts per author for this turn."""
    per_author: dict[str, int] = defaultdict(int)
    out: list[TurnPostSnapshot] = []
    for agent in agents:
        if agent.agent_id is None:
            continue
        if per_author[agent.agent_id] >= max_per_author:
            continue
        handle = agent.handle
        display = agent.display_name or handle
        created_at = get_current_timestamp()
        turn_post_id = f"tp_{uuid4().hex}"
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
                created_at=created_at,
                explanation=_EXPLANATION,
                model_used=None,
                generation_metadata_json=json.dumps({"policy": _POLICY}),
                generation_created_at=created_at,
            )
        )
        per_author[agent.agent_id] += 1
    return out
