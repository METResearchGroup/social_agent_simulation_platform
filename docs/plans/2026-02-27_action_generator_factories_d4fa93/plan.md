---
description: Reorganize naive LLM action-generator factory wiring into per-action modules and clarify the workflow in the feed ranking runbook.
tags:
  - action-generators
  - tooling
  - docs
  - planning
---

## Remember
- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- UI changes: agent captures before/after screenshots itself (no README or instructions for the user)

## Overview
Reorganize the naive-LLM factory plumbing so each action type owns its own `simulation/core/factories/action_generators/<action>/naive_llm.py` module with the `create_naive_llm_<action>_generator` factory and replace the old monolithic `action_generators.py`. Update the registry, scripts, and runbooks to use the new structure and document the pattern in `docs/runbooks/HOW_TO_CREATE_NEW_FEED_RANKING_ALGORITHM.md` (plan assets live in this folder).

## Happy Flow
1. **LLM factories** – `simulation/core/factories/action_generators/{comment,like,follow}/naive_llm.py` each expose `create_naive_llm_<action>_generator(*, llm_service: LLMService | None = None)` and wire the existing generator implementations to `LLMService`.
2. **Registry wiring** – `_create_naive_llm_like`, `_create_naive_llm_follow`, `_create_naive_llm_comment` import their factories from the new module paths so the cached `get_*_generator("naive_llm")` entries resolve as before.
3. **Consumers** – the naive LLM e2e scripts now import from the action-specific factory modules, avoiding the deleted shim.
4. **Docs + lint** – `docs/runbooks/HOW_TO_CREATE_NEW_FEED_RANKING_ALGORITHM.md` explains the per-action factory layout and `scripts/lint_architecture.py` filters missing git-tracked files before dependency scans.

## Manual Verification
- `uv run pytest tests/simulation/core/test_action_generators_registry.py tests/simulation/core/test_naive_llm_action_generators.py tests/simulation/core/test_random_simple_like_policy.py tests/simulation/core/test_random_simple_follow_policy.py tests/simulation/core/test_random_simple_comment_policy.py`
- `uv run --extra test pre-commit run --all-files`
- `uv run python scripts/check_docs_metadata.py docs/runbooks/HOW_TO_CREATE_NEW_FEED_RANKING_ALGORITHM.md`

## Alternative approaches
- Keep a shim module and re-export the factories; rejected because the requirement was to break existing imports and localize action wiring.
- Collapse factory wiring into the registry itself; rejected because this would violate the existing dependency-injection pattern used by e2e scripts and future factory consumers.

## Asset storage
Plan assets live under `docs/plans/2026-02-27_action_generator_factories_d4fa93/` as required.
