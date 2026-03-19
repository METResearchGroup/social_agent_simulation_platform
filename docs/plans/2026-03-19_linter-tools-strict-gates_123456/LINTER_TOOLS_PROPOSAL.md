---
description: Proposal for strict Ruff, hygiene hooks, and Bandit security gates.
tags:
  - linting
  - ruff
  - bandit
  - pre-commit
  - ci
---

# Linter Tools Proposal (Strict Ruff + Security Gates)

## Goal
Make code quality issues hard to merge by turning linting/security checks into strict, blocking gates—without duplicating what you already enforce via architecture and type systems.

This proposal is centered on two repo facts:
1. Your repo already enforces architectural boundaries via `import-linter` and Semgrep.
2. Python linting currently relied on a very small Ruff rule set, so many correctness/security/style hazards could still slip through.

## Current enforcement (baseline)
1. Ruff is run in CI (`uv run ruff check .` and `uv run ruff format --check .`) and in pre-commit (`ruff-check` + `ruff-format`).
2. Type checking is done via Pyright.
3. Architecture/DI constraints are enforced via Semgrep and `import-linter`.
4. Complexity checks exist but are effectively non-gating (`complexipy --max-complexity-allowed 999`).
5. UI linting exists (ESLint/Oxlint), docs linting exists (markdownlint + custom metadata checks).

## Change #1: Strict/blocking Ruff (maximum rule coverage you requested)
### What changes
Update `pyproject.toml`:
- Expand `[tool.ruff.lint].select` beyond `E/F/I` to include the rule families below.
- Keep the existing `ignore = ["E501"]`.
- Keep the existing per-file ignores for migrations (`db/migrations/**` ignores `UP` and `ERA`).

### Rule families enabled
The following families are enabled in `[tool.ruff.lint].select`:
1. `E` / `F` / `I` (already present): syntax errors, undefined names/unused imports, import ordering.
2. `B` (flake8-bugbear): common bug patterns (mutable defaults, unreliable patterns, etc.).
3. `UP` (pyupgrade): modernize to your minimum Python baseline (Python >= 3.10).
4. `SIM` (flake8-simplify): simplify boolean/conditional logic and common verbose patterns.
5. `S` (flake8-bandit): security-ish AST linting (fast, broad “bad patterns”).
6. `N` (pep8-naming): naming convention correctness.
7. `T10` (flake8-debugger): disallow debugger usage.
8. `T20` (flake8-print): disallow `print`.
9. `PT` (flake8-pytest-style): enforce pytest fixture/parametrize correctness.
10. `FAST` (FastAPI specific): FastAPI best-practice linting.
11. `RET` (flake8-return): unreachable/incorrect return patterns.
12. `ERA` (eradicate): commented-out code.
13. `ARG` (flake8-unused-arguments): unused arguments in functions/methods.

### Strictness detail (pre-commit vs CI)
Ruff should be “gate-only”, not “gate + auto-edit”.

Update `.pre-commit-config.yaml`:
- Remove `--fix` from the `ruff-check` hook so developers must fix issues rather than letting the hook rewrite code silently.

CI already runs Ruff without `--fix`, so CI remains strict/blocking.

### Why this isn’t redundant with your existing tools
1. `import-linter` + Semgrep check *architecture and wiring boundaries*; Ruff checks *local correctness and code-pattern risks*.
2. Pyright checks *type correctness*; Ruff rule families above check *code smells, API contract misuse, security patterns (S), and consistency (N/PT/FAST)*.
3. Ruff `S` and Bandit (below) overlap partially, but they are not identical. Ruff `S` is “rule-family fast AST checks”; Bandit is the dedicated security scanner with broader coverage.

## Change #2: Pre-commit hygiene hooks (the repo-wide “cheap wins” set)
### What changes
Update `.pre-commit-config.yaml` to add `pre-commit/pre-commit-hooks` with:
1. `check-yaml`, `check-json`, `check-toml`: syntax validation to prevent broken config files from landing.
2. `trailing-whitespace`: prevent whitespace churn and accidental diffs.
3. `end-of-file-fixer`: consistent EOF handling across editors.
4. `check-merge-conflict`: catch unresolved conflict markers early.
5. `detect-private-key`: stop obvious secret leakage before review.
6. `mixed-line-ending` with `--fix lf`: normalize line endings.

### Why this isn’t redundant
None of your existing custom hooks cover YAML/JSON/TOML syntax validity for general cases, and none of your CI jobs target “accidental whitespace / merge conflict markers”.

## Change #3: Bandit security gate (dedicated security scanner)
### Why Bandit in addition to Ruff `S`
Ruff `S` (flake8-bandit rules) is fast, but it is not the same coverage as Bandit. Dedicated security scanning gives you a broader second opinion for risky patterns.

### What changes
1. Add Bandit to `pyproject.toml` optional dependencies:
   - Add `bandit>=1.9.4` to the `[project.optional-dependencies].test` group.
2. Add CI step:
   - In `.github/workflows/ci.yml`, run Bandit as a blocking step in the Python test job.
3. Add local pre-commit hook:
   - Run Bandit in pre-commit via `uv run --extra test bandit ...`.

### Suggested Bandit command (used in CI/pre-commit)
Scan first-party backend code, exclude tests and UI:
```bash
uv run bandit -r simulation db ai lib feeds jobs ml_tooling -x tests -x ui
```

### Optional next step (not required for strict gating)
If you later want GitHub code-scanning/SARIF integration, Bandit can emit SARIF:
```bash
uv run bandit -r simulation db ai lib feeds jobs ml_tooling -x tests -x ui --format sarif --output bandit.sarif
```

## Non-redundancy matrix (quick check)
1. Ruff (`E/F/I/B/UP/SIM/S/N/T10/T20/PT/FAST/RET/ERA/ARG`): local correctness/style/security patterns.
2. Semgrep (`lint/semgrep/**` + DI guard): enforce contract boundaries (wiring rules).
3. `import-linter`: enforce import dependency purity and module directionality.
4. Pyright: type checking.
5. Bandit: dedicated security scanner.
6. `pre-commit-hooks`: file hygiene (syntax + whitespace + obvious secret leakage).

## Rollout notes (because this is strict)
1. Expect CI to fail until the repo is cleaned up for the newly enabled Ruff/Bandit rule families.
2. Run the following locally before pushing changes:
   - `uv run ruff check .`
   - `uv run ruff format --check .`
   - `uv run bandit -r simulation db ai lib feeds jobs ml_tooling -x tests -x ui`
3. Use pre-commit to validate the full gate locally:
   - `pre-commit run -a`

## Summary of intent
1. Ruff becomes a strict “correctness/style/security-pattern” gate for Python.
2. Pre-commit gains cheap repository hygiene checks to reduce review noise and prevent broken configs/secrets.
3. Bandit adds a dedicated security scan layer so “security-ish” patterns don’t rely solely on Ruff `S`.
