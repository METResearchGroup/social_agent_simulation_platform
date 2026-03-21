from __future__ import annotations

from collections import defaultdict

from simulation.core.action_history.interfaces import ActionHistoryStore


class InMemoryActionHistoryStore(ActionHistoryStore):
    """In-memory implementation keyed by run and actor ``agent_id``."""

    def __init__(self) -> None:
        self._likes_by_run_agent_id: dict[str, dict[str, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        self._comments_by_run_agent_id: dict[str, dict[str, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        self._follows_by_run_agent_id: dict[str, dict[str, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )

    def has_liked(self, run_id: str, agent_id: str, post_id: str) -> bool:
        return post_id in self._likes_by_run_agent_id[run_id][agent_id]

    def has_commented(self, run_id: str, agent_id: str, post_id: str) -> bool:
        return post_id in self._comments_by_run_agent_id[run_id][agent_id]

    def has_followed(self, run_id: str, agent_id: str, target_agent_id: str) -> bool:
        return target_agent_id in self._follows_by_run_agent_id[run_id][agent_id]

    def record_like(self, run_id: str, agent_id: str, post_id: str) -> None:
        self._likes_by_run_agent_id[run_id][agent_id].add(post_id)

    def record_comment(self, run_id: str, agent_id: str, post_id: str) -> None:
        self._comments_by_run_agent_id[run_id][agent_id].add(post_id)

    def record_follow(self, run_id: str, agent_id: str, target_agent_id: str) -> None:
        self._follows_by_run_agent_id[run_id][agent_id].add(target_agent_id)
