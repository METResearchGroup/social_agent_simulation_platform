---
name: Unit 1 Feed Algorithms Backend Refactor
overview: Migrate feeds from the monolithic `feeds/feed_generator.py` + `feeds/algorithms.py` setup to a registry-based architecture mirroring `simulation/core/action_generators`, add algorithm metadata, and expose `GET /v1/simulations/feed-algorithms` for the frontend.
todos:
  - id: create-algorithms-package
    content: Create feeds/algorithms/ package (interfaces.py, validators.py, __init__.py)
    status: completed
  - id: implement-chronological
    content: Implement feeds/algorithms/implementations/chronological.py with generate() and METADATA
    status: completed
  - id: create-registry
    content: Create feeds/algorithms/registry.py with get_registered_algorithms() and get_feed_generator()
    status: completed
  - id: refactor-feed-generator
    content: Refactor feeds/feed_generator.py to use registry, remove _FEED_ALGORITHMS
    status: completed
  - id: update-validators-models
    content: Update simulation/core/validators.py and simulation/core/models/runs.py to import from feeds.algorithms
    status: completed
  - id: add-feed-algorithms-endpoint
    content: Add GET /v1/simulations/feed-algorithms route, FeedAlgorithmSchema, and handler
    status: completed
  - id: remove-old-algorithms-file
    content: Delete feeds/algorithms.py (old top-level file) after package is in place
    status: completed
isProject: false
---

# Unit 1: Backend Refactor – Feeds Registry + Metadata

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

---

## Overview

Migrate feed algorithms from the current module-level `_FEED_ALGORITHMS` dict in [feeds/feed_generator.py](feeds/feed_generator.py) to a registry-based architecture under `feeds/algorithms/`, mirroring [simulation/core/action_generators](simulation/core/action_generators). This enables metadata (display_name, description) per algorithm and prepares for feed algorithm selection in the frontend (Unit 2). We also add `GET /v1/simulations/feed-algorithms` so the UI can fetch algorithm options with metadata.

**Current state:** `feeds/algorithms.py` is empty; `feeds/feed_generator.py` imports `generate_chronological_feed` and fails. The chronological logic must be implemented as part of this migration (behavior is defined by [tests/feeds/test_feed_generator.py](tests/feeds/test_feed_generator.py): sort by `created_at` descending, limit 20, return `feed_id`, `agent_handle`, `post_uris`).

---

## Happy Flow

1. **Run creation** – `RunRequest` (POST /v1/simulations/run) accepts `feed_algorithm`; [simulation/api/schemas/simulation.py](simulation/api/schemas/simulation.py) validates via `validate_feed_algorithm` from [simulation/core/validators.py](simulation/core/validators.py) (which will import from `feeds.algorithms.validators` after refactor).
2. **Feed generation** – [feeds/feed_generator.py](feeds/feed_generator.py) calls `registry.get_feed_generator(feed_algorithm)` to obtain the algorithm, runs it on candidate posts, and persists `GeneratedFeed`.
3. **Algorithm metadata** – `GET /v1/simulations/feed-algorithms` calls `feeds.algorithms.registry.get_registered_algorithms()` and returns JSON `[{id, display_name, description, config_schema}]`.

---

## Target Structure

```
feeds/
├── __init__.py
├── algorithms/
│   ├── __init__.py
│   ├── interfaces.py        # FeedAlgorithmMetadata, FeedGenerator protocol
│   ├── registry.py          # FEED_ALGORITHMS, get_registered_algorithms(), get_feed_generator()
│   ├── validators.py        # FEED_ALGORITHMS tuple + validate_feed_algorithm()
│   └── implementations/
│       ├── __init__.py
│       └── chronological.py # generate() + METADATA
├── feed_generator.py        # Uses registry.get_feed_generator(), no _FEED_ALGORITHMS
├── candidate_generation.py
└── ...
```

---

## Implementation Steps

### 1. Create `feeds/algorithms/` package

- Create `feeds/algorithms/__init__.py` exporting `get_registered_algorithms`, `get_feed_generator`, `validate_feed_algorithm`.
- Create `feeds/algorithms/interfaces.py`:
  - `FeedAlgorithmMetadata` (TypedDict): `display_name`, `description`, optional `config_schema`.
  - `FeedGenerator` protocol or abstract class with `generate(candidate_posts, agent, **kwargs) -> dict` returning `{feed_id, agent_handle, post_uris}`.
- Create `feeds/algorithms/validators.py`:
  - `FEED_ALGORITHMS: tuple[str, ...] = ("chronological",)`
  - `validate_feed_algorithm(value: str | None) -> str | None` using `validate_value_in_set` with the registry’s allowed keys (to avoid circular imports, validators can use `FEED_ALGORITHMS` tuple).

### 2. Implement chronological algorithm

- Create `feeds/algorithms/implementations/__init__.py`.
- Create `feeds/algorithms/implementations/chronological.py`:
  - `ALGORITHM_ID = "chronological"`
  - `METADATA: FeedAlgorithmMetadata = {"display_name": "Chronological", "description": "Posts sorted by creation time, newest first. Up to 20 posts per feed."}`
  - `MAX_POSTS_PER_FEED = 20`
  - `generate(candidate_posts, agent, limit=MAX_POSTS_PER_FEED, **kwargs) -> dict`: sort by `created_at` desc, slice `[:limit]`, return dict with `feed_id` (from `GeneratedFeed.generate_feed_id()`), `agent_handle`, `post_uris`.
- Remove or repurpose `feeds/algorithms.py` (the old top-level file). If it exists and is empty, delete it after the new package is in place.

### 3. Create registry

- Create `feeds/algorithms/registry.py`:
  - Import implementations and build `_ALGORITHM_LOOKUP: dict[str, tuple[Callable, FeedAlgorithmMetadata]]`.
  - `get_registered_algorithms() -> list[tuple[str, FeedAlgorithmMetadata]]` (id + metadata).
  - `get_feed_generator(algorithm: str)` returns the callable (no caching needed per MIGRATE_ALGOS; generators are stateless).
  - `FEED_ALGORITHMS: tuple[str, ...]` derived from registry keys for validators.

### 4. Refactor feed_generator

- In [feeds/feed_generator.py](feeds/feed_generator.py): remove `_FEED_ALGORITHMS` and `from feeds.algorithms import generate_chronological_feed`.
- In `_generate_feed`: call `registry.get_feed_generator(feed_algorithm)` and use `validate_value_in_set` with `registry.FEED_ALGORITHMS` (or delegate validation to validators).
- Ensure `_generate_feed` continues to call the algorithm with `candidate_posts` and `agent`, and wrap the returned dict into `GeneratedFeed`.

### 5. Update validators and models

- [simulation/core/validators.py](simulation/core/validators.py): change `validate_feed_algorithm` to import from `feeds.algorithms.validators` (or `feeds.algorithms.registry`) instead of `feeds.feed_generator`.
- [simulation/core/models/runs.py](simulation/core/models/runs.py): change `RunConfig` and `Run` field validators to import `validate_feed_algorithm` from `feeds.algorithms.validators` (or keep using `simulation.core.validators.validate_feed_algorithm` if that re-exports from feeds).

Prefer: keep `simulation.core.validators.validate_feed_algorithm` as the public API and have it call `feeds.algorithms.validators.validate_feed_algorithm` to avoid coupling simulation to feeds structure.

### 6. Add GET /v1/simulations/feed-algorithms

- Add `FeedAlgorithmSchema` in [simulation/api/schemas/simulation.py](simulation/api/schemas/simulation.py): `id`, `display_name`, `description`, `config_schema` (optional).
- Add route constant `SIMULATION_FEED_ALGORITHMS_ROUTE = "GET /v1/simulations/feed-algorithms"` in [simulation/api/routes/simulation.py](simulation/api/routes/simulation.py).
- Add handler `get_simulation_feed_algorithms` that calls `get_registered_algorithms()` and maps to `FeedAlgorithmSchema` list.
- Wire route: `@router.get("/simulations/feed-algorithms", response_model=list[FeedAlgorithmSchema], ...)`.

---

## Manual Verification

- Run feed generator tests: `uv run pytest tests/feeds/test_feed_generator.py -v` — all pass.
- Run validators tests: `uv run pytest tests/simulation/core/test_action_generators_validators.py -v` (if any feed-specific validators exist) and simulation run tests: `uv run pytest tests/api/test_simulation_run.py -v` — pass.
- Run full test suite: `uv run pytest -v` — no regressions.
- Start server: `uv run uvicorn simulation.main:app --reload`
- Call `GET /v1/simulations/feed-algorithms`: `curl -s http://localhost:8000/v1/simulations/feed-algorithms` — returns 200 with `[{"id":"chronological","display_name":"Chronological","description":"...","config_schema":null}]`.
- Call `POST /v1/simulations/run` with `{"num_agents": 1, "num_turns": 1, "feed_algorithm": "chronological"}` — returns 200.
- Call `POST /v1/simulations/run` with `{"num_agents": 1, "feed_algorithm": "invalid"}` — returns 422.

---

## Alternative Approaches

- **Class-based vs callable algorithms:** MIGRATE_ALGOS uses a callable with metadata (simpler than action_generators’ class-per-type). Kept for YAGNI.
- **config.yaml:** Action generators use `config.yaml` for defaults. Deferred as optional; feed algorithm default is hardcoded `"chronological"` in `RunConfig` / `RunRequest`.

---

## Plan Asset Path

```
docs/plans/2026-02-19_feed_algorithms_unit1_backend_<6-digit hash>/
```

(No UI screenshots for Unit 1 — backend-only.)