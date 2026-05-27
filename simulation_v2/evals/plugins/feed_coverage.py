"""Report feed coverage and sanity violations."""

from __future__ import annotations

from typing import ClassVar

from simulation_v2.db.models import GeneratedFeedRecord
from simulation_v2.db.models.evals import EvalScope
from simulation_v2.evals.interfaces import EvalContext, EvalMetricDraft, EvalResult
from simulation_v2.evals.query_helpers import load_feeds_for_scope, load_users


class FeedCoveragePlugin:
    name: ClassVar[str] = "feed_coverage"
    scopes: ClassVar[frozenset[EvalScope]] = frozenset({"turn", "run"})

    def run(self, context: EvalContext) -> EvalResult:
        users = load_users(context)
        feeds = load_feeds_for_scope(context)
        feeds_by_user = {feed.user_id: feed for feed in feeds}

        empty_feeds = 0
        duplicate_post_feeds = 0
        self_authored_feeds = 0
        warnings: list[str] = []

        if context.scope == "turn":
            users_missing_feed = sum(
                1 for user in users if user.user_id not in feeds_by_user
            )
            users_with_feed = len(users) - users_missing_feed
            for feed in feeds:
                empty, duplicate, self_authored, feed_warnings = _inspect_feed(feed)
                empty_feeds += empty
                duplicate_post_feeds += duplicate
                self_authored_feeds += self_authored
                warnings.extend(feed_warnings)
        else:
            turns = context.repos.list_turns_for_run(context.run_id, context.conn)
            users_missing_feed = 0
            users_with_feed = 0
            for turn in turns:
                turn_feeds = [f for f in feeds if f.turn_id == turn.turn_id]
                turn_feed_users = {feed.user_id for feed in turn_feeds}
                users_missing_feed += sum(
                    1 for user in users if user.user_id not in turn_feed_users
                )
                users_with_feed += sum(
                    1 for user in users if user.user_id in turn_feed_users
                )
                for feed in turn_feeds:
                    empty, duplicate, self_authored, feed_warnings = _inspect_feed(feed)
                    empty_feeds += empty
                    duplicate_post_feeds += duplicate
                    self_authored_feeds += self_authored
                    warnings.extend(feed_warnings)

        metrics = [
            EvalMetricDraft(metric_name="users_total", metric_value=float(len(users))),
            EvalMetricDraft(
                metric_name="users_with_feed", metric_value=float(users_with_feed)
            ),
            EvalMetricDraft(
                metric_name="users_missing_feed",
                metric_value=float(users_missing_feed),
            ),
            EvalMetricDraft(metric_name="empty_feeds", metric_value=float(empty_feeds)),
            EvalMetricDraft(
                metric_name="duplicate_post_feeds",
                metric_value=float(duplicate_post_feeds),
            ),
            EvalMetricDraft(
                metric_name="self_authored_feeds",
                metric_value=float(self_authored_feeds),
            ),
        ]

        status = (
            "failed"
            if users_missing_feed > 0
            or duplicate_post_feeds > 0
            or self_authored_feeds > 0
            else "passed"
        )
        return EvalResult(
            plugin_name=self.name,
            status=status,
            metrics=metrics,
            warnings=warnings,
        )


def _inspect_feed(
    feed: GeneratedFeedRecord,
) -> tuple[int, int, int, list[str]]:
    views = feed.feed_posts
    warnings: list[str] = []
    empty = 1 if len(views) == 0 else 0
    duplicate = 0
    self_authored = 0

    seen_post_ids: set[str] = set()
    for view in views:
        if view.post_id in seen_post_ids:
            duplicate += 1
            warnings.append(
                f"duplicate post_id {view.post_id!r} in feed for user {feed.user_id!r}"
            )
        seen_post_ids.add(view.post_id)
        if view.author_id == feed.user_id:
            self_authored += 1
            warnings.append(
                f"self-authored post {view.post_id!r} in feed for user {feed.user_id!r}"
            )

    return empty, duplicate, self_authored, warnings
