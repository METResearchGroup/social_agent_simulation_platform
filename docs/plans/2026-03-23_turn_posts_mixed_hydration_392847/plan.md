---
name: turn_posts mixed hydration
description: "Add turn_posts read path and mixed-ID resolver so feed-visible post IDs hydrate from run_posts and turn_posts; wire query service and engine."
tags: [plan, simulation, persistence, turns, feeds]
overview: "Implement the fifth milestone from [strategy_planning/2026-03-22_v2_refactor_turn_tables/proposal.md](strategy_planning/2026-03-22_v2_refactor_turn_tables/proposal.md): add a `turn_posts` read path and a single mixed-ID resolver so feed-visible post IDs hydrate from both `run_posts` and `turn_posts`, without authored-post generation or UI changes. Schema and atomic writes are already present at head; this slice is persistence interfaces plus query/engine hydration."
todos:
  - id: freeze-contracts
    content: Document resolver order + missing-ID behavior; align TurnPostSnapshot with db/schema turn_posts
    status: pending
  - id: packet-a-domain
    content: Add TurnPostSnapshot + turn_post_snapshot_to_post + unit tests
    status: pending
  - id: packet-b-repo
    content: Add TurnPostRepository ABC, SQLite adapter, integration tests
    status: pending
  - id: packet-c-wire
    content: Mixed hydration in query_service + engine; extend factories/DI
    status: pending
  - id: verify
    content: Run pytest/ruff; add docs/plans/2026-03-23_turn_posts_mixed_hydration_392847/ plan+verification with front matter
    status: pending
isProject: false
---

# `turn_posts` foundation and mixed post resolution

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- Maximum safely delegable parallelism
- Delegated tasks must be impossible to misread

## Overview

The strategy proposal’s fifth milestone closes the gap between an **empty-but-real** `[turn_posts](db/schema.py)` table and a **working read path**: introduce a persisted-row model and repository surface for `turn_posts`, implement **one resolver** that maps feed-visible IDs to hydrated `[Post](simulation/core/models/posts.py)` objects using both `run_posts` and `turn_posts` (per [docs/architecture/turn-feed-post-id-contract.md](docs/architecture/turn-feed-post-id-contract.md)), and wire `[SimulationQueryService.get_turn_data](simulation/core/services/query_service.py)` (and the run-scoped engine helper that resolves post IDs) so feeds and actions stay consistent with the shared namespace. **No** `TurnAction.POST` generation, **no** `[simulation/core/models/actions.py](simulation/core/models/actions.py)` or `[simulation/core/action_generators/](simulation/core/action_generators/)`, and **no** `[ui/](ui/)` changes—authored-post generation remains the optional later milestone in the same strategy doc.

**Baseline at head (verified via repo search):** `[turn_posts](db/schema.py)` exists; `[SimulationQueryService](simulation/core/services/query_service.py)` docstring still states `turn_posts` is not used; there is **no** `TurnPost*` symbol under `[db/repositories/](db/repositories/)`.

## Happy flow

1. A caller requests turn data via `[SimulationQueryService.get_turn_data](simulation/core/services/query_service.py)` (or `[SimulationEngine.get_turn_data](simulation/core/engine.py)`, which delegates to it).
2. Generated feeds and actions load from `turn_generated_feeds` / `turn_*` tables as today.
3. The union of feed `post_ids` and action `post_id` values is passed through a **mixed resolver** that loads matching rows from `[RunPostRepository.read_run_posts_by_ids](db/repositories/interfaces.py)` and a new `**TurnPostRepository.read_turn_posts_by_ids`** (scoped by `run_id`, and keyed by `turn_post_id`).
4. Each row maps to `[Post](simulation/core/models/posts.py)` via existing `run_post_snapshot_to_post` and a new `**turn_post_snapshot_to_post`** (or equivalent) that preserves mandatory `author_agent_id` and stable `post_id`/`uri` rules for API consumers.
5. Feed ordering is preserved; IDs missing from both stores are skipped (or handled per tests—see contracts below).
6. `[SimulationEngine.read_posts_for_run](simulation/core/engine.py)` uses the **same** resolution rules so `[get_posts_by_ids](simulation/api/services/run_query_service.py)` stays correct for run-scoped ID lookups without requiring API signature changes (engine-only change is preferred over touching the proposal’s “forbidden” list unless a gap is discovered in review).

## Serial coordination spine

1. **Freeze resolver contracts** (lookup order, missing-ID behavior, engagement counts for turn posts)—see “Interface or contract freeze.”
2. Add **domain model** for persisted `turn_posts` rows (mirror `[RunPostSnapshot](simulation/core/models/run_posts.py)` patterns; file may be new e.g. `simulation/core/models/turn_posts.py` or adjacent module—match repo style).
3. Add `**TurnPostRepository` + SQLite adapter** implementation following existing adapter/repository patterns (see `[db/adapters/sqlite/run_post_adapter.py](db/adapters/sqlite/run_post_adapter.py)` as reference).
4. Extend **DI**: `[simulation/core/factories/query_service.py](simulation/core/factories/query_service.py)` and any composition root that builds `SimulationQueryService` / `SimulationEngine` must receive the new repository.
5. Implement **mixed hydration** in `get_turn_data` and align `read_posts_for_run` with the same helper to avoid drift.
6. **Tests** proving mixed IDs, order, and missing IDs; then run the manual verification commands.

## Interface or contract freeze

- **Shared namespace:** `turn_generated_feeds.post_ids`, `turn_likes.post_id`, and `turn_comments.post_id` remain one feed-visible vocabulary ([turn-feed-post-id-contract.md](docs/architecture/turn-feed-post-id-contract.md)).
- **No polymorphic FK:** resolution stays in application code.
- **Mandatory `author_agent_id`** on turn-authored hydrated posts (table already enforces NOT NULL).
- **Lookup strategy (must be explicit in code + tests):** e.g. for each ID, resolve via `run_posts` first, then `turn_posts` for remaining IDs **or** document a disjoint-ID invariant—pick one approach and test the edge case where an ID exists in neither table (typically: omit post from hydrated list; document).
- **Engagement counts:** `[run_post_like_repo](db/repositories/interfaces.py)` / `[run_post_comment_repo](db/repositories/interfaces.py)` apply to **run** snapshots only; for `turn_posts` rows, use **zero** like/reply counts unless/until turn-scoped engagement storage exists (avoid inventing new tables in this slice).
- **Out of scope:** `[simulation/core/models/actions.py](simulation/core/models/actions.py)`, `[simulation/core/action_generators/](simulation/core/action_generators/)`, `[ui/](ui/)`, migrations (schema already landed).

## Parallel task packets

### Packet A — Domain mapping

- **Objective:** Define `TurnPostSnapshot` (frozen pydantic) and `turn_post_snapshot_to_post(...) -> Post` with validators aligned to `[db/schema.py` `turn_posts` columns](db/schema.py).
- **Parallelizable:** Yes, if it only adds new types and pure functions; no DB writes.
- **Inspect:** `[simulation/core/models/posts.py](simulation/core/models/posts.py)`, `[simulation/core/models/run_posts.py](simulation/core/models/run_posts.py)`, `[PostSource](simulation/core/models/posts.py)`.
- **Change:** `[simulation/core/models/posts.py](simulation/core/models/posts.py)` and new model file as needed; **forbid** touching repositories in the same commit if using strict parallel ownership—otherwise serialize after interface sketch.
- **Forbidden:** `[db/schema.py](db/schema.py)`, adapters.
- **Preconditions:** None.
- **Verification:** `uv run pytest tests/simulation/core -q` (targeted new tests once added).
- **Done when:** Snapshot + mapper round-trip unit tests pass; `Post` invariants satisfied.

### Packet B — Repository + SQLite adapter

- **Objective:** Implement `TurnPostRepository` ABC in `[db/repositories/interfaces.py](db/repositories/interfaces.py)` and SQLite read path (e.g. `[db/adapters/sqlite/turn_post_adapter.py](db/adapters/sqlite/turn_post_adapter.py)` + wiring in the repository concrete class pattern used elsewhere).
- **Parallelizable:** After Packet A’s row shape is stable **or** interface uses dict/tuple until model lands—prefer serial dependency on `TurnPostSnapshot` to avoid churn.
- **Inspect:** `[db/adapters/sqlite/run_post_adapter.py](db/adapters/sqlite/run_post_adapter.py)`, `[db/repositories/run_post_repository.py](db/repositories/run_post_repository.py)` (or equivalent), `[db/schema.py` `turn_posts](db/schema.py)`.
- **Change:** `db/repositories/interfaces.py`, new adapter/repository files under `db/`; **forbid** `simulation/core/services/query_service.py` until Packet C.
- **Preconditions:** `TurnPostSnapshot` field list matches columns.
- **Verification:** `uv run pytest tests/db/repositories -k "turn_post" -q` (add integration test reading known IDs from SQLite).

### Packet C — Query service + engine integration

- **Objective:** Wire mixed resolution into `[SimulationQueryService.get_turn_data](simulation/core/services/query_service.py)` and `[SimulationEngine.read_posts_for_run](simulation/core/engine.py)`; extend `[create_query_service](simulation/core/factories/query_service.py)` and engine construction sites.
- **Parallelizable:** No—depends on Packet B (and Packet A for mapping).
- **Inspect:** `[simulation/core/services/query_service.py](simulation/core/services/query_service.py)`, `[simulation/core/engine.py](simulation/core/engine.py)`, app factory wiring (grep `create_query_service`, `SimulationEngine(`).
- **Change:** query service, engine, factories/composition; tests under `[tests/simulation/core/test_query_service.py](tests/simulation/core/test_query_service.py)`, `[tests/api/test_run_query_service.py](tests/api/test_run_query_service.py)` as needed.
- **Forbidden:** `[ui/](ui/)`, action generators.

## Integration order

Packet A → Packet B → Packet C → full pytest sweep for touched areas.

## Final verification

- Proposal-suggested commands (adapted to repo paths):
  - `uv run pytest tests/simulation/core/test_query_service.py tests/api/test_run_query_service.py tests/db/repositories -k "post" -q`
  - Broader safety: `uv run pytest tests/simulation/core tests/api -q` (time permitting)
- **Expected:** all pass; new tests cover mixed `run_post_id` + `turn_post_id` in one feed and missing-ID behavior.

## Alternative approaches

- **Resolver inside `RunPostRepository`:** Rejected—mixes two physical tables behind a misnamed interface; a dedicated `TurnPostRepository` keeps boundaries clear (matches the strategy proposal’s “new files if cleaner”).
- **Polymorphic FK in SQLite:** Rejected—explicitly out of architecture ([turn-feed-post-id-contract.md](docs/architecture/turn-feed-post-id-contract.md)).
- **Extend API with `turn_number` for `get_posts_by_ids`:** Deferred unless engine-level resolution proves insufficient; prefer engine changes first to stay within the proposal’s allowed-file list.

## Manual verification (checklist)

- `uv sync --extra test` (if deps unchanged, skip)
- `uv run pytest tests/simulation/core/test_query_service.py tests/api/test_run_query_service.py tests/db/repositories -k "post" -q` — expect: **0 failures**
- Add/confirm targeted tests: same feed contains both ID kinds; stable ordering; missing ID does not crash
- `uv run ruff check .` on touched Python files (repo gate)
- Optional: `uv run pyright .` on touched paths if your workflow requires it

## Plan asset storage

Save working notes, verification logs, and any diagrams under:

`docs/plans/2026-03-23_turn_posts_mixed_hydration_392847/`

Include `plan.md` and `verification.md` with YAML front matter (`description`, `tags`) per [AGENTS.md](AGENTS.md); run `uv run python scripts/check_docs_metadata.py` on those paths before merge.

**UI:** Not in scope—no `images/before` or `images/after` requirement.

## Gaps and clarifications (non-blocking)


| Topic                                                                                                                                | Recommendation                                                                                                                                                                                                                                                                                                              |
| ------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **ID collision** between `run_post_id` and `turn_post_id` strings                                                                    | Document and test lookup order (e.g. run-first, then turn) or prove disjoint ID generation; do not leave implicit.                                                                                                                                                                                                          |
| **Proposal allowed-files list** omits `[simulation/api/services/run_query_service.py](simulation/api/services/run_query_service.py)` | Prefer fixing `[SimulationEngine.read_posts_for_run](simulation/core/engine.py)` so `[get_posts_by_ids](simulation/api/services/run_query_service.py)` inherits mixed resolution without API edits. If `turn_number` is ever required for disambiguation, revisit—**PK `turn_post_id` should normally suffice** per schema. |
| `**[feed_post_repository](db/repositories/feed_post_repository.py)`** listed in proposal                                             | Only touch if a shared resolver is placed there; likely **out of scope** for run/turn persisted posts.                                                                                                                                                                                                                      |

No blocking questions unless you require **API-visible** `turn_number` on post-by-ID endpoints for a specific client contract.
