"""Dummy simulation data returned by API routes during UI integration."""

from datetime import datetime, timedelta

from simulation.api.schemas.simulation import (
    AgentActionSchema,
    AgentSchema,
    FeedSchema,
    PostSchema,
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

DUMMY_AGENTS: list[AgentSchema] = [
    AgentSchema(
        handle="@alice.bsky.social",
        name="Alice Chen",
        bio="AI researcher and educator. Building the future of human-AI collaboration.",
        generated_bio="Alice is a passionate AI researcher who focuses on making artificial intelligence more accessible and understandable. She regularly shares insights about machine learning, human-computer interaction, and the ethical implications of AI technology.",
        followers=12450,
        following=892,
        posts_count=3421,
    ),
    AgentSchema(
        handle="@bob.tech",
        name="Bob Martinez",
        bio="Software engineer | Open source contributor | Coffee enthusiast ☕",
        generated_bio="Bob is an experienced software engineer with a strong focus on open-source contributions. He loves sharing technical knowledge, code reviews, and occasionally posts about his coffee adventures.",
        followers=8765,
        following=1203,
        posts_count=2105,
    ),
    AgentSchema(
        handle="@charlie.dev",
        name="Charlie Kim",
        bio="Building products that matter. Former startup founder.",
        generated_bio="Charlie is a product-focused engineer with a background in startup entrepreneurship. He shares lessons learned, product development insights, and thoughts on building sustainable businesses.",
        followers=15432,
        following=567,
        posts_count=4521,
    ),
    AgentSchema(
        handle="@diana.design",
        name="Diana Park",
        bio="UX Designer | Accessibility advocate | Design systems enthusiast",
        generated_bio="Diana is a UX designer passionate about creating inclusive and accessible digital experiences. She frequently shares design system patterns, accessibility best practices, and thoughts on how design impacts user behavior.",
        followers=9876,
        following=1456,
        posts_count=1876,
    ),
    AgentSchema(
        handle="@edward.data",
        name="Edward Wu",
        bio="Data scientist | ML engineer | Stats nerd 📊",
        generated_bio="Edward is a data scientist who loves diving deep into datasets and building machine learning models. He shares analysis insights, statistical findings, and practical ML techniques with the community.",
        followers=11234,
        following=789,
        posts_count=3210,
    ),
    AgentSchema(
        handle="@fiona.frontend",
        name="Fiona Lee",
        bio="Frontend engineer | React enthusiast | CSS wizard",
        generated_bio="Fiona is a frontend engineer specializing in React and modern CSS. She enjoys building performant web applications and sharing tips on component architecture, performance optimization, and creative CSS techniques.",
        followers=6543,
        following=923,
        posts_count=1567,
    ),
    AgentSchema(
        handle="@george.backend",
        name="George Thompson",
        bio="Backend engineer | Distributed systems | Database optimization",
        generated_bio="George is a backend engineer with expertise in distributed systems and database design. He shares insights on system architecture, scalability challenges, and database performance tuning strategies.",
        followers=14567,
        following=612,
        posts_count=2890,
    ),
    AgentSchema(
        handle="@hannah.ai",
        name="Hannah Rodriguez",
        bio="AI product manager | ML adoption | Ethical AI",
        generated_bio="Hannah is a product manager focused on bringing AI products to market. She writes about ML adoption strategies, ethical considerations in AI development, and bridging the gap between technical teams and business stakeholders.",
        followers=8765,
        following=1345,
        posts_count=2103,
    ),
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

DUMMY_POSTS: list[PostSchema] = [
    PostSchema(
        uri="at://did:plc:example1/post1",
        author_display_name="Alice Chen",
        author_handle="@alice.bsky.social",
        text="Just finished reading an amazing paper on transformer architectures. The attention mechanism continues to surprise me with its elegance!",
        bookmark_count=23,
        like_count=145,
        quote_count=8,
        reply_count=12,
        repost_count=34,
        created_at="2025-01-15T10:00:00",
    ),
    PostSchema(
        uri="at://did:plc:example2/post2",
        author_display_name="Bob Martinez",
        author_handle="@bob.tech",
        text="Found a beautiful bug today that only shows up on Tuesdays during leap years. Classic. 🐛",
        bookmark_count=5,
        like_count=67,
        quote_count=2,
        reply_count=8,
        repost_count=12,
        created_at="2025-01-15T11:30:00",
    ),
    PostSchema(
        uri="at://did:plc:example3/post3",
        author_display_name="Charlie Kim",
        author_handle="@charlie.dev",
        text="The best product decisions are often the ones that seem obvious in retrospect but were controversial at the time.",
        bookmark_count=89,
        like_count=234,
        quote_count=15,
        reply_count=45,
        repost_count=78,
        created_at="2025-01-15T13:00:00",
    ),
    PostSchema(
        uri="at://did:plc:example4/post4",
        author_display_name="Diana Park",
        author_handle="@diana.design",
        text="Accessibility isn't optional. Every design decision impacts real people with real needs. Let's build for everyone. ♿",
        bookmark_count=156,
        like_count=423,
        quote_count=28,
        reply_count=67,
        repost_count=112,
        created_at="2025-01-15T14:15:00",
    ),
    PostSchema(
        uri="at://did:plc:example5/post5",
        author_display_name="Edward Wu",
        author_handle="@edward.data",
        text="Just visualized a dataset with 10M rows and the patterns that emerged were fascinating. Sometimes you need to zoom out to see the forest for the trees.",
        bookmark_count=34,
        like_count=198,
        quote_count=12,
        reply_count=23,
        repost_count=45,
        created_at="2025-01-15T15:30:00",
    ),
    PostSchema(
        uri="at://did:plc:example6/post6",
        author_display_name="Fiona Lee",
        author_handle="@fiona.frontend",
        text="CSS Grid + Flexbox = unstoppable. Just built a responsive layout that would have taken me hours before. Modern CSS is magical.",
        bookmark_count=78,
        like_count=312,
        quote_count=19,
        reply_count=34,
        repost_count=89,
        created_at="2025-01-15T16:00:00",
    ),
    PostSchema(
        uri="at://did:plc:example7/post7",
        author_display_name="George Thompson",
        author_handle="@george.backend",
        text="Database indexing is like a library catalog system. Without it, you're searching through every book. With it, you go straight to the shelf.",
        bookmark_count=112,
        like_count=445,
        quote_count=31,
        reply_count=56,
        repost_count=123,
        created_at="2025-01-15T17:20:00",
    ),
    PostSchema(
        uri="at://did:plc:example8/post8",
        author_display_name="Hannah Rodriguez",
        author_handle="@hannah.ai",
        text="The hardest part of building AI products isn't the technology—it's understanding user needs and ensuring the AI actually solves real problems.",
        bookmark_count=67,
        like_count=289,
        quote_count=22,
        reply_count=41,
        repost_count=98,
        created_at="2025-01-15T18:45:00",
    ),
    PostSchema(
        uri="at://did:plc:example9/post9",
        author_display_name="Alice Chen",
        author_handle="@alice.bsky.social",
        text='Reading through code reviews and learning so much. The best teams learn from each other. Always ask "why?" not just "what?"',
        bookmark_count=45,
        like_count=178,
        quote_count=9,
        reply_count=19,
        repost_count=42,
        created_at="2025-01-16T09:00:00",
    ),
    PostSchema(
        uri="at://did:plc:example10/post10",
        author_display_name="Bob Martinez",
        author_handle="@bob.tech",
        text="Refactored a legacy component today. It's like archaeology—carefully removing layers to discover the original intent. Satisfying when it all clicks.",
        bookmark_count=28,
        like_count=134,
        quote_count=6,
        reply_count=15,
        repost_count=29,
        created_at="2025-01-16T10:30:00",
    ),
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
