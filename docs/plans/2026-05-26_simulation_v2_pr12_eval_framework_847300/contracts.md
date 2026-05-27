# PR 12 Eval Framework — Contract Freeze

| Symbol | Location | Contract |
| --- | --- | --- |
| `EvalScope` | reuse from `simulation_v2/db/models/evals.py` | `"turn" \| "run"` |
| `EvalMetricDraft` | `simulation_v2/evals/interfaces.py` | `metric_name: str`, `metric_value: float`, `metadata_json: dict \| None = None` — pre-persistence metric payload |
| `EvalResult` | `simulation_v2/evals/interfaces.py` | `plugin_name: str`, `status: Literal["passed","failed"]`, `metrics: list[EvalMetricDraft]`, `warnings: list[str] = []` |
| `EvalContext` | `simulation_v2/evals/interfaces.py` | `repos: SimulationRepositories`, `conn: sqlite3.Connection`, `run_id: str`, `config: LocalSimulationConfig`, `scope: EvalScope`, `turn_id: str \| None`, `turn_number: int \| None`, `turn_summary: dict \| None = None` (optional; unused in PR 12) |
| `EvalPlugin` | `simulation_v2/evals/interfaces.py` | Protocol: `name: str`, `scope: EvalScope`, `run(context: EvalContext) -> EvalResult` |
| `get_eval_plugin` | `simulation_v2/evals/registry.py` | `(name: str) -> EvalPlugin \| None` — returns `None` for unknown names |
| `register_eval_plugin` | `simulation_v2/evals/registry.py` | `(plugin: EvalPlugin) -> None` — for tests and PR 13 registration |
| `EvalPluginRunSummary` | `simulation_v2/evals/runner.py` | Returned per plugin: `eval_run_id`, `plugin_name`, `status`, `metrics: list[EvalMetricRecord]` |
| `run_turn_evals` | `simulation_v2/evals/runner.py` | `(run_id, turn_id, turn_number, config, repos, conn) -> list[EvalPluginRunSummary]`; no-op when `not config.evals.enabled` |
| `run_run_evals` | `simulation_v2/evals/runner.py` | `(run_id, config, repos, conn) -> list[EvalPluginRunSummary]`; same enable gate |
| `insert_eval_run` / `insert_eval_metric` | `simulation_v2/db/repositories.py` | **Already complete** — reuse as-is |
| `new_eval_run_id` / `new_eval_metric_id` | `simulation_v2/ids.py` | **Already exist** |
| `EvalConfig` | `simulation_v2/config.py` | **Already exists** — `enabled`, `fail_run_on_error`, `turn_plugins`, `run_plugins`; do not change defaults in PR 12 |

## File-interaction invariants

| Owner | Allowed callers | Forbidden |
| --- | --- | --- |
| `evals.runner` | `turn_executor`, `run_executor`, tests | Only module that executes plugins and writes eval rows |
| `evals.registry` | `evals.runner`, tests, PR 13 plugin modules | No SQLite, no worker imports |
| Eval plugins | invoked via runner only | Must not mutate run state; read via `EvalContext` only |
| `db.repositories` | runner (insert/get eval rows) | Must not import `evals.runner` or plugins |

## Eval run status mapping

| Outcome | `eval_runs.status` | `eval_runs.error` |
| --- | --- | --- |
| Plugin returns `status="passed"` | `"completed"` | `None` |
| Plugin returns `status="failed"` | `"failed"` | join `warnings` or fixed message |
| Plugin raises | `"failed"` | `str(exc)` |
| Unknown plugin name | *(skip — no row)* | — |
