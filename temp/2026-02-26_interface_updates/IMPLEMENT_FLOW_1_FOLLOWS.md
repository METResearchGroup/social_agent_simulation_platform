## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- UI changes: agent captures before/after screenshots itself (no README or instructions for the user)

## Overview

Flow 1 (Follows) PR 1 adds a **“Follows” dropdown** (collapsible section) to the **agent detail view** in the UI, showing a **count** and a **paginated list** of follows using **mock data** (10 rows per page, 5 pages hydrated by default). This establishes the reusable “viewer component” pattern that will later be applied to Followers/Likes/Comments and can be reused for Start Simulation’s “Select Agents” view.

## Scope

- **In scope (PR 1)**:
  - Add a new **Follows** section in `ui/components/details/AgentDetail.tsx`.
  - Show **count** in the header (e.g. `Follows (50)`).
  - Render a **paginated** list with mock follow rows: **10 rows/page**, **5 pages** (50 total).
  - Ensure the UI is deterministic and demoable.
- **Out of scope (PR 1)**:
  - Backend/API wiring for real follows.
  - Persisting follows.
  - Add/remove follows (this is PR 3 per the proposal).
  - “Followers” section (Flow 2).

## Existing code to build on (current state)

- **Agent detail UI**:
  - `ui/components/details/AgentDetail.tsx` already uses `CollapsibleSection` for:
    - `Feed`
    - `Liked Posts`
    - `Comments`
  - `ui/components/details/CollapsibleSection.tsx` supports `count?: number` and formats headings as `${title} (${count})`.
- **UI list patterns**:
  - There is no general pagination component yet.
  - The closest “paging” pattern is “Load more” in `ui/components/sidebars/RunHistorySidebar.tsx` for agents.
- **Backend persistence (important for later PRs)**:
  - A run-scoped follow action table already exists:
    - Migration: `db/migrations/versions/b8e4d1f2a3c6_add_likes_comments_follows_tables.py`
    - Schema source-of-truth: `db/schema.py` (table `follows`)
    - Repository: `db/repositories/follow_repository.py`
    - SQLite adapter: `db/adapters/sqlite/follow_adapter.py`
  - Current follow model uses `user_id` as the follow target:
    - Domain: `simulation/core/models/actions.py` (`class Follow`)
    - Generator: `simulation/core/action_generators/follow/algorithms/random_simple.py` sets `user_id = post.author_handle`
  - Run-turn API currently returns empty `agent_actions`:
    - `simulation/api/services/run_query_service.py` sets `agent_actions={}` in turn payloads.

## Happy Flow (PR 1, UI-only mock)

1. User navigates to **View agents** in the UI (`ui/components/sidebars/RunHistorySidebar.tsx`).
2. User selects an agent; `ui/components/agents/AgentsView.tsx` renders `ui/components/details/AgentDetail.tsx`.
3. In `AgentDetail`, user expands **Follows**:
   - The section header shows `Follows (50)` (or whatever mock count is).
   - The body shows page 1 with **10 rows**.
   - User navigates across **5 pages** and sees the rows update.

## Plan assets

- Store screenshots in:
  - `docs/plans/2026-03-08_agent_follows_dropdown_185185/images/before/`
  - `docs/plans/2026-03-08_agent_follows_dropdown_185185/images/after/`

## Implementation plan (PR 1)

### 1) Capture “before” screenshots (mandatory first step)

- Capture baseline images showing:
  - View agents sidebar with a selected agent
  - Current agent detail view with an existing section expanded (e.g. “Liked Posts”) to show styling baseline
- Save as:
  - `docs/plans/2026-03-08_agent_follows_dropdown_185185/images/before/view-agents-agent-detail.png`
  - `docs/plans/2026-03-08_agent_follows_dropdown_185185/images/before/agent-detail-expanded-section.png`

### 2) Introduce a reusable paginated viewer primitive

Because this “paginated hydrated list” pattern will be reused in:

- Flow 1 Follows
- Flow 2 Followers
- Flow 3 Likes
- Flow 4 Comments
- Start Simulation “Select Agents” (see `temp/2026-02-26_interface_updates/PROPOSED_START_SIMULATION_FLOW.md`)

…add a small UI primitive (recommended):

- Add: `ui/components/details/PaginatedViewer.tsx`

Proposed API:

- Props:
  - `items: T[]`
  - `pageSize: number` (PR 1 uses 10)
  - `renderRow: (item: T) => React.ReactNode`
  - `getKey: (item: T) => string`
  - `emptyState?: React.ReactNode`
- Behavior:
  - Internal `pageIndex` state (0-indexed)
  - Controls: `Prev`, `Next`, and numeric buttons `1..N`
  - Disabled states at bounds
  - Optional helper text (e.g. `Showing 11–20 of 50`)

### 3) Add deterministic mock follow data

Option A (recommended):

- Add: `ui/lib/mocks/mockFollows.ts`

Option B (minimal files):

- Keep mock builder local to `ui/components/details/AgentDetail.tsx`

Requirements:

- Deterministic per `agent.handle` (stable across rerenders)
- Exactly **50** follow rows so pagination is 10 rows × 5 pages

Example mock row shape:

- `handle` (target handle)
- `displayName`
- `createdAt` (optional; can be a placeholder if not displayed)

### 4) Add “Follows” section to agent detail UI

- Update: `ui/components/details/AgentDetail.tsx`
  - Extend `ExpandedSectionsState` with `follows: boolean`
  - Add a new `CollapsibleSection`:
    - `title="Follows"`
    - `count={mockFollows.length}`
  - Render the list via `PaginatedViewer`:
    - `pageSize={10}`
    - Show simple row UI consistent with existing beige styles (`bg-beige-50`, `border-beige-200`, `text-beige-*`)

### 5) “Show that this works” (verification affordances)

Add stable selectors (optional but helpful):

- `data-testid="agent-detail-follows"`
- `data-testid="agent-detail-follows-page-prev"`
- `data-testid="agent-detail-follows-page-next"`
- `data-testid="agent-detail-follows-row-${handle}"`

### 6) Capture “after” screenshots (mandatory last step)

- Save:
  - `docs/plans/2026-03-08_agent_follows_dropdown_185185/images/after/agent-detail-follows-collapsed.png`
  - `docs/plans/2026-03-08_agent_follows_dropdown_185185/images/after/agent-detail-follows-page-1.png`
  - `docs/plans/2026-03-08_agent_follows_dropdown_185185/images/after/agent-detail-follows-page-5.png`

## Manual Verification

- [ ] Start API:
  - `PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload`
  - Confirm health: open `http://localhost:8000/health` and see success
- [ ] Start UI:
  - `cd ui && npm run dev`
- [ ] Navigate to **View agents**
- [ ] Select an agent
- [ ] Expand **Follows (50)**
  - [ ] Page 1 shows 10 rows
  - [ ] Navigate pages 2–5; rows update; bounds disable prev/next appropriately
- [ ] Lint UI:
  - `cd ui && npm run lint:all`
  - Expect: exit code 0

## Persistence / DB direction (for PR 2+ / PR 3)

### Current DB reality

The repo already has run-scoped persisted follows:

- Table: `follows` with `run_id` (NOT NULL) and `turn_number` (NOT NULL)
  - Migration: `db/migrations/versions/b8e4d1f2a3c6_add_likes_comments_follows_tables.py`
  - Schema: `db/schema.py`
- Repository/adapter:
  - `db/repositories/follow_repository.py`
  - `db/adapters/sqlite/follow_adapter.py`

This table is clearly an **event log for simulation turns**, not an editable user-managed social graph.

### Recommended approach: separate “manual social graph” from “simulation follow actions”

Instead of retrofitting run/turn nullability + `source` into the existing action table, introduce a new table to represent the editable “agent follows” relationship used by the agent-detail editor.

Example future schema:

- `agent_follow_edges` (or `manual_follows`)
  - `id` (pk)
  - `agent_handle` (the agent being edited; follower)
  - `target_handle` (who they follow; could be another agent or external handle)
  - `source` enum: `manual` | `simulation` (optional; if the table is manual-only, source can be constant)
  - `created_at`
  - `created_by_app_user_id` (optional auditing)

Proposed API for later PRs:

- `GET /v1/simulations/agents/{handle}/follows?limit=&offset=`
- `POST /v1/simulations/agents/{handle}/follows`

### Why not “just add a source enum to follows table”?

Because `db/schema.py` and the migration model `follows` as **run-turn action rows**:

- mixing long-lived editable state (“manual follows”) with run-scoped events (“simulation follows”) tends to complicate constraints, queries, and UI expectations.
- SQLite migrations to make run/turn nullable plus backfilling constraints are doable but higher-risk than adding a new clean table.

## Alternative approaches

- **Minimal PR 1**: no `PaginatedViewer` component; inline pagination directly in `ui/components/details/AgentDetail.tsx`.
  - Faster now, but will duplicate logic across Followers/Likes/Comments and Start Simulation “Select Agents”.
- **Use “Load more” instead of pagination**:
  - Simpler UI, but doesn’t meet the explicit “5 pages hydrated” requirement and makes later parity across dropdowns harder.
