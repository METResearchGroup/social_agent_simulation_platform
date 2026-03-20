---
name: Normalize agent creation paths
overview: Wire every production path that mints or imports `Agent` rows to use `canonical_agent_id()` from [`lib/agent_id.py`](lib/agent_id.py), rewrite committed local-dev seed fixtures to canonical 16-char hex IDs, and update narrowly scoped tests that assert the old behaviors—without touching DB migrations, adapters, or runtime action/query layers.
description: Normalize agent_id emission for API creation, Bluesky migration job, and local seed fixtures to canonical 16-char hex IDs.
tags:
  - agent-id
  - canonical-ids
  - local-dev-seed
  - simulation-api
todos:
  - id: p1-api
    content: "Packet P1: Replace _generate_agent_id in agent_command_service.py with canonical_agent_id()"
    status: pending
  - id: p2-migrate-job
    content: "Packet P2: migrate_agents_to_new_schema.py + test_migrate_agents_to_new_schema.py canonical IDs"
    status: pending
  - id: p3-seed
    content: "Packet P3: Rewrite seed JSON (4 files), seed_loader optional asserts, test_local_mode_seed.py"
    status: pending
  - id: integrate-verify
    content: "Integration: targeted pytest, ruff, pyright; scoped rg sweep for creation bypasses"
    status: pending
  - id: plan-assets
    content: Add notes or ID map under docs/plans/2026-03-20_normalize_agent_creation_paths_582941/
    status: pending
isProject: false
---

# Normalize agent creation paths

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- Maximum safely delegable parallelism
- Delegated tasks must be impossible to misread
- No `ui/` work in this unit; no browser before/after screenshots required

---

## Overview

After the canonical contract in `[lib/agent_id.py](lib/agent_id.py)` and rollout-safe `[Agent](simulation/core/models/agent.py)` validation landed, the next step is to stop **emitting** non-canonical IDs from every code path that creates or imports agents: API user-agent creation, the one-off Bluesky profile migration job, and local-dev JSON seeding. Persisted databases may still contain legacy rows until a future primary-key migration runs; this unit only changes **what new writes produce** and **what committed fixtures contain**, plus minimal test updates where assertions pin the old strings.

---

## Happy Flow

1. **API create:** `[create_agent](simulation/api/services/agent_command_service.py)` calls `canonical_agent_id()` (no source) instead of `uuid.uuid4().hex`, then builds `[Agent](simulation/core/models/agent.py)`, `[AgentBio](simulation/core/models/agent_bio.py)`, and `[UserAgentProfileMetadata](simulation/core/models/user_agent_profile_metadata.py)` with that single canonical `agent_id` (row `id` fields may remain UUID-hex; only `agent_id` semantics are in scope per [strategy proposal](strategy_planning/2026-03-20_agent_id_migration/proposal.md)).
2. **Profile migration job:** `[main](jobs/migrate_agents_to_new_schema.py)` computes `canonical_id = canonical_agent_id(profile.did)` once per profile and uses it for `Agent`, `AgentBio`, and `UserAgentProfileMetadata`, including `get_latest_agent_bio` / `get_by_agent_id` lookups that currently key by raw DID.
3. **Local dev seed:** JSON under `[simulation/local_dev/seed_fixtures/](simulation/local_dev/seed_fixtures/)` stores only `^[0-9a-f]{16}$` values in every `agent_id` / `follower_agent_id` / `target_agent_id` column across `[agents.json](simulation/local_dev/seed_fixtures/agents.json)`, `[agent_persona_bios.json](simulation/local_dev/seed_fixtures/agent_persona_bios.json)`, `[user_agent_profile_metadata.json](simulation/local_dev/seed_fixtures/user_agent_profile_metadata.json)`, and `[agent_follow_edges.json](simulation/local_dev/seed_fixtures/agent_follow_edges.json)`. Optional: `[_load_fixtures](simulation/local_dev/seed_loader.py)` asserts or normalizes so legacy literals cannot slip back in silently.
4. **Verification:** Targeted pytest + ruff/pyright on touched modules; fixtures digest in `[_fixtures_digest](simulation/local_dev/seed_loader.py)` changes, so developers with an existing local DB follow existing `LOCAL_RESET_DB` workflow.

---

## Interface or contract freeze

- **Frozen imports:** `canonical_agent_id`, `is_canonical_agent_id` from `[lib/agent_id.py](lib/agent_id.py)` only.
- **Frozen non-goals (explicit exclusions):** no edits to `[db/schema.py](db/schema.py)`, no new Alembic revisions under `[db/migrations/versions/](db/migrations/versions/)`, no changes to action generators, query services, or SQLite adapters/repositories listed as out-of-scope in the [strategy proposal](strategy_planning/2026-03-20_agent_id_migration/proposal.md).
- **Determinism:** migration and any fixture rewrite must use `canonical_agent_id(stable_source_string)`—for fixtures, `canonical_agent_id(legacy_agent_id_string)` per legacy ID gives a stable 1:1 map across all JSON files.

---

## Serial coordination spine

1. **Define fixture ID map:** List every unique legacy `agent_*` ID in seed JSON; assign `new_id = canonical_agent_id(old_id)` (same for all files so cross-references stay consistent). `[generated_feeds.json](simulation/local_dev/seed_fixtures/generated_feeds.json)` is handle-based only; no change unless a field is added later elsewhere.
2. **Land independent code paths** (API service and migration job can proceed in parallel after the map is agreed—no shared files).
3. **Apply fixture rewrites + seed_loader hardening + `[tests/local_dev/test_local_mode_seed.py](tests/local_dev/test_local_mode_seed.py)`** (hardcoded `agent_0240dc0d4a4c7e73` must become the new canonical value for Alice’s row).
4. **Update `[tests/jobs/test_migrate_agents_to_new_schema.py](tests/jobs/test_migrate_agents_to_new_schema.py)`** assertions from raw DIDs to `canonical_agent_id("did:plc:...")`.
5. **Scoped sweep:** `rg` for `agent_id=` / `_generate_agent_id` under `simulation/api/services/`, `jobs/`, `simulation/local_dev/` only; fix any remaining bypasses. Do **not** bulk-rewrite the rest of `tests/` (many `did:plc:` mocks are intentionally deferred until the FK migration and broader test pass).

---

## Parallel task packets

### Packet P1 — API agent creation


| Field                  | Content                                                                                                                                                                                                                                                                                                                         |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Task ID**            | `P1-api-canonical-agent-id`                                                                                                                                                                                                                                                                                                     |
| **Objective**          | Persist only canonical 16-char hex `agent_id` for POST `/v1/simulations/agents`.                                                                                                                                                                                                                                                |
| **Why parallelizable** | Single file `[simulation/api/services/agent_command_service.py](simulation/api/services/agent_command_service.py)`; no overlap with job or seed fixtures.                                                                                                                                                                       |
| **Inspect**            | Above file; `[lib/agent_id.py](lib/agent_id.py)`.                                                                                                                                                                                                                                                                               |
| **Allowed to change**  | `[simulation/api/services/agent_command_service.py](simulation/api/services/agent_command_service.py)`                                                                                                                                                                                                                          |
| **Forbidden**          | DB schema/migrations; `[simulation/core/services/command_service.py](simulation/core/services/command_service.py)` (out of scope).                                                                                                                                                                                              |
| **Preconditions**      | Contract helpers merged.                                                                                                                                                                                                                                                                                                        |
| **Dependencies**       | None.                                                                                                                                                                                                                                                                                                                           |
| **Implementation**     | Replace `[_generate_agent_id](simulation/api/services/agent_command_service.py)` body with `return canonical_agent_id()`; add `from lib.agent_id import canonical_agent_id`; drop `uuid` import only if no longer needed for bio/metadata row `id` fields (those still use `uuid.uuid4().hex` today—likely keep `uuid` import). |
| **Verification**       | `uv run pytest tests/api/test_simulation_agents.py -v`                                                                                                                                                                                                                                                                          |
| **Expected**           | All pass; POST success path still 201; no response schema change (still no `agent_id` in public body if unchanged today).                                                                                                                                                                                                       |
| **Done when**          | No `uuid.uuid4().hex` used for **agent_id** generation in this service.                                                                                                                                                                                                                                                         |
| **Coordinator review** | Grep file for `uuid4`—only non–agent-id uses remain.                                                                                                                                                                                                                                                                            |


### Packet P2 — Profile migration job


| Field                  | Content                                                                                                                                                                                                                                                                                                                                   |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Task ID**            | `P2-migrate-job-canonical-did`                                                                                                                                                                                                                                                                                                            |
| **Objective**          | Store `canonical_agent_id(profile.did)` everywhere the job currently uses `profile.did` as `agent_id`.                                                                                                                                                                                                                                    |
| **Why parallelizable** | Touches only `[jobs/migrate_agents_to_new_schema.py](jobs/migrate_agents_to_new_schema.py)` and its test file.                                                                                                                                                                                                                            |
| **Inspect**            | Job file; `[tests/jobs/test_migrate_agents_to_new_schema.py](tests/jobs/test_migrate_agents_to_new_schema.py)`.                                                                                                                                                                                                                           |
| **Allowed to change**  | `[jobs/migrate_agents_to_new_schema.py](jobs/migrate_agents_to_new_schema.py)`, `[tests/jobs/test_migrate_agents_to_new_schema.py](tests/jobs/test_migrate_agents_to_new_schema.py)`                                                                                                                                                      |
| **Forbidden**          | Repositories/adapters (behavior change only via job).                                                                                                                                                                                                                                                                                     |
| **Preconditions**      | Contract helpers merged.                                                                                                                                                                                                                                                                                                                  |
| **Dependencies**       | None (parallel with P1).                                                                                                                                                                                                                                                                                                                  |
| **Implementation**     | Introduce `canonical_id = canonical_agent_id(profile.did)` after profile loop start; use for `Agent`, `AgentBio`, metadata, and `get_latest_agent_bio` guard; update test expected IDs to `canonical_agent_id("did:plc:alice123")` and `canonical_agent_id("did:plc:bob456")` (import helper in test or inline constants from one place). |
| **Verification**       | `uv run pytest tests/jobs/test_migrate_agents_to_new_schema.py -v`                                                                                                                                                                                                                                                                        |
| **Done when**          | Job never writes raw DID into `agent_id` columns.                                                                                                                                                                                                                                                                                         |
| **Coordinator review** | Single `canonical_id` variable per iteration—no duplicate `canonical_agent_id(profile.did)` calls that could drift.                                                                                                                                                                                                                       |


### Packet P3 — Seed fixtures, loader, local dev tests


| Field                  | Content                                                                                                                                                                                                                                                                                               |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Task ID**            | `P3-seed-fixtures-canonical`                                                                                                                                                                                                                                                                          |
| **Objective**          | Committed seed data uses canonical IDs only; loader optionally enforces; local mode tests updated.                                                                                                                                                                                                    |
| **Why parallelizable** | After P1/P2 merge or in branch with clean base; **do not parallelize editing the same JSON with another packet.**                                                                                                                                                                                     |
| **Inspect**            | `[simulation/local_dev/seed_loader.py](simulation/local_dev/seed_loader.py)`; four JSON files listed above; `[tests/local_dev/test_local_mode_seed.py](tests/local_dev/test_local_mode_seed.py)`.                                                                                                     |
| **Allowed to change**  | `[simulation/local_dev/seed_fixtures/*.json](simulation/local_dev/seed_fixtures/)` (subset with agent FKs), `[simulation/local_dev/seed_loader.py](simulation/local_dev/seed_loader.py)`, `[tests/local_dev/test_local_mode_seed.py](tests/local_dev/test_local_mode_seed.py)`                        |
| **Forbidden**          | Adapters outside seed loader’s direct use.                                                                                                                                                                                                                                                            |
| **Preconditions**      | Fixture ID map from serial spine.                                                                                                                                                                                                                                                                     |
| **Dependencies**       | None vs P1/P2 logically, but integrate after P1/P2 to run full suite.                                                                                                                                                                                                                                 |
| **Implementation**     | Replace every legacy `agent`_* id with `canonical_agent_id(that_string)` consistently; update SQL params in local dev tests; optionally after building `Agent` in `_load_fixtures`, `assert is_canonical_agent_id(...)` or normalize with one clear policy (prefer fail-fast for committed fixtures). |
| **Verification**       | `uv run pytest tests/local_dev/test_local_mode_seed.py -v`                                                                                                                                                                                                                                            |
| **Done when**          | No `agent_` prefix remains in those four fixtures; tests use new literals or `canonical_agent_id` for assertions.                                                                                                                                                                                     |
| **Coordinator review** | Grep `seed_fixtures` for `agent_` or `did:` in agent-key fields—should be empty.                                                                                                                                                                                                                      |


---

## Integration order

1. Merge **P1** and **P2** (order arbitrary).
2. Land **P3** (fixtures + loader + local tests).
3. Run combined targeted suite:

```bash
uv run pytest tests -k "agent_id or simulation_agents or migrate_agents_to_new_schema or local_mode_seed" -v
```

1. Run lint/type on touched paths:

```bash
uv run ruff check simulation/api/services/agent_command_service.py jobs/migrate_agents_to_new_schema.py simulation/local_dev/seed_loader.py tests/jobs/test_migrate_agents_to_new_schema.py tests/local_dev/test_local_mode_seed.py
uv run pyright simulation/api/services/agent_command_service.py jobs simulation/local_dev tests/jobs tests/local_dev
```

---

## Manual verification

- `uv run pytest tests/api/test_simulation_agents.py tests/jobs/test_migrate_agents_to_new_schema.py tests/local_dev/test_local_mode_seed.py -v` — all pass
- `uv run pytest tests -k "agent_id" -v` — contract tests still pass
- `rg "uuid4().hex" simulation/api/services/agent_command_service.py` — not used for `_generate_agent_id` (line 104–106 region removed/refactored)
- `rg "agent_0240dc0d4a4c7e73" simulation/local_dev/seed_fixtures` — zero matches after rewrite
- Confirm no migration files or `db/schema.py` changes: `git diff --name-only | rg "db/migrations|db/schema"` — empty
- Optional full gate: `uv run pre-commit run --all-files` and `uv run pyright .` before merge (per [AGENTS.md](AGENTS.md))

---

## Final verification

- API-created agents persist 16-char hex `agent_id` only.
- Migration job writes canonical IDs derived from `profile.did`.
- Local seed fixtures and loader path emit canonical IDs only for agent-key fields; local dev tests align.
- `[tests/jobs/test_migrate_agents_to_new_schema.py](tests/jobs/test_migrate_agents_to_new_schema.py)` asserts canonical IDs, not raw DIDs.
- No schema/migration/adapter edits in this unit.

---

## Alternative approaches

- **Chosen:** Rewrite committed JSON to canonical values using `canonical_agent_id(legacy_id)` for a deterministic internal map—simple to verify and consistent with “one helper.”
- **Not chosen:** Loader-only normalization without updating JSON—hides drift between disk and DB and makes reviews harder; acceptable only as a temporary safety net alongside rewrites, not instead of them.
- **Deferred:** Bulk replacement of `did:plc:` in all integration tests and `[tests/factories/records.py](tests/factories/records.py)`—large churn, overlaps FK migration and dedicated test/verification work; keep this unit focused on creation paths listed in the proposal.

---

## Plan asset storage

Implementation notes and optional ID mapping scratchpad:

`docs/plans/2026-03-20_normalize_agent_creation_paths_582941/`

(No UI screenshots; backend/fixtures only.)

---

## Risks (from proposal, condensed)

- **Fixture/test churn:** Updating four JSON files changes `[_fixtures_digest](simulation/local_dev/seed_loader.py)`; developers need DB reset—document in commit message.
- **Identity note:** Hashing `profile.did` is stable; hashing handles for other paths is not—this unit sticks to DID for the migration job and legacy string for fixture mapping as above.
