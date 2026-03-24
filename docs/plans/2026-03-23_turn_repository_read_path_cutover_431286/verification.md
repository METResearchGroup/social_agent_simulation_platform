---
description: Verification checklist for turn repository read-path cutover slice
tags: [verification, plan, database, turns, repositories]
---

# Turn repository read-path cutover — verification

- [ ] `uv run pytest tests/db/repositories/test_generated_feed_repository.py tests/db/repositories/test_generated_feed_repository_integration.py tests/db/repositories/test_action_repositories_integration.py tests/db/repositories/test_run_repository.py tests/db/repositories/test_run_repository_integration.py -q` — all pass.
- [ ] `uv run pytest tests/simulation/core/test_query_service.py tests/api/test_run_query_service.py tests/api/test_simulation_run.py -q` — all pass.
- [ ] `rg "\b(turn_metadata|generated_feeds|likes|comments|follows)\b" db/repositories db/adapters/sqlite simulation/core/services tests/db/repositories tests/simulation/core tests/api` — remaining hits are intentional names, migration tests, or mapping comments; no live SQL on legacy tables.
- [ ] Optional: `uv run pytest tests/db/adapters/sqlite/test_run_adapter.py -q` — pass.
