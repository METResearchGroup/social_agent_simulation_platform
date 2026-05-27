"""Convert validated proposed actions into pending turn entity diffs."""

from __future__ import annotations

from simulation_v2.db.models import (
    CommentRecord,
    FollowRecord,
    LikeRecord,
    PostRecord,
    ProposedActionRecord,
)
from simulation_v2.ids import (
    new_comment_id,
    new_follow_id,
    new_like_id,
    new_post_id,
)
from simulation_v2.memory.service import build_memory_diffs
from simulation_v2.time import get_current_timestamp
from simulation_v2.worker.state import PendingTurnDiffs, TurnStateSnapshot


def build_pending_turn_diffs(
    validated_actions: list[ProposedActionRecord],
    snapshot: TurnStateSnapshot,
) -> PendingTurnDiffs:
    posts: list[PostRecord] = []
    likes: list[LikeRecord] = []
    follows: list[FollowRecord] = []
    comments: list[CommentRecord] = []

    for action in validated_actions:
        metadata_json = _metadata_for_action(action)
        created_at = get_current_timestamp()
        if action.action_type == "like_post":
            likes.append(
                LikeRecord(
                    like_id=new_like_id(),
                    run_id=snapshot.run_id,
                    post_id=action.target_id or "",
                    author_id=action.user_id,
                    created_at=created_at,
                    created_at_turn=snapshot.turn_number,
                    metadata_json=metadata_json,
                )
            )
        elif action.action_type == "follow_user":
            follows.append(
                FollowRecord(
                    follow_id=new_follow_id(),
                    run_id=snapshot.run_id,
                    follower_id=action.user_id,
                    followee_id=action.target_id or "",
                    created_at=created_at,
                    created_at_turn=snapshot.turn_number,
                    metadata_json=metadata_json,
                )
            )
        elif action.action_type == "write_post":
            posts.append(
                PostRecord(
                    post_id=new_post_id(),
                    run_id=snapshot.run_id,
                    author_id=action.user_id,
                    content=action.target_content or "",
                    created_at=created_at,
                    created_at_turn=snapshot.turn_number,
                    metadata_json=metadata_json,
                )
            )
        elif action.action_type == "comment_on_post":
            comments.append(
                CommentRecord(
                    comment_id=new_comment_id(),
                    run_id=snapshot.run_id,
                    parent_post_id=action.target_id or "",
                    author_id=action.user_id,
                    content=action.target_content or "",
                    created_at=created_at,
                    created_at_turn=snapshot.turn_number,
                    metadata_json=metadata_json,
                )
            )
        else:
            raise ValueError(f"Unsupported action type {action.action_type!r}")

    return PendingTurnDiffs(
        posts=posts,
        likes=likes,
        follows=follows,
        comments=comments,
        memory_diffs=build_memory_diffs(validated_actions, snapshot),
    )


def _metadata_for_action(action: ProposedActionRecord) -> dict[str, str]:
    metadata: dict[str, str] = {"proposed_action_id": action.action_id}
    if action.generation_id is not None:
        metadata["generation_id"] = action.generation_id
    return metadata
