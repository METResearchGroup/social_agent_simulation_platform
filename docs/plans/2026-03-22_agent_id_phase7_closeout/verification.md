---
description: Milestone verification record for agent ID Phase 7 closeout (head-state verifier, fixture cleanup, API persistence proof).
tags: [plan, verification, agent_id, migration]
---

# Agent ID Migration Phase 7 — Verification Record

Verification performed per the closeout plan (agent_id migration: canonical inventory, legacy-shape negative pass, ordinary fixture cleanup, `POST /v1/simulations/agents` persistence proof).

The strategy proposal [strategy_planning/2026-03-20_agent_id_migration/proposal.md](../../../strategy_planning/2026-03-20_agent_id_migration/proposal.md) Phase 7 closeout criteria are satisfied: all listed commands exited **0**, and the new head-state verifier covers the full proposal column inventory on a real SQLite database upgraded to `head`.

## Canonical helper and migration mapping

```bash
uv run pytest tests/lib/test_agent_id.py tests/scripts/migrations/test_agent_id_migration.py tests/db/test_agent_id_pk_migration.py -q
```

**Result**: exit 0 — 25 passed

## Profile migration and local-dev seed

```bash
uv run pytest tests/jobs/test_migrate_agents_to_new_schema.py tests/local_dev/test_local_mode_seed.py -q
```

**Result**: exit 0 — 4 passed

## Repository and persistence boundaries

```bash
uv run pytest tests/db/repositories/test_action_repositories_integration.py tests/db/repositories/test_generated_feed_repository.py tests/db/repositories/test_generated_feed_repository_integration.py tests/db/repositories/test_feed_post_repository.py tests/db/repositories/test_feed_post_repository_integration.py -q
```

**Result**: exit 0 — 81 passed

## Runtime, query, and feed surfaces

```bash
uv run pytest tests/simulation/core/test_command_service.py tests/simulation/core/test_query_service.py tests/feeds/test_feed_generator.py -q
```

**Result**: exit 0 — 44 passed

## API surfaces

```bash
uv run pytest tests/api/test_simulation_agents.py tests/api/test_run_query_service.py tests/api/test_simulation_run.py -q
```

**Result**: exit 0 — 35 passed

## Lint

```bash
uv run ruff check tests/db/agent_id_inventory.py tests/db/test_agent_id_pk_migration.py
```

**Result**: All checks passed

## Proposal status

With the above green runs and the head-state inventory verifier in place, the **agent ID migration proposal Phase 7 closeout work described in this effort is complete** from an automated verification standpoint.
