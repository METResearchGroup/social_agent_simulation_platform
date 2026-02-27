---
name: flow0-pr1-create-agent-submit
description: "Simplify the Create Agent flow and make newly created agents appear first in the listing."
tags:
  - ui
  - backend
  - docs
overview: "Implement Flow 0 / PR 1 from `temp/2026-02-26_interface_updates/PROPOSED_AGENT_DETAIL_MIGRATION.md`: simplify the “Create Agent” UI by removing the unused “History” and “Link to existing agents” sections, and ensure “Submit” reliably creates an agent that immediately appears in the “View agents” UI (even when local seed data contains >100 agents) by changing agent list ordering to newest-first."
todos:
  - id: screenshots-before
    content: Capture before screenshots of the current UI happy path (Create agent form showing “History” + “Link to existing agents”, and the post-submit/agents view state) and save into `docs/plans/2026-02-26_flow0_pr1_create_agent_submit_739214/images/before/`.
    status: in_progress
  - id: ui-remove-history-link
    content: Update `ui/components/agents/CreateAgentView.tsx` (and its call site in `ui/app/page.tsx`) to remove the “History” and “Link to existing agents” sections and delete now-dead state/props/imports.
    status: pending
  - id: backend-newest-first-order
    content: Change agent list ordering to `updated_at DESC, handle ASC` in `db/adapters/sqlite/agent_adapter.py`, and update docstrings in `db/repositories/interfaces.py`, `db/repositories/agent_repository.py`, and `simulation/api/services/agent_query_service.py`.
    status: pending
  - id: update-api-tests
    content: Update `tests/api/test_simulation_agents.py` expectations for newest-first ordering and ensure pagination/query tests remain deterministic.
    status: pending
  - id: screenshots-after
    content: Capture after screenshots of the updated UI happy path (Create agent form without the two sections, and successful submit showing the created agent in View agents) and save into `docs/plans/2026-02-26_flow0_pr1_create_agent_submit_739214/images/after/`.
    status: pending
isProject: false
---

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- UI changes: agent captures before/after screenshots itself (no README or instructions for the user)

## Overview

Flow 0 / PR 1 is about making “Create Agent” a clean, working path: remove two non-persisted sections (“History” and “Link to existing agents”) from the create form, and make sure a newly-created agent shows up immediately in the “View agents” list/detail after submit. Today, `GET /v1/simulations/agents` is ordered by handle, so a newly-created agent may not land in the first page when local seed fixtures contain many agents; we’ll switch ordering to **newest-first** (updated_at desc, handle asc) so the freshly created agent is returned in the initial page and can be selected/rendered.

## Happy Flow

1. User opens the UI root route (`/`) implemented by `[ui/app/page.tsx](ui/app/page.tsx)` and switches `viewMode` to `create-agent`.
2. The create form component `[ui/components/agents/CreateAgentView.tsx](ui/components/agents/CreateAgentView.tsx)` renders only the core fields (handle, display name, bio) and a Submit button (no “History”, no “Link to existing agents”).
3. On submit, `[ui/app/page.tsx](ui/app/page.tsx)` calls `postAgent()` from `[ui/lib/api/simulation.ts](ui/lib/api/simulation.ts)`, which performs `POST /v1/simulations/agents`.
4. Backend route handler in `[simulation/api/routes/simulation.py](simulation/api/routes/simulation.py)` validates `CreateAgentRequest` and invokes `create_agent()` in `[simulation/api/services/agent_command_service.py](simulation/api/services/agent_command_service.py)` to persist agent + bio + metadata in one transaction.
5. UI switches `viewMode` to `agents` and selects the created handle. The agents list refresh calls `GET /v1/simulations/agents` (via `getAgents()` in `[ui/lib/api/simulation.ts](ui/lib/api/simulation.ts)`).
6. Backend agent listing (`list_agents()` in `[simulation/api/services/agent_query_service.py](simulation/api/services/agent_query_service.py)`) returns the first page ordered newest-first; the created agent is included and thus appears in `[ui/components/agents/AgentsView.tsx](ui/components/agents/AgentsView.tsx)` and detail renders via `[ui/components/details/AgentDetail.tsx](ui/components/details/AgentDetail.tsx)`.

## Implementation Plan

### Assets (required)

- Plan assets directory:
  - `docs/plans/2026-02-26_flow0_pr1_create_agent_submit_739214/`
  - Before screenshots: `docs/plans/2026-02-26_flow0_pr1_create_agent_submit_739214/images/before/`
  - After screenshots: `docs/plans/2026-02-26_flow0_pr1_create_agent_submit_739214/images/after/`

### UI: Remove “Link to existing agents” and “History” from Create Agent

- Update `[ui/components/agents/CreateAgentView.tsx](ui/components/agents/CreateAgentView.tsx)`
  - Delete the two `CollapsibleSection` blocks:
    - `title="History"` (currently uses `comments`, `likedPostUris`)
    - `title="Link to existing agents"` (currently uses `linkedAgentHandles`, `SearchInput`, `LoadingSpinner`, and agent list paging props)
  - Remove now-dead state + helpers:
    - `comments`, `likedPostUris`, `linkedAgentHandles`
    - `historyOpen`, `linkOpen`
    - `handleAddComment`, `handleRemoveComment`, `handleCommentChange`, `handleLinkedAgentToggle`, and `createCommentEntry()`
  - Simplify `CreateAgentViewProps` to only what the PR1 form needs:
    - keep `onSubmit({handle, displayName, bio})`
    - remove all props supporting the removed link/history UI (`agents`, `agentsLoading`*, `agentsError`, `agentsHasMore`, `agentsQuery`, `onRetryAgents`, `onLoadMoreAgents`, `onAgentsQueryChange`)
  - Remove unused imports (`LoadingSpinner`, `CollapsibleSection`, `SearchInput`, `Agent`) once the UI sections are deleted.
- Update call site in `[ui/app/page.tsx](ui/app/page.tsx)`
  - Update `<CreateAgentView ... />` to pass only the new required props.

### Backend: Make agent list newest-first so created agent is visible

Goal: ensure that immediately after `POST /v1/simulations/agents`, the subsequent `GET /v1/simulations/agents?limit=100&offset=0` includes the newly created agent.

- Change SQLite agent read ordering in `[db/adapters/sqlite/agent_adapter.py](db/adapters/sqlite/agent_adapter.py)`
  - Update these queries to:
    - `ORDER BY updated_at DESC, handle ASC`
  - Affected methods:
    - `read_all_agents()`
    - `read_agents_page()`
    - `read_agents_page_by_handle_like()`
- Update ordering descriptions in:
  - `[db/repositories/interfaces.py](db/repositories/interfaces.py)` (AgentRepository docstrings)
  - `[db/repositories/agent_repository.py](db/repositories/agent_repository.py)` (method docstrings)
  - `[simulation/api/services/agent_query_service.py](simulation/api/services/agent_query_service.py)` (function docstring and module-level comments)

### Tests: Update API ordering expectations

- Update `[tests/api/test_simulation_agents.py](tests/api/test_simulation_agents.py)` to match the new deterministic ordering.
  - Replace “sorted by handle” assertions with “sorted by updated_at desc, handle asc”.
  - Update pagination and `q` pagination expectations to reflect newest-first ordering (still deterministic because of the `handle ASC` tie-break).
  - Add/adjust at least one test that demonstrates “newly created agent appears on first page” under the new ordering semantics.

## Manual Verification (checklist)

- **Backend**
  - Install deps:

```bash
    uv sync --extra test
    

```

```
Expected: completes successfully.
```

- Run API in local mode (auth bypass enabled via `LOCAL=true`):

```bash
    LOCAL=true PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload
    

```

```
Expected: server starts; `GET http://localhost:8000/health` returns `{"status":"ok"}`.
```

- Run targeted tests:

```bash
    uv run pytest -q tests/api/test_simulation_agents.py
    

```

```
Expected: all pass.
```

- **UI**
  - Install UI deps:

```bash
    cd ui && npm install
    

```

- Run UI in local mode (frontend auth bypass enabled by `LOCAL=true` in `[ui/next.config.ts](ui/next.config.ts)`):

```bash
    cd ui && LOCAL=true NEXT_PUBLIC_SIMULATION_API_URL=http://localhost:8000/v1 npm run dev
    

```

```
Expected: Next dev server on `http://localhost:3000`.
```

- Click-through checks in the browser:
  - Open `http://localhost:3000`
  - Click **Create agent**
  - Confirm **no** “History” section exists
  - Confirm **no** “Link to existing agents” section exists
  - Enter:
    - Handle: `new-user-<unique>.bsky.social`
    - Display name: `New User`
    - Bio: optional
  - Click **Submit**
  - Confirm you land on **View agents** and the new agent is visible in the list (near the top due to newest-first ordering) and selectable; the detail panel shows the new agent.
- UI lint:

```bash
    cd ui && npm run lint:all
    

```

```
Expected: no errors.
```

- **Pre-commit (repo quality gate)**

```bash
uv run pre-commit run --all-files
```

Expected: all hooks pass.

## Alternative approaches

- **Frontend pin/merge only (not chosen)**: keep backend ordering by handle and add client-side logic to “pin” the created agent into the current list. This avoids API changes, but adds state complexity and can regress when agent lists refetch.
- **Backend newest-first (chosen)**: change the canonical ordering for `GET /v1/simulations/agents` to newest-first. This keeps UI simple and ensures the post-create refresh returns the created agent on the first page, at the cost of updating API tests and any consumers relying on handle ordering.

