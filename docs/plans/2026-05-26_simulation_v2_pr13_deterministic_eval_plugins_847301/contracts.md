# PR 13 Deterministic Eval Plugins — Contract Freeze

| Symbol | Location | Contract |
| --- | --- | --- |
| `EvalPlugin.scopes` | `simulation_v2/evals/interfaces.py` | `ClassVar[frozenset[EvalScope]]` — default `frozenset({"turn", "run"})` for all four PR 13 plugins |
| `EvalScope` | reuse from `simulation_v2/db/models/evals.py` | `"turn" \| "run"` |
| Metric naming | this file (table below) | Stable dot-separated `metric_name` values per plugin |
| `load_*` helpers | `simulation_v2/evals/query_helpers.py` | Scope-aware reads via `context.repos` only; no imports from `worker/`, `actions/`, `feeds/` |
| Plugin registration | `simulation_v2/evals/registry.py` | `register_builtin_eval_plugins()` called at import from `simulation_v2/evals/__init__.py` |
| Pass/fail gates | each plugin | See per-plugin table below |

## Metric names

| Plugin | `metric_name` | `metadata_json` |
| --- | --- | --- |
| `action_counts` | `proposed`, `accepted`, `rejected`, `executed` | `{"action_type": "<canonical>"}` |
| `invalid_action_rate` | `rate`, `rejected_count`, `proposed_count` | `{"action_type", "filter_id", "filter_reason"}` |
| `feed_coverage` | `users_total`, `users_with_feed`, `users_missing_feed`, `empty_feeds`, `duplicate_post_feeds`, `self_authored_feeds` | optional `{"user_id"}` on violations |
| `llm_structured_output` | `generation_count`, `success_rate` | `{"action_type", "status"}` where status ∈ `completed`, `failed`, `schema_failed` |

Canonical `action_type` strings: `like_post`, `write_post`, `follow_user`, `comment_on_post`.

## Pass/fail

| Plugin | `status="failed"` when |
| --- | --- |
| `action_counts` | any `accepted != executed` for an action type |
| `invalid_action_rate` | never (informational) |
| `feed_coverage` | `users_missing_feed > 0` OR `duplicate_post_feeds > 0` OR `self_authored_feeds > 0` |
| `llm_structured_output` | never (informational) |

## File-interaction invariants

| Owner | Allowed callers | Forbidden |
| --- | --- | --- |
| `evals.runner` | `turn_executor`, `run_executor`, tests | Only module that executes plugins and writes eval rows |
| `evals.registry` | `evals.runner`, tests, plugin registration | No SQLite, no worker imports |
| Eval plugins | invoked via runner only | Must not mutate run state; read via `EvalContext` only |
| `evals.query_helpers` | eval plugins | No imports from `worker/`, `actions/`, `feeds/` |
