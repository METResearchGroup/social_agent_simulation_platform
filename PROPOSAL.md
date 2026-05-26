# Proposal: Local `simulation_v2` Architecture

## Proposed File Structure

The implementation should keep the public entryway the same:

```bash
PYTHONPATH=. uv run python simulation_v2/main.py
```

`simulation_v2/main.py` should still simulate a run from a base set of posts, but internally it should route through a local version of the architecture in `architecture.md`: local control plane, local dispatch, local execution plane, SQLite persistence, turn-level orchestration, and plugin-style evals.

Only `simulation_v2/` should contain runtime code. The only repo-local imports from outside `simulation_v2` should be:

- `lib/load_env_vars.py` for the OpenAI key.
- `lib/timestamp_utils.py` for timestamps.

Proposed target structure:

```text
simulation_v2/
  main.py                              # existing entryway; parses local config and starts one run
  config.py                            # new: local run/feed/LLM/action/eval config models
  ids.py                               # new: small UUID helpers for run/turn/action/feed IDs
  time.py                              # new: wrapper around lib.timestamp_utils
  logging_config.py                    # existing; keep local logging setup

  control_plane/
    __init__.py                        # new
    service.py                         # new: create/read runs and local run requests
    dispatcher.py                      # new: in-process dispatch; no queue, no AWS

  worker/
    __init__.py                        # new
    service.py                         # new: executes one run job
    run_executor.py                    # new: run-level loop and run status transitions
    turn_executor.py                   # new: turn-level pipeline
    state.py                           # new: turn snapshot and in-memory pending diffs

  db/
    __init__.py                        # new
    connection.py                      # new: sqlite3 connection factory and transaction helper
    schema.py                          # new: creates local SQLite tables and indexes
    database.py                        # new: thin facade exposing repositories
    repositories.py                    # new: explicit read/write methods grouped by entity
    models/
      __init__.py                      # new
      actions.py                       # new: Generation, LlmProposedAction, ProposedAction
      comments.py                      # new: CommentRecord
      evals.py                         # new: EvalRunRecord, EvalMetricRecord
      feeds.py                         # new: GeneratedFeedRecord, FeedPostView
      follows.py                       # new: FollowRecord
      likes.py                         # new: LikeRecord
      memory.py                        # new: AgentMemoryRecord and memory diff records
      posts.py                         # new: PostRecord
      runs.py                          # new: RunRecord, TurnRecord, RunStatus, TurnStatus
      seed.py                          # new: SeedDatasetRecord or SeedImportRecord
      users.py                         # new: UserRecord

  seed/
    __init__.py                        # new
    loader.py                          # new: load/generate the base users/posts for a run
    generator.py                       # new: local fake seed data generation currently in seed_data.py
    cache.py                           # new: optional filtered seed cache currently in load_seed_data.py

  feeds/
    __init__.py                        # new
    interfaces.py                      # new: FeedGenerator protocol/base class
    service.py                         # new: orchestrates feed generation and persistence
    reverse_chronological.py           # new: simple feed plugin
    most_liked.py                      # new: current ranking behavior
    validators.py                      # new: feed dedupe/self-post checks

  actions/
    __init__.py                        # new
    service.py                         # new: per-agent action pipeline
    llm.py                             # new/move: local structured OpenAI calls
    prompts.py                         # new/move: action prompts
    models.py                          # new: LLM structured output models
    validators.py                      # new: business validators returning accept/reject records
    executor.py                        # new: applies accepted actions to pending diffs
    noise.py                           # new: action probability gates

  memory/
    __init__.py                        # new
    service.py                         # new: fetch/update memory around each agent turn
    episodic.py                        # new/move: episodic memory update
    personalized.py                    # new/move: profile/personalized memory update
    social.py                          # new/move: relationship memory update

  evals/
    __init__.py                        # new
    interfaces.py                      # new: EvalPlugin protocol and EvalContext
    registry.py                        # new: plugin registration and selection from config
    runner.py                          # new: runs eval plugins after each turn/run
    plugins/
      __init__.py                      # new
      action_counts.py                 # new: deterministic smoke metrics
      invalid_action_rate.py           # new: rejected/proposed action metrics
      feed_coverage.py                 # new: feed generation sanity metrics
      llm_structured_output.py         # new: schema success/failure metrics
      golden_dataset.py                # new: optional fixture-based regression plugin

  telemetry/
    __init__.py                        # existing; keep but make local-first
    opik.py                            # new/move: Opik setup and trace helpers
    llm_collector.py                   # existing or simplified
    simulation_metrics.py              # existing or simplified
    context.py                         # existing or simplified

  legacy_to_remove_or_fold_in/
    # Not an actual directory. During implementation, fold these existing modules
    # into the structure above instead of keeping parallel systems:
    # agents/, models/, feeds.py, load_seed_data.py, seed_data.py,
    # simulate_run.py, simulate_turn.py
```

The last block is intentional: the final implementation should not keep both the old and new orchestrators alive. It is fine to migrate incrementally while working, but the finished proof of concept should have one clear path from `main.py` to SQLite-backed run execution.

## Local Architecture Mapping

The cloud design maps to local services like this:

| Architecture concept | Local proof-of-concept equivalent |
| --- | --- |
| Control plane API | `control_plane.service` called directly by `main.py` |
| SQS dispatch | `control_plane.dispatcher.dispatch_now()` in-process |
| Worker node | `worker.service.run_job()` |
| RDS | `simulation_v2/db` SQLite database |
| S3 datasets/scratch | SQLite tables plus optional local seed cache under `simulation_v2/seed/` |
| Secrets Manager | `lib.load_env_vars.EnvVarsContainer` only |
| Opik/cloud telemetry | Opik LLM traces when configured, plus local metric rows and logs |

This gives the same service-level breakdown and state transitions without pretending local development needs a queue, object store, or remote deployment surface.

## SQLite Storage Plan

Use Python's standard `sqlite3` module. Keep the layer deliberately thin:

- `connection.py` opens the database, enables foreign keys, and exposes a `transaction()` context manager.
- `schema.py` owns `CREATE TABLE IF NOT EXISTS` statements and practical indexes.
- `repositories.py` contains straightforward methods such as `insert_run`, `update_run_status`, `list_posts_for_run`, `insert_generated_feed`, `insert_proposed_action`, `insert_post`, `insert_like`, and `insert_eval_metric`.
- `database.py` wires connection + schema + repositories so callers do not pass raw connections around.
- `db/models/` stores Pydantic data records that mirror persisted rows.

Suggested tables:

- `runs`: `run_id`, `status`, `config_json`, `seed_metadata_json`, `created_at`, `started_at`, `finished_at`, `error`.
- `turns`: `turn_id`, `run_id`, `turn_number`, `status`, `created_at`, `started_at`, `finished_at`, `error`.
- `users`: `user_id`, `run_id`, `name`, `email`, `username`, `profile_json`, `created_at`.
- `posts`: `post_id`, `run_id`, `author_id`, `content`, `created_at`, `created_at_turn`, `metadata_json`.
- `likes`: `like_id`, `run_id`, `post_id`, `author_id`, `created_at`, `created_at_turn`, `metadata_json`.
- `comments`: `comment_id`, `run_id`, `parent_post_id`, `author_id`, `content`, `created_at`, `created_at_turn`, `metadata_json`.
- `follows`: `follow_id`, `run_id`, `follower_id`, `followee_id`, `created_at`, `created_at_turn`, `metadata_json`.
- `agent_memories`: `run_id`, `user_id`, `preferences_json`, `episodic`, `personalized`, `social`, `updated_at`.
- `memory_diffs`: `memory_diff_id`, `run_id`, `turn_id`, `user_id`, `memory_type`, `content`, `created_at`.
- `generated_feeds`: `feed_id`, `run_id`, `turn_id`, `user_id`, `algorithm`, `feed_post_ids_json`, `feed_posts_json`, `created_at`.
- `generations`: `generation_id`, `run_id`, `turn_id`, `user_id`, `action_type`, `parsed_response_json`, `raw_response_json`, `status`, `latency_ms`, `prompt_tokens`, `completion_tokens`, `cost_usd`, `created_at`, `error`.
- `llm_proposed_actions`: `llm_proposed_action_id`, `generation_id`, `run_id`, `turn_id`, `user_id`, `action_type`, `target_type`, `target_id`, `target_content`, `metadata_json`, `created_at`.
- `proposed_actions`: `action_id`, `record_kind`, `generation_id`, `run_id`, `turn_id`, `user_id`, `action_type`, `target_type`, `target_id`, `target_content`, `filter_id`, `filter_reason`, `rejection_stage`, `metadata_json`, `created_at`.
- `eval_runs`: `eval_run_id`, `run_id`, `turn_id`, `scope`, `plugin_name`, `status`, `created_at`, `finished_at`, `error`.
- `eval_metrics`: `eval_metric_id`, `eval_run_id`, `run_id`, `turn_id`, `plugin_name`, `metric_name`, `metric_value`, `metadata_json`, `created_at`.

Keep append-only behavior for social actions, proposed actions, generated feeds, generations, memory diffs, and eval metrics. `runs`, `turns`, and `agent_memories` are the only records that should be updated in place.

Local idempotency should be handled with database constraints, status checks, and turn-level transactions rather than a distributed job framework:

- `runs.run_id` is globally unique.
- `turns` has a unique `(run_id, turn_number)` constraint.
- Seed state has per-run uniqueness, such as `(run_id, user_id)`, `(run_id, post_id)`, `(run_id, like_id)`, and `(run_id, follower_id, followee_id)`.
- `agent_memories` has a unique `(run_id, user_id)` constraint.
- `generated_feeds` has a unique `(run_id, turn_id, user_id)` constraint.
- `likes` has a unique `(run_id, author_id, post_id)` constraint so retries cannot duplicate likes.
- `follows` has a unique `(run_id, follower_id, followee_id)` constraint so retries cannot duplicate follows.
- Turn execution writes generated feeds, proposed actions, executed entity diffs, memory diffs, and eval rows through explicit transactions so partial turns fail cleanly.
- The worker should skip completed turns on retry and only execute turns whose status is not `completed`.

## Run-Level Flow

`main.py` should remain the human-facing entrypoint:

1. Build a `LocalSimulationConfig` with defaults matching today: 10 users, 5 base posts per user, 3 turns.
2. Open or create the local SQLite DB, defaulting to something like `simulation_v2/local_simulation.sqlite3`.
3. Call `control_plane.service.start_run(config, dispatch=True)`.
4. Print the final run summary with `run_id`, user count, initial post count, final post count, and turn count.

`control_plane.service.start_run()` should:

1. Create a `RunRecord(status="queued")`.
2. Store the config JSON.
3. If `dispatch=True`, call `control_plane.dispatcher.dispatch_now(run_id)`.
4. Return the `run_id`.

`control_plane.dispatcher.dispatch_now()` should:

1. Build a local `RunJob(run_id=...)`.
2. Call `worker.service.run_job(job)`.
3. Let the worker own all execution status transitions.

`worker.service.run_job()` should:

1. Check the run is `queued` or explicitly retryable.
2. Mark the run `running`.
3. Load/generate the seed dataset.
4. Persist seed users, seed posts, seed follows, seed likes, and initial memories into SQLite.
5. Call `worker.run_executor.execute_run(run_id, config)`.
6. Mark the run `completed` on success or `failed` with an error message on failure.

`worker.run_executor.execute_run()` should:

1. Loop `turn_number` from 1 through `config.total_turns`.
2. Create a `TurnRecord(status="running")`.
3. Call `worker.turn_executor.execute_turn(run_id, turn_id, turn_number, config)`.
4. Run configured turn-scope eval plugins.
5. Mark the turn `completed`.
6. After the final turn, run configured run-scope eval plugins.

This preserves the current shape of `simulate_run()` but moves the source of truth from an in-memory `TurnInputsModel` to SQLite-backed run state.

## Turn-Level Flow

`worker.turn_executor.execute_turn()` should implement the architecture document's turn pipeline directly:

1. Load a `TurnStateSnapshot` from SQLite:
   - users and profiles
   - cumulative posts/comments/likes/follows
   - current agent memories
   - config, run ID, turn ID, turn number
2. Generate feeds:
   - `feeds.service.generate_and_persist_feeds(snapshot, config.feed)`
   - choose a plugin such as `most_liked` or `reverse_chronological`
   - validate feeds for duplicate posts and self-authored posts
   - persist one `GeneratedFeedRecord` per user
3. Run agent actions:
   - for each user, load memory and feed
   - call LLM action proposers for likes, posts, follows, and comments if enabled
   - persist every LLM call as a `Generation`
   - persist raw model outputs as `LlmProposedAction`
   - run business validators and persist accepted/rejected `ProposedAction` rows
   - apply stochastic action noise after validation and record filtered actions as rejected with `filter_id="action_noise"` rather than dropping them silently
4. Execute accepted actions into `PendingTurnDiffs`:
   - post diffs
   - like diffs
   - follow diffs
   - comment diffs
   - memory diffs
5. Persist diffs in one transaction:
   - insert accepted posts/likes/follows/comments
   - insert memory diffs
   - update `agent_memories`
6. Return a `TurnExecutionSummary` for logging and evals.

The important behavioral change is that turn N+1 reads the durable output of turn N. Today, actions are returned but not merged into a persistent state, so later turns cannot fully depend on earlier simulated behavior.

## Action Pipeline Details

Use one service path for all action types:

```text
ActionPlanner -> LLM generation -> raw proposed action rows
              -> business validators -> accepted/rejected action rows
              -> action noise filter -> executable pending diffs
```

Minimum action types for the proof of concept:

- `like_post`
- `write_post`
- `follow_user`
- `comment_on_post`

The current code handles likes, posts, and follows. Comments should be added because the architecture includes them and because they exercise the same target validation pattern as likes.

LLM calls should stay simple:

- Use LangChain's basic `ChatOpenAI` integration for OpenAI chat completions.
- Use Pydantic structured outputs for `like_post`, `write_post`, `follow_user`, and `comment_on_post`.
- Use `tenacity` for bounded retries around transient provider failures and timeouts.
- Use Opik for LLM telemetry when configured, while still persisting local `generations` rows so the run is inspectable from SQLite.
- Record model name, prompt/action type, latency, token/cost metadata when available, parsed response, raw response when available, final status, and final error.

Do not add a multi-provider abstraction yet. OpenAI through LangChain is enough for this proof of concept, and provider swapping would add complexity before it pays for itself.

Business validators should be plain functions returning structured validation results:

- no self-like
- no duplicate like by the same user on the same post
- no self-follow
- no duplicate follow
- target post exists
- target user exists
- comment parent post exists
- generated post/comment content is non-empty
- max actions per user per turn

Do not build a generic rules engine yet. A small registry of named validator functions is enough for evals to reuse the same reasons and counts.

## Memory Flow

Memory should become a first-class local service rather than a prompt helper with a stub update:

1. On seed import, create one `agent_memories` row per user with:
   - preferences from the seed profile
   - empty or generated episodic memory
   - simple personalized memory
   - empty social relationship memory
2. Before each agent acts, `memory.service.fetch_memory(user_id, run_id)` returns the prompt-ready memory text plus structured fields if needed.
3. After accepted actions are known, `memory.service.build_memory_diffs()` creates deterministic first-pass updates:
   - episodic: summarize the user's accepted actions this turn
   - personalized: optionally append stable preference observations from posts/likes
   - social: note followed users or repeated interactions
4. Persist `memory_diffs` append-only and update the current `agent_memories` row.

For the proof of concept, memory updates can be deterministic string updates. LLM-updated memory can be added later if needed, but it should not block the architecture migration.

## Feed Flow

Feed generation should be plugin-style but small:

```python
class FeedGenerator(Protocol):
    name: str
    def generate(self, snapshot: TurnStateSnapshot, user_id: str, config: FeedConfig) -> list[FeedPostView]: ...
```

Initial plugins:

- `most_liked`: equivalent to the current feed behavior.
- `reverse_chronological`: useful deterministic baseline and eval fixture.

`feeds.service` should be the only caller that:

1. resolves the configured generator
2. calls it for every user
3. validates generated feeds
4. persists generated feeds

Action code should receive feed records from storage or from the feed service result, not regenerate feeds itself.

## Eval Plugin Design

Evals should live under `simulation_v2/evals/` and be plugin-style:

```python
class EvalPlugin(Protocol):
    name: str
    scope: Literal["turn", "run"]
    def run(self, context: EvalContext) -> EvalResult: ...
```

`EvalContext` should include:

- database/repository access
- run ID
- optional turn ID and turn number
- local config
- optional turn summary

`EvalResult` should include:

- plugin name
- metric rows
- optional warnings
- pass/fail status for deterministic gates

Initial eval plugins:

- `action_counts`: count proposed, accepted, rejected, and executed actions by type.
- `invalid_action_rate`: rejected / proposed by action type and validator reason.
- `feed_coverage`: users with feeds, empty feeds, duplicate feed posts, self-authored feed posts.
- `llm_structured_output`: successful vs failed generations by action type.
- `golden_dataset`: optional local fixture comparison for single-turn regression once fixtures exist.

`evals.runner` should run:

- turn-scope plugins after each turn completes action persistence
- run-scope plugins after all turns complete

All eval outputs should persist to `eval_runs` and `eval_metrics`. The default proof-of-concept should log eval summaries but should not fail the run unless `config.evals.fail_run_on_error=True`.

## Proposed Interactions Between Files

High-level call graph:

```text
main.py
  -> control_plane.service.start_run()
    -> db.database.initialize()
    -> db.repositories.insert_run()
    -> control_plane.dispatcher.dispatch_now()
      -> worker.service.run_job()
        -> seed.loader.load_seed_dataset()
        -> db.repositories.insert_seed_state()
        -> worker.run_executor.execute_run()
          -> worker.turn_executor.execute_turn()
            -> db.repositories.load_turn_snapshot()
            -> feeds.service.generate_and_persist_feeds()
              -> feeds.<plugin>.generate()
              -> feeds.validators.validate_feed()
              -> db.repositories.insert_generated_feed()
            -> actions.service.run_actions_for_turn()
              -> memory.service.fetch_memory()
              -> actions.llm.invoke_structured()
              -> db.repositories.insert_generation()
              -> db.repositories.insert_llm_proposed_action()
              -> actions.validators.validate()
              -> db.repositories.insert_proposed_action()
              -> actions.noise.apply_action_noise()
              -> actions.executor.to_pending_diffs()
            -> memory.service.build_memory_diffs()
            -> db.repositories.persist_turn_diffs()
          -> evals.runner.run_turn_evals()
          -> evals.runner.run_run_evals()
```

Status transitions:

```text
run:  queued -> running -> completed
run:  queued -> running -> failed
turn: pending/running -> completed
turn: pending/running -> failed
```

The worker should be the only layer that marks runs or turns `running`, `completed`, or `failed`. The control plane only creates queued work.

## Migration Strategy

Implement in this order:

1. Add `config.py`, `ids.py`, `time.py`, and the SQLite layer under `db/`.
2. Move DB row models into `db/models/`.
3. Add the local control plane and dispatcher.
4. Add seed import into SQLite while preserving current default run size.
5. Add run executor and turn executor with feed generation only.
6. Move action logic into `actions/` and persist generations/proposed actions/accepted actions.
7. Add `PendingTurnDiffs` and make later turns read previous turn outputs from SQLite.
8. Add deterministic memory updates.
9. Add eval plugin interfaces, registry, runner, and the first deterministic plugins.
10. Replace `simulate_run.py` and `simulate_turn.py` with compatibility facades or remove them once `main.py` uses the new path.

During migration, avoid introducing a FastAPI API, queue abstraction, async worker framework, ORM, or non-Opik cloud service requirement. The useful abstraction boundary is service-level ownership, not deployment mimicry.

## Definition of Done

The proof of concept is complete when:

- `PYTHONPATH=. uv run python simulation_v2/main.py` starts and completes a local run.
- The default run still uses 10 users, 5 initial posts per user, and 3 turns unless config overrides it.
- A local SQLite database contains runs, turns, users, posts, likes, follows, generated feeds, generations, proposed actions, memories, and eval metrics.
- Turn 2 and turn 3 feeds/actions can see posts, likes, follows, comments, and memory changes from earlier turns.
- Rejected actions are persisted with reason and rejection stage.
- Evals run through `simulation_v2/evals/` plugins and write metrics to SQLite.
- Runtime code remains self-contained inside `simulation_v2/`, except for the two allowed `lib` helpers.

## Proposed PR Breakdown

Err toward smaller PRs. Each PR should leave `simulation_v2` in a runnable or at least importable state, and each should include narrow tests or a clear local verification command.

Every PR's completion criteria should include these invariants:

- Data-model invariant: any new persisted shape has a Pydantic model in `simulation_v2/db/models/`, and repository writes/readbacks round-trip through that model.
- File-interaction invariant: each PR names the owning module and the only modules that should call it; callers should go through service/repository interfaces instead of reaching across layers.
- Boundary invariant: runtime code stays inside `simulation_v2/`, except repo-local imports from `lib/load_env_vars.py` and `lib/timestamp_utils.py`.
- Import invariant: higher-level orchestration may depend inward on services, but DB repositories must not import worker/feed/action/eval services.
- Verification invariant: tests or smoke commands assert both behavior and expected rows/files touched.

### PR 1: Local Config and Utility Baseline

Scope:

- Add `simulation_v2/config.py` with `LocalSimulationConfig`, `FeedConfig`, `ActionConfig`, `LlmConfig`, `EvalConfig`, and storage config.
- Add `simulation_v2/ids.py` for ID generation helpers.
- Add `simulation_v2/time.py` as the local wrapper around `lib.timestamp_utils`.
- Keep `main.py` behavior unchanged except optionally constructing the config object internally.

Completion criteria:

- Default config matches today's behavior: 10 users, 5 base posts per user, 3 turns.
- Config models validate and serialize to JSON.
- File-interaction invariant: `main.py`, control-plane code, worker code, feed services, action services, and eval runner read config through `simulation_v2/config.py`; config models do not import those consumers.
- `PYTHONPATH=. uv run python simulation_v2/main.py` still starts the existing run path.
- Verification: run focused config tests and the existing `simulation_v2/main.py` entry command.

### PR 2: SQLite Connection, Schema, and DB Models

Scope:

- Add `simulation_v2/db/connection.py`, `schema.py`, `database.py`, and `repositories.py`.
- Add initial `simulation_v2/db/models/` records for runs, turns, users, posts, likes, follows, comments, memories, feeds, actions, generations, and evals.
- Implement schema creation and foreign-key enforcement.
- Add uniqueness constraints for local idempotency: `(run_id, turn_number)`, per-run seed entity keys, `(run_id, user_id)` for memories, `(run_id, turn_id, user_id)` for feeds, `(run_id, author_id, post_id)` for likes, and `(run_id, follower_id, followee_id)` for follows.

Completion criteria:

- A database can be initialized at a local path.
- All proposed tables are created idempotently.
- Data-model invariant: each table has a matching model under `simulation_v2/db/models/`, and repository methods accept/return those models rather than untyped dicts.
- File-interaction invariant: `simulation_v2/db/schema.py` owns DDL, `simulation_v2/db/connection.py` owns connections/transactions, and non-DB services interact through `simulation_v2/db/database.py` or `repositories.py`.
- A smoke test can open the DB, create schema twice, and verify core tables exist.
- Constraint tests prove duplicate turns, seed records, feeds, likes, follows, and memories are rejected or upserted intentionally.
- No existing run behavior is changed yet.
- Verification: run focused SQLite schema/repository tests against a temporary database.

### PR 3: Run and Turn Status Persistence

Scope:

- Implement run and turn repository methods.
- Add run status transitions: `queued`, `running`, `completed`, `failed`.
- Add turn status transitions: `running`, `completed`, `failed`.
- Keep this PR at the repository/service-boundary level; avoid baking worker-owned status transitions into `main.py`.

Completion criteria:

- Repository tests can create a `runs` row and one unique `turns` row per turn.
- Data-model invariant: `RunRecord`, `TurnRecord`, `RunStatus`, and `TurnStatus` are the only persisted run/turn status shapes used by repositories.
- File-interaction invariant: repository status methods live in `simulation_v2/db/repositories.py`; worker-owned transition logic is not implemented in `main.py`.
- Failures persist error text on the run or turn.
- Completed turns are detectable so retry logic can skip them later.
- Verification: run focused run/turn repository tests against a temporary database.

### PR 4: Local Control Plane and Dispatcher

Scope:

- Add `simulation_v2/control_plane/service.py`.
- Add `simulation_v2/control_plane/dispatcher.py`.
- Add `simulation_v2/worker/service.py` with a minimal `RunJob`.
- Move run creation out of `main.py` and into the control-plane service.

Completion criteria:

- `main.py` calls `start_run(config, dispatch=True)`.
- File-interaction invariant: `main.py` only talks to `control_plane.service`; `control_plane.dispatcher` is the only control-plane file that calls `worker.service`.
- Control plane only creates queued work.
- Worker owns transitions to running/completed/failed.
- Data-model invariant: local dispatch passes a typed `RunJob` or equivalent job model containing `run_id` and no embedded mutable run state.
- Worker skips already completed turns on retry and does not duplicate run/turn rows.
- No API server, queue library, or cloud abstraction is introduced.
- Verification: run a local dispatch smoke test that creates one run, dispatches it once, and retries without duplicating completed work.

### PR 5: Seed Import Into SQLite

Scope:

- Add `simulation_v2/seed/loader.py`, `generator.py`, and optional `cache.py`.
- Move or wrap current seed loading so the default seed subset is persisted to SQLite.
- Insert users, base posts, seed likes, seed follows, and initial agent memory rows.

Completion criteria:

- A fresh run DB contains the configured number of users and base posts.
- Data-model invariant: seed import writes `UserRecord`, `PostRecord`, `LikeRecord`, `FollowRecord`, and `AgentMemoryRecord` shapes expected by `simulation_v2/db/models/`.
- File-interaction invariant: `seed.loader` is the only seed module called by `worker.service`; seed modules write through repositories and do not call worker/feed/action/eval services.
- Seed likes/follows are present when available from the seed source.
- Initial memories exist for every user.
- The seed import is idempotent per run and does not duplicate rows on retry.
- Verification: run focused seed import tests that import the same seed twice for one run and compare row counts.

### PR 6: SQLite-Backed Turn Snapshot

Scope:

- Add `simulation_v2/worker/state.py`.
- Implement `load_turn_snapshot(run_id, turn_id)` from SQLite.
- Include users, cumulative posts/comments/likes/follows, generated feed history if needed, and current memories.
- Introduce `PendingTurnDiffs` without yet changing action execution.

Completion criteria:

- Turn executor can load all state needed for feed generation from SQLite.
- Data-model invariant: `TurnStateSnapshot` contains typed users, posts, likes, follows, comments, generated-feed summaries if needed, and current memories, not raw database rows.
- File-interaction invariant: `worker.state` reads through repositories only; `feeds`, `actions`, and `memory` consume the snapshot but do not build it themselves.
- Snapshot counts match persisted seed data on turn 1.
- Snapshot counts include previously inserted diffs in a focused test.
- Verification: run snapshot tests with a temporary DB containing seed rows plus synthetic prior-turn diffs.

### PR 7: Feed Service and Feed Plugins

Scope:

- Add `simulation_v2/feeds/interfaces.py`, `service.py`, `most_liked.py`, `reverse_chronological.py`, and `validators.py`.
- Port current feed behavior to the `most_liked` plugin.
- Persist one generated feed per user per turn.

Completion criteria:

- Turn execution generates feeds from the SQLite snapshot.
- Data-model invariant: feed plugins return `FeedPostView` records and `feeds.service` persists `GeneratedFeedRecord` records.
- File-interaction invariant: `feeds.service` is the only module that resolves feed plugins and writes generated feeds; action code reads the feed result or persisted feed records instead of invoking plugins directly.
- `most_liked` produces equivalent behavior to the current feed ranking.
- `reverse_chronological` works as a deterministic baseline.
- Generated feeds are persisted and include hydrated feed post views.
- Seen-post filtering is explicitly out of scope; feed validation only covers duplicate posts and self-authored posts for now.
- Verification: run feed service tests for both plugins and persisted generated-feed rows.

### PR 8: Action Models, Prompts, and LLM Generation Persistence

Scope:

- Add `simulation_v2/actions/models.py`, `prompts.py`, and `llm.py`.
- Move structured output models for likes, posts, follows, and comments into the action package.
- Use LangChain `ChatOpenAI` for basic OpenAI chat completions.
- Use `tenacity` for bounded retries around transient provider failures and timeouts.
- Add Opik tracing for LLM calls when configured.
- Persist every LLM attempt to `generations`, including schema failures.
- Persist raw proposed actions to `llm_proposed_actions`.

Completion criteria:

- Every LLM call has a generation row with status and metadata.
- Data-model invariant: structured LLM outputs live in `simulation_v2/actions/models.py`; persisted generation rows use `GenerationRecord` and proposed raw action rows use `LlmProposedActionRecord`.
- File-interaction invariant: only `actions.llm` wraps LangChain, Tenacity, and Opik; `actions.service` calls `actions.llm` and persists via repositories.
- Generation metadata includes model name, action type, latency, token/cost fields when available, and Opik trace context when available.
- Schema failures are stored instead of disappearing into logs.
- Like/write/follow behavior remains functionally equivalent before business validation changes.
- Comments have structured output support even if execution is introduced in the next PR.
- Verification: run mocked LLM tests that cover success, retryable failure, schema failure, and Opik-disabled mode.

### PR 9: Business Validators and Proposed Action Records

Scope:

- Add `simulation_v2/actions/validators.py`.
- Implement named validators for likes, follows, posts, and comments.
- Persist accepted and rejected rows to `proposed_actions`.
- Reuse validator names and reasons for evals.

Completion criteria:

- Invalid actions are rejected with `record_kind="rejected"`, `rejection_stage="business_rules"`, `filter_id`, and `filter_reason`.
- Accepted actions are persisted with `record_kind="validated"`.
- Data-model invariant: all accepted and rejected action rows use one `ProposedActionRecord` shape with `record_kind` distinguishing validated vs rejected records.
- File-interaction invariant: `actions.validators` owns validation functions and returns structured validation results; it does not write to SQLite directly.
- Validators cover no self-like, duplicate like, no self-follow, duplicate follow, missing targets, empty content, and max actions per turn.
- Verification: run validator tests that assert accepted/rejected rows and rejection reasons for each action type.

### PR 10: Action Noise and Turn Diff Execution

Scope:

- Add `simulation_v2/actions/noise.py` and `executor.py`.
- Apply configured action probabilities after business validation.
- Convert accepted post/like/follow/comment actions into `PendingTurnDiffs`.
- Persist executable diffs to SQLite in a single transaction.

Completion criteria:

- Noise-filtered actions are recorded as rejected with `filter_id="action_noise"`.
- Executed actions create durable posts, likes, follows, and comments.
- Data-model invariant: `PendingTurnDiffs` contains typed `PostRecord`, `LikeRecord`, `FollowRecord`, `CommentRecord`, and memory diff records before persistence.
- File-interaction invariant: `actions.executor` converts validated actions to pending diffs; `worker.turn_executor` owns the transaction that persists those diffs.
- Turn 2 sees actions executed in turn 1.
- The old behavior where actions are returned but not merged into state is removed.
- Verification: run turn-diff execution tests that execute two turns and assert turn 2 reads turn 1 writes.

### PR 11: Deterministic Memory Service

Scope:

- Add `simulation_v2/memory/service.py`, `episodic.py`, `personalized.py`, and `social.py`.
- Replace the current memory fetch/update stubs with SQLite-backed memory reads and deterministic updates.
- Persist append-only `memory_diffs` and update current `agent_memories`.

Completion criteria:

- Agent prompts use memory from SQLite.
- Each turn writes episodic memory diffs for users with accepted actions.
- Data-model invariant: current memory uses `AgentMemoryRecord`; append-only updates use memory diff records with explicit memory type.
- File-interaction invariant: `memory.service` is the only module that formats memory for prompts and builds memory diffs; action code requests memory through this service.
- Current memory changes are visible in the next turn.
- No LLM-based memory update is required for this PR.
- Verification: run memory service tests that fetch memory, apply diffs, and reload updated memory in a later turn.

### PR 12: Eval Plugin Framework

Scope:

- Add `simulation_v2/evals/interfaces.py`, `registry.py`, and `runner.py`.
- Add `eval_runs` and `eval_metrics` repository methods if not already complete.
- Wire turn-scope eval execution after each turn and run-scope eval execution after run completion.

Completion criteria:

- Evals can be enabled/disabled from config.
- Eval plugin results persist to SQLite.
- Data-model invariant: eval plugins return `EvalResult` objects containing metric records that map to `EvalRunRecord` and `EvalMetricRecord`.
- File-interaction invariant: `evals.runner` is the only module that executes plugins and writes eval rows; plugins read context and return results without mutating run state directly.
- Eval failures are recorded and do not fail the run by default.
- The runner supports both turn and run scopes.
- Verification: run eval runner tests with one passing plugin and one failing plugin.

### PR 13: Initial Deterministic Eval Plugins

Scope:

- Add `action_counts`, `invalid_action_rate`, `feed_coverage`, and `llm_structured_output` plugins.
- Add focused tests or fixtures for each plugin.
- Log concise eval summaries at the end of each turn/run.

Completion criteria:

- Action counts match rows in `proposed_actions` and executed entity tables.
- Invalid action rate is grouped by action type and validator reason.
- Feed coverage reports missing feeds, empty feeds, duplicate feed posts, and self-authored feed posts.
- Structured output metrics report generation success/failure by action type.
- Data-model invariant: each deterministic plugin emits stable metric names and numeric metric values suitable for `eval_metrics`.
- File-interaction invariant: plugins read through `EvalContext` only and do not import worker/action/feed internals.
- Verification: run deterministic eval plugin tests against a fixture SQLite database.

### PR 14: Golden Dataset Eval Skeleton

Scope:

- Add a small local golden fixture format under `simulation_v2/evals/fixtures/`.
- Add `plugins/golden_dataset.py`.
- Support single-turn expected likes/follows/write-topic checks.

Completion criteria:

- Golden eval can run against a tiny fixture without needing a full LLM-backed run.
- Data-model invariant: golden fixture cases have an explicit fixture schema/version and map to `EvalMetricRecord` outputs.
- File-interaction invariant: `plugins/golden_dataset.py` owns fixture parsing; `evals.runner` only invokes the plugin interface.
- Metrics include precision/recall/F1 where labels exist.
- Missing optional labels are skipped explicitly rather than treated as failures.
- Verification: run golden dataset tests against a tiny fixture with partial labels.

### PR 15: Main Entrypoint Cutover and Legacy Cleanup

Scope:

- Point `simulation_v2/main.py` entirely at the new local architecture.
- Remove or reduce `simulate_run.py` and `simulate_turn.py` to compatibility shims if external callers still need them.
- Fold old `agents/`, top-level `feeds.py`, `load_seed_data.py`, `seed_data.py`, and old `models/` code into the new structure or delete unused paths inside `simulation_v2`.

Completion criteria:

- `PYTHONPATH=. uv run python simulation_v2/main.py` completes the SQLite-backed run path.
- There is one clear runtime path, not parallel old/new implementations.
- File-interaction invariant: `main.py` enters through `control_plane.service`; legacy modules, if kept as shims, delegate to the new path and do not contain independent run logic.
- Data-model invariant: the final path writes all expected core record types: runs, turns, users, posts, likes, follows, comments, memories, feeds, generations, proposed actions, eval runs, and eval metrics.
- The run summary reports initial and final entity counts.
- Runtime code remains inside `simulation_v2/`, except the allowed `lib` helpers.
- Verification: run the default `simulation_v2/main.py` command and inspect the generated SQLite run summary.

### PR 16: End-to-End Local Verification

Scope:

- Add an end-to-end smoke test or script that runs a tiny local simulation.
- Verify DB contents after completion.
- Document the local command and expected DB artifacts in a short `simulation_v2/README.md`.

Completion criteria:

- A tiny run completes quickly and deterministically enough for local verification.
- The verification checks runs, turns, feeds, proposed actions, executed actions, memories, and eval metrics.
- Data-model invariant: smoke verification asserts required tables have rows matching the expected tiny-run cardinalities and cross-table foreign keys.
- File-interaction invariant: documented smoke flow uses the public entrypoint and does not call internal services directly.
- Documentation explains how to run the proof of concept, where the SQLite DB is created, and how to inspect the results.
- Verification: run the documented smoke command from a clean checkout and confirm the DB assertions pass.
