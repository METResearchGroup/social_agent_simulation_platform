---
description: Implementation plan for the naive LLM-based like, comment, and follow generators with shared LLM helpers and E2E scripts.
tags: [plan, llm, action-generators, ai]
---

# Naive LLM Action Generators — Implementation Plan

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

---

## Overview

Add naive LLM-based action generators for like, comment, and follow. Each uses a single LLM call per `generate()` with simple prompts, Pydantic response schemas, and constructor-injected `LLMService` (Option B). Shared helpers (`_posts_to_minimal_json`, `_resolve_model_used`) live in `simulation/core/action_generators/utils/llm_utils.py`. E2E scripts run with real LLM access via `EnvVarsContainer` for `.env` loading.

---

## As-Implemented Details

### Directory Structure

```
simulation/core/action_generators/
  like/algorithms/
    random_simple.py           # existing
    naive_llm/
      __init__.py              # Exports NaiveLLMLikeGenerator
      algorithm.py             # Implementation (not naive_llm_algorithm.py)
      prompt.py                # LIKE_PROMPT
      response_models.py       # LikePrediction
      e2e_test_run.py          # Real LLM e2e (uses EnvVarsContainer)
  comment/algorithms/
    naive_llm/
      __init__.py, algorithm.py, prompt.py, response_models.py, e2e_test_run.py
  follow/algorithms/
    naive_llm/
      __init__.py, algorithm.py, prompt.py, response_models.py, e2e_test_run.py
  utils/
    __init__.py
    llm_utils.py               # _posts_to_minimal_json, _resolve_model_used
```

### Shared Utils

`simulation/core/action_generators/utils/llm_utils.py`:

- `_posts_to_minimal_json(posts: list[BlueskyFeedPost]) -> str` — serialize posts to minimal JSON
- `_resolve_model_used() -> str | None` — model identifier for metadata, or None if unavailable

Used by like and comment for `_posts_to_minimal_json`; all three use `_resolve_model_used`. Follow keeps `_authors_to_minimal_json` local (different input shape).

### E2E Scripts

Each `e2e_test_run.py`:

- Imports `EnvVarsContainer` from `lib.load_env_vars`
- Calls `EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)` at start of `main()` to load `.env` and validate
- Runs 3 `generate()` calls with mock candidates; prints results

### Files Created

| File | Purpose |
|------|---------|
| `simulation/core/action_generators/utils/__init__.py` | Package marker |
| `simulation/core/action_generators/utils/llm_utils.py` | Shared `_posts_to_minimal_json`, `_resolve_model_used` |
| `simulation/core/action_generators/like/algorithms/naive_llm/__init__.py` | Export `NaiveLLMLikeGenerator` |
| `simulation/core/action_generators/like/algorithms/naive_llm/algorithm.py` | Implementation |
| `simulation/core/action_generators/like/algorithms/naive_llm/prompt.py` | `LIKE_PROMPT` |
| `simulation/core/action_generators/like/algorithms/naive_llm/response_models.py` | `LikePrediction` |
| `simulation/core/action_generators/like/algorithms/naive_llm/e2e_test_run.py` | E2E with real LLM |
| Same pattern for `comment/` and `follow/` | 10 additional files |
| `tests/simulation/core/test_naive_llm_action_generators.py` | Unit tests (mock LLM) |

### Files Modified

| File | Change |
|------|--------|
| `simulation/core/action_generators/validators.py` | Add `"naive_llm"` to `LIKE_ALGORITHMS`, `FOLLOW_ALGORITHMS`, `COMMENT_ALGORITHMS` |
| `simulation/core/action_generators/registry.py` | Add `_create_naive_llm_like`, `_create_naive_llm_follow`, `_create_naive_llm_comment` factories |
| `tests/simulation/core/test_action_generators_registry.py` | Add `test_get_*_generator_naive_llm` for like, follow, comment |

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM coupling | Constructor injection | docs/RULES.md; testable without patching |
| Batching | One prompt per `generate()` | One call with list-shaped response |
| Algorithm filename | `algorithm.py` | Folder already named `naive_llm` |
| Env loading (e2e) | `EnvVarsContainer.get_env_var(...)` | Centralized loader from PR #100 |

---

## Happy Flow

1. `SocialMediaAgent.like_posts(feed)` → `get_like_generator(algorithm="naive_llm")` → `NaiveLLMLikeGenerator()` (or cached).
2. `generator.generate(candidates=feed, ...)` builds prompt via `_posts_to_minimal_json`, calls `llm_service.structured_completion(..., response_model=LikePrediction)`.
3. LLM returns `LikePrediction(post_ids=[...])`; generator filters to valid candidate IDs, builds `GeneratedLike` per post, sorts by `post_id`.
4. Same pattern for comment and follow; follow uses `_authors_to_minimal_json` for authors-only prompt.

---

## Manual Verification

### 1. Lint and format

```bash
uv run ruff check .
uv run ruff format --check .
```

Expected: All checks passed.

### 2. Type check

```bash
uv run pyright .
```

Expected: `0 errors, 0 warnings`.

### 3. Unit tests (mocked LLM)

```bash
uv run pytest tests/simulation/core/test_naive_llm_action_generators.py tests/simulation/core/test_action_generators_registry.py -v
```

Expected: 28 passed (13 naive_llm + 15 registry).

### 4. Full test suite

```bash
uv run pytest
```

Expected: All tests pass.

### 5. E2E scripts (real LLM)

Requires `OPENAI_API_KEY` in `.env` (loaded via `EnvVarsContainer`):

```bash
uv run python simulation/core/action_generators/like/algorithms/naive_llm/e2e_test_run.py
```

Expected: 3 blocks of output; each shows "Likes generated: N" and post_ids.

```bash
uv run python simulation/core/action_generators/comment/algorithms/naive_llm/e2e_test_run.py
```

Expected: 3 blocks; each shows "Comments generated: N" and (post_id, text) pairs.

```bash
uv run python simulation/core/action_generators/follow/algorithms/naive_llm/e2e_test_run.py
```

Expected: 3 blocks; each shows "Follows generated: N" and user_ids.

### 6. Pre-commit

```bash
uv run pre-commit run --all-files
```

Expected: ruff, pyright, pytest pass (oxlint/React Doctor may fail if UI deps differ).

---

## Plan Asset Storage

This plan is stored at:

```
docs/plans/2026-02-18_naive_llm_action_generators_887eadcb/
  plan.md   # This file
```

---

## Alternative Approaches

- **Protocol vs constructor injection**: Chose constructor injection for simplicity; protocol can be added later for batching.
- **Algorithm filename**: Initially `naive_llm_algorithm.py`; renamed to `algorithm.py` since folder already encodes the name.
- **Env loading (e2e)**: Initially `load_dotenv()`; switched to `EnvVarsContainer` after merge of [PR #100](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/100).
