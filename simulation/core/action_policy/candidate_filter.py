from __future__ import annotations

from dataclasses import dataclass

from lib.agent_id import canonical_agent_id, is_canonical_agent_id
from simulation.core.action_history.interfaces import ActionHistoryStore
from simulation.core.action_policy.interfaces import AgentActionFeedFilter
from simulation.core.models.posts import Post


@dataclass(frozen=True)
class ActionCandidateFeeds:
    """Action-specific feed candidates for a single agent."""

    like_candidates: list[Post]
    comment_candidates: list[Post]
    follow_candidates: list[Post]


def _follow_target_key_for_history(post: Post) -> str:
    """Match ``record_follow`` / follow generation: canonical id when available."""
    if post.author_agent_id and is_canonical_agent_id(post.author_agent_id):
        return post.author_agent_id
    if post.author_handle:
        return canonical_agent_id(post.author_handle)
    raise ValueError(
        f"Cannot derive follow target key for post {post.post_id!r}: "
        "missing author_agent_id and author_handle"
    )


class HistoryAwareActionFeedFilter(AgentActionFeedFilter):
    """Default candidate filter backed by action history checks."""

    def filter_candidates(
        self,
        *,
        run_id: str,
        agent_handle: str,
        agent_id: str,
        feed: list[Post],
        action_history_store: ActionHistoryStore,
    ) -> ActionCandidateFeeds:
        _ = agent_handle
        like_candidates = [
            post
            for post in feed
            if not action_history_store.has_liked(run_id, agent_id, post.post_id)
        ]
        comment_candidates = [
            post
            for post in feed
            if not action_history_store.has_commented(run_id, agent_id, post.post_id)
        ]
        follow_candidates = [
            post
            for post in feed
            if not action_history_store.has_followed(
                run_id,
                agent_id,
                _follow_target_key_for_history(post),
            )
        ]
        return ActionCandidateFeeds(
            like_candidates=like_candidates,
            comment_candidates=comment_candidates,
            follow_candidates=follow_candidates,
        )
