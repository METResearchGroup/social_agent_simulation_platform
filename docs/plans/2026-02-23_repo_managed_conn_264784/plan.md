# Repository-Managed Connection Implementation Plan

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

---

## Overview

Move transaction lifecycle management from adapters into repositories. **All** adapters require `conn` for every operation (read and write). Repositories own `TransactionProvider` and wrap every adapter call in `run_transaction()`, passing the yielded connection. Adapters never create connections or commit; they only execute SQL against a provided `conn`. This keeps the adapter layer as pure data access and centralizes orchestration in the repository layer.

**Status:** Complete (all adapters and repositories migrated).

**Cursor rule:** `.cursor/rules/repo-managed-connections.mdc` (applies to `db/**/*.py`, `jobs/*.py`, `simulation/**/*.py`).

---

## Scope (Completed)

### Base interfaces
- `db/adapters/base.py` – All adapter methods now have required `conn` parameter (keyword-only)

### Adapters (9 files)
- `db/adapters/sqlite/run_adapter.py` – write_run, read_run, read_all_runs, update_run_status, read_turn_metadata, read_turn_metadata_for_run, write_turn_metadata
- `db/adapters/sqlite/metrics_adapter.py` – write_turn_metrics, read_turn_metrics, read_turn_metrics_for_run, write_run_metrics, read_run_metrics
- `db/adapters/sqlite/profile_adapter.py` – write_profile, read_profile, read_all_profiles
- `db/adapters/sqlite/feed_post_adapter.py` – all 6 methods
- `db/adapters/sqlite/generated_feed_adapter.py` – all 5 methods
- `db/adapters/sqlite/generated_bio_adapter.py` – all 3 methods
- `db/adapters/sqlite/agent_adapter.py` – all 4 methods
- `db/adapters/sqlite/agent_bio_adapter.py` – all 3 methods
- `db/adapters/sqlite/user_agent_profile_metadata_adapter.py` – both methods

### Repositories (9 files)
- `db/repositories/run_repository.py` – TransactionProvider, wraps create_run, get_run, list_runs, update_run_status, get_turn_metadata, list_turn_metadata, write_turn_metadata
- `db/repositories/metrics_repository.py` – TransactionProvider, wraps all read/write
- `db/repositories/profile_repository.py` – TransactionProvider
- `db/repositories/feed_post_repository.py` – TransactionProvider
- `db/repositories/generated_feed_repository.py` – TransactionProvider
- `db/repositories/generated_bio_repository.py` – TransactionProvider
- `db/repositories/agent_repository.py` – TransactionProvider
- `db/repositories/agent_bio_repository.py` – TransactionProvider
- `db/repositories/user_agent_profile_metadata_repository.py` – TransactionProvider

### Factory wiring
- `simulation/core/factories/engine.py` – Passes `transaction_provider` to all `create_sqlite_*_repository()` calls
- All factory functions now accept `transaction_provider: TransactionProvider`

### Tests
- Adapter tests: Pass `conn=mock_conn` to all adapter methods; use `create_mock_conn_context()` (no get_connection mock)
- Repository tests: Pass `transaction_provider=make_mock_transaction_provider()`; assertions expect `conn` in adapter call kwargs
- Integration tests: Pass `SqliteTransactionProvider()` to all repo factories

### Jobs (all updated)
- `jobs/migrate_agents_to_new_schema.py` – Passes `SqliteTransactionProvider()` to repo factories
- `jobs/generate_profile_bios.py` – Uses `SqliteTransactionProvider` for profile, feed_post, generated_bio repos
- `jobs/load_initial_bluesky_profiles.py` – Uses `SqliteTransactionProvider` for profile, feed_post repos
- `jobs/view_generated_bios.py` – Uses `SqliteTransactionProvider` for generated_bio repo
- `jobs/view_generated_feeds.py` – Uses `SqliteTransactionProvider` for generated_feed repo

---

## Happy Flow

See `happy_flow.mmd` for the Mermaid flowchart.

**Transactional path:** `SimulationPersistenceService.write_turn()` uses `run_transaction()`, passes `conn` to repos; repos forward `conn` to adapters; adapters execute SQL; service context commits.

**Standalone path:** Any repo method called without `conn` → repository runs `with transaction_provider.run_transaction() as c` → passes `conn=c` to adapter → adapter executes SQL → context commits.

---

## Manual Verification

1. **Run DB tests:** `uv run pytest tests/db/` – Expected: all 327 tests pass.
2. **Run full test suite:** `uv run pytest` – Expected: all tests pass (except pre-existing env-var tests).
3. **Run smoke test:** `SIMULATION_API_URL=http://localhost:8000 uv run pytest -m smoke tests/api/test_simulation_smoke.py` – Expected: smoke tests pass.
4. **Run linters:** `uv run ruff check . && uv run ruff format --check . && uv run pyright .` – Expected: no errors.
