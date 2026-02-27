from __future__ import annotations

from dataclasses import dataclass

from simulation.core.action_history.interfaces import ActionHistoryStore
from simulation.core.action_policy.interfaces import AgentActionFeedFilter
from simulation.core.models.posts import Post


@dataclass(frozen=True)
class ActionCandidateFeeds:
    """Action-specific feed candidates for a single agent."""

    like_candidates: list[Post]
    comment_candidates: list[Post]
    follow_candidates: list[Post]


class HistoryAwareActionFeedFilter(AgentActionFeedFilter):
    """Default candidate filter backed by action history checks."""

    def filter_candidates(
        self,
        *,
        run_id: str,
        agent_handle: str,
        feed: list[Post],
        action_history_store: ActionHistoryStore,
    ) -> ActionCandidateFeeds:
        like_candidates = [
            post
            for post in feed
            if not action_history_store.has_liked(run_id, agent_handle, post.post_id)
        ]
        comment_candidates = [
            post
            for post in feed
            if not action_history_store.has_commented(
                run_id, agent_handle, post.post_id
            )
        ]
        follow_candidates = [
            post
            for post in feed
            if not action_history_store.has_followed(
                run_id, agent_handle, post.author_handle
            )
        ]
        return ActionCandidateFeeds(
            like_candidates=like_candidates,
            comment_candidates=comment_candidates,
            follow_candidates=follow_candidates,
        )
