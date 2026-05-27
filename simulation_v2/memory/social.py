"""Social memory diff content builders."""

from __future__ import annotations

from simulation_v2.db.models import ProposedActionRecord


def build_social_diff_content(
    turn_number: int,
    actions: list[ProposedActionRecord],
) -> str | None:
    follow_actions = [
        action for action in actions if action.action_type == "follow_user"
    ]
    if not follow_actions:
        return None
    clauses = [f"followed {action.target_id or ''}" for action in follow_actions]
    return f"Turn {turn_number}: {'; '.join(clauses)}"


def append_social(existing: str | None, new_segment: str) -> str:
    if not existing:
        return new_segment
    return f"{existing}\n{new_segment}"
