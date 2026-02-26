"""Read-side CQRS service for simulation run lookup APIs."""

from __future__ import annotations

from lib.validation_decorators import validate_inputs
from simulation.api.schemas.simulation import (
    FeedSchema,
    PostSchema,
    RunConfigDetail,
    RunDetailsResponse,
    RunListItem,
    TurnActionsItem,
    TurnSchema,
)
from simulation.core.engine import SimulationEngine
from simulation.core.models.metrics import RunMetrics, TurnMetrics
from simulation.core.models.posts import BlueskyFeedPost
from simulation.core.models.runs import Run
from simulation.core.models.turns import TurnMetadata
from simulation.core.utils.exceptions import RunNotFoundError
from simulation.core.utils.validators import validate_run_exists, validate_run_id

MAX_UNFILTERED_POSTS: int = 500


def list_runs(*, engine: SimulationEngine) -> list[RunListItem]:
    """List persisted runs from the database, newest first."""
    runs: list[Run] = engine.list_runs()
    runs_sorted = sorted(runs, key=lambda r: r.created_at, reverse=True)
    return [
        RunListItem(
            run_id=r.run_id,
            created_at=r.created_at,
            total_turns=r.total_turns,
            total_agents=r.total_agents,
            status=r.status,
        )
        for r in runs_sorted
    ]


def get_turns_for_run(
    *, run_id: str, engine: SimulationEngine
) -> dict[str, TurnSchema]:
    """Build TurnSchema payloads from persisted turn metadata + generated feeds.

    Note: agent_actions are currently not persisted in SQLite. This endpoint returns
    an empty agent_actions mapping for now.
    """
    validated_run_id = validate_run_id(run_id)
    run = engine.get_run(validated_run_id)
    if run is None:
        raise RunNotFoundError(validated_run_id)

    metadata_list = engine.list_turn_metadata(validated_run_id)
    metadata_sorted = sorted(metadata_list, key=lambda m: m.turn_number)

    turns: dict[str, TurnSchema] = {}
    for item in metadata_sorted:
        feeds = engine.read_feeds_for_turn(validated_run_id, item.turn_number)
        agent_feeds = {
            feed.agent_handle: FeedSchema(
                feed_id=feed.feed_id,
                run_id=feed.run_id,
                turn_number=feed.turn_number,
                agent_handle=feed.agent_handle,
                post_uris=list(feed.post_uris),
                created_at=feed.created_at,
            )
            for feed in feeds
        }
        turns[str(item.turn_number)] = TurnSchema(
            turn_number=item.turn_number,
            agent_feeds=agent_feeds,
            agent_actions={},
        )
    return turns


def _post_to_schema(post: BlueskyFeedPost) -> PostSchema:
    return PostSchema(
        uri=post.uri,
        author_display_name=post.author_display_name,
        author_handle=post.author_handle,
        text=post.text,
        bookmark_count=post.bookmark_count,
        like_count=post.like_count,
        quote_count=post.quote_count,
        reply_count=post.reply_count,
        repost_count=post.repost_count,
        created_at=post.created_at,
    )


def get_posts_by_uris(
    *, uris: list[str] | None = None, engine: SimulationEngine
) -> list[PostSchema]:
    """Return posts from the database.

    If uris is None/empty, returns up to MAX_UNFILTERED_POSTS posts.
    """
    posts: list[BlueskyFeedPost]
    if not uris:
        posts = engine.read_all_feed_posts()[:MAX_UNFILTERED_POSTS]
    else:
        posts = engine.read_feed_posts_by_uris(uris)

    return [_post_to_schema(p) for p in sorted(posts, key=lambda p: p.uri)]


@validate_inputs((validate_run_id, "run_id"))
def get_run_details(*, run_id: str, engine: SimulationEngine) -> RunDetailsResponse:
    """Build run-details response for a persisted run.

    Args:
        run_id: Identifier for the run.
        engine: Simulation engine exposing read/query methods.

    Returns:
        RunDetailsResponse with run config and ordered turn summaries.

    Raises:
        ValueError: If run_id is empty.
        RunNotFoundError: If the run does not exist.
    """
    run = engine.get_run(run_id)
    run = validate_run_exists(run=run, run_id=run_id)

    metadata_list: list[TurnMetadata] = engine.list_turn_metadata(run_id)
    turn_metrics_list: list[TurnMetrics] = engine.list_turn_metrics(run_id)
    turns: list[TurnActionsItem] = _build_turn_actions_items(
        metadata_list=metadata_list,
        turn_metrics_list=turn_metrics_list,
    )
    run_metrics: RunMetrics | None = engine.get_run_metrics(run_id)

    return RunDetailsResponse(
        run_id=run.run_id,
        status=run.status,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        config=RunConfigDetail(
            num_agents=run.total_agents,
            num_turns=run.total_turns,
            feed_algorithm=run.feed_algorithm,
            metric_keys=run.metric_keys,
        ),
        turns=turns,
        run_metrics=run_metrics.metrics if run_metrics else None,
    )


def _build_turn_actions_items(
    *, metadata_list: list[TurnMetadata], turn_metrics_list: list[TurnMetrics]
) -> list[TurnActionsItem]:
    """Map turn metadata to deterministic, API-serializable turn summaries."""
    metrics_by_turn: dict[int, TurnMetrics] = {
        item.turn_number: item for item in turn_metrics_list
    }
    sorted_metadata: list[TurnMetadata] = sorted(
        metadata_list,
        key=lambda item: item.turn_number,
    )
    return [
        TurnActionsItem(
            turn_number=item.turn_number,
            created_at=item.created_at,
            total_actions={
                action.value: count for action, count in item.total_actions.items()
            },
            metrics=metrics_by_turn[item.turn_number].metrics
            if item.turn_number in metrics_by_turn
            else None,
        )
        for item in sorted_metadata
    ]
