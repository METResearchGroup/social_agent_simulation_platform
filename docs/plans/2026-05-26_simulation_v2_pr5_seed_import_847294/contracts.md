# PR 5 Seed Import — Contract Freeze

| Symbol | Location | Contract |
|--------|----------|----------|
| `load_seed_dataset` | `simulation_v2/seed/loader.py` | `(seed: SeedConfig, *, allow_cached: bool = True) -> SeedDataset` |
| `persist_seed_for_run` | `simulation_v2/seed/loader.py` | `(run_id: str, dataset: SeedDataset, repos: SimulationRepositories, conn: sqlite3.Connection) -> SeedImportSummary` |
| `import_seed_if_needed` | `simulation_v2/seed/loader.py` | `(run_id: str, config: LocalSimulationConfig, repos: SimulationRepositories, conn: sqlite3.Connection) -> SeedImportSummary \| None` — returns `None` when skipped |
| `update_run_seed_metadata` | `simulation_v2/db/repositories.py` | `(run_id: str, seed_metadata_json: dict, conn) -> RunRecord` |
| `SeedDataset` | `simulation_v2/seed/models.py` | Pydantic model: `users`, `posts`, `likes`, `follows` (filtered subset keyed by id) |
| `SeedImportSummary` | `simulation_v2/seed/models.py` | Counts: `user_count`, `post_count`, `like_count`, `follow_count`, `memory_count` |

## File-interaction invariants (PR 5)

| Owner | Allowed callers | Forbidden |
|-------|-----------------|-----------|
| `seed.loader` | `worker.service`, tests | Must not import worker/feed/action/eval |
| `seed.generator`, `seed.cache` | `seed.loader` only | Must not write SQLite |
| `worker.service` | `control_plane.dispatcher`, tests | May import `seed.loader` only (not generator/cache directly) |
| `db/repositories.py` | seed loader, worker, control plane | No schema changes in PR 5 |

**Idempotency rule:** skip import when `run.seed_metadata_json is not None`. Do not rely on catching `IntegrityError` as the primary guard.
