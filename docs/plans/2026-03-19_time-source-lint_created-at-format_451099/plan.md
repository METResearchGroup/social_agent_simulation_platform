---
description: Enforce a single time source (`get_current_timestamp`) and unify `CREATED_AT_FORMAT` across core + tests.
tags: [plan, semgrep, linting, python, timestamp-utils, created-at]
---

## Remember
- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- Maximum safely delegable parallelism
- Delegated tasks must be independently executable and independently verifiable

## Overview
This change makes timestamp handling deterministic and mechanically enforceable by (1) defining `CREATED_AT_FORMAT: str = "%Y_%m_%d-%H:%M:%S"` in `lib/timestamp_utils.py` and routing all `created_at` generation through `get_current_timestamp()`, and (2) removing any remaining inline usages of the raw timestamp format string so they consistently reference `CREATED_AT_FORMAT`. It also adds Semgrep rules that enforce a stronger invariant: outside `lib/timestamp_utils.py`, current timestamp creation must go through `lib.timestamp_utils.get_current_timestamp()` (no direct wall-clock calls) and to fail the build if the raw timestamp format literal is reintroduced outside `lib/timestamp_utils.py`.

## Happy Flow
1. `lib/timestamp_utils.py`
   1. Exports `CREATED_AT_FORMAT` as a shared constant.
   2. Implements `get_current_timestamp()` to return “now” formatted with `CREATED_AT_FORMAT`.
2. Core generation call sites in `simulation/` and `db/`
   1. When they need a `created_at` string for persisted/domain objects, they call `lib.timestamp_utils.get_current_timestamp()`.
   2. They never call wall-clock APIs directly; the only allowed entry point for current timestamp strings is `lib.timestamp_utils.get_current_timestamp()` (enforced by Semgrep).
3. Parsing/validation call sites (e.g., recency scoring)
   1. Use `CREATED_AT_FORMAT` for `datetime.strptime(..., CREATED_AT_FORMAT)` to keep parsing aligned with generation.
4. Semgrep gate in `lint/semgrep/`
   1. Blocks any new `datetime.now()` / `time.time()` usage under `simulation/` and `db/`.
   2. Blocks reintroduction of the raw literal `"%Y_%m_%d-%H:%M:%S"` under the repo (except `lib/timestamp_utils.py`).
5. Pre-commit + CI integration
   1. `uv tool run semgrep --config lint/semgrep --error` is run via `.pre-commit-config.yaml` (and presumably CI the same way), making these checks non-optional.

## Serial Coordination Spine
1. Update the time contract in `lib/timestamp_utils.py` (define `CREATED_AT_FORMAT`, and ensure `get_current_timestamp()` uses it).
2. Add Semgrep rules under `lint/semgrep/` that encode the contract:
   1. ban wall-clock calls in `simulation/` + `db/`
   2. ban reintroducing the raw format literal outside `lib/timestamp_utils.py`
3. Update call sites to match the contract (import `CREATED_AT_FORMAT` and remove local duplicates; replace inline timestamp literals).

## Interface or Contract Freeze
### Required exported symbols (exact names)
1. `lib/timestamp_utils.py`
   1. `CREATED_AT_FORMAT: str = "%Y_%m_%d-%H:%M:%S"`
   2. `get_current_timestamp() -> str` returns `datetime.now(<approved tz>).strftime(CREATED_AT_FORMAT)`

### Timezone decision (keep behavior stable)
To minimize behavioral change, implement `get_current_timestamp()` using the existing repo behavior: `datetime.now()` (naive local time) formatted with `CREATED_AT_FORMAT`.

Semgrep + literal replacement do not depend on timezone choice; only the internal implementation of `get_current_timestamp()` does.

### Contract invariants (must hold after the implementation)
1. The raw string literal `"%Y_%m_%d-%H:%M:%S"` exists only in `lib/timestamp_utils.py` (inside `CREATED_AT_FORMAT`).
2. Outside `lib/timestamp_utils.py`, any current timestamp creation goes through `lib.timestamp_utils.get_current_timestamp()` (so there should be no direct `datetime.now(` / `datetime.utcnow(` / `time.time(` wall-clock calls in `simulation/` or `db/`).
3. All `created_at` string generation in `simulation/` and `db/` uses `lib.timestamp_utils.get_current_timestamp()`.

## Parallel Task Packets

### Task ID: A1
**Objective:** Remove per-module timestamp format literals and use shared `CREATED_AT_FORMAT` in core action generators.

**Why parallelizable:** Each file is independent and only needs import + constant replacement; no shared state.

**Exact files to inspect:**
- `simulation/core/action_generators/like/algorithms/random_simple.py`
- `simulation/core/action_generators/follow/algorithms/random_simple.py`
- `simulation/core/action_generators/comment/algorithms/random_simple.py`

**Exact files allowed to change:**
- The three files above only

**Exact files forbidden to change:**
- `lib/timestamp_utils.py`
- `lint/semgrep/**`
- other repo files

**Preconditions:**
- `lib.timestamp_utils` exports `CREATED_AT_FORMAT`

**Dependency tasks:**
- Must run after Contract Freeze step #1 (A: update `lib/timestamp_utils.py`)

**Required contracts and invariants:**
- No remaining occurrences of `CREATED_AT_FORMAT: str = "%Y_%m_%d-%H:%M:%S"` inside these modules.
- `datetime.strptime(created_at, ...)` uses imported `CREATED_AT_FORMAT`.

**Implementation instructions:**
1. In each module, delete the local constant:
   - `CREATED_AT_FORMAT: str = "%Y_%m_%d-%H:%M:%S"`
2. Update imports:
   - currently: `from lib.timestamp_utils import get_current_timestamp`
   - change to: `from lib.timestamp_utils import CREATED_AT_FORMAT, get_current_timestamp`
3. Update parsing calls:
   - keep logic but ensure second argument is `CREATED_AT_FORMAT` from the shared import.

**Verification commands (expected outputs):**
1. `rg "%Y_%m_%d-%H:%M:%S" simulation/core/action_generators -g"*.py"`
   - Expected: no matches (empty output).

2. `python -c "import simulation.core.action_generators.like.algorithms.random_simple as m; assert m.CREATED_AT_FORMAT is not None"` (or a lightweight import check)
   - Expected: imports succeed.

**Done-when checklist:**
- [ ] All three `random_simple.py` files import `CREATED_AT_FORMAT` from `lib.timestamp_utils`.
- [ ] No raw format literals remain in these files.

**Coordinator review checklist:**
- [ ] Confirm `CREATED_AT_FORMAT` is not redefined locally in these files.
- [ ] Confirm parsing uses `datetime.strptime(..., CREATED_AT_FORMAT)`.

---

### Task ID: A2
**Objective:** Replace inline `"%Y_%m_%d-%H:%M:%S"` format literals in tests with shared `CREATED_AT_FORMAT`.

**Why parallelizable:** Test files don’t affect each other’s runtime behavior beyond shared constant import.

**Exact files to inspect:**
- `tests/factories/_helpers.py`
- `ml_tooling/emotion/tests/test_classifier.py`

**Exact files allowed to change:**
- the two files above only

**Exact files forbidden to change:**
- `lib/timestamp_utils.py`
- `lint/semgrep/**`
- any production core code

**Preconditions:**
- `lib.timestamp_utils` exports `CREATED_AT_FORMAT`

**Dependency tasks:**
- Must run after Contract Freeze step #1 (A: update `lib/timestamp_utils.py`)

**Required contracts and invariants:**
- The raw string literal `"%Y_%m_%d-%H:%M:%S"` does not appear in these files after the update.

**Implementation instructions:**
1. `tests/factories/_helpers.py`
   - import `CREATED_AT_FORMAT` from `lib.timestamp_utils`
   - replace `dt.strftime("%Y_%m_%d-%H:%M:%S")` with `dt.strftime(CREATED_AT_FORMAT)`
2. `ml_tooling/emotion/tests/test_classifier.py`
   - import `CREATED_AT_FORMAT` from `lib.timestamp_utils`
   - replace `datetime.strptime(result.label_timestamp, "%Y_%m_%d-%H:%M:%S")`
     with `datetime.strptime(result.label_timestamp, CREATED_AT_FORMAT)`

**Verification commands (expected outputs):**
1. `rg "%Y_%m_%d-%H:%M:%S" tests ml_tooling -g"*.py"`
   - Expected: no matches.

2. `uv run pytest tests/factories/_helpers.py ml_tooling/emotion/tests/test_classifier.py`
   - Expected: tests pass.

**Done-when checklist:**
- [ ] No raw timestamp format literals remain in the listed test files.

**Coordinator review checklist:**
- [ ] Imports are unused? (If any lint is enforced, ruff will catch it.)

---

### Task ID: A3
**Objective:** Add Semgrep rules to enforce the time-source + created-at format contract.

**Why parallelizable:** Semgrep rules are declarative and don’t depend on test updates.

**Exact files to inspect:**
- `.pre-commit-config.yaml` (Semgrep invocation line)
- `lint/semgrep/python-di.yml` (existing Semgrep rule file and style)

**Exact files allowed to change:**
- Add a new file `lint/semgrep/python-time-source.yml` (preferred)
  - OR update `lint/semgrep/python-di.yml` if the repo convention requires single-file configs

**Exact files forbidden to change:**
- `.pre-commit-config.yaml` (unless the Semgrep config path requires adjustment after we add a new file)

**Preconditions:**
- Contract Freeze step #1 defines `CREATED_AT_FORMAT`

**Dependency tasks:**
- Must run after Contract Freeze step #1 (so the literal ban matches the exact string)

**Required contracts and invariants:**
1. Semgrep fails (ERROR severity) on:
   - `datetime.now(...)` and `time.time(...)` under `simulation/` and `db/`
2. Semgrep fails on reintroducing `"%Y_%m_%d-%H:%M:%S"` as a string literal anywhere except `lib/timestamp_utils.py`

**Implementation instructions:**
1. Create `lint/semgrep/python-time-source.yml` with rules:
   - Rule 1: ban `datetime.now(...)` in `simulation/**` and `db/**`
  - Rule 1b: ban `datetime.utcnow(...)` in `simulation/**` and `db/**`
   - Rule 2: ban `time.time(...)` in `simulation/**` and `db/**`
   - Rule 3: ban string literal `"%Y_%m_%d-%H:%M:%S"` outside `lib/timestamp_utils.py`
2. Use the following rule skeleton (then fill in `id`/`message` wording as needed):
```yaml
rules:
  - id: python.time.no-datetime-now-in-sim-and-db
    languages: [python]
    message: "Outside lib/timestamp_utils.py, current timestamps must come from lib.timestamp_utils.get_current_timestamp(). Do not call datetime.now() (or other wall-clock APIs) directly in simulation/ or db/."
    severity: ERROR
    patterns:
      - pattern: datetime.now(...)
    paths:
      include:
        - /simulation/**
        - /db/**

  - id: python.time.no-datetime-utcnow-in-sim-and-db
    languages: [python]
    message: "Outside lib/timestamp_utils.py, current timestamps must come from lib.timestamp_utils.get_current_timestamp(). Do not call datetime.utcnow() directly in simulation/ or db/."
    severity: ERROR
    patterns:
      - pattern: datetime.utcnow(...)
    paths:
      include:
        - /simulation/**
        - /db/**

  - id: python.time.no-time-time-in-sim-and-db
    languages: [python]
    message: "Outside lib/timestamp_utils.py, current timestamps must come from lib.timestamp_utils.get_current_timestamp(). Do not call time.time() directly in simulation/ or db/."
    severity: ERROR
    patterns:
      - pattern: time.time(...)
    paths:
      include:
        - /simulation/**
        - /db/**

  - id: python.time.no-inline-created-at-format-literal
    languages: [python]
    message: "Use lib.timestamp_utils.CREATED_AT_FORMAT instead of the raw %Y_%m_%d-%H:%M:%S literal."
    severity: ERROR
    patterns:
      # Prefer a direct string-literal pattern; if it doesn't match due to escaping,
      # switch to pattern-regex.
      - pattern: "\"%Y_%m_%d-%H:%M:%S\""
    paths:
      exclude:
        - /lib/timestamp_utils.py
```
3. Configure Semgrep `paths` so it uses:
   - includes: `simulation/` + `db/` for wall-clock rules
   - excludes: `lib/timestamp_utils.py` for the literal rule
4. Set `severity: ERROR` and add a clear `message` telling developers to use `lib.timestamp_utils.get_current_timestamp()` and/or `lib.timestamp_utils.CREATED_AT_FORMAT`.

**Verification commands (expected outputs):**
1. `uv tool run semgrep --config lint/semgrep --error`
   - Expected: `0 findings`

2. `rg "%Y_%m_%d-%H:%M:%S" -g"*.py" -S`
   - Expected: only `lib/timestamp_utils.py` contains the literal

**Done-when checklist:**
- [ ] `uv tool run semgrep ...` reports zero findings.
- [ ] Semgrep error messages clearly instruct the correct fix.

**Coordinator review checklist:**
- [ ] Ensure rule paths are correct and do not accidentally ban the allowed usage in `lib/timestamp_utils.py`.

---

## Integration Order
1. Apply Contract Freeze in `lib/timestamp_utils.py`.
2. Run Tasks A1/A2/A3 in parallel (call-site updates + Semgrep rule addition), ensuring A1/A2 imports compile against A contract.
3. Run global consistency checks:
   - `rg` checks for remaining literals and banned time sources.
4. Run test suite and linters.

## Manual Verification
- [ ] Semgrep gate: from repo root, run `uv tool run semgrep --config lint/semgrep --error`
  - Expected: `0 findings`
- [ ] Literal consistency check:
  - Run `rg "%Y_%m_%d-%H:%M:%S" -g"*.py"`
  - Expected: only one hit in `lib/timestamp_utils.py` (the `CREATED_AT_FORMAT` definition)
- [ ] Wall-clock ban check (core scope):
  - Run `rg "datetime\\.(now|utcnow)\\(" simulation db -g"*.py"`
  - Expected: no matches
  - Run `rg "time\\.time\\(" simulation db -g"*.py"`
  - Expected: no matches
- [ ] Python lint:
  - Run `uv run ruff check .`
  - Run `uv run ruff format . --check`
- [ ] Tests:
  - Run `uv run pytest`

## Final Verification
Confirm the repository is “contract clean” by ensuring:
- [ ] Semgrep produces `0 findings`
- [ ] All timestamp format literals were unified to `CREATED_AT_FORMAT`
- [ ] No new wall-clock calls appear in `simulation/` + `db/` (so current timestamp creation is centralized via `lib.timestamp_utils.get_current_timestamp()`)
- [ ] Unit/integration tests pass

## Alternative Approaches
1. Introduce a `Clock` interface + DI instead of Semgrep.
   - Pros: more flexible time mocking and deterministic replay.
   - Cons: higher refactor cost across many call sites; Semgrep is faster to roll out and still enforces the key invariants.
2. Use Semgrep to only ban `datetime.now()` and keep string literals as-is.
   - Pros: smaller diff.
   - Cons: doesn’t fully unify parsing/formatting, leaving room for drift and inconsistent timestamps in tests/algorithms.
