---
description: Execution plan for strict linter and security gate rollout.
tags:
  - linting
  - ruff
  - bandit
  - pre-commit
  - ci
name: Strict Linter Gates
overview: Turn the repo’s Python code quality tooling into strict, blocking CI + pre-commit gates by aligning Ruff’s maximum rule coverage to the proposal, ensuring file-hygiene hooks are enforced, and keeping a dedicated Bandit security scanner blocking in both CI and pre-commit.
todos:
  - id: audit-config
    content: Audit `pyproject.toml`, `.pre-commit-config.yaml`, and `.github/workflows/ci.yml` against `LINTER_TOOLS_PROPOSAL.md` to identify the minimal deltas needed.
    status: pending
  - id: packet-ruff-bandit-pyproject
    content: Update `pyproject.toml` so Ruff select/ignore/per-file-ignores match the proposal rule families and `target-version` aligns to the Python >=3.10 baseline; ensure `bandit>=1.9.4` stays in the `test` optional-deps group.
    status: pending
  - id: packet-precommit-hygiene-bandit
    content: Ensure `.pre-commit-config.yaml` includes the proposal’s `pre-commit-hooks` hygiene checks, keeps `ruff-check` gate-only (no `--fix`), and includes the `bandit` hook with the exact include/exclude scope.
    status: pending
  - id: packet-ci-bandit-gate
    content: "Verify and (if needed) update `.github/workflows/ci.yml` so the Python `test` job runs the blocking sequence: `ruff check .` -> `ruff format --check .` -> `bandit ... -x tests -x ui` -> `pyright .` -> `pytest`."
    status: pending
  - id: fix-gate-violations
    content: Run the local gate commands (`pre-commit run -a`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run bandit ...`, `uv run pyright .`, `uv run pytest`) and fix any new violations introduced by the stricter gates.
    status: pending
  - id: final-verification
    content: Re-run the exact final verification commands on HEAD and confirm all exit codes are `0`.
    status: pending
isProject: false
---

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- Maximum safely delegable parallelism
- Delegated tasks must be impossible to misread

## Overview

Implement the repo-wide “Strict Ruff + Security Gates” proposal from `LINTER_TOOLS_PROPOSAL.md` by auditing and updating configuration so that (1) Ruff runs with maximum rule-family coverage (correct per-file ignores and minimum-version assumptions), (2) pre-commit enforces cheap repository hygiene (syntax, whitespace, merge conflicts, obvious secrets, line endings), and (3) a dedicated Bandit scan blocks on security-ish patterns, using the same include/exclude scope.

Asset folder for any future artifacts (screenshots not required for this change): `docs/plans/2026-03-19_linter-tools-strict-gates_123456/`

## Happy Flow

1. Developer runs `pre-commit` locally (via `pre-commit run -a`), which executes: `ruff-check`, `ruff-format --check`, cheap hygiene hooks, and the `bandit` hook (scanning first-party backend code with `-x tests -x ui`).
2. In CI, the `test` job runs in order: `uv run ruff check .` -> `uv run ruff format --check .` -> `uv run bandit ... -x tests -x ui` -> `uv run pyright .` -> `uv run pytest`.
3. On PR merge, the repo ensures that correctness/style/security-pattern issues in Python cannot be merged without first being fixed by the developer (Ruff and Bandit are blocking; Ruff does not auto-fix in hooks).

## Serial Coordination Spine

1. Confirm current config parity against each proposal change (Ruff strictness, pre-commit hygiene, Bandit gate) by reading:
  - `pyproject.toml`
  - `.pre-commit-config.yaml`
  - `.github/workflows/ci.yml`
2. Apply the minimal set of deltas found during the audit (expected at minimum: align Ruff’s `target-version` to Python >=3.10 baseline if currently set higher).
3. Run the same verification commands used by CI and pre-commit, then resolve any newly introduced violations.
4. Re-run `pre-commit run -a` to ensure local gating matches CI gating.

## Interface or Contract Freeze

- Contract: keep CI/pre-commit gates strict/blocking (no `ruff-check` auto-fixing).
- Contract: preserve existing architectural enforcement (Semgrep + `import-linter`) and type checking (Pyright) as-is; this plan only touches lint/security + hygiene gates.
- File ownership for parallel work (prevents shared ownership):
  - Packet A owns `pyproject.toml`.
  - Packet B owns `.pre-commit-config.yaml`.
  - Packet C owns `.github/workflows/ci.yml`.

## Parallel Task Packets

### Parallel Task Packet A: Ruff strictness + Bandit dependency (pyproject)

- Task ID: `packet-ruff-bandit-pyproject`
- One-sentence objective: Ensure `pyproject.toml` enables the full Ruff rule-family set from the proposal, keeps the correct ignores, and aligns Ruff to the Python >=3.10 baseline; also ensure Bandit is present in the `test` optional dependency group.
- Why parallelizable: It only modifies/validates `pyproject.toml` settings that feed Ruff/Bandit tooling, independent of YAML workflow hook ordering.
- Exact files to inspect:
  - `pyproject.toml`
- Exact files allowed to change:
  - `pyproject.toml`
- Exact files forbidden to change:
  - `.pre-commit-config.yaml`
  - `.github/workflows/ci.yml`
- Preconditions:
  - Repo already has Ruff + Bandit + pre-commit + CI wiring in place (audit may reveal minor mismatches).
- Required contracts/invariants:
  - `[tool.ruff.lint].select` includes `E,F,I,B,UP,SIM,S,N,T10,T20,PT,FAST,RET,ERA,ARG`.
  - `ignore = ["E501"]` remains.
  - `[tool.ruff.lint.per-file-ignores]` keeps migrations ignores for `"db/migrations/**" = ["UP","ERA"]`.
  - Ruff `target-version` must match the minimum supported runtime (proposal: Python >= 3.10).
  - `bandit>=1.9.4` remains in `[project.optional-dependencies].test`.
- Step-by-step implementation instructions:
  1. Inspect `[tool.ruff]` and confirm `target-version` currently reflects the minimum baseline.
  2. If `target-version` is set to a higher baseline (e.g. `py312`), update it to `py310` to satisfy the proposal’s “modernize to your minimum Python baseline (Python >= 3.10)”.
  3. Confirm `[tool.ruff.lint].select` contains every rule-family in `LINTER_TOOLS_PROPOSAL.md`.
  4. Confirm `ignore` and migrations `per-file-ignores` match the proposal.
  5. Confirm `[project.optional-dependencies].test` includes `bandit>=1.9.4`.
- Exact verification commands:
  1. `uv run ruff check .`
  2. `uv run ruff format --check .`
  3. `uv run bandit -r simulation db ai lib feeds jobs ml_tooling -x tests -x ui`
- Expected outputs from verification:
  - All commands exit with code `0`.
  - Ruff commands report no violations; Bandit reports no findings.
- Done-when checklist:
  - `target-version` matches Python >=3.10 intent.
  - Ruff select/ignore/per-file ignores match the proposal.
  - Bandit optional dependency exists in the `test` group.
- Coordinator review checklist:
  - No additional Ruff rule families beyond the proposal list were introduced.
  - No changes to architectural boundary tooling.

### Parallel Task Packet B: Pre-commit hygiene + ruff gate + bandit hook (pre-commit config)

- Task ID: `packet-precommit-hygiene-bandit`
- One-sentence objective: Ensure `.pre-commit-config.yaml` enforces repo hygiene hooks and that the Ruff hook remains “gate-only” (no `--fix` for ruff-check), and that the Bandit hook uses the proposed include/exclude scope.
- Why parallelizable: It edits/validates hook configuration only and does not depend on CI job step content ordering.
- Exact files to inspect:
  - `.pre-commit-config.yaml`
- Exact files allowed to change:
  - `.pre-commit-config.yaml`
- Exact files forbidden to change:
  - `pyproject.toml`
  - `.github/workflows/ci.yml`
- Preconditions:
  - The repo uses `pre-commit` with Ruff + local tool hooks.
- Required contracts/invariants:
  - Pre-commit `ruff-check` must not use `--fix` (proposal gate-only requirement).
  - Pre-commit must include `pre-commit/pre-commit-hooks` hygiene hooks:
    - `check-yaml`, `check-json`, `check-toml`, `trailing-whitespace`, `end-of-file-fixer`, `check-merge-conflict`, `detect-private-key`, and `mixed-line-ending` with `--fix lf`.
  - Pre-commit must include a local `bandit` hook using:
    - `uv run --extra test bandit -r simulation db ai lib feeds jobs ml_tooling -x tests -x ui`
- Step-by-step implementation instructions:
  1. Inspect the Ruff pre-commit hook stanza for `id: ruff-check` and verify there is no `--fix` argument.
  2. Inspect the `pre-commit/pre-commit-hooks` stanza to confirm every hygiene hook from the proposal exists.
  3. Confirm the `mixed-line-ending` hook includes `args: [--fix, lf]`.
  4. Confirm the local `bandit` hook stanza exists and matches the proposed bandit command.
  5. If any required hook/stanza is missing or mismatched, add/update it.
- Exact verification commands:
  1. `pre-commit run -a`
  2. (Optional quick sanity) `pre-commit run ruff-check --all-files`
- Expected outputs from verification:
  - `pre-commit run -a` exits `0`.
  - No Ruff fixes are applied by the `ruff-check` hook; any necessary fixes must come from manual edits or `ruff-format` formatting.
- Done-when checklist:
  - Hygiene hook set matches the proposal.
  - Ruff hook remains gate-only.
  - Bandit hook uses the correct scope/exclusions.
- Coordinator review checklist:
  - No additional hooks were added that would broaden scope beyond the proposal.

### Parallel Task Packet C: Bandit gate in CI (workflow config)

- Task ID: `packet-ci-bandit-gate`
- One-sentence objective: Ensure `.github/workflows/ci.yml` runs Ruff and Bandit as blocking steps with the correct commands and ordering in the Python test job.
- Why parallelizable: It modifies/validates workflow orchestration and does not affect hook configuration in pre-commit.
- Exact files to inspect:
  - `.github/workflows/ci.yml`
- Exact files allowed to change:
  - `.github/workflows/ci.yml`
- Exact files forbidden to change:
  - `pyproject.toml`
  - `.pre-commit-config.yaml`
- Preconditions:
  - CI already has jobs for Python linting and tests.
- Required contracts/invariants:
  - In the Python `test` job, CI includes:
    - `uv run ruff check .`
    - `uv run ruff format --check .`
    - `uv run bandit -r simulation db ai lib feeds jobs ml_tooling -x tests -x ui`
  - Bandit must be a blocking step (i.e., run without `continue-on-error: true`).
- Step-by-step implementation instructions:
  1. Find the CI job where Ruff linting runs (likely `jobs.test.steps`).
  2. Verify the exact Ruff commands match the proposal intent (no `--fix`).
  3. Verify the Bandit command matches the proposed scope/exclusions exactly.
  4. If any commands are missing, add the Bandit step and/or Ruff format check.
  5. Ensure ordering is `ruff check` -> `ruff format --check` -> `bandit` -> `pyright` -> `pytest`.
- Exact verification commands:
  1. Local mirror of CI (requires no GitHub):
    - `uv run ruff check .`
    - `uv run ruff format --check .`
    - `uv run bandit -r simulation db ai lib feeds jobs ml_tooling -x tests -x ui`
    - `uv run pyright .`
    - `uv run pytest`
- Expected outputs from verification:
  - All commands exit `0`.
- Done-when checklist:
  - CI runs Ruff and Bandit exactly per required contracts.
- Coordinator review checklist:
  - Workflow changes only affect lint/security gate wiring.

## Integration Order

1. Packet A completes first (because it may change Ruff’s `target-version` and therefore what Ruff flags).
2. Packet B and Packet C complete next (hook/workflow wiring).
3. Coordinator runs a full local gate pass to ensure everything is consistent:
  - `pre-commit run -a`
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run bandit ...`

## Final Verification

- Run the following locally on the final branch HEAD:
  1. `uv run ruff check .`
  2. `uv run ruff format --check .`
  3. `uv run bandit -r simulation db ai lib feeds jobs ml_tooling -x tests -x ui`
  4. `uv run pyright .`
  5. `uv run pytest`
  6. `pre-commit run -a`
- Expected outcome:
  - All commands exit `0`.

## Manual Verification

Checklist (matches `LINTER_TOOLS_PROPOSAL.md` rollout notes):

- `uv run ruff check .` (exit code `0`, no “Found” violations)
- `uv run ruff format --check .` (exit code `0`, no formatting diffs reported)
- `uv run bandit -r simulation db ai lib feeds jobs ml_tooling -x tests -x ui` (exit code `0`, no findings)
- `pre-commit run -a` (exit code `0`)
- `uv run pytest` (exit code `0`)

## Alternative approaches

- GitHub code-scanning/SARIF: The proposal notes optional SARIF emission for Bandit; we keep this plan focused on blocking gates via pre-commit + CI to maximize immediate “hard to merge” effect.
- Ruff auto-fixing in pre-commit: intentionally avoided because the proposal requires Ruff be “gate-only” to reduce silent rewrites and keep diffs intentional.
