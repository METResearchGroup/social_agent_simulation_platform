from __future__ import annotations

from simulation.core.action_history.interfaces import ActionHistoryStore


def record_action_targets(
    *,
    run_id: str,
    agent_id: str,
    like_post_ids: list[str],
    comment_post_ids: list[str],
    follow_target_agent_ids: list[str],
    action_history_store: ActionHistoryStore,
) -> None:
    """Record validated action targets into action history."""
    for post_id in like_post_ids:
        action_history_store.record_like(run_id, agent_id, post_id)
    for post_id in comment_post_ids:
        action_history_store.record_comment(run_id, agent_id, post_id)
    for target_agent_id in follow_target_agent_ids:
        action_history_store.record_follow(run_id, agent_id, target_agent_id)
