"""Seed data loader for JSON fixtures under `simulation/local_dev/seed_fixtures/`.

This module is the **canonical** code path for loading those fixtures into a SQLite
database: local dev (`LOCAL=true`) and future non-local bootstrap (e.g. deploy) must
use the same entry point—there is no second fixture root.

`seed_database_from_fixtures_if_needed` is the public API (`db_path` + optional
`fixtures_dir`). `seed_local_db_if_needed` is a stable alias with the same
signature.

Seed policy:
- Seed once: if the DB has a matching fixtures digest, do nothing.
- If the DB is already seeded with a different digest, do not overwrite; log a warning
  and instruct the developer to reset via LOCAL_RESET_DB=1 (local workflow).
"""

from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from db.adapters.sqlite.agent_adapter import SQLiteAgentAdapter
from db.adapters.sqlite.agent_bio_adapter import SQLiteAgentBioAdapter
from db.adapters.sqlite.agent_follow_edge_adapter import SQLiteAgentFollowEdgeAdapter
from db.adapters.sqlite.agent_post_comment_adapter import SQLiteAgentPostCommentAdapter
from db.adapters.sqlite.agent_post_like_adapter import SQLiteAgentPostLikeAdapter
from db.adapters.sqlite.feed_post_adapter import SQLiteFeedPostAdapter
from db.adapters.sqlite.generated_feed_adapter import SQLiteGeneratedFeedAdapter
from db.adapters.sqlite.metrics_adapter import SQLiteMetricsAdapter
from db.adapters.sqlite.run_adapter import SQLiteRunAdapter
from db.adapters.sqlite.user_agent_profile_metadata_adapter import (
    SQLiteUserAgentProfileMetadataAdapter,
)
from db.backfills.agent_posts import backfill_agent_posts_from_feed_posts
from lib.agent_id import is_canonical_agent_id
from lib.timestamp_utils import get_current_timestamp
from simulation.core.models.agent import Agent, PersonaSource
from simulation.core.models.agent_bio import AgentBio, PersonaBioSource
from simulation.core.models.agent_follow_edge import AgentFollowEdge
from simulation.core.models.agent_post_comments import AgentPostComment
from simulation.core.models.agent_post_likes import AgentPostLike
from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.metrics import RunMetrics, TurnMetrics
from simulation.core.models.posts import Post, PostSource
from simulation.core.models.runs import Run
from simulation.core.models.turns import TurnMetadata
from simulation.core.models.user_agent_profile_metadata import UserAgentProfileMetadata
from simulation.local_dev.seed_metrics_fixtures import (
    parse_runs_and_turn_metadata,
    read_json_list,
    read_seed_metrics,
)

logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).resolve().parent / "seed_fixtures"

_SEED_META_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS local_seed_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
)
"""


@dataclass(frozen=True)
class SeedFixtures:
    runs: list[Run]
    turn_metadata: list[TurnMetadata]
    generated_feeds: list[GeneratedFeed]
    feed_posts: list[Post]
    agent_post_likes: list[dict]
    agent_post_comments: list[dict]
    turn_metrics: list[TurnMetrics]
    run_metrics: list[RunMetrics]
    agents: list[Agent]
    agent_persona_bios: list[AgentBio]
    user_agent_profile_metadata: list[UserAgentProfileMetadata]
    agent_follow_edges: list[AgentFollowEdge]


def _fixtures_digest(fixtures_dir: Path) -> str:
    """Compute a stable sha256 digest over fixture filenames and bytes."""
    hasher = hashlib.sha256()
    paths = sorted(p for p in fixtures_dir.glob("*.json") if p.is_file())
    if not paths:
        raise RuntimeError(f"No seed fixtures found in {fixtures_dir}")
    for path in paths:
        hasher.update(path.name.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def _ensure_seed_meta(conn: sqlite3.Connection) -> None:
    conn.execute(_SEED_META_TABLE_SQL)


def _get_seed_meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute(
        "SELECT value FROM local_seed_meta WHERE key = ?",
        (key,),
    ).fetchone()
    if row is None:
        return None
    return str(row[0])


def _set_seed_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO local_seed_meta (key, value) VALUES (?, ?)",
        (key, value),
    )


def _validate_canonical_ids(
    collection: Iterable[object],
    *,
    attr_name: str,
    source_label: str,
) -> None:
    for item in collection:
        value = getattr(item, attr_name)
        if not is_canonical_agent_id(value):
            msg = f"{source_label} {attr_name} must be canonical 16-char hex: {value!r}"
            raise ValueError(msg)


def _load_fixtures(fixtures_dir: Path) -> SeedFixtures:
    runs, turn_metadata = parse_runs_and_turn_metadata(fixtures_dir)
    agents_raw = read_json_list(fixtures_dir / "agents.json")
    bios_raw = read_json_list(fixtures_dir / "agent_persona_bios.json")
    metadata_raw = read_json_list(fixtures_dir / "user_agent_profile_metadata.json")
    follow_edges_raw = read_json_list(fixtures_dir / "agent_follow_edges.json")
    posts_raw = read_json_list(fixtures_dir / "bluesky_feed_posts.json")
    agent_post_likes_raw = read_json_list(fixtures_dir / "agent_post_likes.json")
    agent_post_comments_raw = read_json_list(fixtures_dir / "agent_post_comments.json")
    feeds_raw = read_json_list(fixtures_dir / "generated_feeds.json")
    agents: list[Agent] = []
    for item in agents_raw:
        agents.append(
            Agent(
                agent_id=str(item["agent_id"]),
                handle=str(item["handle"]),
                persona_source=PersonaSource(str(item["persona_source"])),
                display_name=str(item["display_name"]),
                created_at=str(item["created_at"]),
                updated_at=str(item["updated_at"]),
            )
        )

    bios: list[AgentBio] = []
    for item in bios_raw:
        bios.append(
            AgentBio(
                id=str(item["id"]),
                agent_id=str(item["agent_id"]),
                persona_bio=str(item["persona_bio"]),
                persona_bio_source=PersonaBioSource(str(item["persona_bio_source"])),
                created_at=str(item["created_at"]),
                updated_at=str(item["updated_at"]),
            )
        )
    user_md = [UserAgentProfileMetadata.model_validate(item) for item in metadata_raw]
    follow_edges = [AgentFollowEdge.model_validate(item) for item in follow_edges_raw]

    _validate_canonical_ids(
        agents, attr_name="agent_id", source_label="Seed agents.json"
    )
    _validate_canonical_ids(
        bios,
        attr_name="agent_id",
        source_label="Seed agent_persona_bios.json",
    )
    _validate_canonical_ids(
        user_md,
        attr_name="agent_id",
        source_label="Seed user_agent_profile_metadata.json",
    )
    _validate_canonical_ids(
        follow_edges,
        attr_name="follower_agent_id",
        source_label="Seed agent_follow_edges.json",
    )
    _validate_canonical_ids(
        follow_edges,
        attr_name="target_agent_id",
        source_label="Seed agent_follow_edges.json",
    )
    handle_to_agent_id = {a.handle: a.agent_id for a in agents}
    posts: list[Post] = []
    for item in posts_raw:
        handle = str(item["author_handle"])
        author_agent_id = handle_to_agent_id.get(handle)
        if author_agent_id is None:
            raise ValueError(
                "Seed feed post author_handle "
                f"{handle!r} has no matching agent in agents.json"
            )
        posts.append(
            Post.model_validate(
                {
                    **item,
                    "source": PostSource.BLUESKY,
                    "author_agent_id": author_agent_id,
                }
            )
        )
    feeds = [GeneratedFeed.model_validate(item) for item in feeds_raw]

    turn_metrics, run_metrics = read_seed_metrics(fixtures_dir)

    return SeedFixtures(
        runs=runs,
        turn_metadata=turn_metadata,
        generated_feeds=feeds,
        feed_posts=posts,
        agent_post_likes=agent_post_likes_raw,
        agent_post_comments=agent_post_comments_raw,
        turn_metrics=turn_metrics,
        run_metrics=run_metrics,
        agents=agents,
        agent_persona_bios=bios,
        user_agent_profile_metadata=user_md,
        agent_follow_edges=follow_edges,
    )


def seed_database_from_fixtures_if_needed(
    *, db_path: str, fixtures_dir: Path = FIXTURES_DIR
) -> None:
    """Seed the database at ``db_path`` from ``fixtures_dir`` if not already seeded.

    Does not require ``LOCAL=true``; callers supply an explicit ``db_path``. This
    function assumes Alembic migrations have already been applied to ``db_path``.
    """
    fixtures_dir = fixtures_dir.resolve()
    digest = _fixtures_digest(fixtures_dir)

    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        _ensure_seed_meta(conn)
        existing = _get_seed_meta(conn, "fixtures_sha256")
        if existing == digest:
            logger.info("Seed already applied (fixtures_sha256=%s).", digest)
            return
        if existing is not None and existing != digest:
            logger.warning(
                "Database already seeded with different fixtures (db_path=%s). "
                "existing_fixtures_sha256=%s current_fixtures_sha256=%s. "
                "Refusing to overwrite; run with LOCAL_RESET_DB=1 to reset.",
                db_path,
                existing,
                digest,
            )
            return

        fixtures = _load_fixtures(fixtures_dir)

        run_adapter = SQLiteRunAdapter()
        metrics_adapter = SQLiteMetricsAdapter()
        feed_adapter = SQLiteGeneratedFeedAdapter()
        post_adapter = SQLiteFeedPostAdapter()
        agent_adapter = SQLiteAgentAdapter()
        bio_adapter = SQLiteAgentBioAdapter()
        agent_follow_edge_adapter = SQLiteAgentFollowEdgeAdapter()
        agent_post_like_adapter = SQLiteAgentPostLikeAdapter()
        agent_post_comment_adapter = SQLiteAgentPostCommentAdapter()
        user_md_adapter = SQLiteUserAgentProfileMetadataAdapter()

        now = get_current_timestamp()

        conn.execute("BEGIN")
        try:
            for run in fixtures.runs:
                run_adapter.write_run(run, conn=conn)

            for agent in fixtures.agents:
                agent_adapter.write_agent(agent, conn=conn)
            for bio in fixtures.agent_persona_bios:
                bio_adapter.write_agent_bio(bio, conn=conn)
            for md in fixtures.user_agent_profile_metadata:
                user_md_adapter.write_user_agent_profile_metadata(md, conn=conn)
            for edge in fixtures.agent_follow_edges:
                agent_follow_edge_adapter.write_agent_follow_edge(edge, conn=conn)
            for agent in fixtures.agents:
                user_md_adapter.sync_follow_counts(
                    agent_id=agent.agent_id,
                    followers_count=agent_follow_edge_adapter.count_edges_by_target_agent_id(
                        agent.agent_id,
                        conn=conn,
                    ),
                    follows_count=agent_follow_edge_adapter.count_edges_by_follower_agent_id(
                        agent.agent_id,
                        conn=conn,
                    ),
                    updated_at=now,
                    conn=conn,
                )

            post_adapter.write_feed_posts(fixtures.feed_posts, conn=conn)
            backfill_agent_posts_from_feed_posts(conn=conn, now_timestamp=now)

            if fixtures.agent_post_likes:
                # Resolve liker_agent_id (by agent handle) and agent_post_id (by
                # the (source, source_post_id) pair) after agent_posts backfill.
                liker_handles = [
                    row["liker_handle"] for row in fixtures.agent_post_likes
                ]
                liker_handles = list(dict.fromkeys(liker_handles))
                handle_to_agent = agent_adapter.read_agents_by_handles(
                    liker_handles,
                    conn=conn,
                )

                unique_source_pairs: set[tuple[str, str]] = set()
                for row in fixtures.agent_post_likes:
                    source = str(row["post_source"])
                    source_post_id = str(row["post_source_post_id"])
                    unique_source_pairs.add((source, source_post_id))

                if unique_source_pairs:
                    placeholders = ", ".join("(?, ?)" for _ in unique_source_pairs)
                    params: list[str] = []
                    for source, source_post_id in sorted(unique_source_pairs):
                        params.extend([source, source_post_id])
                    sql = f"SELECT source, source_post_id, agent_post_id FROM agent_posts WHERE (source, source_post_id) IN ({placeholders})"  # noqa: S608  # nosec B608
                    rows = conn.execute(sql, tuple(params)).fetchall()

                    pair_to_agent_post_id = {
                        (str(r["source"]), str(r["source_post_id"])): str(
                            r["agent_post_id"]
                        )
                        for r in rows
                    }

                    missing = unique_source_pairs - set(pair_to_agent_post_id.keys())
                    if missing:
                        raise ValueError(
                            "agent_post_likes fixtures reference missing agent_posts: "
                            + ", ".join(
                                f"(source={s}, source_post_id={sp})"
                                for s, sp in missing
                            )
                        )
                else:
                    pair_to_agent_post_id = {}

                def _deterministic_agent_post_like_id(
                    *, liker_agent_id: str, agent_post_id: str
                ) -> str:
                    digest = hashlib.sha256(
                        f"{liker_agent_id}:{agent_post_id}".encode()
                    ).hexdigest()
                    return f"agent_post_like_import_{digest}"

                resolved_likes: list[AgentPostLike] = []
                for row in fixtures.agent_post_likes:
                    liker_handle = str(row["liker_handle"])
                    if liker_handle not in handle_to_agent:
                        raise ValueError(
                            f"agent_post_likes fixture references unknown liker_handle={liker_handle}"
                        )
                    liker_agent_id = handle_to_agent[liker_handle].agent_id

                    post_source = str(row["post_source"])
                    post_source_post_id = str(row["post_source_post_id"])
                    agent_post_id = pair_to_agent_post_id[
                        (post_source, post_source_post_id)
                    ]

                    resolved_likes.append(
                        AgentPostLike(
                            agent_post_like_id=str(
                                row.get("agent_post_like_id")
                                or _deterministic_agent_post_like_id(
                                    liker_agent_id=liker_agent_id,
                                    agent_post_id=agent_post_id,
                                )
                            ),
                            agent_post_id=agent_post_id,
                            liker_agent_id=liker_agent_id,
                            created_at=str(row.get("created_at") or now),
                        )
                    )

                agent_post_like_adapter.write_agent_post_likes(
                    resolved_likes,
                    conn=conn,
                )

            if fixtures.agent_post_comments:
                author_handles = [
                    str(row["author_handle"]) for row in fixtures.agent_post_comments
                ]
                author_handles = list(dict.fromkeys(author_handles))
                handle_to_agent = agent_adapter.read_agents_by_handles(
                    author_handles,
                    conn=conn,
                )

                unique_source_pairs_comments: set[tuple[str, str]] = set()
                for row in fixtures.agent_post_comments:
                    source = str(row["post_source"])
                    source_post_id = str(row["post_source_post_id"])
                    unique_source_pairs_comments.add((source, source_post_id))

                if unique_source_pairs_comments:
                    placeholders = ", ".join(
                        "(?, ?)" for _ in unique_source_pairs_comments
                    )
                    pair_params: list[str] = []
                    for source, source_post_id in sorted(unique_source_pairs_comments):
                        pair_params.extend([source, source_post_id])
                    sql = f"SELECT source, source_post_id, agent_post_id FROM agent_posts WHERE (source, source_post_id) IN ({placeholders})"  # noqa: S608  # nosec B608
                    rows = conn.execute(sql, tuple(pair_params)).fetchall()
                    pair_to_agent_post_id_c = {
                        (str(r["source"]), str(r["source_post_id"])): str(
                            r["agent_post_id"]
                        )
                        for r in rows
                    }
                    missing_c = unique_source_pairs_comments - set(
                        pair_to_agent_post_id_c.keys()
                    )
                    if missing_c:
                        raise ValueError(
                            "agent_post_comments fixtures reference missing agent_posts: "
                            + ", ".join(
                                f"(source={s}, source_post_id={sp})"
                                for s, sp in missing_c
                            )
                        )
                else:
                    pair_to_agent_post_id_c = {}

                def _deterministic_agent_post_comment_id(
                    *,
                    author_agent_id: str,
                    agent_post_id: str,
                    body_text: str,
                    published_at: str,
                ) -> str:
                    digest = hashlib.sha256(
                        f"{author_agent_id}:{agent_post_id}:{body_text}:{published_at}".encode()
                    ).hexdigest()
                    return f"agent_post_comment_import_{digest}"

                resolved_comments: list[AgentPostComment] = []
                for row in fixtures.agent_post_comments:
                    author_handle = str(row["author_handle"])
                    if author_handle not in handle_to_agent:
                        raise ValueError(
                            "agent_post_comments fixture references unknown author_handle="
                            f"{author_handle}"
                        )
                    author_agent_id = handle_to_agent[author_handle].agent_id
                    post_source = str(row["post_source"])
                    post_source_post_id = str(row["post_source_post_id"])
                    agent_post_id = pair_to_agent_post_id_c[
                        (post_source, post_source_post_id)
                    ]
                    body_text = str(row["body_text"])
                    published_at = str(row.get("published_at") or now)
                    created_at = str(row.get("created_at") or now)
                    updated_at = str(row.get("updated_at") or now)
                    resolved_comments.append(
                        AgentPostComment(
                            agent_post_comment_id=str(
                                row.get("agent_post_comment_id")
                                or _deterministic_agent_post_comment_id(
                                    author_agent_id=author_agent_id,
                                    agent_post_id=agent_post_id,
                                    body_text=body_text,
                                    published_at=published_at,
                                )
                            ),
                            agent_post_id=agent_post_id,
                            author_agent_id=author_agent_id,
                            body_text=body_text,
                            published_at=published_at,
                            created_at=created_at,
                            updated_at=updated_at,
                        )
                    )

                agent_post_comment_adapter.write_agent_post_comments(
                    resolved_comments,
                    conn=conn,
                )

            for tm in fixtures.turn_metadata:
                run_adapter.write_turn_metadata(tm, conn=conn)
            for feed in fixtures.generated_feeds:
                feed_adapter.write_generated_feed(feed, conn=conn)
            for tm in fixtures.turn_metrics:
                metrics_adapter.write_turn_metrics(tm, conn=conn)
            for rm in fixtures.run_metrics:
                metrics_adapter.write_run_metrics(rm, conn=conn)

            _set_seed_meta(conn, "fixtures_sha256", digest)
            _set_seed_meta(conn, "seeded_at", now)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

        logger.info(
            "Seeded database from fixtures. db_path=%s fixtures_sha256=%s",
            db_path,
            digest,
        )
    finally:
        conn.close()


def seed_local_db_if_needed(*, db_path: str, fixtures_dir: Path = FIXTURES_DIR) -> None:
    """Alias for :func:`seed_database_from_fixtures_if_needed` (same behavior).

    Prefer importing :func:`seed_database_from_fixtures_if_needed` for new code.
    """
    seed_database_from_fixtures_if_needed(db_path=db_path, fixtures_dir=fixtures_dir)
