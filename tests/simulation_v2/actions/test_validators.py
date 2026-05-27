"""Unit tests for action business-rule validators."""

from __future__ import annotations

import pytest

from simulation_v2.actions.validators import (
    ActionValidationOutcome,
    validate_comment_on_post_action,
    validate_follow_user_action,
    validate_like_post_action,
    validate_write_post_action,
)


def _accepted() -> ActionValidationOutcome:
    return ActionValidationOutcome(accepted=True)


def _rejected(filter_id: str, reason: str) -> ActionValidationOutcome:
    return ActionValidationOutcome(
        accepted=False,
        filter_id=filter_id,  # type: ignore[arg-type]
        filter_reason=reason,
    )


FEED_POST_IDS = {"p1", "p2"}
FEED_AUTHORS = {"p1": "u1", "p2": "u2"}
FOLLOW_CANDIDATES = {"u2", "u3"}


class TestValidateLikePostAction:
    def test_accepts_valid_like(self) -> None:
        outcome = validate_like_post_action(
            user_id="u1",
            post_id="p2",
            feed_post_ids=FEED_POST_IDS,
            feed_author_by_post_id=FEED_AUTHORS,
            snapshot_liked_post_ids=set(),
            accepted_likes_this_turn=set(),
            accepted_like_count=0,
            max_likes=5,
        )
        assert outcome == _accepted()

    @pytest.mark.parametrize(
        ("kwargs", "filter_id", "reason"),
        [
            (
                {
                    "user_id": "u1",
                    "post_id": "p1",
                    "feed_post_ids": FEED_POST_IDS,
                    "feed_author_by_post_id": FEED_AUTHORS,
                    "snapshot_liked_post_ids": set(),
                    "accepted_likes_this_turn": set(),
                    "accepted_like_count": 0,
                    "max_likes": 5,
                },
                "no_self_like",
                "Cannot like your own post",
            ),
            (
                {
                    "user_id": "u1",
                    "post_id": "p2",
                    "feed_post_ids": FEED_POST_IDS,
                    "feed_author_by_post_id": FEED_AUTHORS,
                    "snapshot_liked_post_ids": set(),
                    "accepted_likes_this_turn": {"p2"},
                    "accepted_like_count": 1,
                    "max_likes": 5,
                },
                "duplicate_like",
                "Duplicate like for post p2",
            ),
            (
                {
                    "user_id": "u1",
                    "post_id": "p2",
                    "feed_post_ids": FEED_POST_IDS,
                    "feed_author_by_post_id": FEED_AUTHORS,
                    "snapshot_liked_post_ids": {"p2"},
                    "accepted_likes_this_turn": set(),
                    "accepted_like_count": 0,
                    "max_likes": 5,
                },
                "duplicate_like",
                "Duplicate like for post p2",
            ),
            (
                {
                    "user_id": "u1",
                    "post_id": "p9",
                    "feed_post_ids": FEED_POST_IDS,
                    "feed_author_by_post_id": FEED_AUTHORS,
                    "snapshot_liked_post_ids": set(),
                    "accepted_likes_this_turn": set(),
                    "accepted_like_count": 0,
                    "max_likes": 5,
                },
                "missing_target_post",
                "Post p9 not in feed",
            ),
            (
                {
                    "user_id": "u1",
                    "post_id": "p2",
                    "feed_post_ids": FEED_POST_IDS,
                    "feed_author_by_post_id": FEED_AUTHORS,
                    "snapshot_liked_post_ids": set(),
                    "accepted_likes_this_turn": set(),
                    "accepted_like_count": 2,
                    "max_likes": 2,
                },
                "max_actions_per_turn",
                "Exceeded max like_post per turn (2)",
            ),
        ],
    )
    def test_rejects_invalid_like(
        self, kwargs: dict, filter_id: str, reason: str
    ) -> None:
        outcome = validate_like_post_action(**kwargs)
        assert outcome == _rejected(filter_id, reason)


class TestValidateFollowUserAction:
    def test_accepts_valid_follow(self) -> None:
        outcome = validate_follow_user_action(
            user_id="u1",
            followee_id="u2",
            follow_candidate_ids=FOLLOW_CANDIDATES,
            snapshot_followed_user_ids=set(),
            accepted_follows_this_turn=set(),
            accepted_follow_count=0,
            max_follows=3,
        )
        assert outcome == _accepted()

    @pytest.mark.parametrize(
        ("kwargs", "filter_id", "reason"),
        [
            (
                {
                    "user_id": "u1",
                    "followee_id": "u1",
                    "follow_candidate_ids": FOLLOW_CANDIDATES,
                    "snapshot_followed_user_ids": set(),
                    "accepted_follows_this_turn": set(),
                    "accepted_follow_count": 0,
                    "max_follows": 3,
                },
                "no_self_follow",
                "Cannot follow yourself",
            ),
            (
                {
                    "user_id": "u1",
                    "followee_id": "u2",
                    "follow_candidate_ids": FOLLOW_CANDIDATES,
                    "snapshot_followed_user_ids": set(),
                    "accepted_follows_this_turn": {"u2"},
                    "accepted_follow_count": 1,
                    "max_follows": 3,
                },
                "duplicate_follow",
                "Duplicate follow for user u2",
            ),
            (
                {
                    "user_id": "u1",
                    "followee_id": "u2",
                    "follow_candidate_ids": FOLLOW_CANDIDATES,
                    "snapshot_followed_user_ids": {"u2"},
                    "accepted_follows_this_turn": set(),
                    "accepted_follow_count": 0,
                    "max_follows": 3,
                },
                "duplicate_follow",
                "Duplicate follow for user u2",
            ),
            (
                {
                    "user_id": "u1",
                    "followee_id": "u9",
                    "follow_candidate_ids": FOLLOW_CANDIDATES,
                    "snapshot_followed_user_ids": set(),
                    "accepted_follows_this_turn": set(),
                    "accepted_follow_count": 0,
                    "max_follows": 3,
                },
                "missing_target_user",
                "User u9 not in follow candidates",
            ),
            (
                {
                    "user_id": "u1",
                    "followee_id": "u3",
                    "follow_candidate_ids": FOLLOW_CANDIDATES,
                    "snapshot_followed_user_ids": set(),
                    "accepted_follows_this_turn": set(),
                    "accepted_follow_count": 1,
                    "max_follows": 1,
                },
                "max_actions_per_turn",
                "Exceeded max follow_user per turn (1)",
            ),
        ],
    )
    def test_rejects_invalid_follow(
        self, kwargs: dict, filter_id: str, reason: str
    ) -> None:
        outcome = validate_follow_user_action(**kwargs)
        assert outcome == _rejected(filter_id, reason)


class TestValidateWritePostAction:
    def test_accepts_non_empty_content(self) -> None:
        outcome = validate_write_post_action(
            content="Hello world",
            accepted_write_count=0,
            max_posts=2,
        )
        assert outcome == _accepted()

    @pytest.mark.parametrize(
        ("kwargs", "filter_id", "reason"),
        [
            (
                {"content": "   ", "accepted_write_count": 0, "max_posts": 2},
                "empty_content",
                "Action content is empty",
            ),
            (
                {"content": None, "accepted_write_count": 0, "max_posts": 2},
                "empty_content",
                "Action content is empty",
            ),
            (
                {"content": "ok", "accepted_write_count": 2, "max_posts": 2},
                "max_actions_per_turn",
                "Exceeded max write_post per turn (2)",
            ),
        ],
    )
    def test_rejects_invalid_write(
        self, kwargs: dict, filter_id: str, reason: str
    ) -> None:
        outcome = validate_write_post_action(**kwargs)
        assert outcome == _rejected(filter_id, reason)


class TestValidateCommentOnPostAction:
    def test_accepts_valid_comment(self) -> None:
        outcome = validate_comment_on_post_action(
            parent_post_id="p1",
            content="Nice post",
            feed_post_ids=FEED_POST_IDS,
            accepted_comment_count=0,
            max_comments=3,
        )
        assert outcome == _accepted()

    @pytest.mark.parametrize(
        ("kwargs", "filter_id", "reason"),
        [
            (
                {
                    "parent_post_id": "p1",
                    "content": "",
                    "feed_post_ids": FEED_POST_IDS,
                    "accepted_comment_count": 0,
                    "max_comments": 3,
                },
                "empty_content",
                "Action content is empty",
            ),
            (
                {
                    "parent_post_id": "p9",
                    "content": "hi",
                    "feed_post_ids": FEED_POST_IDS,
                    "accepted_comment_count": 0,
                    "max_comments": 3,
                },
                "missing_parent_post",
                "Parent post p9 not in feed",
            ),
            (
                {
                    "parent_post_id": "p1",
                    "content": "hi",
                    "feed_post_ids": FEED_POST_IDS,
                    "accepted_comment_count": 1,
                    "max_comments": 1,
                },
                "max_actions_per_turn",
                "Exceeded max comment_on_post per turn (1)",
            ),
        ],
    )
    def test_rejects_invalid_comment(
        self, kwargs: dict, filter_id: str, reason: str
    ) -> None:
        outcome = validate_comment_on_post_action(**kwargs)
        assert outcome == _rejected(filter_id, reason)
