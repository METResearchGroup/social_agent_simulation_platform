"""Dummy simulation data returned by API routes during UI integration."""

from datetime import datetime, timedelta

from simulation.api.schemas.simulation import (
    AgentActionSchema,
    FeedSchema,
    RunListItem,
    TurnSchema,
)
from simulation.core.models.actions import TurnAction
from simulation.core.models.runs import RunStatus

_DUMMY_AGENT_HANDLES: list[str] = [
    "@alice.bsky.social",
    "@bob.tech",
    "@charlie.dev",
    "@diana.design",
    "@edward.data",
    "@fiona.frontend",
    "@george.backend",
    "@hannah.ai",
]

_DUMMY_POST_URIS: list[str] = [
    "at://did:plc:example1/post1",
    "at://did:plc:example2/post2",
    "at://did:plc:example3/post3",
    "at://did:plc:example4/post4",
    "at://did:plc:example5/post5",
    "at://did:plc:example6/post6",
    "at://did:plc:example7/post7",
    "at://did:plc:example8/post8",
    "at://did:plc:example9/post9",
    "at://did:plc:example10/post10",
]

_RUN_COMPLETED_TURNS: dict[str, int] = {
    "run_2025-01-15T10:30:00": 10,
    "run_2025-01-15T14:45:00": 3,
    "run_2025-01-16T09:15:00": 5,
    "run_2025-01-17T08:20:00": 8,
    "run_2025-01-18T11:00:00": 5,
}


def _timestamp_for_turn(*, base_iso: str, minutes: int, seconds: int = 0) -> str:
    base_dt = datetime.fromisoformat(base_iso)
    timestamp: datetime = base_dt + timedelta(minutes=minutes, seconds=seconds)
    return timestamp.isoformat(timespec="seconds")


def _create_turn(
    *,
    run_id: str,
    run_created_at: str,
    turn_number: int,
    agent_handles: list[str],
) -> TurnSchema:
    start_offset: int = turn_number % len(agent_handles)
    num_agents: int = min(len(agent_handles), 5)
    selected_agents: list[str] = []
    for idx in range(num_agents):
        selected_index: int = (start_offset + idx) % len(agent_handles)
        selected_agents.append(agent_handles[selected_index])

    agent_feeds: dict[str, FeedSchema] = {}
    agent_actions: dict[str, list[AgentActionSchema]] = {}

    for idx, agent_handle in enumerate(selected_agents):
        post_start_idx: int = (turn_number * len(selected_agents) + idx) % len(
            _DUMMY_POST_URIS
        )
        post_uris: list[str] = [
            _DUMMY_POST_URIS[post_start_idx % len(_DUMMY_POST_URIS)],
            _DUMMY_POST_URIS[(post_start_idx + 1) % len(_DUMMY_POST_URIS)],
            _DUMMY_POST_URIS[(post_start_idx + 2) % len(_DUMMY_POST_URIS)],
        ]

        agent_feeds[agent_handle] = FeedSchema(
            feed_id=f"feed_{run_id}_turn{turn_number}_{agent_handle}",
            run_id=run_id,
            turn_number=turn_number,
            agent_handle=agent_handle,
            post_uris=post_uris,
            created_at=_timestamp_for_turn(
                base_iso=run_created_at,
                minutes=turn_number,
            ),
        )

        actions: list[AgentActionSchema] = []
        if turn_number % 2 == 0 and idx % 2 == 0 and len(post_uris) > 0:
            actions.append(
                AgentActionSchema(
                    action_id=f"action_{run_id}_turn{turn_number}_{agent_handle}_1",
                    agent_handle=agent_handle,
                    post_uri=post_uris[0],
                    type=TurnAction.LIKE,
                    created_at=_timestamp_for_turn(
                        base_iso=run_created_at,
                        minutes=turn_number,
                        seconds=5,
                    ),
                )
            )

        if turn_number % 3 == 0 and idx == 0 and len(selected_agents) > 1:
            actions.append(
                AgentActionSchema(
                    action_id=f"action_{run_id}_turn{turn_number}_{agent_handle}_2",
                    agent_handle=agent_handle,
                    user_id=selected_agents[1],
                    type=TurnAction.FOLLOW,
                    created_at=_timestamp_for_turn(
                        base_iso=run_created_at,
                        minutes=turn_number,
                        seconds=7,
                    ),
                )
            )

        agent_actions[agent_handle] = actions

    return TurnSchema(
        turn_number=turn_number,
        agent_feeds=agent_feeds,
        agent_actions=agent_actions,
    )


def _build_dummy_turns() -> dict[str, dict[str, TurnSchema]]:
    turns_by_run: dict[str, dict[str, TurnSchema]] = {}
    run_lookup: dict[str, RunListItem] = {run.run_id: run for run in DUMMY_RUNS}

    for run_id, completed_turns in _RUN_COMPLETED_TURNS.items():
        run: RunListItem = run_lookup[run_id]
        run_agent_handles: list[str] = _DUMMY_AGENT_HANDLES[: run.total_agents]
        turns: dict[str, TurnSchema] = {}
        for turn_number in range(completed_turns):
            turns[str(turn_number)] = _create_turn(
                run_id=run_id,
                run_created_at=run.created_at,
                turn_number=turn_number,
                agent_handles=run_agent_handles,
            )
        turns_by_run[run_id] = turns

    return turns_by_run


DUMMY_RUNS: list[RunListItem] = [
    RunListItem(
        run_id="run_2025-01-15T10:30:00",
        created_at="2025-01-15T10:30:00",
        total_turns=10,
        total_agents=3,
        status=RunStatus.COMPLETED,
    ),
    RunListItem(
        run_id="run_2025-01-15T14:45:00",
        created_at="2025-01-15T14:45:00",
        total_turns=10,
        total_agents=4,
        status=RunStatus.RUNNING,
    ),
    RunListItem(
        run_id="run_2025-01-16T09:15:00",
        created_at="2025-01-16T09:15:00",
        total_turns=5,
        total_agents=3,
        status=RunStatus.RUNNING,
    ),
    RunListItem(
        run_id="run_2025-01-17T08:20:00",
        created_at="2025-01-17T08:20:00",
        total_turns=15,
        total_agents=4,
        status=RunStatus.RUNNING,
    ),
    RunListItem(
        run_id="run_2025-01-18T11:00:00",
        created_at="2025-01-18T11:00:00",
        total_turns=20,
        total_agents=4,
        status=RunStatus.RUNNING,
    ),
]

DUMMY_TURNS: dict[str, dict[str, TurnSchema]] = _build_dummy_turns()
DUMMY_RUN_IDS: set[str] = {run.run_id for run in DUMMY_RUNS}
