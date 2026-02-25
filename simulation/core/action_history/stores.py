from __future__ import annotations

from collections import defaultdict

from simulation.core.action_history.interfaces import ActionHistoryStore


class InMemoryActionHistoryStore(ActionHistoryStore):
    """In-memory implementation keyed by run and agent."""

    def __init__(self) -> None:
        self._likes_by_run_agent: dict[str, dict[str, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        self._comments_by_run_agent: dict[str, dict[str, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        self._follows_by_run_agent: dict[str, dict[str, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )

    def has_liked(self, run_id: str, agent_handle: str, post_id: str) -> bool:
        return post_id in self._likes_by_run_agent[run_id][agent_handle]

    def has_commented(self, run_id: str, agent_handle: str, post_id: str) -> bool:
        return post_id in self._comments_by_run_agent[run_id][agent_handle]

    def has_followed(self, run_id: str, agent_handle: str, user_id: str) -> bool:
        return user_id in self._follows_by_run_agent[run_id][agent_handle]

    def record_like(self, run_id: str, agent_handle: str, post_id: str) -> None:
        self._likes_by_run_agent[run_id][agent_handle].add(post_id)

    def record_comment(self, run_id: str, agent_handle: str, post_id: str) -> None:
        self._comments_by_run_agent[run_id][agent_handle].add(post_id)

    def record_follow(self, run_id: str, agent_handle: str, user_id: str) -> None:
        self._follows_by_run_agent[run_id][agent_handle].add(user_id)
