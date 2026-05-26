# PR 4 Control Plane — Frozen Contracts

## Signatures

| Symbol | Location | Contract |
|--------|----------|----------|
| `RunJob` | `simulation_v2/worker/models.py` | Pydantic model: `{ run_id: str }` only; no embedded config or mutable state |
| `start_run` | `simulation_v2/control_plane/service.py` | `(config: LocalSimulationConfig, *, dispatch: bool = True, db_path: Path \| None = None) -> str` |
| `dispatch_now` | `simulation_v2/control_plane/dispatcher.py` | `(run_id: str, *, db_path: Path) -> None` |
| `run_job` | `simulation_v2/worker/service.py` | `(job: RunJob, *, db_path: Path) -> None` |

## File-Interaction Invariants (PR 4)

| Owner | Allowed callers | Forbidden |
|-------|-----------------|-----------|
| `control_plane/service.py` | `main.py` | Must not call `worker.service` directly |
| `control_plane/dispatcher.py` | `control_plane/service.py` | Only control-plane module that imports worker |
| `worker/service.py` | `control_plane/dispatcher.py`, tests | Must not import feed/action/eval/seed modules |
| `db/repositories.py` | control plane (insert/read), worker (status + turns) | No schema changes in PR 4 |

## Retry Semantics (PR 4)

- Completed run: `run_job` no-op.
- `running` run: resume turn loop; skip turns where `status == "completed"`.
- Never re-`insert_turn` when `(run_id, turn_number)` already exists (UNIQUE constraint).
- `failed` run: raise `RunNotRetryableError` — defer `failed → running` to a later PR.
