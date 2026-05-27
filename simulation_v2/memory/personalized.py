"""Personalized memory diff content builders."""

from __future__ import annotations

from simulation_v2.db.models import ProposedActionRecord


def build_personalized_diff_content(
    turn_number: int,
    actions: list[ProposedActionRecord],
) -> str | None:
    write_actions = [action for action in actions if action.action_type == "write_post"]
    if not write_actions:
        return None
    clauses = [f'posted "{action.target_content or ""}"' for action in write_actions]
    return f"Turn {turn_number}: {'; '.join(clauses)}"


def append_personalized(existing: str | None, new_segment: str) -> str:
    if not existing:
        return new_segment
    return f"{existing}\n{new_segment}"
