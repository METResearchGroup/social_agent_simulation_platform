# Proposed app updates: mock social actions & scoped metrics

This document proposes **two separate workflows**: (1) richer, constraint-safe **seed** mock data via a **builder script** that emits like/comment/follow simulation records plus aligned metadata, and (2) turn-scoped vs run-scoped metrics using **Pattern A (metadata-first)** so stored metrics always derive from `TurnMetadata`, with UI work to surface values and tables.

The description below is anchored to the current architecture: seeded fixtures under `simulation/local_dev/seed_fixtures/`, turn payloads from `SimulationEngine.get_turn_data` serialized in `simulation/api/services/run_query_service.py`, action gating in `simulation/core/action_policy/candidate_filter.py` (`HistoryAwareActionFeedFilter`), and builtin metrics in `simulation/core/metrics/builtins/actions.py`.

---

## Workflow 1 — Mock data: likes, comments, and “no repeats” invariants

### Problem

- The run detail UI derives **“Liked Posts”** and **“Comments”** from **per-turn simulation actions** (`AgentAction` list), not from catalog tables such as `agent_post_likes` / `agent_post_comments` seeded by `simulation/local_dev/seed_loader.py` (those model a separate “social graph” on feed posts).
- Today, seeded runs can show **zero** likes/comments in the turn inspector if persisted turn actions do not include those types, even when catalog fixtures have likes/comments elsewhere.
- You want **non-duplicate** likes and comments **per agent per run**, and the same idea for follows: do not target a user the agent already follows **in that run**.

### How the product already enforces invariants (live simulation)

For runs executed by `SimulationCommandService._simulate_turn`:

1. **Candidate filtering** — `HistoryAwareActionFeedFilter.filter_candidates` removes feed posts the agent has already liked, already commented on, or whose author they already follow, using `ActionHistoryStore` (`has_liked`, `has_commented`, `has_followed`).
2. **Validation** — `simulation/core/action_policy/rules_validator.py` rejects duplicate targets in a single batch and re-checks history (e.g. previously liked posts).

So for **new runs**, the invariant is already “by design” as long as history is recorded every turn and feed posts carry correct `post_id` / `author_agent_id`.

### Gap: seeded / static “mock” runs

Fixture-backed runs must **manually** align:

- `turn_metadata.json` — `total_actions` per turn.
- Whatever backs `get_turn_data` (generated feeds, likes, comments, follows persisted for that run/turn — depending on your DB adapters and seed paths).
- `turn_metrics` / `run_metrics` — under **Workflow 2 Pattern A**, these are **derived** from `turn_metadata`, not authored separately (see below).

If action rows, metadata, and feeds drift relative to each other, the UI shows inconsistent counts; the builder and Pattern A are meant to prevent that.

### Decided approach — Richer *seed* data (deterministic demo DB)

This is the chosen path for Workflow 1 (not the “tune live generators” path).

1. **Authoring model**
   Treat each seeded run as a small timeline:

   - For each turn, for each participating agent, assign zero or more actions of types `like`, `comment`, `follow`, `post`.
   - **Global uniqueness per run**:
     - `(liker_agent_id, post_id)` at most once for likes.
     - `(commenter_agent_id, post_id)` at most once for comments.
     - `(follower_agent_id, target_agent_id)` at most once for follows (match how history keys follows — today via post author’s `agent_id` in `HistoryAwareActionFeedFilter`).

2. **Builder script (primary deliverable)**
   Add a **small builder script** (invoked via `uv run` or similar) that:

   - Reads agent IDs, post IDs, and feed membership from existing fixtures (and any other inputs the seed graph needs).
   - Emits, in one deterministic pass:
     - **`turn_metadata`** with correct `total_actions` per turn.
     - **Persisted simulation records for likes, comments, and follows** — i.e. whatever rows the DB and repositories need so `get_turn_data` / turn APIs return non-empty `GeneratedLike`, `GeneratedComment`, and `GeneratedFollow` actions for demo runs (plus feeds/posts alignment). The script output should feed the seed pipeline (JSON fixtures and/or documented steps) so the demo DB is internally consistent.
   - Optionally also emits companion JSON for generated feeds if the builder is the single place that defines which posts appear in which turn’s feed.

3. **Validation**
   Add a **`uv run` validation step** (script or check bundled with the builder) that **fails** if any duplicate `(agent, post)` or `(agent, follow_target)` appears across all turns of a run, or if emitted counts disagree with `turn_metadata`.

4. **Catalog tables**
   `agent_post_likes.json` / `agent_post_comments.json` remain optional background realism for non–run-detail features. The run-detail UI’s “Liked Posts” / “Comments” / follow-related views for seeded runs come from the **simulation action records** the builder maintains, not from those catalog files alone.

### Deferred (not part of this plan)

- **Tune live generators** (`generate_likes` / `generate_comments` / `generate_follows` probabilities) — can be a follow-up; invariants for executed runs remain covered by `HistoryAwareActionFeedFilter` and the rules validator today.

### Acceptance criteria (Workflow 1)

- For at least one seeded run, multiple turns show **non-zero** likes, comments, and follows for **some** agents (backed by persisted like/comment/follow records from the builder output).
- No seed output violates per-run uniqueness rules above; the validation step enforces it.
- Multi-turn tests or script checks still prove the **live** runtime path cannot double-like / double-comment / double-follow the same target in one run (unchanged product behavior).

---

## Workflow 2 — Metrics per turn vs per run, accurate and visible under “Agents”

### Current behavior (relevant pieces)

- **Computation** — Builtin metrics are defined in `simulation/core/metrics/builtins/actions.py`:
  - **Turn scope:** `turn.actions.counts_by_type`, `turn.actions.total` (the latter depends on the former).
  - **Run scope:** `run.actions.total_by_type`, `run.actions.total` (run rollup from **all** `TurnMetadata` rows via `run_repo.list_turn_metadata`).
- **Persistence** — `turn_metrics` / `run_metrics` tables (seeded from `turn_metrics.json` / `run_metrics.json` in local dev).
- **API** — `GET /v1/simulations/runs/{run_id}` returns `RunDetailsResponse` with `run_metrics` and `turns: TurnActionsItem[]` where each item includes `total_actions` and optional `metrics` (`run_query_service._build_turn_actions_items`).
- **API gap** — `GET` turns for a run returns `TurnSchema`, which includes `agent_feeds` and `agent_actions` but **does not** include the computed metric map (`ui/types/api.generated.ts` — `TurnSchema` vs `TurnActionsItem`).
- **UI gap** — `RunParametersBlock` shows **which** metric keys were selected (`metric_keys`), not the **values**. Run summary (`RunSummary`) does not surface `run_metrics`. Turn detail (`DetailsPanel` / `TurnDetailContent`) does not show per-turn stored metrics or a metrics table under **Agents**.

### Design goals

1. **Turn view** — Show **only** turn-scoped metrics for the selected turn (and optionally the raw `total_actions` for that turn — they should agree).
2. **Run summary view** — Show **only** run-scoped metrics (aggregates).
3. **Accuracy** — Stored `turn_metrics` / `run_metrics` must **match** recomputation from `TurnMetadata` using the same `MetricsRegistry` used at execution time (see **Pattern A** below).
4. **Agents section** — Add a **metrics table** (run summary and per-turn) that is easy to scan; content should reflect the scope (run vs turn).

### Single source of truth (backend) — **Pattern A (decided)**

**Pattern A — Metadata-first** is the chosen approach for Workflow 2 and applies everywhere: execution, seeding, and any future repair path.

- **Canonical counts** — `TurnMetadata.total_actions` is the single source of truth for action counts per turn.
- **Metric rows** — After each turn completes (and when building or refreshing seed data), run the **metric registry** to produce `TurnMetrics` for that turn and, after the final turn, `RunMetrics` for the run. Do **not** hand-edit `turn_metrics.json` / `run_metrics.json` as independent sources of truth.
- **Seed fixtures** — Either:
  - **generate** `turn_metrics.json` / `run_metrics.json` from `turn_metadata.json` using the same Python metric classes the engine uses, or
  - **omit** those JSON files from hand maintenance and **emit metric rows only inside `seed_loader`** (or the builder pipeline) immediately after `turn_metadata` is written.

This removes the class of bugs where `turn_metrics` says “2 likes” but `turn_metadata` says otherwise.

**Not in scope for this plan:** a separate “reconcile job” (Pattern B) that asserts equality after the fact — Pattern A makes that unnecessary if the pipeline always derives metrics from metadata.

### Per-agent breakdown (the table under “Agents”)

Run-level and turn-level **builtin** metrics today are **aggregates**, not per agent. To make the table meaningful and “accurate based on the state of the data”:

1. **Turn view table** — For the selected turn, derive rows **from `turn.agentActions`** (already loaded):

   | Agent | Likes | Comments | Follows | Posts |
   |-------|-------|----------|---------|-------|
   | …     | counts| …        | …       | …     |

   Totals row should equal `TurnActionsItem.total_actions` for that turn (and should equal the sum implied by `turn.actions.counts_by_type` if you map action types consistently).

2. **Run summary table** — Sum the same per-agent columns **across all turns** in the client (from cached turn payloads), **or** expose a small backend summary. Cross-check the grand totals against `run_metrics` (`run.actions.total_by_type` / `run.actions.total`).

3. **Optional future metric** — If you need per-agent metrics in the **metric registry** (for export, alerting), add new registered metrics with a clear scope (e.g. turn-scoped JSON map `agent_id -> counts`). That is a larger change; the table above can ship first without new metric keys.

### API / UI plumbing

1. **Minimize duplicate fetches** — `useSimulationPageState` already loads run details for config. **Reuse** `RunDetailsResponse.turns` (with `metrics` + `total_actions`) keyed by `turn_number` when rendering turn metrics, so the UI does not depend on extending `TurnSchema` unless you prefer a single endpoint.

2. **If you prefer one endpoint** — Add optional `metrics` (and maybe `total_actions`) to `TurnSchema` in OpenAPI, implement in `get_turns_for_run`, regenerate UI types. Tradeoff: larger payloads for large runs.

3. **Components** — Introduce something like `MetricsSummaryTable` (run vs turn props) and render it **below** the “Agents” heading in:

   - `RunSummary` — run metrics + optional per-agent **cumulative** table.
   - `TurnDetailContent` — turn metrics + per-agent **this turn** table.

4. **Run parameters strip** — Keep `metric_keys` as configuration context; add a short line “Values below” or move **values** only into the new tables to avoid duplicating four chip-like keys without numbers.

### Acceptance criteria (Workflow 2)

- Run summary shows **run-scoped** metric values (not only keys).
- Each turn view shows **turn-scoped** metric values for that turn only.
- Per-agent table matches actions visible in expanded agent cards for that scope.
- Seeded DB: `turn_metrics` / `run_metrics` are **always produced from** `turn_metadata` via Pattern A (no independent hand-editing of metric JSON).
- No turn-level-only keys shown as primary on the run summary, and vice versa.

---

## Proposed PR stack (ordered)

High-level breakdown for serial landing; each PR should be one reviewable unit. Subsequent agents can drill into file-level tasks and tests per PR.

### Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- Maximum safely delegable parallelism where PR boundaries allow
- **UI PR:** implementing agent’s **first** todo = capture **before** screenshots; **last** todo = capture **after** screenshots (store under `docs/plans/<YYYY-MM-DD>_<descriptor>_<6-digit hash>/images/before|after/` — see **Plan asset storage** below). Do not substitute with README instructions for the user.

### Overview

Ship **Pattern A** so metrics never drift from `TurnMetadata`, expose run- vs turn-scoped metric **values** and per-agent **tables** in the UI, then add a **deterministic seed builder** plus validation and regenerated fixtures so demo runs show realistic likes, comments, and follows without duplicate targets per agent per run.

### Happy flow (end-to-end)

1. **Execution path** — `SimulationCommandService` completes a turn → `TurnMetadata.total_actions` persisted → metric registry computes `TurnMetrics` (and eventually `RunMetrics` after final turn) → same shapes as today in `simulation/api/services/run_query_service.py` (`RunDetailsResponse`, `TurnActionsItem`).
2. **Seed path** — Builder script emits `turn_metadata` + simulation action records (likes, comments, follows, feeds as needed) under `simulation/local_dev/seed_fixtures/` → `simulation/local_dev/seed_loader.py` loads metadata and action rows → **Pattern A** derives `turn_metrics` / `run_metrics` rows (or generated JSON) from metadata, never independently authored.
3. **UI** — `GET /v1/simulations/runs/{run_id}` (already used for config) supplies `run_metrics` and `turns[].metrics` + `total_actions` → `useSimulationPageState` / run-detail context cache → `RunSummary` shows run-scoped values + cumulative per-agent table; `TurnDetailContent` shows turn-scoped values + this-turn per-agent table derived from `turn.agentActions`.

### Serial coordination spine

1. **PR1** must merge first (defines how metrics are produced for both live runs and seeds).
2. **PR2** and **PR3** can run in parallel **after PR1** (different primary directories: `ui/` vs `scripts/` + `simulation/local_dev/seed_fixtures/`). If one team owns both, keep **PR2 before PR3** so UI verification can use Pattern A + richer seeds from PR3 in one pass; otherwise UI can be validated against live completed runs before seed regeneration lands.
3. **PR4** is optional polish after PR2–PR3.

### Interface or contract freeze (for parallel work after PR1)

- Do not change `RunDetailsResponse` / `TurnActionsItem` field names without versioning discussion; UI work should consume existing OpenAPI shapes first.
- `TurnMetadata.total_actions` remains the canonical input to metric computation.

### Proposed PRs (in order)

#### PR1 — Pattern A: metrics from `TurnMetadata` (execution + seed)

- **Goal:** `TurnMetrics` and `RunMetrics` are always computed from `TurnMetadata` via the same `MetricsRegistry` / builtin metrics as in `simulation/core/metrics/builtins/actions.py` — for **both** post-turn persistence and **seed loading** (`simulation/local_dev/seed_loader.py`).
- **Primary touchpoints:** `simulation/core/services/command_service.py` (or the code path that finalizes a turn), `simulation/core/engine.py`, `simulation/local_dev/seed_loader.py`, `db/adapters/sqlite/metrics_adapter.py` (if inserts move), `simulation/local_dev/seed_fixtures/turn_metrics.json` and `run_metrics.json` (delete hand-maintenance or replace with generator output from metadata).
- **Tests:** `uv run pytest` for metrics and seed paths; add coverage that stored metrics match recomputation from `TurnMetadata` for a representative run.
- **Out of scope for this PR:** UI; Workflow 1 builder script (except whatever minimal hook is needed so seeds don’t hand-edit metrics).

#### PR2 — UI: metric values + per-agent tables (run summary + turn detail)

- **Goal:** Show **values** for run-scoped metrics on the run summary and turn-scoped metrics per turn; add **MetricsSummaryTable** (or equivalent) and per-agent breakdown tables under **Agents** per `PROPOSED_APP_UPDATES.md` Workflow 2.
- **Primary touchpoints:** `ui/hooks/useSimulationPageState.ts`, `ui/components/run-detail/RunDetailContext.tsx` (if present), `ui/components/details/RunSummary.tsx`, `ui/components/details/DetailsPanel.tsx`, `ui/components/details/TurnDetailContent` (inline or extracted), `ui/components/details/RunParametersBlock.tsx` (avoid duplicate empty chips vs tables), new table component(s) under `ui/components/details/`.
- **Data:** Prefer reusing `getRunDetails` / cached `RunDetailsResponse` for `run_metrics` and `turns[]` keyed by `turn_number` rather than extending `TurnSchema` unless a follow-up explicitly needs it.
- **Verification:** `cd ui && npm run lint:all`; manual clicks per **Manual verification** below; **before/after screenshots** in plan asset folder (implementing agent runs browser).

#### PR3 — Workflow 1: deterministic seed builder + validation + fixture regeneration

- **Goal:** Script(s) under `scripts/` emit aligned `turn_metadata`, persisted like/comment/follow (and feed) simulation records; validation rejects duplicate targets and count skew; regenerate `simulation/local_dev/seed_fixtures/` so at least one demo run shows non-zero likes, comments, and follows in the turn inspector.
- **Primary touchpoints:** new `scripts/` entry points (exact names TBD), `simulation/local_dev/seed_fixtures/*.json`, `simulation/local_dev/seed_loader.py` (only if loader must understand new artifact layout), `docs/architecture/simulation-actions-model.md` (align with `simulation/core/action_policy/candidate_filter.py` history keys).
- **Depends on:** PR1 (metrics derived from emitted `turn_metadata` — builder must not emit standalone metric JSON).
- **Tests / checks:** `uv run python scripts/<validator>.py` (or pytest) on fixtures; optional CI hook documented in PR description.

#### PR4 — (Optional) Hardening and follow-ups

- Wire validator into `uv run pre-commit` or CI if desired; tune live `simulation/core/agent_actions.py` generators; OpenAPI extend `TurnSchema` with metrics — only if product asks.

### Parallel task packets (after PR1)

| Packet | Can start after | Focus |
|--------|-----------------|--------|
| UI (PR2) | PR1 | `ui/` only; consumes stable API |
| Seeds (PR3) | PR1 | `scripts/`, `simulation/local_dev/seed_fixtures/`, docs architecture |

Avoid editing the same files in both packets without coordination (e.g. do not split `seed_loader.py` across two PRs without assignment).

### Integration order

1. Merge PR1 → run full Python test suite + local API smoke with seeded DB.
2. Merge PR2 and/or PR3 → full-stack manual pass: seeded run in UI shows metrics + tables; turn inspector shows likes/comments/follows after PR3 fixtures.
3. PR4 as needed.

### Manual verification (checklist)

#### Backend (PR1, PR3)

- [ ] `uv sync --extra test` then `uv run pytest` (scope to changed tests first, then broader if needed).
- [ ] `PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload` → `GET http://localhost:8000/health` → `GET /v1/simulations/runs/{run_id}` for a seeded run: `run_metrics` and `turns[].metrics` consistent with `turns[].total_actions`.

#### UI (PR2)

- [ ] `cd ui && npm run dev` and `npm run lint:all`.
- [ ] Select a **completed** run → **Run summary**: run-level metric **values** visible; per-agent cumulative table under Agents matches expanded cards across turns (sanity).
- [ ] Select **Turn N** → turn-level metric **values** only; per-agent table for **that turn** matches likes/comments/follows/posts in agent rows.
- [ ] Implementing agent: before/after screenshots stored under `docs/plans/<date>_<descriptor>_<hash>/images/`.

#### Seeds (PR3)

- [ ] Run validator script on fixtures; exit code 0.
- [ ] Fresh seed: `LOCAL_RESET_DB=1` (or project runbook) → reload app → open seeded run → non-zero actions in multiple turns.

### Alternative approaches (recap)

- **Extend `GET /v1/simulations/runs/{run_id}/turns` (`TurnSchema`) with metrics** instead of reusing run details — rejected for v1 in `PROPOSED_APP_UPDATES.md` to avoid payload duplication; revisit if clients need a single turns endpoint with metrics.
- **Per-agent metrics in the metric registry** — deferred; client-side aggregation from `agent_actions` is enough for the tables initially.

### Plan asset storage (implementation phase)

When execution starts, create `docs/plans/<YYYY-MM-DD>_<short-descriptor>_<6-digit-hash>/` for screenshots, notes, and any exported OpenAPI diffs. **Repository rule:** Markdown under `docs/plans/` needs YAML front matter (`description`, `tags`) per `AGENTS.md`; add it if you add new plan files there.

---

## Implementation order (legacy one-liner)

1. **PR1** — Pattern A backend
2. **PR2** — UI metrics + tables
3. **PR3** — Seed builder + validation + fixtures
4. **PR4** — Optional hardening

(Superseded by **Proposed PR stack** above for execution.)

---

## Out of scope (unless you explicitly want them later)

- Showing catalog `agent_post_likes` / `agent_post_comments` in the same UI sections as simulation actions (different semantics; would need copy and labeling).
- New metric types beyond action counts (engagement rates, feed position, etc.) — the same scoping rules would apply.
