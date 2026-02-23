# Repository-Managed Connection Implementation Plan

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

---

## Overview

Move transaction lifecycle management from adapters into repositories. When `conn` is `None`, the repository uses `TransactionProvider.run_transaction()` to create a transaction and passes the connection to the adapter. Adapters no longer create connections or commit; they only execute SQL against a provided `conn`. This keeps the adapter layer as pure data access and centralizes orchestration in the repository layer.

**Affected components:**

- db/repositories/metrics_repository.py – add `TransactionProvider`, wrap calls when `conn=None`
- db/repositories/run_repository.py – same
- db/adapters/sqlite/metrics_adapter.py – remove `conn=None` branch; require conn
- db/adapters/sqlite/run_adapter.py – same for `update_run_status`, `write_turn_metadata`, `read_turn_metadata`
- db/adapters/base.py – update docstrings for conn (adapter receives conn from caller/repo)
- Factories: db/repositories/metrics_repository.py, db/repositories/run_repository.py, simulation/core/factories/engine.py
- Tests: adapter tests, integration tests, repository unit tests

---

## Happy Flow

See `happy_flow.mmd` for the Mermaid flowchart.

**Transactional path (unchanged):** `SimulationPersistenceService.write_turn()` uses `run_transaction()`, passes `conn` to both repos; repos forward `conn` to adapters; adapters execute SQL; service context commits.

**Standalone path (new behavior):** `metrics_repo.write_turn_metrics(metrics)` called with no `conn` → repository runs `with transaction_provider.run_transaction() as conn` → passes `conn` to adapter → adapter executes SQL → context commits.

---

## Implementation Steps

### 0. Create plan asset directory and store assets

Create `docs/plans/2026-02-23_repo_managed_conn_264784/` and save:
- `plan.md` – Full plan document
- `happy_flow.mmd` – Mermaid flowchart from Happy Flow (for docs or tooling)

### 1. Update factory wiring so `TransactionProvider` is created before repos

**File:** simulation/core/factories/engine.py

- Move `transaction_provider` creation before repository creation (around lines 78–89).
- Pass `transaction_provider` into `create_sqlite_repository()` and `create_sqlite_metrics_repository()`.
- Example order: create `transaction_provider` if `None`, then `run_repo` and `metrics_repo` using it.

### 2. Add `TransactionProvider` to `SQLiteMetricsRepository`

**File:** db/repositories/metrics_repository.py

- Add `transaction_provider: TransactionProvider` to `__init__`.
- In `write_turn_metrics`: if `conn is not None`, forward to adapter; else `with self._transaction_provider.run_transaction() as c: self._db_adapter.write_turn_metrics(turn_metrics, conn=c)`.
- Same pattern for `write_run_metrics`.
- Update `create_sqlite_metrics_repository` to accept `transaction_provider: TransactionProvider` and pass it in.

### 3. Add `TransactionProvider` to `SQLiteRunRepository`

**File:** db/repositories/run_repository.py

- Add `transaction_provider: TransactionProvider` to `__init__`.
- In `update_run_status`: if `conn is not None`, forward; else `with self._transaction_provider.run_transaction() as c: ... self._db_adapter.update_run_status(..., conn=c)`.
- In `write_turn_metadata`: same pattern.
- Update `create_sqlite_repository` to accept `transaction_provider: TransactionProvider` and pass it in.

### 4. Simplify `SQLiteMetricsAdapter` to require conn

**File:** db/adapters/sqlite/metrics_adapter.py

- Remove the `if conn is not None` / `else: with get_connection()...` branch in `write_turn_metrics` and `write_run_metrics`.
- Keep only the path that uses `conn`; delete the `get_connection()` + `commit()` path.

### 5. Simplify `SQLiteRunAdapter` to require conn for transactional methods

**File:** db/adapters/sqlite/run_adapter.py

- `update_run_status`: remove `conn=None` branch; only use provided `conn`.
- `write_turn_metadata`: remove `conn=None` branch; only use provided `conn`.
- `read_turn_metadata`: keep supporting optional `conn` for read-only operations. Only change the write methods and `update_run_status`.

### 6. Update base adapter interfaces

**File:** db/adapters/base.py

- Update docstrings for conn parameter in relevant methods.

### 7–9. Update tests and verify

See Manual Verification section.

---

## Manual Verification

1. **Run full test suite**: `uv run pytest` – Expected: all tests pass.
2. **Run repo and adapter tests**: `uv run pytest tests/db/repositories/ tests/db/adapters/` – Expected: all pass.
3. **Run smoke test**: `SIMULATION_API_URL=http://localhost:8000 uv run pytest -m smoke tests/api/test_simulation_smoke.py` – Expected: smoke tests pass.
4. **Run linters**: `uv run ruff check . && uv run ruff format --check . && uv run pyright .` – Expected: no errors.
