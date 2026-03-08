---
description: >-
  Update the shared string validation helper so callers only pass the value and
  keep existing contextual errors via wrapper utilities.
tags:
  - planning
  - validation
---

## Remember
- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

## Title
Remove `field_name` from `validate_non_empty_string` and update all callers/tests

## Overview
Streamline `validate_non_empty_string` in `lib/validation_utils.py` so it only needs the value and delivers consistent `"value ..."` errors; ripple that change through every domain model, generated model, SQLite adapter, API schema, and validator wrapper while keeping regression coverage intact and preserving the contextual labeled messages where external code depends on them.

## Happy Flow
1. **Helper contract** – `lib/validation_utils.py:146` accepts a single `value`, validates `None`, non-`str`, and emptiness, and returns the trimmed string with `"value ..."` errors.
2. **Domain/generator consumers** – Pydantic validators across `simulation/core/models/*.py` and `simulation/core/models/generated/*.py` call the helper with only the incoming field to keep type coercion consistent.
3. **API/schema guards** – `simulation/api/schemas/simulation.py` strips request values and hands them to the helper without redundant field labels.
4. **Adapters** – SQLite builders (`db/adapters/sqlite/*.py`) call the helper directly before running SQL, ensuring their inputs are trimmed.
5. **Wrapper translation** – `simulation/core/utils/validators.py` keeps the existing labeled errors for consumers like repositories by catching `ValueError`s, rephrasing them, and re-raising so external assertions still see `run_id cannot be empty`.

## Data Flow
1. **Input normalization** – API validators and domain models trim inputs (e.g., handles, URIs) and call `validate_non_empty_string(value)` to ensure non-empty strings flow inward.
2. **Domain enforcement** – Models built by Pydantic propagate trimmed, validated strings into attributes returned to repositories and adapters.
3. **Persistence checks** – Repository wrappers call `_validate_non_empty_string_labeled(...)` when exposed to external callers, translating helper errors into field-specific messages before hitting SQLite adapters.
4. **Storage** – Validated IDs/handles proceed to SQLite adapters (`agent_adapter`, `agent_bio_adapter`, `user_agent_profile_metadata_adapter`) without redundant labeling, preventing malformed rows.

## Manual Verification
- `uv sync --extra test` — installs dependencies needed for the expanded pytest run.
- `uv run pytest tests/lib/test_validation_utils.py -q` — helper tests pass with the new error strings.
- `uv run pytest tests/db/repositories/test_profile_repository.py tests/db/repositories/test_generated_feed_repository.py tests/db/repositories/test_feed_post_repository.py -q` — verifies affected repositories still raise the expected labeled errors.
- `uv run pytest` — full suite passes (623 tests, 2 skipped) with no collection errors after installing test dependencies.
- `uv run ruff check .` — linting passes.
- `uv run pyright .` — type checking passes.

## Alternative approaches
Keeping `field_name` optional and defaulting to `"value"` would have avoided API churn, but the goal was to drop the extra argument entirely so callers no longer need repetitive labels; wrapping helpers in `_validate_non_empty_string_labeled` still preserves the contextual messages for high-level APIs.

## Assumptions
- Labeled error messages (`"<field> cannot be empty"`) live in the repo wrappers, not the helper.
- `_field_name(info)` helpers remain for potential future needs and are not removed in this change.
