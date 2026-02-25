# Agent search/filtering (handle-only)

## Overview
Add a case-insensitive, substring search to agent lists by extending `GET /v1/simulations/agents` with an optional `q` query param (handle-only). Wire the UI to expose “Search by handle” in both “View agents” and “Create agent → Link to existing agents”, keeping pagination + load-more working against filtered results.

## Happy Flow
1. **UI input** – User types into “Search by handle” in `ui/components/sidebars/RunHistorySidebar.tsx` or in Create Agent’s linking section `ui/components/agents/CreateAgentView.tsx` (shared `ui/components/ui/SearchInput.tsx`).
2. **State reset + fetch** – `ui/hooks/useSimulationPageState.ts` debounces query, resets agent pagination, and fetches `getAgents({ limit, offset: 0, q })` from `ui/lib/api/simulation.ts`.
3. **Backend route** – `simulation/api/routes/simulation.py` accepts `q` (max length 200) and calls the query service in `asyncio.to_thread(...)`.
4. **Query service + DB** – `simulation/api/services/agent_query_service.py` scrubs `q` into a safe LIKE pattern via `lib/sql_like.py` and queries SQLite via repo/adapter methods.
5. **Pagination** – “Load more” continues fetching additional pages using the same `q`.

## Query semantics
- **Matching:** case-insensitive substring match against `handle` only.
- **Wildcards:** `*` = any-length, `?` = single character.
- **Scrubbing:** SQL LIKE metacharacters are escaped so `%` / `_` are treated literally; only `*` / `?` are wildcards.
- **SQL:** SQLite uses `LIKE ? ESCAPE '\\' COLLATE NOCASE`, ordered by `handle` with `LIMIT/OFFSET`.

## Manual Verification
### Automated
- `uv sync --extra test`
- `uv run pytest -q` — all tests pass
- `uv run pre-commit run --all-files` — all hooks pass

### Backend (local)
- `DISABLE_AUTH=1 PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload`
- `curl -s "http://localhost:8000/v1/simulations/agents?limit=5&offset=0"` — 200 JSON list
- `curl -s "http://localhost:8000/v1/simulations/agents?q=a*social&limit=5&offset=0"` — filtered list
- `curl -s "http://localhost:8000/v1/simulations/agents?q=%25&limit=5&offset=0"` — `%` treated literally (not a wildcard)

### UI (local)
- `cd ui && NEXT_PUBLIC_DISABLE_AUTH=true npm run dev`
- Click **View agents** → type `ALPHA` → list filters
- Click **Create agent** → expand **Link to existing agents** → type `g*` → list filters; **Load more** works within filtered results
- Switch modes (Runs ↔ Agents ↔ Create agent) → query clears

## Alternative approaches considered
- UI-only filtering of already-loaded pages: smallest change, but incorrect at scale because it can’t search beyond loaded agents.
- Dedicated “agents index” endpoint: fast typeahead, but adds a second caching surface and still requires fetching large lists.

## Screenshots
- Before: `docs/plans/2026-02-25_agent_search_filtering_217714/images/before/`
- After: `docs/plans/2026-02-25_agent_search_filtering_217714/images/after/`

