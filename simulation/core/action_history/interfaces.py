from __future__ import annotations

from abc import ABC, abstractmethod


class ActionHistoryStore(ABC):
    """Run-scoped storage for previously accepted agent actions."""

    @abstractmethod
    def has_liked(self, run_id: str, agent_handle: str, post_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def has_commented(self, run_id: str, agent_handle: str, post_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def has_followed(self, run_id: str, agent_handle: str, user_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def record_like(self, run_id: str, agent_handle: str, post_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def record_comment(self, run_id: str, agent_handle: str, post_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def record_follow(self, run_id: str, agent_handle: str, user_id: str) -> None:
        raise NotImplementedError
