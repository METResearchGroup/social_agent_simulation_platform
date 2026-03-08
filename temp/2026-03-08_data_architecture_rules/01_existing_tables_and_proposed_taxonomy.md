# Existing Tables And Proposed Taxonomy

At schema `HEAD`, you effectively have **15 tables**, and they already fall into a few distinct worlds even if the names are not yet fully normalized.

## Current Tables

| Scope | Tables | What they are |
|---|---|---|
| App/auth | `app_users` | App-level authenticated users |
| External ingest / legacy seed data | `bluesky_profiles`, `bluesky_feed_posts`, `agent_bios` | Imported Bluesky data plus an older generated-bio table |
| Current agent catalog | `agent`, `agent_persona_bios`, `user_agent_profile_metadata` | The newer user-editable agent system |
| Run / turn execution | `runs`, `turn_metadata`, `turn_metrics`, `run_metrics`, `generated_feeds`, `likes`, `comments`, `follows` | Immutable simulation execution data |

The two most important “current-state” clusters are already visible in the schema:

```161:203:db/schema.py
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
    ...
    sa.ForeignKeyConstraint(
        ["agent_id"], ["agent.agent_id"], name="fk_agent_persona_bios_agent_id"
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
    ...
    sa.ForeignKeyConstraint(
        ["agent_id"],
        ["agent.agent_id"],
        name="fk_user_agent_profile_metadata_agent_id",
    ),
)
```

And the run-scoped execution side is also already explicit:

```34:121:db/schema.py
runs = sa.Table(
    "runs",
    metadata,
    sa.Column("run_id", sa.Text(), primary_key=True),
    sa.Column("app_user_id", sa.Text(), nullable=True),
    sa.Column("created_at", sa.Text(), nullable=False),
    sa.Column("total_turns", sa.Integer(), nullable=False),
    sa.Column("total_agents", sa.Integer(), nullable=False),
    ...
)

turn_metadata = sa.Table(
    "turn_metadata",
    metadata,
    sa.Column("run_id", sa.Text(), nullable=False),
    sa.Column("turn_number", sa.Integer(), nullable=False),
    ...
    sa.ForeignKeyConstraint(["run_id"], ["runs.run_id"], name="fk_turn_metadata_run_id"),
)

turn_metrics = sa.Table(
    "turn_metrics",
    metadata,
    sa.Column("run_id", sa.Text(), nullable=False),
    sa.Column("turn_number", sa.Integer(), nullable=False),
    ...
)

run_metrics = sa.Table(
    "run_metrics",
    metadata,
    sa.Column("run_id", sa.Text(), nullable=False),
    ...
)

generated_feeds = sa.Table(
    "generated_feeds",
    metadata,
    sa.Column("feed_id", sa.Text(), nullable=False),
    sa.Column("run_id", sa.Text(), nullable=False),
    sa.Column("turn_number", sa.Integer(), nullable=False),
    sa.Column("agent_handle", sa.Text(), nullable=False),
    sa.Column("post_uris", sa.Text(), nullable=False),
    ...
)
```

And your follow/like/comment tables are already semantically turn-event tables, even if they are not prefixed `turn_`:

```206:288:db/schema.py
likes = sa.Table(
    "likes",
    metadata,
    sa.Column("like_id", sa.Text(), primary_key=True),
    sa.Column("run_id", sa.Text(), nullable=False),
    sa.Column("turn_number", sa.Integer(), nullable=False),
    sa.Column("agent_handle", sa.Text(), nullable=False),
    sa.Column("post_id", sa.Text(), nullable=False),
    ...
)

comments = sa.Table(
    "comments",
    metadata,
    sa.Column("comment_id", sa.Text(), primary_key=True),
    sa.Column("run_id", sa.Text(), nullable=False),
    sa.Column("turn_number", sa.Integer(), nullable=False),
    sa.Column("agent_handle", sa.Text(), nullable=False),
    sa.Column("post_id", sa.Text(), nullable=False),
    ...
)

follows = sa.Table(
    "follows",
    metadata,
    sa.Column("follow_id", sa.Text(), primary_key=True),
    sa.Column("run_id", sa.Text(), nullable=False),
    sa.Column("turn_number", sa.Integer(), nullable=False),
    sa.Column("agent_handle", sa.Text(), nullable=False),
    sa.Column("user_id", sa.Text(), nullable=False),
    ...
)
```

## How They Relate Today

Here is the actual enforced relationship graph:

- `agent_persona_bios.agent_id -> agent.agent_id`
- `user_agent_profile_metadata.agent_id -> agent.agent_id`
- `turn_metadata.run_id -> runs.run_id`
- `turn_metrics.run_id -> runs.run_id`
- `run_metrics.run_id -> runs.run_id`
- `generated_feeds.run_id -> runs.run_id`
- `likes.run_id -> runs.run_id`
- `comments.run_id -> runs.run_id`
- `follows.run_id -> runs.run_id`

Just as important are the **logical relationships that are not FK-enforced yet**:

- `runs.app_user_id` clearly points at `app_users.id`, but there is no DB FK.
- `generated_feeds.agent_handle` logically points at an agent, but there is no FK.
- `likes.agent_handle`, `comments.agent_handle`, `follows.agent_handle` logically point at an agent, but there is no FK.
- `likes.post_id` and `comments.post_id` logically point at posts, but there is no FK.
- `follows.user_id` is a free-form target, not a normalized edge to `agent`.

That means the current DB already separates **run identity** from **agent identity**, but it does **not** yet have a normalized, durable “social graph” layer.

You can also see the separation in the read side:

- `list_agents()` hydrates from `agent` + latest bio + metadata counts.
- `get_run_details()` hydrates from `runs` + turn/run metrics.
- `get_turns_for_run()` hydrates from turn metadata + generated feeds and currently returns empty `agent_actions`.

```15:86:simulation/api/services/agent_query_service.py
def list_agents(...):
    ...
    bio_map = bio_repo.get_latest_bios_by_agent_ids(agent_ids)
    metadata_map = metadata_repo.get_metadata_by_agent_ids(agent_ids)
    ...
    return AgentSchema(
        handle=agent.handle,
        name=agent.display_name,
        bio=persona_bio,
        generated_bio="",
        followers=followers,
        following=follows,
        posts_count=posts_count,
    )
```

```42:77:simulation/api/services/run_query_service.py
def get_turns_for_run(*, run_id: str, engine: SimulationEngine) -> dict[str, TurnSchema]:
    ...
    for item in metadata_sorted:
        feeds = engine.read_feeds_for_turn(validated_run_id, item.turn_number)
        ...
        turns[str(item.turn_number)] = TurnSchema(
            turn_number=item.turn_number,
            agent_feeds=agent_feeds,
            agent_actions={},
        )
```

## The Clean Model To Move Toward

I would formalize three scopes:

- `agent_*` = editable, current seed state
- `run_*` = immutable snapshot of seed state captured when a run starts
- `turn_*` = immutable execution outputs during the run

And I would **not** force a rename of existing `likes/comments/follows` just for naming purity. Their semantics are already `turn_*`; document that and move forward.

## Tables I’d Add

### `agent_*` tables

These are the source of truth for “what exists before simulation starts”.

- `agent_follow_edges`
- `agent_posts`
- `agent_post_likes`
- `agent_post_comments`

If you want external, non-agent handles in follows, `agent_follow_edges` should probably look like:

- `id`
- `follower_agent_id`
- `target_agent_id` nullable
- `target_handle`
- `target_kind` = `agent` | `external_profile`
- `created_at`
- optional `created_by_app_user_id`
- optional `updated_at` only if you expect edits on the row itself

My strongest recommendation: use `agent_id` as the internal FK anchor, not `handle`, because handles are display identifiers and may become mutable or normalized differently later.

### `run_*` tables

These are the missing piece today. They matter as soon as “Select Agents” becomes real and runs must preserve historical start state.

Minimum useful set:

- `run_agents`
- `run_follow_edges`

Likely eventual set:

- `run_agents`
- `run_follow_edges`
- `run_posts`
- `run_post_likes`
- `run_post_comments`

`run_agents` is essential. Without it, a run only knows `total_agents`, not *which* agents participated.

I would also consider storing a denormalized snapshot in `run_agents` so history is stable even if the underlying agent later changes:

- `run_id`
- `agent_id`
- `handle_at_start`
- `display_name_at_start`
- `persona_bio_at_start`
- `followers_count_at_start`
- `follows_count_at_start`
- `posts_count_at_start`

Then the relationship is:

- `agent_*` is live current state
- `run_*` is historical frozen state
- turn events append on top of that snapshot

### `turn_*` tables

You already have most of these semantically:

- `turn_metadata`
- `turn_metrics`
- `generated_feeds`
- `likes`
- `comments`
- `follows`

Future likely addition if agents can author new posts during simulation:

- `turn_posts`

That one is worth calling out: right now your simulation persists likes/comments/follows as actions, but **not posts as run events**. If you later want “an agent creates a post during turn 4”, you’ll want a true turn-scoped post table.

## Recommended Boundaries

I’d write the architecture rule like this:

- `agent_*` tables are mutable current-state tables.
- `run_*` tables are immutable snapshots created at run start.
- `turn_*` tables and existing event tables (`likes/comments/follows`) are immutable execution logs.
- Historical run queries must not derive behaviorally relevant state from current `agent_*` tables.
- Do not mix scopes inside one table with nullable `run_id` / `turn_number` or a `source` enum.

That last point is the big one. I would explicitly ban the “one table with `source = manual | simulation`” approach in `docs/RULES.md`.

## The Biggest Design Constraint

For init-time likes/comments, you need init-time posts first.

So the dependency order is:

1. `agent_follow_edges`
2. `agent_posts`
3. `agent_post_likes`
4. `agent_post_comments`

Because likes/comments cannot exist meaningfully without a stable post target.

That is why follows are the right first feature. They do not need another seed table to be coherent.

## Suggested Docs Shape

I would keep this very simple at first.

### Option A: one canonical architecture doc

Use one file first:

- `docs/architecture/seed-state-run-snapshot-turn-events.md`

Suggested outline:

1. Problem statement
2. Existing tables and current schema reality
3. Canonical scopes: `agent_*`, `run_*`, `turn_*`
4. Naming rules
5. Allowed relationships between scopes
6. Tables by scope
7. Data lifecycle: edit agent -> start run -> execute turns -> read history
8. Non-goals
9. Migration / rollout plan

### Option B: small architecture section

If you expect more docs soon:

- `docs/architecture/README.md`
- `docs/architecture/data-scopes.md`
- `docs/architecture/social-graph.md`
- `docs/architecture/run-snapshots.md`

I would start with Option A unless you already know you’ll write several architecture docs soon.

## What To Add To `docs/RULES.md`

A new section like `Persistence scopes` would be enough.

I’d add rules along these lines:

- Use `agent_*` for editable current-state simulation seed data.
- Use `run_*` for immutable snapshots captured at run creation.
- Use `turn_*` and event tables for immutable execution outputs.
- Do not overload one table to hold both seed state and run/turn state.
- Do not make `run_id` or `turn_number` nullable just to mix scopes.
- Prefer `agent_id` FKs for current-state tables; use handles only as denormalized display data or external targets.
- Historical run APIs must read from `run_*` and turn/event tables, not live `agent_*`.

## What To Enforce With Linters

You already have `scripts/lint_architecture.py`, so I would extend that pattern rather than invent a completely different enforcement model.

### Good next lints

- `SCHEMA-1`: `agent_*` tables must not contain `run_id` or `turn_number`.
- `SCHEMA-2`: `run_*` and turn-event tables must include `run_id`.
- `SCHEMA-3`: turn-event tables must include non-null `turn_number`.
- `SCHEMA-4`: `agent_*` tables should FK to `agent.agent_id` where applicable.
- `SCHEMA-5`: forbid `source` enum fields on mixed-lifecycle tables unless explicitly allowlisted.
- `PY-10`: run query/command services must not import `agent_*` repositories for historical reads.
- `PY-11`: agent edit/query services must not import run event repositories unless explicitly allowlisted.
- `PY-12`: no writes to turn-event tables outside the simulation execution/persistence path.

### Implementation shape

I’d split enforcement into two scripts:

- keep `scripts/lint_architecture.py` for Python import / DI / service boundary rules
- add `scripts/lint_schema_conventions.py` for `db/schema.py` conventions

`lint_schema_conventions.py` can import `db.schema.metadata` and mechanically inspect:

- table names
- columns
- nullability
- FK targets
- presence/absence of `run_id`, `turn_number`, `agent_id`

That will be much more robust than regexing SQLAlchemy source text.

## My Recommended Concrete Next Step

If you want the smallest, highest-value architecture plan, I would declare:

1. `agent_follow_edges` is the next new table.
2. `run_agents` is the next required run-snapshot table once “Select Agents” lands.
3. `run_follow_edges` is the first run snapshot derived from agent seed state.
4. Existing `follows` remains a turn-event table and is not reused for manual state.
5. `agent_posts` is a prerequisite before any init-time likes/comments work.

That gives you a clean ladder instead of trying to solve the full social model in one move.

If you want, I can next draft the exact content for `docs/architecture/seed-state-run-snapshot-turn-events.md` and a companion `docs/RULES.md` section in final prose form.
