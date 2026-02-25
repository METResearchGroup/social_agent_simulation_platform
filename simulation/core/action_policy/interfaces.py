from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from simulation.core.action_history.interfaces import ActionHistoryStore
from simulation.core.models.posts import BlueskyFeedPost

if TYPE_CHECKING:
    from simulation.core.action_policy.candidate_filter import ActionCandidateFeeds


class AgentActionFeedFilter(ABC):
    """Filters a hydrated feed into action-specific eligible candidates."""

    @abstractmethod
    def filter_candidates(
        self,
        *,
        run_id: str,
        agent_handle: str,
        feed: list[BlueskyFeedPost],
        action_history_store: ActionHistoryStore,
    ) -> "ActionCandidateFeeds":
        raise NotImplementedError
