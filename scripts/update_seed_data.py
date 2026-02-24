"""Generate deterministic local-dev seed fixtures.

Writes JSON fixtures to simulation/local_dev/seed_fixtures/*.json.

These fixtures are imported into the local dummy DB when LOCAL=true.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from simulation.api.dummy_data import DUMMY_AGENTS, DUMMY_POSTS, DUMMY_RUNS, DUMMY_TURNS
from simulation.api.schemas.simulation import TurnSchema
from simulation.core.metrics.defaults import get_default_metric_keys
from simulation.core.models.actions import TurnAction

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPO_ROOT / "simulation" / "local_dev" / "seed_fixtures"


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8")


def _count_actions(turn: TurnSchema) -> dict[str, int]:
    counts: dict[str, int] = {}
    for actions in turn.agent_actions.values():
        for action in actions:
            key = (
                action.type.value
                if isinstance(action.type, TurnAction)
                else str(action.type)
            )
            counts[key] = counts.get(key, 0) + 1
    return {k: v for k, v in sorted(counts.items()) if v > 0}


def _turn_created_at(turn: TurnSchema) -> str:
    # FeedSchema.created_at exists for every agent feed; use the min as deterministic turn timestamp.
    if not turn.agent_feeds:
        # Fallback: deterministic but clearly synthetic.
        return "2025-01-01T00:00:00"
    return min(feed.created_at for feed in turn.agent_feeds.values())


def _compute_turn_metrics(*, total_actions: dict[str, int]) -> dict[str, object]:
    counts_by_type = dict(sorted(total_actions.items()))
    total = sum(int(v) for v in counts_by_type.values())
    return {
        "turn.actions.counts_by_type": counts_by_type,
        "turn.actions.total": total,
    }


def _compute_run_metrics(
    *, turn_total_actions: list[dict[str, int]]
) -> dict[str, object]:
    totals: dict[str, int] = {a.value: 0 for a in TurnAction}
    for counts in turn_total_actions:
        for k, v in counts.items():
            totals[k] = totals.get(k, 0) + int(v)
    totals_by_type = dict(sorted(totals.items()))
    total = sum(totals_by_type.values())
    return {
        "run.actions.total_by_type": totals_by_type,
        "run.actions.total": total,
    }


@dataclass(frozen=True)
class Fixtures:
    runs: list[dict]
    turn_metadata: list[dict]
    generated_feeds: list[dict]
    feed_posts: list[dict]
    turn_metrics: list[dict]
    run_metrics: list[dict]
    agents: list[dict]
    agent_persona_bios: list[dict]
    user_agent_profile_metadata: list[dict]


def build_fixtures() -> Fixtures:
    metric_keys = get_default_metric_keys()
    expected_keys = {
        "turn.actions.counts_by_type",
        "turn.actions.total",
        "run.actions.total_by_type",
        "run.actions.total",
    }
    unknown = set(metric_keys) - expected_keys
    if unknown:
        raise RuntimeError(
            "update_seed_data.py only supports builtin action metrics. "
            f"Unknown metric keys in defaults: {sorted(unknown)}. "
            "Update the seed generator to compute these metrics, then re-run."
        )

    runs_out: list[dict] = []
    turn_md_out: list[dict] = []
    feeds_out: list[dict] = []
    posts_out: list[dict] = []
    turn_metrics_out: list[dict] = []
    run_metrics_out: list[dict] = []

    agents_out: list[dict] = []
    bios_out: list[dict] = []
    user_md_out: list[dict] = []

    # --- Agents (for /v1/simulations/agents and local run detail agent lookup) ---
    # Use deterministic agent_id derived from handle.
    # Store persona_bio in agent_persona_bios (UI uses this as "bio").
    base_agent_ts = "2025-01-01T00:00:00"
    for agent in sorted(DUMMY_AGENTS, key=lambda a: a.handle):
        agent_id = _stable_id("agent", agent.handle)
        agents_out.append(
            {
                "agent_id": agent_id,
                "handle": agent.handle,
                "persona_source": "sync_bluesky",
                "display_name": agent.name,
                "created_at": base_agent_ts,
                "updated_at": base_agent_ts,
            }
        )
        bios_out.append(
            {
                "id": _stable_id("bio", agent.handle),
                "agent_id": agent_id,
                "persona_bio": agent.bio,
                "persona_bio_source": "user_provided",
                "created_at": base_agent_ts,
                "updated_at": base_agent_ts,
            }
        )
        user_md_out.append(
            {
                "id": _stable_id("md", agent.handle),
                "agent_id": agent_id,
                "followers_count": agent.followers,
                "follows_count": agent.following,
                "posts_count": agent.posts_count,
                "created_at": base_agent_ts,
                "updated_at": base_agent_ts,
            }
        )

    # --- Posts ---
    for post in sorted(DUMMY_POSTS, key=lambda p: p.uri):
        posts_out.append(
            {
                "uri": post.uri,
                "author_display_name": post.author_display_name,
                "author_handle": post.author_handle,
                "text": post.text,
                "bookmark_count": post.bookmark_count,
                "like_count": post.like_count,
                "quote_count": post.quote_count,
                "reply_count": post.reply_count,
                "repost_count": post.repost_count,
                "created_at": post.created_at,
            }
        )

    # --- Runs, turn metadata, feeds, metrics ---
    for run in sorted(DUMMY_RUNS, key=lambda r: r.created_at):
        run_id = run.run_id
        status = run.status.value if hasattr(run.status, "value") else str(run.status)
        runs_out.append(
            {
                "run_id": run_id,
                "created_at": run.created_at,
                "total_turns": run.total_turns,
                "total_agents": run.total_agents,
                "feed_algorithm": "chronological",
                "metric_keys": metric_keys,
                "started_at": run.created_at,
                "status": status,
                "completed_at": run.created_at if status == "completed" else None,
            }
        )

        turns_for_run: dict[str, TurnSchema] | None = DUMMY_TURNS.get(run_id)
        if not turns_for_run:
            continue

        # Stable order by integer turn_number.
        ordered_turn_numbers = sorted(int(k) for k in turns_for_run.keys())
        per_turn_total_actions: list[dict[str, int]] = []
        for tn in ordered_turn_numbers:
            turn = turns_for_run[str(tn)]
            total_actions = _count_actions(turn)
            per_turn_total_actions.append(total_actions)
            created_at = _turn_created_at(turn)

            turn_md_out.append(
                {
                    "run_id": run_id,
                    "turn_number": tn,
                    "total_actions": total_actions,
                    "created_at": created_at,
                }
            )

            for feed in turn.agent_feeds.values():
                feeds_out.append(
                    {
                        "feed_id": feed.feed_id,
                        "run_id": feed.run_id,
                        "turn_number": feed.turn_number,
                        "agent_handle": feed.agent_handle,
                        "post_uris": list(feed.post_uris),
                        "created_at": feed.created_at,
                    }
                )

            # Metrics are derived from turn_metadata in production; keep deterministic fixture copies.
            tm = _compute_turn_metrics(total_actions=total_actions)
            turn_metrics_out.append(
                {
                    "run_id": run_id,
                    "turn_number": tn,
                    "metrics": {k: tm[k] for k in sorted(tm.keys())},
                    "created_at": created_at,
                }
            )

        rm = _compute_run_metrics(turn_total_actions=per_turn_total_actions)
        run_metrics_out.append(
            {
                "run_id": run_id,
                "metrics": {k: rm[k] for k in sorted(rm.keys())},
                "created_at": run.created_at,
            }
        )

    # Stable ordering for deterministic diffs
    runs_out.sort(key=lambda r: r["created_at"])
    turn_md_out.sort(key=lambda t: (t["run_id"], t["turn_number"]))
    feeds_out.sort(key=lambda f: (f["run_id"], f["turn_number"], f["agent_handle"]))
    turn_metrics_out.sort(key=lambda t: (t["run_id"], t["turn_number"]))
    run_metrics_out.sort(key=lambda r: r["run_id"])

    return Fixtures(
        runs=runs_out,
        turn_metadata=turn_md_out,
        generated_feeds=feeds_out,
        feed_posts=posts_out,
        turn_metrics=turn_metrics_out,
        run_metrics=run_metrics_out,
        agents=agents_out,
        agent_persona_bios=bios_out,
        user_agent_profile_metadata=user_md_out,
    )


def main() -> None:
    fixtures = build_fixtures()
    _write_json(FIXTURES_DIR / "runs.json", fixtures.runs)
    _write_json(FIXTURES_DIR / "turn_metadata.json", fixtures.turn_metadata)
    _write_json(FIXTURES_DIR / "generated_feeds.json", fixtures.generated_feeds)
    _write_json(FIXTURES_DIR / "bluesky_feed_posts.json", fixtures.feed_posts)
    _write_json(FIXTURES_DIR / "turn_metrics.json", fixtures.turn_metrics)
    _write_json(FIXTURES_DIR / "run_metrics.json", fixtures.run_metrics)
    _write_json(FIXTURES_DIR / "agents.json", fixtures.agents)
    _write_json(FIXTURES_DIR / "agent_persona_bios.json", fixtures.agent_persona_bios)
    _write_json(
        FIXTURES_DIR / "user_agent_profile_metadata.json",
        fixtures.user_agent_profile_metadata,
    )

    print(f"Wrote seed fixtures to {FIXTURES_DIR}")


if __name__ == "__main__":
    main()
