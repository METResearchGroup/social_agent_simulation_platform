---
name: naive-llm-mixin-refactor
overview: Refactor the three naive-LLM action generators (like/comment/follow) to share LLM-call + filter/dedupe scaffolding via a lightweight Python mixin, preserving public class names, constructor signatures, and output semantics verified by existing tests.
todos:
  - id: add-mixin
    content: Add `simulation/core/action_generators/utils/llm_action_generator_mixin.py` with helpers for LLM call + filter/dedupe (IDs and items).
    status: completed
  - id: refactor-like
    content: Update `simulation/core/action_generators/like/algorithms/naive_llm/algorithm.py` to use mixin helpers; preserve behavior + sorting.
    status: completed
  - id: refactor-follow
    content: Update `simulation/core/action_generators/follow/algorithms/naive_llm/algorithm.py` to use mixin helpers; preserve unique-author preprocessing + sorting.
    status: completed
  - id: refactor-comment
    content: Update `simulation/core/action_generators/comment/algorithms/naive_llm/algorithm.py` to use mixin helpers for response item filtering/deduping; preserve behavior + sorting.
    status: completed
  - id: verify
    content: Run ruff format/check and the two targeted pytest files; confirm no behavior changes.
    status: completed
isProject: false
---

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

## Plan asset storage

- Create and store any notes/snippets in: `docs/plans/2026-02-28_refactor_naive_llm_action_mixins_402817/`

## Overview

The three naive-LLM generators duplicate the same core steps: call `LLMService.structured_completion`, filter to candidate IDs, deduplicate, then emit `Generated*` objects sorted deterministically. We’ll introduce a **lightweight mixin** that centralizes only the shared helper logic (LLM call wrapper + filter/dedupe helpers) while letting each generator keep its own `generate()` and its existing prompt/build functions. This keeps the refactor small, preserves the current module layout, and aligns with existing unit tests in `tests/simulation/core/test_naive_llm_action_generators.py`.

## Happy Flow (end-to-end)

1. Caller requests a generator from the registry, e.g. `get_like_generator(algorithm="naive_llm")`.
  - Registry: `[simulation/core/action_generators/registry.py](simulation/core/action_generators/registry.py)` uses `_create_naive_llm_like()` to call the factory.
2. Factory returns a concrete generator wired with an `LLMService`.
  - Factories: 
    - `[simulation/core/factories/action_generators/like/naive_llm.py](simulation/core/factories/action_generators/like/naive_llm.py)`
    - `[simulation/core/factories/action_generators/comment/naive_llm.py](simulation/core/factories/action_generators/comment/naive_llm.py)`
    - `[simulation/core/factories/action_generators/follow/naive_llm.py](simulation/core/factories/action_generators/follow/naive_llm.py)`
3. Generator `generate()` runs (still owned by each concrete class):
  - Builds prompt (existing helpers stay in place).
  - Calls LLM via a new mixin helper that wraps `self._llm.structured_completion(...)`.
  - Filters + dedupes LLM output via new mixin helpers, matching current semantics:
    - Like: valid post IDs are `post.id` from candidates.
    - Comment: valid post IDs are `post.id`; response items include `(post_id, text)`.
    - Follow: valid IDs are author handles; candidates are reduced to unique authors (excluding self) before prompting.
  - Builds `GeneratedLike` / `GeneratedComment` / `GeneratedFollow` exactly as today and sorts deterministically (`post_id` or `user_id`).
4. Existing unit tests validate empty-input behavior, invalid-id filtering, and deterministic sort ordering.
  - Tests: `[tests/simulation/core/test_naive_llm_action_generators.py](tests/simulation/core/test_naive_llm_action_generators.py)`

## Implementation details (concrete edits)

### 1) Add a lightweight mixin for shared scaffolding

- Add new module: `[simulation/core/action_generators/utils/llm_action_generator_mixin.py](simulation/core/action_generators/utils/llm_action_generator_mixin.py)`
- Responsibilities (keep it intentionally small):
  - **LLM call wrapper**: a method that takes `prompt: str` and `response_model: type[...]` and calls `self._llm.structured_completion(...)`.
  - **Filter + dedupe (IDs)**: helper that takes `response_ids: list[str]` and `valid_ids: set[str]` and returns a list preserving first-occurrence order.
  - **Filter + dedupe (items)**: helper that takes `items: list[T]`, `valid_ids: set[str]`, and an `item_id: Callable[[T], str]` extractor, returning items in first-occurrence order.
- Non-goals:
  - Do not move prompt templates, response models, or `Generated`* builders into the mixin.
  - Do not change logging messages unless required by tests.

### 2) Refactor naive-LLM like generator to use mixin helpers

- Update: `[simulation/core/action_generators/like/algorithms/naive_llm/algorithm.py](simulation/core/action_generators/like/algorithms/naive_llm/algorithm.py)`
  - Make `NaiveLLMLikeGenerator` inherit from the mixin (e.g., `class NaiveLLMLikeGenerator(LLMActionGeneratorMixin, LikeGenerator):`).
  - Replace `_deduplicate_post_ids` / `_get_ids_to_like` usage with the mixin’s ID filter/dedupe helper.
  - Keep:
    - `_build_prompt(...)`
    - `_build_generated_like(...)`
    - final `generated.sort(key=lambda g: g.like.post_id)`

### 3) Refactor naive-LLM follow generator to use mixin helpers

- Update: `[simulation/core/action_generators/follow/algorithms/naive_llm/algorithm.py](simulation/core/action_generators/follow/algorithms/naive_llm/algorithm.py)`
  - Inherit from the mixin.
  - Replace `_deduplicate_follow_ids` / `_get_ids_to_follow` with the mixin’s ID filter/dedupe helper.
  - Keep:
    - `_collect_unique_authors(...)` (including self-exclusion and “most recent post per author” selection)
    - `_authors_to_minimal_json(...)`
    - `_build_generated_follow(...)`
    - final `generated.sort(key=lambda g: g.follow.user_id)`

### 4) Refactor naive-LLM comment generator to use mixin helpers

- Update: `[simulation/core/action_generators/comment/algorithms/naive_llm/algorithm.py](simulation/core/action_generators/comment/algorithms/naive_llm/algorithm.py)`
  - Inherit from the mixin.
  - Replace the inline `already_included_post_ids` loop with the mixin’s “filter+dedupe items” helper, where `item_id` extracts `CommentPredictionItem.post_id`.
  - Preserve sorting by `comment.post_id`.

### 5) Export hygiene (only if needed)

- If you want the mixin import path to be stable/convenient, optionally update `[simulation/core/action_generators/utils/__init__.py](simulation/core/action_generators/utils/__init__.py)` to export the mixin. (Not required if you import by full module path.)

## Manual Verification

- **Format**:
  - `uv run ruff format simulation/core/action_generators/utils/llm_action_generator_mixin.py simulation/core/action_generators/like/algorithms/naive_llm/algorithm.py simulation/core/action_generators/comment/algorithms/naive_llm/algorithm.py simulation/core/action_generators/follow/algorithms/naive_llm/algorithm.py`
  - Expected: exits 0 and formats files (or no changes).
- **Lint**:
  - `uv run ruff check simulation/core/action_generators/utils/llm_action_generator_mixin.py simulation/core/action_generators/like/algorithms/naive_llm/algorithm.py simulation/core/action_generators/comment/algorithms/naive_llm/algorithm.py simulation/core/action_generators/follow/algorithms/naive_llm/algorithm.py`
  - Expected: `All checks passed!` (or no new violations).
- **Unit tests (targeted)**:
  - `uv run pytest -q tests/simulation/core/test_naive_llm_action_generators.py`
  - `uv run pytest -q tests/simulation/core/test_action_generators_registry.py`
  - Expected: all tests pass.
- **(Optional) Type check**:
  - `uv run pyright simulation/core/action_generators`
  - Expected: no new errors.

## Alternative approaches

- **Template-method mixin (mixin owns `generate()`)**: More DRY, but higher coupling and more behavioral risk; you explicitly chose the lighter helpers-only approach.
- **Shared module-level helper functions**: Even simpler, but doesn’t exercise/teach the mixin pattern you’re trying to learn.
- **Abstract base class**: Similar to template-method but usually heavier; tends to force a single flow even when small differences (like follow’s unique-author preprocessing) exist.

