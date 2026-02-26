"""Local-dev seed data loader.

Loads deterministic JSON fixtures into a SQLite database for LOCAL=true workflows.

Seed policy:
- Seed once: if the DB has a matching fixtures digest, do nothing.
- If the DB is already seeded with a different digest, do not overwrite; log a warning
  and instruct the developer to reset via LOCAL_RESET_DB=1.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from db.adapters.sqlite.agent_adapter import SQLiteAgentAdapter
from db.adapters.sqlite.agent_bio_adapter import SQLiteAgentBioAdapter
from db.adapters.sqlite.agent_seed_comment_adapter import SQLiteAgentSeedCommentAdapter
from db.adapters.sqlite.agent_seed_follow_adapter import SQLiteAgentSeedFollowAdapter
from db.adapters.sqlite.agent_seed_like_adapter import SQLiteAgentSeedLikeAdapter
from db.adapters.sqlite.feed_post_adapter import SQLiteFeedPostAdapter
from db.adapters.sqlite.generated_feed_adapter import SQLiteGeneratedFeedAdapter
from db.adapters.sqlite.metrics_adapter import SQLiteMetricsAdapter
from db.adapters.sqlite.run_adapter import SQLiteRunAdapter
from db.adapters.sqlite.user_agent_profile_metadata_adapter import (
    SQLiteUserAgentProfileMetadataAdapter,
)
from lib.timestamp_utils import get_current_timestamp
from simulation.core.models.actions import TurnAction
from simulation.core.models.agent import Agent, PersonaSource
from simulation.core.models.agent_bio import AgentBio, PersonaBioSource
from simulation.core.models.agent_seed_actions import (
    AgentSeedComment,
    AgentSeedFollow,
    AgentSeedLike,
)
from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.metrics import RunMetrics, TurnMetrics
from simulation.core.models.persisted_actions import (
    PersistedComment,
    PersistedFollow,
    PersistedLike,
)
from simulation.core.models.posts import BlueskyFeedPost
from simulation.core.models.runs import Run
from simulation.core.models.turns import TurnMetadata
from simulation.core.models.user_agent_profile_metadata import UserAgentProfileMetadata

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
    feed_posts: list[BlueskyFeedPost]
    turn_metrics: list[TurnMetrics]
    run_metrics: list[RunMetrics]
    agents: list[Agent]
    agent_persona_bios: list[AgentBio]
    user_agent_profile_metadata: list[UserAgentProfileMetadata]
    agent_seed_likes: list[AgentSeedLike]
    agent_seed_comments: list[AgentSeedComment]
    agent_seed_follows: list[AgentSeedFollow]
    likes: list[PersistedLike]
    comments: list[PersistedComment]
    follows: list[PersistedFollow]


def _read_json_list(path: Path) -> list[dict]:
    """Read and validate a fixture file containing a JSON array."""
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError(f"Fixture must be a JSON array: {path}")
    if not all(isinstance(item, dict) for item in data):
        raise ValueError(f"Fixture array must contain objects: {path}")
    return data  # type: ignore[return-value]


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
    """Ensure the local_seed_meta table exists before seeding."""
    conn.execute(_SEED_META_TABLE_SQL)


def _get_seed_meta(conn: sqlite3.Connection, key: str) -> str | None:
    """Return a stored seed metadata value if present."""
    row = conn.execute(
        "SELECT value FROM local_seed_meta WHERE key = ?",
        (key,),
    ).fetchone()
    if row is None:
        return None
    return str(row[0])


def _set_seed_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    """Persist a metadata key/value pair for the local seed."""
    conn.execute(
        "INSERT OR REPLACE INTO local_seed_meta (key, value) VALUES (?, ?)",
        (key, value),
    )


def _load_fixtures(fixtures_dir: Path) -> SeedFixtures:
    """Load all local seed fixtures and convert them into models."""
    runs_raw = _read_json_list(fixtures_dir / "runs.json")
    agents_raw = _read_json_list(fixtures_dir / "agents.json")
    bios_raw = _read_json_list(fixtures_dir / "agent_persona_bios.json")
    metadata_raw = _read_json_list(fixtures_dir / "user_agent_profile_metadata.json")
    agent_seed_likes_raw = _read_json_list(fixtures_dir / "agent_seed_likes.json")
    agent_seed_comments_raw = _read_json_list(fixtures_dir / "agent_seed_comments.json")
    agent_seed_follows_raw = _read_json_list(fixtures_dir / "agent_seed_follows.json")
    posts_raw = _read_json_list(fixtures_dir / "bluesky_feed_posts.json")
    feeds_raw = _read_json_list(fixtures_dir / "generated_feeds.json")
    turn_md_raw = _read_json_list(fixtures_dir / "turn_metadata.json")
    turn_metrics_raw = _read_json_list(fixtures_dir / "turn_metrics.json")
    run_metrics_raw = _read_json_list(fixtures_dir / "run_metrics.json")
    likes_raw = _read_json_list(fixtures_dir / "likes.json")
    comments_raw = _read_json_list(fixtures_dir / "comments.json")
    follows_raw = _read_json_list(fixtures_dir / "follows.json")

    runs = [Run.model_validate(item) for item in runs_raw]
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
    posts = [BlueskyFeedPost.model_validate(item) for item in posts_raw]
    feeds = [GeneratedFeed.model_validate(item) for item in feeds_raw]

    turn_metadata: list[TurnMetadata] = []
    for item in turn_md_raw:
        raw_total_actions = item.get("total_actions", {})
        if not isinstance(raw_total_actions, dict):
            raise ValueError("turn_metadata.total_actions must be an object")
        total_actions = {TurnAction(k): int(v) for k, v in raw_total_actions.items()}
        tm = TurnMetadata(
            run_id=str(item["run_id"]),
            turn_number=int(item["turn_number"]),
            total_actions=total_actions,
            created_at=str(item["created_at"]),
        )
        turn_metadata.append(tm)

    turn_metrics = [TurnMetrics.model_validate(item) for item in turn_metrics_raw]
    run_metrics = [RunMetrics.model_validate(item) for item in run_metrics_raw]

    return SeedFixtures(
        runs=runs,
        turn_metadata=turn_metadata,
        generated_feeds=feeds,
        feed_posts=posts,
        turn_metrics=turn_metrics,
        run_metrics=run_metrics,
        agents=agents,
        agent_persona_bios=bios,
        user_agent_profile_metadata=user_md,
        agent_seed_likes=[
            AgentSeedLike.model_validate(item) for item in agent_seed_likes_raw
        ],
        agent_seed_comments=[
            AgentSeedComment.model_validate(item) for item in agent_seed_comments_raw
        ],
        agent_seed_follows=[
            AgentSeedFollow.model_validate(item) for item in agent_seed_follows_raw
        ],
        likes=[PersistedLike.model_validate(item) for item in likes_raw],
        comments=[PersistedComment.model_validate(item) for item in comments_raw],
        follows=[PersistedFollow.model_validate(item) for item in follows_raw],
    )


def _write_persisted_likes(
    *, conn: sqlite3.Connection, likes: list[PersistedLike]
) -> None:
    """Insert persisted like records into the likes table."""
    if not likes:
        return
    conn.executemany(
        """
        INSERT INTO likes (
            like_id, run_id, turn_number, agent_handle, post_id,
            created_at, explanation, model_used, generation_metadata_json,
            generation_created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                item.like_id,
                item.run_id,
                item.turn_number,
                item.agent_handle,
                item.post_id,
                item.created_at,
                item.explanation,
                item.model_used,
                item.generation_metadata_json,
                item.generation_created_at,
            )
            for item in likes
        ],
    )


def _write_persisted_comments(
    *, conn: sqlite3.Connection, comments: list[PersistedComment]
) -> None:
    """Insert persisted comment records into the comments table."""
    if not comments:
        return
    conn.executemany(
        """
        INSERT INTO comments (
            comment_id, run_id, turn_number, agent_handle, post_id,
            text, created_at, explanation, model_used, generation_metadata_json,
            generation_created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                item.comment_id,
                item.run_id,
                item.turn_number,
                item.agent_handle,
                item.post_id,
                item.text,
                item.created_at,
                item.explanation,
                item.model_used,
                item.generation_metadata_json,
                item.generation_created_at,
            )
            for item in comments
        ],
    )


def _write_persisted_follows(
    *, conn: sqlite3.Connection, follows: list[PersistedFollow]
) -> None:
    """Insert persisted follow records into the follows table."""
    if not follows:
        return
    conn.executemany(
        """
        INSERT INTO follows (
            follow_id, run_id, turn_number, agent_handle, user_id,
            created_at, explanation, model_used, generation_metadata_json,
            generation_created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                item.follow_id,
                item.run_id,
                item.turn_number,
                item.agent_handle,
                item.user_id,
                item.created_at,
                item.explanation,
                item.model_used,
                item.generation_metadata_json,
                item.generation_created_at,
            )
            for item in follows
        ],
    )


def seed_local_db_if_needed(*, db_path: str, fixtures_dir: Path = FIXTURES_DIR) -> None:
    """Seed the database at db_path from fixtures_dir if not already seeded.

    This function assumes Alembic migrations have already been applied to db_path.
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
            logger.info("Local seed already applied (fixtures_sha256=%s).", digest)
            return
        if existing is not None and existing != digest:
            logger.warning(
                "Local DB already seeded with different fixtures. "
                "existing_fixtures_sha256=%s current_fixtures_sha256=%s. "
                "Refusing to overwrite; run with LOCAL_RESET_DB=1 to reset.",
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
        user_md_adapter = SQLiteUserAgentProfileMetadataAdapter()
        seed_like_adapter = SQLiteAgentSeedLikeAdapter()
        seed_comment_adapter = SQLiteAgentSeedCommentAdapter()
        seed_follow_adapter = SQLiteAgentSeedFollowAdapter()

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

            seed_like_adapter.write_agent_seed_likes(
                fixtures.agent_seed_likes,
                conn=conn,
            )
            seed_comment_adapter.write_agent_seed_comments(
                fixtures.agent_seed_comments,
                conn=conn,
            )
            seed_follow_adapter.write_agent_seed_follows(
                fixtures.agent_seed_follows,
                conn=conn,
            )

            post_adapter.write_feed_posts(fixtures.feed_posts, conn=conn)
            for feed in fixtures.generated_feeds:
                feed_adapter.write_generated_feed(feed, conn=conn)
            for tm in fixtures.turn_metadata:
                run_adapter.write_turn_metadata(tm, conn=conn)
            for tm in fixtures.turn_metrics:
                metrics_adapter.write_turn_metrics(tm, conn=conn)
            for rm in fixtures.run_metrics:
                metrics_adapter.write_run_metrics(rm, conn=conn)

            _write_persisted_likes(conn=conn, likes=fixtures.likes)
            _write_persisted_comments(conn=conn, comments=fixtures.comments)
            _write_persisted_follows(conn=conn, follows=fixtures.follows)

            _set_seed_meta(conn, "fixtures_sha256", digest)
            _set_seed_meta(conn, "seeded_at", now)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

        logger.info(
            "Seeded local DB from fixtures. db_path=%s fixtures_sha256=%s",
            db_path,
            digest,
        )
    finally:
        conn.close()
