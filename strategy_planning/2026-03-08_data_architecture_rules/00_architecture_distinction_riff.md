# Architecture Distinction Riff

The cleanest architecture here is to stop thinking in terms of `manual` vs `simulation` and instead think in terms of `seed state` vs `run snapshot` vs `turn events`.

Right now the codebase already implicitly separates long-lived agent data from run-scoped action data. The agent catalog is persistent and global:

```161:203:db/schema.py
agent = sa.Table(
    "agent",
    metadata,
    sa.Column("agent_id", sa.Text(), primary_key=True),
    sa.Column("handle", sa.Text(), nullable=False),
    ...
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
)
```

But likes/comments/follows are modeled as immutable run-turn rows, not editable profile state:

```206:288:db/schema.py
# --- Run-scoped action tables (likes, comments, follows) ---

follows = sa.Table(
    "follows",
    metadata,
    sa.Column("follow_id", sa.Text(), primary_key=True),
    sa.Column("run_id", sa.Text(), nullable=False),
    sa.Column("turn_number", sa.Integer(), nullable=False),
    sa.Column("agent_handle", sa.Text(), nullable=False),
    sa.Column("user_id", sa.Text(), nullable=False),
    ...
    sa.UniqueConstraint(
        "run_id",
        "turn_number",
        "agent_handle",
        "user_id",
        name="uq_follows_run_turn_agent_user",
    ),
)
```

So my recommendation is:

## Core Decision

Use three scopes:

1. `agent_*` = long-lived, editable seed state for an agent profile.
2. `run_*` = immutable snapshot of the seed state used when a run starts.
3. existing `likes/comments/follows` = append-only turn events produced during simulation.

That is a better boundary than `source = manual | simulation` on one table.

Why: your earlier idea of adding a `source` enum to `follows` would work mechanically, but it mixes two different concepts:

- editable baseline state
- generated event history

Those have different lifecycles, constraints, APIs, and query patterns. Also, future seed data may be imported or AI-assisted, not literally “manual”, so `manual` is the wrong abstraction boundary.

## How I’d define the two domains

`manual social graph` should mean: “current editable seed state for an agent before a run starts.”

That includes:
That includes:

- who this agent follows
- eventually authored posts that should exist at initialization
- eventually likes/comments that should already exist before turn 0

`run/turn data` should mean: “what happened during a specific simulation.”

That includes:

- run membership
- initial snapshot used for that run
- per-turn generated likes/comments/follows
- metrics, feeds, summaries

A good rule is:

- If it should still exist when no run exists, it is seed state.
- If changing it later should not rewrite history, it belongs in a run snapshot or turn event table.
- If it has `turn_number`, it is an event, not profile state.

## Important nuance for posts/comments/likes at init time

Follows are easy because they are just edges. Likes/comments are trickier because they target a post.

That leads to an important design rule:

- A pre-run like/comment can only be seed state if it targets a persistent post in the seed layer.
- If it targets a post created during a run, it is necessarily run-scoped.

So if you want “manual likes/comments at init time”, you will eventually need persistent pre-run post records too, not just counts. Otherwise those likes/comments have nothing stable to point at.

## Recommended DB shape

I would codify this direction:

### Seed state tables

- `agent_follow_edges`
- later `agent_posts`
- later `agent_post_likes`
- later `agent_post_comments`

These are the source of truth for editable pre-run state.

For follows, I’d prefer something like:

- `id`
- `follower_agent_id`
- `target_agent_id` nullable
- `target_handle`
- `target_kind` = `agent` | `external_profile`
- `created_at`
- optional provenance fields like `created_by_app_user_id`, `origin`

I would not call the table `manual_follows`. `agent_follow_edges` is better because it describes what it is, not how it was created.

### Run snapshot tables

Not needed for the first UI-only step, but needed before this data affects simulation behavior.

At minimum:

- `run_agents`
- `run_initial_follow_edges`

Later, if posts/comments/likes matter at init:

- `run_initial_posts`
- `run_initial_post_likes`
- `run_initial_post_comments`

This snapshot layer is the key piece missing today. Without it, if you edit an agent’s follows after a run completes, you risk changing the apparent starting state of historical runs.

### Turn event tables

Keep the existing action tables as-is:

- `likes`
- `comments`
- `follows`

They already behave like event logs, and the surrounding code assumes that. The persistence service writes them per turn in one transaction, and the follow repository is explicitly `read_follows_by_run_turn(...)`. That’s exactly the right shape for run events.

## How to make the distinction explicit in docs and code

I’d codify a repo rule like this:

- `agent_*` tables are editable current-state tables.
- `run_*` tables are immutable snapshots taken at run creation.
- `likes/comments/follows` are immutable turn events generated by the simulator.
- UI agent detail pages edit `agent_*`.
- Run history pages read `run_*` and turn event tables.
- Historical runs must never read current `agent_*` directly for behaviorally relevant state.

That one rule will prevent a lot of future confusion.

## What this means for Start Simulation

This ties directly into `Select Agents`.

Today `RunRequest` only stores `num_agents`, not the actual selected identities, and there is no persisted run membership/snapshot yet. So when Start Simulation becomes “select specific agents”, I’d treat that as the moment you formalize run snapshots:

- user selects agents from the global `agent` catalog
- backend writes `run`
- backend writes `run_agents`
- backend snapshots relevant seed state from `agent_*` into `run_*`
- simulation executes
- turn events append to `likes/comments/follows`

That is the durable separation between “what existed at start” and “what happened during the run”.

## What to do with `user_agent_profile_metadata`

I would keep `user_agent_profile_metadata` as a summary table, not the source of truth.

So:

- source of truth for follows: `agent_follow_edges`
- summary/cache: `user_agent_profile_metadata.follows_count` and `followers_count`

When follows are added or removed, update counts transactionally. For internal-agent follow targets, update both sides. For external handles, only the follower’s `follows_count` changes.

Same idea later for `posts_count`.

## Proposed architecture doc

I’d add something like `docs/architecture/agent-seed-state-vs-run-data.md`.

Suggested sections:

- Purpose
- Definitions
  - seed state
  - run snapshot
  - turn event
- Current state in repo
- Decision
- Database conventions
- API conventions
- Start Simulation implications
- Future extensions for posts/comments/likes
- Non-goals

If you want, I can draft the exact markdown for that file next, including the concrete table naming and a phased rollout plan that matches your PR sequencing.
