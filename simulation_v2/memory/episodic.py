"""Episodic memory diff content builders."""

from __future__ import annotations

from simulation_v2.db.models import ProposedActionRecord


def _format_action_clause(action: ProposedActionRecord) -> str:
    if action.action_type == "like_post":
        return f"liked post {action.target_id or ''}"
    if action.action_type == "write_post":
        content = action.target_content or ""
        return f'wrote post "{content}"'
    if action.action_type == "follow_user":
        return f"followed user {action.target_id or ''}"
    if action.action_type == "comment_on_post":
        content = action.target_content or ""
        return f'commented on {action.target_id or ""} "{content}"'
    raise ValueError(f"Unsupported action type {action.action_type!r}")


def build_episodic_diff_content(
    turn_number: int,
    actions: list[ProposedActionRecord],
) -> str | None:
    if not actions:
        return None
    clauses = [_format_action_clause(action) for action in actions]
    return f"Turn {turn_number}: {'; '.join(clauses)}"


def append_episodic(existing: str | None, new_segment: str) -> str:
    if not existing:
        return new_segment
    return f"{existing}\n{new_segment}"
