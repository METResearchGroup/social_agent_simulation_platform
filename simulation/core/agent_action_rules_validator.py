from collections import Counter

from simulation.core.action_history import ActionHistoryStore
from simulation.core.models.actions import TurnAction
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
        comment_post_ids = [comment.comment.post_id for comment in comments]
        follow_user_ids = [follow.follow.user_id for follow in follows]

        self.validate_duplicates(
            run_id=run_id,
            turn_number=turn_number,
            agent_handle=agent_handle,
            like_post_ids=like_post_ids,
            comment_post_ids=comment_post_ids,
            follow_user_ids=follow_user_ids,
        )

        self.validate_previously_acted_on(
            run_id=run_id,
            turn_number=turn_number,
            agent_handle=agent_handle,
            like_post_ids=like_post_ids,
            comment_post_ids=comment_post_ids,
            follow_user_ids=follow_user_ids,
            action_history_store=action_history_store,
        )

        return like_post_ids, comment_post_ids, follow_user_ids

    def validate_duplicates(
        self,
        *,
        run_id: str,
        turn_number: int,
        agent_handle: str,
        like_post_ids: list[str],
        comment_post_ids: list[str],
        follow_user_ids: list[str],
    ) -> None:
        self._validate_duplicates(
            action_type=TurnAction.LIKE,
            run_id=run_id,
            turn_number=turn_number,
            agent_handle=agent_handle,
            identifiers=like_post_ids,
        )
        self._validate_duplicates(
            action_type=TurnAction.COMMENT,
            run_id=run_id,
            turn_number=turn_number,
            agent_handle=agent_handle,
            identifiers=comment_post_ids,
        )
        self._validate_duplicates(
            action_type=TurnAction.FOLLOW,
            run_id=run_id,
            turn_number=turn_number,
            agent_handle=agent_handle,
            identifiers=follow_user_ids,
        )

    def validate_previously_acted_on(
        self,
        *,
        run_id: str,
        turn_number: int,
        agent_handle: str,
        like_post_ids: list[str],
        comment_post_ids: list[str],
        follow_user_ids: list[str],
        action_history_store: ActionHistoryStore,
    ) -> None:
        self._validate_previously_acted_on(
            action_type=TurnAction.LIKE,
            run_id=run_id,
            turn_number=turn_number,
            agent_handle=agent_handle,
            identifiers=like_post_ids,
            action_history_store=action_history_store,
        )
        self._validate_previously_acted_on(
            action_type=TurnAction.COMMENT,
            run_id=run_id,
            turn_number=turn_number,
            agent_handle=agent_handle,
            identifiers=comment_post_ids,
            action_history_store=action_history_store,
        )
        self._validate_previously_acted_on(
            action_type=TurnAction.FOLLOW,
            run_id=run_id,
            turn_number=turn_number,
            agent_handle=agent_handle,
            identifiers=follow_user_ids,
            action_history_store=action_history_store,
        )

    def _validate_duplicates(
        self,
        *,
        action_type: TurnAction,
        run_id: str,
        turn_number: int,
        agent_handle: str,
        identifiers: list[str],
    ) -> None:
        if action_type == TurnAction.LIKE:
            self._validate_duplicate_likes(
                run_id=run_id,
                turn_number=turn_number,
                agent_handle=agent_handle,
                like_post_ids=identifiers,
            )
        elif action_type == TurnAction.COMMENT:
            self._validate_duplicate_comments(
                run_id=run_id,
                turn_number=turn_number,
                agent_handle=agent_handle,
                comment_post_ids=identifiers,
            )
        elif action_type == TurnAction.FOLLOW:
            self._validate_duplicate_follows(
                run_id=run_id,
                turn_number=turn_number,
                agent_handle=agent_handle,
                follow_user_ids=identifiers,
            )
        else:
            raise ValueError(f"Unknown action_type for duplicate validation: {action_type}")

    def _validate_previously_acted_on(
        self,
        *,
        action_type: TurnAction,
        run_id: str,
        turn_number: int,
        agent_handle: str,
        identifiers: list[str],
        action_history_store: ActionHistoryStore,
    ) -> None:
        if action_type == TurnAction.LIKE:
            self._validate_previously_liked(
                run_id=run_id,
                turn_number=turn_number,
                agent_handle=agent_handle,
                like_post_ids=identifiers,
                action_history_store=action_history_store,
            )
        elif action_type == TurnAction.COMMENT:
            self._validate_previously_commented(
                run_id=run_id,
                turn_number=turn_number,
                agent_handle=agent_handle,
                comment_post_ids=identifiers,
                action_history_store=action_history_store,
            )
        elif action_type == TurnAction.FOLLOW:
            self._validate_previously_followed(
                run_id=run_id,
                turn_number=turn_number,
                agent_handle=agent_handle,
                follow_user_ids=identifiers,
                action_history_store=action_history_store,
            )
        else:
            raise ValueError(f"Unknown action_type for history validation: {action_type}")

    def _validate_duplicate_likes(
        self,
        *,
        run_id: str,
        turn_number: int,
        agent_handle: str,
        like_post_ids: list[str],
    ) -> None:
        duplicate_like_targets = self._find_duplicates(like_post_ids)
        if duplicate_like_targets:
            raise ValueError(
                f"Agent {agent_handle} liked duplicate targets in run {run_id}, "
                f"turn {turn_number}. Duplicate post IDs: {duplicate_like_targets}"
            )

    def _validate_duplicate_comments(
        self,
        *,
        run_id: str,
        turn_number: int,
        agent_handle: str,
        comment_post_ids: list[str],
    ) -> None:
        duplicate_comment_targets = self._find_duplicates(comment_post_ids)
        if duplicate_comment_targets:
            raise ValueError(
                f"Agent {agent_handle} commented duplicate targets in run {run_id}, "
                f"turn {turn_number}. Duplicate post IDs: {duplicate_comment_targets}"
            )

    def _validate_duplicate_follows(
        self,
        *,
        run_id: str,
        turn_number: int,
        agent_handle: str,
        follow_user_ids: list[str],
    ) -> None:
        duplicate_follow_targets = self._find_duplicates(follow_user_ids)
        if duplicate_follow_targets:
            raise ValueError(
                f"Agent {agent_handle} followed duplicate targets in run {run_id}, "
                f"turn {turn_number}. Duplicate user IDs: {duplicate_follow_targets}"
            )

    def _validate_previously_liked(
        self,
        *,
        run_id: str,
        turn_number: int,
        agent_handle: str,
        like_post_ids: list[str],
        action_history_store: ActionHistoryStore,
    ) -> None:
        for post_id in like_post_ids:
            if action_history_store.has_liked(run_id, agent_handle, post_id):
                raise ValueError(
                    f"Agent {agent_handle} cannot like post {post_id} again in run {run_id}, "
                    f"turn {turn_number}"
                )

    def _validate_previously_commented(
        self,
        *,
        run_id: str,
        turn_number: int,
        agent_handle: str,
        comment_post_ids: list[str],
        action_history_store: ActionHistoryStore,
    ) -> None:
        for post_id in comment_post_ids:
            if action_history_store.has_commented(run_id, agent_handle, post_id):
                raise ValueError(
                    f"Agent {agent_handle} cannot comment on post {post_id} again in run {run_id}, "
                    f"turn {turn_number}"
                )

    def _validate_previously_followed(
        self,
        *,
        run_id: str,
        turn_number: int,
        agent_handle: str,
        follow_user_ids: list[str],
        action_history_store: ActionHistoryStore,
    ) -> None:
        for user_id in follow_user_ids:
            if action_history_store.has_followed(run_id, agent_handle, user_id):
                raise ValueError(
                    f"Agent {agent_handle} cannot follow user {user_id} again in run {run_id}, "
                    f"turn {turn_number}"
                )

    def _find_duplicates(self, identifiers: list[str]) -> list[str]:
        counter = Counter(identifiers)
        return [identifier for identifier, count in counter.items() if count > 1]
