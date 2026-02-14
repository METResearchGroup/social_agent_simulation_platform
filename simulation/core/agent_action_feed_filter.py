from abc import ABC, abstractmethod
from dataclasses import dataclass

from simulation.core.action_history import ActionHistoryStore
from simulation.core.models.posts import BlueskyFeedPost


@dataclass(frozen=True)
class ActionCandidateFeeds:
    """Action-specific feed candidates for a single agent."""

    like_candidates: list[BlueskyFeedPost]
    comment_candidates: list[BlueskyFeedPost]
    follow_candidates: list[BlueskyFeedPost]


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
    ) -> ActionCandidateFeeds:
        raise NotImplementedError


class HistoryAwareActionFeedFilter(AgentActionFeedFilter):
    """Default candidate filter backed by action history checks."""

    def filter_candidates(
        self,
        *,
        run_id: str,
        agent_handle: str,
        feed: list[BlueskyFeedPost],
        action_history_store: ActionHistoryStore,
    ) -> ActionCandidateFeeds:
        like_candidates = [
            post
            for post in feed
            if not action_history_store.has_liked(run_id, agent_handle, post.id)
        ]
        comment_candidates = [
            post
            for post in feed
            if not action_history_store.has_commented(run_id, agent_handle, post.id)
        ]
        follow_candidates = [
            post
            for post in feed
            if not action_history_store.has_followed(run_id, agent_handle, post.author_handle)
        ]
        return ActionCandidateFeeds(
            like_candidates=like_candidates,
            comment_candidates=comment_candidates,
            follow_candidates=follow_candidates,
        )
