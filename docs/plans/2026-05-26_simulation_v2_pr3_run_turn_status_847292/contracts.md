# simulation_v2 PR3 run/turn status contracts

Frozen interface for run and turn lifecycle persistence (repository layer only).

## Status types (unchanged from PR2)

- `RunStatus`: `queued | running | completed | failed` — `simulation_v2/db/models/runs.py`
- `TurnStatus`: `pending | running | completed | failed`

## Allowed transitions (repository-enforced)

| Entity | From | To |
|--------|------|-----|
| Run | `queued` | `running` |
| Run | `running` | `completed`, `failed` |
| Run | same status | same status (idempotent) |
| Turn | `pending` | `running`, `failed` |
| Turn | `running` | `completed`, `failed` |
| Turn | same status | same status (idempotent) |

Disallowed (must raise `InvalidStatusTransitionError`): `completed → running`, `failed → running`, `completed → failed`, and any other backward or skip transition.

## Timestamp / error rules

Use `simulation_v2/time.py` `get_current_timestamp()` unless caller passes an explicit `timestamp: str` (for deterministic tests).

| New status | Column updates |
|------------|----------------|
| `running` | Set `started_at = timestamp` **only if currently NULL** |
| `completed` | Set `finished_at = timestamp`; clear `error` |
| `failed` | Set `finished_at = timestamp`; set `error` (required non-empty string) |

Initial insert behavior unchanged: `insert_run` creates `status=queued`; `insert_turn` creates `status=pending`.

## New repository methods

All methods take `conn: sqlite3.Connection` as the final positional arg (matching PR2). Return updated typed records after updates.

```python
# simulation_v2/db/repositories.py — SimulationRepositories

def update_run_status(
    self,
    run_id: str,
    status: RunStatus,
    conn: sqlite3.Connection,
    *,
    error: str | None = None,
    timestamp: str | None = None,
) -> RunRecord: ...

def update_turn_status(
    self,
    turn_id: str,
    status: TurnStatus,
    conn: sqlite3.Connection,
    *,
    error: str | None = None,
    timestamp: str | None = None,
) -> TurnRecord: ...

def list_turns_for_run(
    self, run_id: str, conn: sqlite3.Connection
) -> list[TurnRecord]: ...
# ORDER BY turn_number ASC

def get_turn_by_run_and_number(
    self, run_id: str, turn_number: int, conn: sqlite3.Connection
) -> TurnRecord | None: ...
```

## Exceptions (`simulation_v2/db/errors.py`)

- `RunNotFoundError(run_id: str)` — UPDATE rowcount 0 on run
- `TurnNotFoundError(turn_id: str)` — UPDATE rowcount 0 on turn
- `InvalidStatusTransitionError(current, target, entity_kind)` — illegal transition
- `ValueError` — `failed` without `error` message

## File-interaction invariants (PR3)

| Owner | Callers (future) | Forbidden |
|-------|------------------|-----------|
| `db/repositories.py` status methods | PR4 worker, PR4 control plane (read-only status) | `main.py`, worker modules (not created yet), feed/action/eval services |
| `db/errors.py` | repositories + tests | worker importing errors directly for business logic |

## Out of scope (explicit)

- No changes to `simulation_v2/main.py`
- No `control_plane/`, `worker/` modules
- No schema DDL changes
- No state machine logic in application layer
