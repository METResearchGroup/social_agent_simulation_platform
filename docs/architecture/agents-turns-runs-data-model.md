# Agents, Turns, and Runs

We have mental models around the concepts of `Agent*`, `Turn*`, and `Run*`. This doc helps differentiate these concepts.

## What are these concepts?

### What is `Agent*`?

`Agent*` refers to what exists before a run starts. This is the "seed state", the data that app users can choose to include in a simulation run. This can be edited and changed over time, so that, for example, the traits for Agent A today and six months from now will be different. This is discussed more in the `run-snapshots.md` document.

The tables here include:

- `agent`: canonical pre-run agent identity: agent_id, handle, display_name, etc.
- `agent_persona_bios`: pre-run persona/bio rows attached to an agent
- `user_agent_profile_metadata`: pre-run summary/cache counts for an agent: followers_count, follows_count, posts_count. Important nuance: this is a cache/summary, not the source of truth for edges/posts.
- `agent_follow_edges`: pre-run follow graph between agents
- `agent_posts`: pre-run posts belonging to an agent
- `agent_post_likes`: pre-run likes on posts (and which agents made those likes).
- `agent_post_comments`: pre-run comments on posts (and which agents made those posts).

### What is `Turn*`?

`Turn*` refers to the per-turn history of what happened during a simulation run.

This is a **conceptual scope**, not only a naming convention. Some tables in this scope are literally prefixed `turn_*`, while others are legacy-named event tables that still belong to the same lifecycle.

The key question answered by `Turn*` data is:

- "What happened during turn N of this run?"
This scope includes a few kinds of per-turn data:
- per-turn summaries, such as aggregate counts or metadata for a turn
- per-turn metrics
- per-turn generated outputs, such as feeds shown to agents during that turn
- per-turn action logs, such as likes, comments, and follows produced during that turn

The important invariant is lifecycle:

- if the row is an append-only output of a specific run and turn, it belongs to the `Turn*` scope
- if the row should exist before a run starts, it does **not** belong to `Turn*`
- if the row describes what was true at the start of a run, it belongs to `Run*Snapshot`, not `Turn*`

TODO: migrate all Turn tables to use the `turn_*` nomenclature.

### What is `Run*`?

We have 3 related `Run*` concepts:

#### Run records

This tells us "what run is this?". This information is in the `runs` table.

#### Run-start snapshot

This pertains to "what was true when the run began". We discuss this in more depth in `run-snapshots.md`.

These tables include:

- `run_agents`
- `run_follow_edges`
- `run_posts`
- `run_post_likes`
- `run_post_comments`

#### Run-level derived summaries

These answer questions about the run **as a whole**, rather than about the run's initial state or about any specific turn. This category is for derived outputs that are computed from the run and persisted at run scope.

They are:

- not the run record itself
- not part of `Run*Snapshot`
- not tied to a single turn
A useful way to think about them is:
- `runs` tells us **what run this is**
- `Run*Snapshot` tells us **what was true when the run began**
- `Turn*` tells us **what happened during each turn**
- run-level derived summaries tell us **what we concluded about the run overall**
Today, the clearest example of this category is run-level metrics computed across the full run.

## "Happy Flow"

### During a simulation

1. Choose participants + social network + base pool of posts from global `Agent*` catalog.
2. Create an entry in `runs` and snapshot the relevant inputs to a given run in `Run*Snapshot`.
3. Execute each of the turns. Append to the `Turn*` tables along the way. 4. Update the entry in `runs` when a run is finished.

### When replaying what happened during a simulation

1. Get the run that we're interested in, from `runs`.
2. Get the corresponding `Run*Snapshot` records, so we know the state of each of the inputs to the run.
3. Get the `Turn*` values for the given run.
4. Reconstruct the run.

### When updating the information about an agent

We can have, say, Agent A. We might want to update some information about that agent (e.g., who that agent follows, what posts they've written) before the next simulation run. In the current setup:

- `Agent*` affects only future runs.
- `Run*Snapshot` preserves the truth for past runs.

So if you edit an agent today:

- `agent_follow_edges`, `agent_posts`, `agent_persona_bios`, and `user_agent_profile_metadata` may all change.
- but an old run’s `run_agents`, `run_follow_edges`, `run_posts`, and `run_post_likes` should remain unchanged

That is why historical reads should use `Run*Snapshot`, not live `Agent*`.

Some `Run*` tables still keep a pointer back to live seed rows, for example `run_posts.agent_post_id` and `run_agents.agent_id`. That linkage is useful for provenance, debugging, and traceability, but it should not change the interpretation of history. The authoritative historical values are the denormalized `*_at_start` columns.

So the correct reasoning is:

- link back to `Agent*` for lineage.
- read `Run*Snapshot` for historical truth.

## Core invariants to maintain

- If something must exist outside of the context of a run, it's maintained in `Agent*` (for example, seed data).
- If we need to know what the state of a run was at the start (for historical replay), it needs to be in `Run*Snapshot`.
- If it's related to what happens during a turn, it must be in `Turn*`.

Structural expectations:

- `agent_*` tables should not carry run_id/turn_number
- `run_*` tables should include run_id
- `turn_* / turn-event` tables should include both run_id and non-null turn_number.

## Supporting data outside this taxonomy

Not every persisted table in the repository belongs to the `Agent*` / `Run*` / `Turn*` model.

This taxonomy is specifically for **simulation state and simulation history**. Some tables exist for adjacent concerns and should not be forced into one of these three buckets.

Examples of supporting or out-of-scope data include:

- app/auth records
- ingest or import catalogs
- enrichment tables
- other operational or auxiliary data that supports the simulation platform without being part of simulation lifecycle state

These tables may still relate to the simulation system, but they do not represent:

- pre-run seed state
- frozen start-of-run state
- append-only per-turn run history

The rule is:

- use the `Agent*` / `Run*` / `Turn*` taxonomy for simulation lifecycle data
- do not force unrelated supporting tables into the taxonomy just for naming consistency
