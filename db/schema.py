"""SQLAlchemy schema definitions for Alembic migrations.

This project uses sqlite3 directly at runtime (see `db/adapters/sqlite/*`), but Alembic
needs SQLAlchemy `MetaData` to support autogenerate and to serve as a schema
source-of-truth for migrations.

Important:
- Keep this schema aligned with what migrations produce at HEAD.
- The initial migration in this repo intentionally omits the
  `generated_feeds.run_id -> runs.run_id` foreign key; a later migration adds it.
"""

from __future__ import annotations

import sqlalchemy as sa

metadata = sa.MetaData()


# --- Core tables ---

runs = sa.Table(
    "runs",
    metadata,
    sa.Column("run_id", sa.Text(), primary_key=True),
    sa.Column("created_at", sa.Text(), nullable=False),
    sa.Column("total_turns", sa.Integer(), nullable=False),
    sa.Column("total_agents", sa.Integer(), nullable=False),
    sa.Column(
        "feed_algorithm",
        sa.Text(),
        nullable=False,
        server_default=sa.text("'chronological'"),
    ),
    sa.Column("metric_keys", sa.Text(), nullable=True),
    sa.Column("started_at", sa.Text(), nullable=False),
    sa.Column("status", sa.Text(), nullable=False),
    sa.Column("completed_at", sa.Text(), nullable=True),
    sa.CheckConstraint("total_turns > 0", name="ck_runs_total_turns_gt_0"),
    sa.CheckConstraint("total_agents > 0", name="ck_runs_total_agents_gt_0"),
    sa.CheckConstraint(
        "status IN ('running', 'completed', 'failed')", name="ck_runs_status_valid"
    ),
    sa.CheckConstraint(
        "("
        "(status = 'completed' AND completed_at IS NOT NULL AND completed_at >= started_at)"
        " OR "
        "(status != 'completed' AND completed_at IS NULL)"
        ")",
        name="ck_runs_completed_at_consistent",
    ),
)

turn_metadata = sa.Table(
    "turn_metadata",
    metadata,
    sa.Column("run_id", sa.Text(), nullable=False),
    sa.Column("turn_number", sa.Integer(), nullable=False),
    sa.Column("total_actions", sa.Text(), nullable=False),
    sa.Column("created_at", sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(
        ["run_id"], ["runs.run_id"], name="fk_turn_metadata_run_id"
    ),
    sa.CheckConstraint("turn_number >= 0", name="ck_turn_metadata_turn_number_gte_0"),
    sa.PrimaryKeyConstraint("run_id", "turn_number", name="pk_turn_metadata"),
)

turn_metrics = sa.Table(
    "turn_metrics",
    metadata,
    sa.Column("run_id", sa.Text(), nullable=False),
    sa.Column("turn_number", sa.Integer(), nullable=False),
    sa.Column("metrics", sa.Text(), nullable=False),
    sa.Column("created_at", sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(["run_id"], ["runs.run_id"], name="fk_turn_metrics_run_id"),
    sa.CheckConstraint("turn_number >= 0", name="ck_turn_metrics_turn_number_gte_0"),
    sa.PrimaryKeyConstraint("run_id", "turn_number", name="pk_turn_metrics"),
)

run_metrics = sa.Table(
    "run_metrics",
    metadata,
    sa.Column("run_id", sa.Text(), nullable=False),
    sa.Column("metrics", sa.Text(), nullable=False),
    sa.Column("created_at", sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(["run_id"], ["runs.run_id"], name="fk_run_metrics_run_id"),
    sa.PrimaryKeyConstraint("run_id", name="pk_run_metrics"),
)

generated_feeds = sa.Table(
    "generated_feeds",
    metadata,
    sa.Column("feed_id", sa.Text(), nullable=False),
    sa.Column("run_id", sa.Text(), nullable=False),
    sa.Column("turn_number", sa.Integer(), nullable=False),
    sa.Column("agent_handle", sa.Text(), nullable=False),
    sa.Column("post_uris", sa.Text(), nullable=False),
    sa.Column("created_at", sa.Text(), nullable=False),
    # NOTE: This FK is applied by the second Alembic migration.
    sa.ForeignKeyConstraint(
        ["run_id"],
        ["runs.run_id"],
        name="fk_generated_feeds_run_id",
    ),
    sa.PrimaryKeyConstraint(
        "agent_handle", "run_id", "turn_number", name="pk_generated_feeds"
    ),
)


# --- Data ingest / enrichment tables ---

bluesky_profiles = sa.Table(
    "bluesky_profiles",
    metadata,
    sa.Column("handle", sa.Text(), primary_key=True),
    sa.Column("did", sa.Text(), nullable=False),
    sa.Column("display_name", sa.Text(), nullable=False),
    sa.Column("bio", sa.Text(), nullable=False),
    sa.Column("followers_count", sa.Integer(), nullable=False),
    sa.Column("follows_count", sa.Integer(), nullable=False),
    sa.Column("posts_count", sa.Integer(), nullable=False),
)

bluesky_feed_posts = sa.Table(
    "bluesky_feed_posts",
    metadata,
    sa.Column("uri", sa.Text(), primary_key=True),
    sa.Column("author_display_name", sa.Text(), nullable=False),
    sa.Column("author_handle", sa.Text(), nullable=False),
    sa.Column("text", sa.Text(), nullable=False),
    sa.Column("bookmark_count", sa.Integer(), nullable=False),
    sa.Column("like_count", sa.Integer(), nullable=False),
    sa.Column("quote_count", sa.Integer(), nullable=False),
    sa.Column("reply_count", sa.Integer(), nullable=False),
    sa.Column("repost_count", sa.Integer(), nullable=False),
    sa.Column("created_at", sa.Text(), nullable=False),
)

agent_bios = sa.Table(
    "agent_bios",
    metadata,
    sa.Column("handle", sa.Text(), primary_key=True),
    sa.Column("generated_bio", sa.Text(), nullable=False),
    sa.Column("created_at", sa.Text(), nullable=False),
)

agent = sa.Table(
    "agent",
    metadata,
    sa.Column("agent_id", sa.Text(), primary_key=True),
    sa.Column("handle", sa.Text(), nullable=False),
    sa.Column("persona_source", sa.Text(), nullable=False),
    sa.Column("display_name", sa.Text(), nullable=False),
    sa.Column("created_at", sa.Text(), nullable=False),
    sa.Column("updated_at", sa.Text(), nullable=False),
    sa.UniqueConstraint("handle", name="uq_agent_handle"),
)

agent_persona_bios = sa.Table(
    "agent_persona_bios",
    metadata,
    sa.Column("id", sa.Text(), primary_key=True),
    sa.Column("agent_id", sa.Text(), nullable=False),
    sa.Column("persona_bio", sa.Text(), nullable=False),
    sa.Column("persona_bio_source", sa.Text(), nullable=False),
    sa.Column("created_at", sa.Text(), nullable=False),
    sa.Column("updated_at", sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(
        ["agent_id"], ["agent.agent_id"], name="fk_agent_persona_bios_agent_id"
    ),
)

agent_generated_bios = sa.Table(
    "agent_generated_bios",
    metadata,
    sa.Column("id", sa.Text(), primary_key=True),
    sa.Column("agent_id", sa.Text(), nullable=False),
    sa.Column("generated_bio", sa.Text(), nullable=False),
    sa.Column("model_used", sa.Text(), nullable=True),
    sa.Column("generation_metadata_json", sa.Text(), nullable=True),
    sa.Column("created_at", sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(
        ["agent_id"], ["agent.agent_id"], name="fk_agent_generated_bios_agent_id"
    ),
)

user_agent_profile_metadata = sa.Table(
    "user_agent_profile_metadata",
    metadata,
    sa.Column("id", sa.Text(), primary_key=True),
    sa.Column("agent_id", sa.Text(), nullable=False),
    sa.Column("followers_count", sa.Integer(), nullable=False),
    sa.Column("follows_count", sa.Integer(), nullable=False),
    sa.Column("posts_count", sa.Integer(), nullable=False),
    sa.Column("created_at", sa.Text(), nullable=False),
    sa.Column("updated_at", sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(
        ["agent_id"],
        ["agent.agent_id"],
        name="fk_user_agent_profile_metadata_agent_id",
    ),
    sa.UniqueConstraint("agent_id", name="uq_user_agent_profile_metadata_agent_id"),
)


# --- Run-scoped action tables (likes, comments, follows) ---

likes = sa.Table(
    "likes",
    metadata,
    sa.Column("like_id", sa.Text(), primary_key=True),
    sa.Column("run_id", sa.Text(), nullable=False),
    sa.Column("turn_number", sa.Integer(), nullable=False),
    sa.Column("agent_handle", sa.Text(), nullable=False),
    sa.Column("post_id", sa.Text(), nullable=False),
    sa.Column("created_at", sa.Text(), nullable=False),
    sa.Column("explanation", sa.Text(), nullable=True),
    sa.Column("model_used", sa.Text(), nullable=True),
    sa.Column("generation_metadata_json", sa.Text(), nullable=True),
    sa.Column("generation_created_at", sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(["run_id"], ["runs.run_id"], name="fk_likes_run_id"),
    sa.CheckConstraint("turn_number >= 0", name="ck_likes_turn_number_gte_0"),
    # Within a single run+turn, an agent can like a given post at most once.
    # The domain validator tries to prevent duplicates, but this is the persistence
    # backstop that guarantees we never store duplicate likes for the same target.
    sa.UniqueConstraint(
        "run_id",
        "turn_number",
        "agent_handle",
        "post_id",
        name="uq_likes_run_turn_agent_post",
    ),
)

comments = sa.Table(
    "comments",
    metadata,
    sa.Column("comment_id", sa.Text(), primary_key=True),
    sa.Column("run_id", sa.Text(), nullable=False),
    sa.Column("turn_number", sa.Integer(), nullable=False),
    sa.Column("agent_handle", sa.Text(), nullable=False),
    sa.Column("post_id", sa.Text(), nullable=False),
    sa.Column("text", sa.Text(), nullable=False),
    sa.Column("created_at", sa.Text(), nullable=False),
    sa.Column("explanation", sa.Text(), nullable=True),
    sa.Column("model_used", sa.Text(), nullable=True),
    sa.Column("generation_metadata_json", sa.Text(), nullable=True),
    sa.Column("generation_created_at", sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(["run_id"], ["runs.run_id"], name="fk_comments_run_id"),
    sa.CheckConstraint("turn_number >= 0", name="ck_comments_turn_number_gte_0"),
    # Within a single run+turn, an agent can comment on a given post at most once.
    # This matches the current action rules validator (duplicates rejected) and ensures the
    # DB cannot accumulate duplicate per-target comments for the same turn.
    sa.UniqueConstraint(
        "run_id",
        "turn_number",
        "agent_handle",
        "post_id",
        name="uq_comments_run_turn_agent_post",
    ),
)

follows = sa.Table(
    "follows",
    metadata,
    sa.Column("follow_id", sa.Text(), primary_key=True),
    sa.Column("run_id", sa.Text(), nullable=False),
    sa.Column("turn_number", sa.Integer(), nullable=False),
    sa.Column("agent_handle", sa.Text(), nullable=False),
    sa.Column("user_id", sa.Text(), nullable=False),
    sa.Column("created_at", sa.Text(), nullable=False),
    sa.Column("explanation", sa.Text(), nullable=True),
    sa.Column("model_used", sa.Text(), nullable=True),
    sa.Column("generation_metadata_json", sa.Text(), nullable=True),
    sa.Column("generation_created_at", sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(["run_id"], ["runs.run_id"], name="fk_follows_run_id"),
    sa.CheckConstraint("turn_number >= 0", name="ck_follows_turn_number_gte_0"),
    # Within a single run+turn, an agent can follow a given user at most once.
    # This prevents duplicate follow actions for the same target and keeps persistence aligned with
    # the validator/history checks that treat "followed" as a boolean relationship.
    sa.UniqueConstraint(
        "run_id",
        "turn_number",
        "agent_handle",
        "user_id",
        name="uq_follows_run_turn_agent_user",
    ),
)


# --- Indexes (match current SQLite schema) ---

sa.Index("idx_runs_status", runs.c.status)
sa.Index("idx_runs_created_at", runs.c.created_at.desc())
sa.Index("idx_bluesky_feed_posts_author_handle", bluesky_feed_posts.c.author_handle)
sa.Index("idx_turn_metadata_run_id", turn_metadata.c.run_id)
sa.Index("idx_turn_metrics_run_id", turn_metrics.c.run_id)
sa.Index(
    "idx_agent_persona_bios_agent_id_created_at",
    agent_persona_bios.c.agent_id,
    agent_persona_bios.c.created_at.desc(),
)
sa.Index(
    "idx_agent_generated_bios_agent_id_created_at",
    agent_generated_bios.c.agent_id,
    agent_generated_bios.c.created_at.desc(),
)
sa.Index(
    "idx_likes_run_turn_agent",
    likes.c.run_id,
    likes.c.turn_number,
    likes.c.agent_handle,
)
sa.Index(
    "idx_comments_run_turn_agent",
    comments.c.run_id,
    comments.c.turn_number,
    comments.c.agent_handle,
)
sa.Index(
    "idx_follows_run_turn_agent",
    follows.c.run_id,
    follows.c.turn_number,
    follows.c.agent_handle,
)
