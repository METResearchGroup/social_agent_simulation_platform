---
name: View Agents Feature
overview: Add a top-left "View runs" | "View agents" toggle. When "View agents" is active, show an agent list sidebar and main-area agent detail (reusing AgentDetail with metadata, Feed, Liked Posts, Comments). Uses existing GET /v1/simulations/agents; Feed/Likes/Comments show empty in agent-only context.
todos:
  - id: before-screenshots
    content: Capture before screenshots to docs/plans/2026-02-23_view_agents_feature_a1b2c3/images/before/
    status: completed
  - id: hook-view-mode
    content: Add viewMode, selectedAgentHandle, handleSetViewMode, handleSelectAgent to useSimulationPageState
    status: completed
  - id: sidebar-toggle
    content: Add View runs | View agents toggle and agent list to RunHistorySidebar
    status: completed
  - id: agents-view
    content: Create AgentsView component with AgentDetail (feed=[], actions=[], allPosts=[])
    status: completed
  - id: page-wire
    content: Wire viewMode and AgentsView into page.tsx
    status: completed
  - id: verify-tests
    content: Run lint, pytest, pre-commit; verify manual flow
    status: completed
  - id: after-screenshots
    content: Capture after screenshots to docs/plans/2026-02-23_view_agents_feature_a1b2c3/images/after/
    status: completed
isProject: false
---

# View Agents Feature Implementation Plan

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

---

## Overview

Add a "View runs" | "View agents" toggle at the top-left of the simulation UI. When "View agents" is selected, the sidebar displays the list of agents (from `GET /v1/simulations/agents`), and the main area shows the selected agent's profile in the same collapsible style used in turn detail (AgentDetail). Agent Metadata is fully populated; Feed, Liked Posts, and Comments show empty (0) because those are turn-scoped. Reuse existing `getAgents()`, `AgentDetail`, and `CollapsibleSection`; no new backend endpoints.

---

## Architecture

```mermaid
flowchart TB
    subgraph Page [ui/app/page.tsx]
        viewMode[viewMode: runs or agents]
        contentSwitch{viewMode}
    end

    subgraph Sidebar [RunHistorySidebar]
        Toggle[View runs | View agents toggle]
        RunList[Run list when runs]
        AgentList[Agent list when agents]
        Toggle --> RunList
        Toggle --> AgentList
    end

    subgraph Main [Main content]
        StartOrDetail[StartView or RunDetailView when runs]
        AgentsView[AgentsView when agents]
        contentSwitch --> StartOrDetail
        contentSwitch --> AgentsView
    end

    subgraph AgentsViewContent [AgentsView component]
        AgentDetailCard[AgentDetail feed=[] actions=[] allPosts=[]]
        selectedAgent[selectedAgent from agents]
        selectedAgent --> AgentDetailCard
    end

    getAgents[getAgents GET /simulations/agents] --> agents
    agents --> AgentList
    agents --> selectedAgent
```



---

## Happy Flow

1. User is on simulation page (authenticated). Top-left shows "View runs" | "View agents" toggle; default is "View runs" (current behavior).
2. User clicks "View agents". Sidebar switches to agent list; main area shows AgentsView.
3. Sidebar fetches agents via `getAgents()` (already in [ui/hooks/useSimulationPageState.ts](ui/hooks/useSimulationPageState.ts)); loading/error/empty states mirror RunHistorySidebar.
4. User clicks an agent. Main area shows that agent's detail via [ui/components/details/AgentDetail.tsx](ui/components/details/AgentDetail.tsx) with `feed=[], actions=[], allPosts=[]` (metadata populated; Feed/Likes/Comments show 0 and "No liked posts", "No comments").
5. User clicks "View runs". Sidebar and main content revert to run history and run detail.
6. Deterministic ordering: backend returns agents sorted by handle; no frontend sort change needed.

---

## File Changes

### 1. State and Hook

- **File:** [ui/hooks/useSimulationPageState.ts](ui/hooks/useSimulationPageState.ts)
  - Add `viewMode: 'runs' | 'agents'` state (default `'runs'`).
  - Add `selectedAgentHandle: string | null` (default `null`).
  - Add `handleSetViewMode(mode: 'runs' | 'agents')`.
  - Add `handleSelectAgent(handle: string | null)`.
  - Include `handleRetryAgents` in return (already exists; ensure exported).
  - Expose `viewMode`, `selectedAgentHandle`, `handleSetViewMode`, `handleSelectAgent`, `agents`, `agentsLoading`, `agentsError`, `handleRetryAgents` (most already exposed).

### 2. Sidebar with Toggle

- **File:** [ui/components/sidebars/RunHistorySidebar.tsx](ui/components/sidebars/RunHistorySidebar.tsx)
  - Add props: `viewMode`, `onSetViewMode`, `agents`, `agentsLoading`, `agentsError`, `onRetryAgents`, `selectedAgentHandle`, `onSelectAgent`.
  - Add toggle at top of header (above "Run History"): two buttons "View runs" and "View agents", styled like tabs; active state via `viewMode`.
  - When `viewMode === 'agents'`: render agent list content (mirror run list: loading spinner when `agentsLoading && agents.length === 0`, error + Retry when `agentsError`, "No agents" when `agents.length === 0`, otherwise map agents to buttons with `agent.name`, `agent.handle`; `data-testid={`agent-${agent.handle}`}`).
  - When `viewMode === 'runs'`: keep current run list content.
  - Keep "Start New Run" only when `viewMode === 'runs'`.
  - Match loading/error/empty/retry patterns from existing run list per [docs/RULES.md](docs/RULES.md) (Frontend — Consistency).

### 3. AgentsView Component

- **File:** Create `ui/components/agents/AgentsView.tsx`
  - Props: `agents`, `selectedAgentHandle`, `agentsLoading`, `agentsError`, `onRetryAgents`, `onSelectAgent`.
  - If no agent selected: center message "Select an agent to view details".
  - If selected: find agent by handle; render `AgentDetail` with `agent`, `feed={[]}`, `actions={[]}`, `allPosts={[]}`.
  - Loading: `agentsLoading && agents.length === 0` → LoadingSpinner + "Loading agents…".
  - Error: show message + Retry (same pattern as [ui/components/sidebars/RunHistorySidebar.tsx](ui/components/sidebars/RunHistorySidebar.tsx)).

### 4. Page Layout

- **File:** [ui/app/page.tsx](ui/app/page.tsx)
  - Consume `viewMode`, `selectedAgentHandle`, `handleSetViewMode`, `handleSelectAgent`, `agents`, `agentsLoading`, `agentsError`, `handleRetryAgents` from `useSimulationPageState`.
  - Pass new props to `RunHistorySidebar`.
  - When `viewMode === 'agents'`: render `AgentsView` in main area instead of StartView / RunDetailView.
  - When `viewMode === 'runs'`: keep existing StartView / RunDetailView flow.

### 5. No Backend Changes

- Existing [simulation/api/routes/simulation.py](simulation/api/routes/simulation.py) `GET /v1/simulations/agents` and [ui/lib/api/simulation.ts](ui/lib/api/simulation.ts) `getAgents()` are sufficient.

---

## Manual Verification

1. **Before screenshots**
  - Run `npm run dev` in `ui/`, ensure backend running (e.g. `uv run uvicorn simulation.api.main:app --reload`).
  - Capture current UI: Run History sidebar, run list, run detail with turn selected showing agent cards. Save to `docs/plans/2026-02-23_view_agents_feature_a1b2c3/images/before/`.
2. **Toggle and View agents**
  - Click "View agents". Sidebar shows agent list; main area shows "Select an agent to view details".
  - Click an agent (e.g. Alice Chen). Agent detail appears with Metadata (Name, Bio, Generated Bio, Followers, Following, Posts) and collapsible Feed (0), Liked Posts (0), Comments (0).
  - Click "View runs". UI returns to run history.
3. **Loading and error**
  - In DevTools, throttle network; reload. While loading, see "Loading agents…" in sidebar when View agents.
  - Simulate 500 from `/simulations/agents`; verify error message and Retry button.
4. **Tests and lint**
  - `cd ui && npm run lint` (no errors).
  - `cd /Users/mark/Documents/work/agent_simulation_platform && uv run pytest tests/ -v -x -q` (existing tests pass).
  - `uv run pre-commit run --all-files` (pass).
5. **After screenshots**
  - Capture new UI: View agents with agent selected, View runs. Save to `docs/plans/2026-02-23_view_agents_feature_a1b2c3/images/after/`.

---

## Alternative Approaches

- **Separate route for agents:** Rejected to avoid routing complexity; toggle keeps a single page.
- **Aggregate Feed/Likes/Comments for agents:** Would require new endpoints and aggregation logic; out of scope for MVP. Empty sections with 0 counts are acceptable.
- **Wire agents API to AgentRepository from PR #91:** Optional follow-up; current `list_agents_dummy` and endpoint are sufficient for this feature.

---

## Plan Asset Storage

```
docs/plans/2026-02-23_view_agents_feature_a1b2c3/
├── view_agents_plan.md (this plan)
└── images/
    ├── before/
    │   └── (current UI screenshots)
    └── after/
        └── (new UI screenshots)
```

