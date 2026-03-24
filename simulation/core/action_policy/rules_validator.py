from __future__ import annotations

from collections import Counter
from collections.abc import Callable

from simulation.core.action_history.interfaces import ActionHistoryStore
from simulation.core.agent_actions import MAX_AUTHORED_POSTS_PER_TURN
from simulation.core.models.actions import TurnAction
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.turn_posts import TurnPostSnapshot

# Type alias for duplicate validator: (validator, run_id, turn_number, agent_handle, identifiers) -> None
_DuplicateValidator = Callable[
    ["AgentActionRulesValidator", str, int, str, list[str]], None
]
# Type alias for history validator
_HistoryValidator = Callable[
    [
        "AgentActionRulesValidator",
        str,
        int,
        str,
        str,
        list[str],
        ActionHistoryStore,
    ],
    None,
]


def _dispatch_duplicate_like(
    validator: AgentActionRulesValidator,
    run_id: str,
    turn_number: int,
    agent_handle: str,
    identifiers: list[str],
) -> None:
    validator._validate_duplicate_likes(
        run_id=run_id,
        turn_number=turn_number,
        agent_handle=agent_handle,
        like_post_ids=identifiers,
    )


def _dispatch_duplicate_comment(
    validator: AgentActionRulesValidator,
    run_id: str,
    turn_number: int,
    agent_handle: str,
    identifiers: list[str],
) -> None:
    validator._validate_duplicate_comments(
        run_id=run_id,
        turn_number=turn_number,
        agent_handle=agent_handle,
        comment_post_ids=identifiers,
    )


def _dispatch_duplicate_follow(
    validator: AgentActionRulesValidator,
    run_id: str,
    turn_number: int,
    agent_handle: str,
    identifiers: list[str],
) -> None:
    validator._validate_duplicate_follows(
        run_id=run_id,
        turn_number=turn_number,
        agent_handle=agent_handle,
        follow_target_agent_ids=identifiers,
    )


def _dispatch_history_like(
    validator: AgentActionRulesValidator,
    run_id: str,
    turn_number: int,
    agent_handle: str,
    agent_id: str,
    identifiers: list[str],
    action_history_store: ActionHistoryStore,
) -> None:
    validator._validate_previously_liked(
        run_id=run_id,
        turn_number=turn_number,
        agent_handle=agent_handle,
        agent_id=agent_id,
        like_post_ids=identifiers,
        action_history_store=action_history_store,
    )


def _dispatch_history_comment(
    validator: AgentActionRulesValidator,
    run_id: str,
    turn_number: int,
    agent_handle: str,
    agent_id: str,
    identifiers: list[str],
    action_history_store: ActionHistoryStore,
) -> None:
    validator._validate_previously_commented(
        run_id=run_id,
        turn_number=turn_number,
        agent_handle=agent_handle,
        agent_id=agent_id,
        comment_post_ids=identifiers,
        action_history_store=action_history_store,
    )


def _dispatch_history_follow(
    validator: AgentActionRulesValidator,
    run_id: str,
    turn_number: int,
    agent_handle: str,
    agent_id: str,
    identifiers: list[str],
    action_history_store: ActionHistoryStore,
) -> None:
    validator._validate_previously_followed(
        run_id=run_id,
        turn_number=turn_number,
        agent_handle=agent_handle,
        agent_id=agent_id,
        follow_target_agent_ids=identifiers,
        action_history_store=action_history_store,
    )


_DUPLICATE_DISPATCH: dict[TurnAction, _DuplicateValidator] = {
    TurnAction.LIKE: _dispatch_duplicate_like,
    TurnAction.COMMENT: _dispatch_duplicate_comment,
    TurnAction.FOLLOW: _dispatch_duplicate_follow,
}

_HISTORY_DISPATCH: dict[TurnAction, _HistoryValidator] = {
    TurnAction.LIKE: _dispatch_history_like,
    TurnAction.COMMENT: _dispatch_history_comment,
    TurnAction.FOLLOW: _dispatch_history_follow,
}


class AgentActionRulesValidator:
    """Strict validator for generated agent action rules."""

    def validate_turn_posts(
        self,
        *,
        run_id: str,
        turn_number: int,
        posts: list[TurnPostSnapshot],
    ) -> None:
        """Enforce per-author caps and duplicate ``turn_post_id`` within a turn."""
        if not posts:
            return
        duplicate_ids = self._find_duplicates([p.turn_post_id for p in posts])
        if duplicate_ids:
            raise ValueError(
                f"Duplicate turn_post_id values in run {run_id}, turn {turn_number}: "
                f"{duplicate_ids}"
            )
        counts = Counter(p.author_agent_id for p in posts)
        for author_id, count in counts.items():
            if count > MAX_AUTHORED_POSTS_PER_TURN:
                raise ValueError(
                    f"Author {author_id} exceeded MAX_AUTHORED_POSTS_PER_TURN "
                    f"({MAX_AUTHORED_POSTS_PER_TURN}) in run {run_id}, turn {turn_number}: "
                    f"{count} posts"
                )

    def validate(
        self,
        *,
        run_id: str,
        turn_number: int,
        agent_handle: str,
        agent_id: str,
        likes: list[GeneratedLike],
        comments: list[GeneratedComment],
        follows: list[GeneratedFollow],
        action_history_store: ActionHistoryStore,
    ) -> tuple[list[str], list[str], list[str]]:
        """Validate action invariants and return extracted target identifiers."""
        like_post_ids = [like.like.post_id for like in likes]
        comment_post_ids = [comment.comment.post_id for comment in comments]
        follow_target_agent_ids = [follow.follow.target_agent_id for follow in follows]

        self.validate_duplicates(
            run_id=run_id,
            turn_number=turn_number,
            agent_handle=agent_handle,
            like_post_ids=like_post_ids,
            comment_post_ids=comment_post_ids,
            follow_target_agent_ids=follow_target_agent_ids,
        )

        self.validate_previously_acted_on(
            run_id=run_id,
            turn_number=turn_number,
            agent_handle=agent_handle,
            agent_id=agent_id,
            like_post_ids=like_post_ids,
            comment_post_ids=comment_post_ids,
            follow_target_agent_ids=follow_target_agent_ids,
            action_history_store=action_history_store,
        )

        return like_post_ids, comment_post_ids, follow_target_agent_ids

    def validate_duplicates(
        self,
        *,
        run_id: str,
        turn_number: int,
        agent_handle: str,
        like_post_ids: list[str],
        comment_post_ids: list[str],
        follow_target_agent_ids: list[str],
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
            identifiers=follow_target_agent_ids,
        )

    def validate_previously_acted_on(
        self,
        *,
        run_id: str,
        turn_number: int,
        agent_handle: str,
        agent_id: str,
        like_post_ids: list[str],
        comment_post_ids: list[str],
        follow_target_agent_ids: list[str],
        action_history_store: ActionHistoryStore,
    ) -> None:
        self._validate_previously_acted_on(
            action_type=TurnAction.LIKE,
            run_id=run_id,
            turn_number=turn_number,
            agent_handle=agent_handle,
            agent_id=agent_id,
            identifiers=like_post_ids,
            action_history_store=action_history_store,
        )
        self._validate_previously_acted_on(
            action_type=TurnAction.COMMENT,
            run_id=run_id,
            turn_number=turn_number,
            agent_handle=agent_handle,
            agent_id=agent_id,
            identifiers=comment_post_ids,
            action_history_store=action_history_store,
        )
        self._validate_previously_acted_on(
            action_type=TurnAction.FOLLOW,
            run_id=run_id,
            turn_number=turn_number,
            agent_handle=agent_handle,
            agent_id=agent_id,
            identifiers=follow_target_agent_ids,
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
        validator_fn = _DUPLICATE_DISPATCH.get(action_type)
        if validator_fn is None:
            raise ValueError(
                f"Unknown action_type for duplicate validation: {action_type}"
            )
        validator_fn(self, run_id, turn_number, agent_handle, identifiers)

    def _validate_previously_acted_on(
        self,
        *,
        action_type: TurnAction,
        run_id: str,
        turn_number: int,
        agent_handle: str,
        agent_id: str,
        identifiers: list[str],
        action_history_store: ActionHistoryStore,
    ) -> None:
        validator_fn = _HISTORY_DISPATCH.get(action_type)
        if validator_fn is None:
            raise ValueError(
                f"Unknown action_type for history validation: {action_type}"
            )
        validator_fn(
            self,
            run_id,
            turn_number,
            agent_handle,
            agent_id,
            identifiers,
            action_history_store,
        )

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
        follow_target_agent_ids: list[str],
    ) -> None:
        duplicate_follow_targets = self._find_duplicates(follow_target_agent_ids)
        if duplicate_follow_targets:
            raise ValueError(
                f"Agent {agent_handle} followed duplicate targets in run {run_id}, "
                f"turn {turn_number}. Duplicate target agent IDs: {duplicate_follow_targets}"
            )

    def _validate_previously_liked(
        self,
        *,
        run_id: str,
        turn_number: int,
        agent_handle: str,
        agent_id: str,
        like_post_ids: list[str],
        action_history_store: ActionHistoryStore,
    ) -> None:
        for post_id in like_post_ids:
            if action_history_store.has_liked(run_id, agent_id, post_id):
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
        agent_id: str,
        comment_post_ids: list[str],
        action_history_store: ActionHistoryStore,
    ) -> None:
        for post_id in comment_post_ids:
            if action_history_store.has_commented(run_id, agent_id, post_id):
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
        agent_id: str,
        follow_target_agent_ids: list[str],
        action_history_store: ActionHistoryStore,
    ) -> None:
        for target_agent_id in follow_target_agent_ids:
            if action_history_store.has_followed(run_id, agent_id, target_agent_id):
                raise ValueError(
                    f"Agent {agent_handle} cannot follow target {target_agent_id} again in run {run_id}, "
                    f"turn {turn_number}"
                )

    def _find_duplicates(self, identifiers: list[str]) -> list[str]:
        counter = Counter(identifiers)
        return [identifier for identifier, count in counter.items() if count > 1]
