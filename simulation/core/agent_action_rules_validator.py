from collections import Counter

from simulation.core.action_history import ActionHistoryStore
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.generated.like import GeneratedLike


class AgentActionRulesValidator:
    """Strict validator for generated agent action rules."""

    def validate(
        self,
        *,
        run_id: str,
        turn_number: int,
        agent_handle: str,
        likes: list[GeneratedLike],
        comments: list[GeneratedComment],
        follows: list[GeneratedFollow],
        action_history_store: ActionHistoryStore,
    ) -> tuple[list[str], list[str], list[str]]:
        """Validate action invariants and return extracted target identifiers."""
        like_post_ids = [like.like.post_id for like in likes]
        duplicate_like_targets = self._find_duplicates(like_post_ids)
        if duplicate_like_targets:
            raise ValueError(
                f"Agent {agent_handle} liked duplicate targets in run {run_id}, "
                f"turn {turn_number}. Duplicate post IDs: {duplicate_like_targets}"
            )

        comment_post_ids = [comment.comment.post_id for comment in comments]
        duplicate_comment_targets = self._find_duplicates(comment_post_ids)
        if duplicate_comment_targets:
            raise ValueError(
                f"Agent {agent_handle} commented duplicate targets in run {run_id}, "
                f"turn {turn_number}. Duplicate post IDs: {duplicate_comment_targets}"
            )

        follow_user_ids = [follow.follow.user_id for follow in follows]
        duplicate_follow_targets = self._find_duplicates(follow_user_ids)
        if duplicate_follow_targets:
            raise ValueError(
                f"Agent {agent_handle} followed duplicate targets in run {run_id}, "
                f"turn {turn_number}. Duplicate user IDs: {duplicate_follow_targets}"
            )

        for post_id in like_post_ids:
            if action_history_store.has_liked(run_id, agent_handle, post_id):
                raise ValueError(
                    f"Agent {agent_handle} cannot like post {post_id} again in run {run_id}, "
                    f"turn {turn_number}"
                )

        for post_id in comment_post_ids:
            if action_history_store.has_commented(run_id, agent_handle, post_id):
                raise ValueError(
                    f"Agent {agent_handle} cannot comment on post {post_id} again in run {run_id}, "
                    f"turn {turn_number}"
                )

        for user_id in follow_user_ids:
            if action_history_store.has_followed(run_id, agent_handle, user_id):
                raise ValueError(
                    f"Agent {agent_handle} cannot follow user {user_id} again in run {run_id}, "
                    f"turn {turn_number}"
                )

        return like_post_ids, comment_post_ids, follow_user_ids

    def _find_duplicates(self, identifiers: list[str]) -> list[str]:
        counter = Counter(identifiers)
        return [identifier for identifier, count in counter.items() if count > 1]
