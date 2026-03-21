"""Read-side CQRS service for simulation run lookup APIs."""

from __future__ import annotations

from lib.validation_decorators import validate_inputs
from simulation.api.errors import ApiRunNotFoundError
from simulation.api.schemas.simulation import (
    AgentActionSchema,
    FeedSchema,
    PostSchema,
    RunConfigDetail,
    RunDetailsResponse,
    RunListItem,
    TurnActionsItem,
    TurnSchema,
)
from simulation.core.engine import SimulationEngine
from simulation.core.models.actions import TurnAction
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.metrics import RunMetrics, TurnMetrics
from simulation.core.models.posts import Post
from simulation.core.models.runs import Run
from simulation.core.models.turns import TurnData, TurnMetadata
from simulation.core.utils.validators import validate_run_id

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
    """Build TurnSchema payloads from persisted turn metadata via ``get_turn_data``."""
    validated_run_id = validate_run_id(run_id)
    run = engine.get_run(validated_run_id)
    if run is None:
        raise ApiRunNotFoundError(validated_run_id)

    metadata_list = engine.list_turn_metadata(validated_run_id)
    metadata_sorted = sorted(metadata_list, key=lambda m: m.turn_number)

    run_agents = engine.list_run_agents(validated_run_id)
    agent_id_to_handle = {ra.agent_id: ra.handle_at_start for ra in run_agents}

    turns: dict[str, TurnSchema] = {}
    for item in metadata_sorted:
        turn_data = engine.get_turn_data(validated_run_id, item.turn_number)
        if turn_data is None:
            turns[str(item.turn_number)] = TurnSchema(
                turn_number=item.turn_number,
                agent_feeds={},
                agent_actions={},
            )
        else:
            turns[str(item.turn_number)] = _turn_data_to_schema(
                turn_data,
                agent_id_to_handle=agent_id_to_handle,
            )
    return turns


def _resolve_agent_handle(agent_id: str, agent_id_to_handle: dict[str, str]) -> str:
    return agent_id_to_handle.get(agent_id, agent_id)


def _generated_action_to_schema(
    action: GeneratedLike | GeneratedComment | GeneratedFollow,
    *,
    agent_handle: str,
) -> AgentActionSchema:
    if isinstance(action, GeneratedLike):
        return AgentActionSchema(
            action_id=action.like.like_id,
            agent_id=action.like.agent_id,
            agent_handle=agent_handle,
            post_id=action.like.post_id,
            target_agent_id=None,
            type=TurnAction.LIKE,
            created_at=action.like.created_at,
        )
    if isinstance(action, GeneratedComment):
        return AgentActionSchema(
            action_id=action.comment.comment_id,
            agent_id=action.comment.agent_id,
            agent_handle=agent_handle,
            post_id=action.comment.post_id,
            target_agent_id=None,
            type=TurnAction.COMMENT,
            created_at=action.comment.created_at,
        )
    if isinstance(action, GeneratedFollow):
        return AgentActionSchema(
            action_id=action.follow.follow_id,
            agent_id=action.follow.agent_id,
            agent_handle=agent_handle,
            post_id=None,
            target_agent_id=action.follow.target_agent_id,
            type=TurnAction.FOLLOW,
            created_at=action.follow.created_at,
        )
    raise TypeError(
        f"Unsupported generated action type for API serialization: {type(action)!r}"
    )


def _turn_data_to_schema(
    turn_data: TurnData,
    *,
    agent_id_to_handle: dict[str, str],
) -> TurnSchema:
    agent_feeds: dict[str, FeedSchema] = {}
    for agent_id, record in turn_data.feed_records.items():
        agent_feeds[agent_id] = FeedSchema(
            feed_id=record.feed_id,
            run_id=record.run_id,
            turn_number=record.turn_number,
            agent_id=record.agent_id,
            agent_handle=record.agent_handle,
            post_ids=list(record.post_ids),
            created_at=record.created_at,
        )

    agent_actions: dict[str, list[AgentActionSchema]] = {}
    for agent_id, actions in turn_data.actions.items():
        handle = _resolve_agent_handle(agent_id, agent_id_to_handle)
        agent_actions[agent_id] = [
            _generated_action_to_schema(action, agent_handle=handle)
            for action in actions
        ]

    return TurnSchema(
        turn_number=turn_data.turn_number,
        agent_feeds=agent_feeds,
        agent_actions=agent_actions,
    )


def _post_to_schema(post: Post) -> PostSchema:
    return PostSchema(
        post_id=post.post_id,
        source=post.source,
        uri=post.uri,
        author_agent_id=post.author_agent_id,
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


def get_posts_by_ids(
    *,
    post_ids: list[str] | None = None,
    run_id: str | None = None,
    engine: SimulationEngine,
) -> list[PostSchema]:
    """Return posts from the database.

    When run_id is provided with post_ids, resolve from run_posts (run-scoped).
    Otherwise resolve from feed_posts (global catalog).
    If post_ids is None/empty and run_id is None, returns up to MAX_UNFILTERED_POSTS
    from feed_posts.
    """
    posts: list[Post]
    if not post_ids:
        if run_id is not None:
            posts = []
        else:
            posts = engine.read_all_feed_posts()[:MAX_UNFILTERED_POSTS]
    elif run_id is not None:
        posts = engine.read_posts_for_run(run_id, post_ids)
    else:
        posts = engine.read_feed_posts_by_ids(post_ids)

    return [_post_to_schema(p) for p in sorted(posts, key=lambda p: p.post_id)]


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
    if run is None:
        raise ApiRunNotFoundError(run_id)

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
