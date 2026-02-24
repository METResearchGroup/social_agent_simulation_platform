# Add pagination for agent listing (GET `/v1/simulations/agents`)
#
## Remember
- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
#
## Overview
Add offset/limit pagination to the simulation agent listing endpoint to keep the API scalable as agent counts grow. Keep the response shape as `list[AgentSchema]` for minimal API churn, but enforce a default `limit=100` (when callers provide no query params). Update the UI to support incremental loading (“Load more”) so the default limit does not hide agents beyond the first page. Add repository/adapter support so pagination is done in SQL (not “read all then slice”).
#
## Public API / Contract changes
### `GET /v1/simulations/agents`
- **New query params**
  - `limit`: `int`, default `100`, constraints `1 <= limit <= 500`
  - `offset`: `int`, default `0`, constraint `offset >= 0`
- **Response**: unchanged (`200 -> AgentSchema[]`)
- **Behavior**:
  - Results remain ordered by `handle` ascending (deterministic).
  - Returns up to `limit` agents, skipping the first `offset`.
#
## Happy Flow
1. UI calls `GET /v1/simulations/agents?limit=100&offset=0` via `ui/lib/api/simulation.ts:getAgents`.
2. FastAPI route `simulation/api/routes/simulation.py:get_simulation_agents()` validates `limit`/`offset` and calls `_execute_get_simulation_agents(limit, offset)`.
3. `_execute_get_simulation_agents` runs `simulation/api/services/agent_query_service.py:list_agents(limit=..., offset=...)` inside `asyncio.to_thread`.
4. `list_agents` calls `db/repositories/agent_repository.py:list_agents_page(limit, offset)` which uses `LIMIT/OFFSET` in SQLite.
5. `list_agents` batch-fetches bios + metadata for just those agent IDs, maps to `simulation/api/schemas/simulation.py:AgentSchema`.
6. UI renders the first page; when the user clicks “Load more”, UI requests the next page with `offset += 100` and appends.
#
## Data Flow
1. `AgentRepository.list_agents_page()` returns a deterministic slice ordered by `handle` (SQL `ORDER BY handle LIMIT ? OFFSET ?`).
2. `list_agents()` hydrates just that slice via `AgentBioRepository.get_latest_bios_by_agent_ids()` and `UserAgentProfileMetadataRepository.get_metadata_by_agent_ids()` to avoid N+1.
3. The API returns a plain JSON array of `AgentSchema` (no wrapper), so pagination is client-driven via query params.
#
## Manual verification (commands)
- Backend tests:
  - `uv run pytest tests/db/repositories/test_agent_repository_integration.py -v`
  - `uv run pytest tests/api/test_simulation_agents.py -v`
- OpenAPI regeneration:
  - `cd ui && npm run generate:api`
  - `cd ui && npm run check:api`
- UI build:
  - `cd ui && npm run lint:all`
  - `cd ui && npm run build`
