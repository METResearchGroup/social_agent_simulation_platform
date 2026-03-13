---
description: PR 1 plan for codifying persistence scopes (seed state vs run snapshot vs turn events) and adding schema-convention guardrails.
tags: [plan, architecture, persistence, schema, linting]
name: PR1 persistence contract
overview: "Plan the first migration PR as a contract-setting change: document the persistence-scope model and add lightweight schema guardrails, without introducing new tables or runtime behavior changes."
todos:
  - id: write-persistence-contract-docs
    content: Add the persistence-scope contract to docs/RULES.md and a new docs/architecture/seed-state-run-snapshot-turn-events.md doc, then surface it from docs/README.md.
    status: completed
  - id: add-schema-lint-tests
    content: Write focused tests for a new schema-convention linter before implementing the linter itself.
    status: completed
  - id: implement-schema-lint
    content: Add scripts/lint_schema_conventions.py to enforce the new scope rules against db.schema.metadata.
    status: completed
  - id: wire-guardrails
    content: Hook the schema-convention linter into pre-commit and CI, keeping the PR limited to contract enforcement only.
    status: completed
  - id: verify-pr1-scope
    content: Run markdown, lint, and focused test checks to prove PR 1 changes are docs/guardrail only and do not alter runtime behavior.
    status: completed
isProject: false
---

# PR 1 Persistence Scope Contract

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- UI changes: agent captures before/after screenshots itself (no README or instructions for the user)

## Overview

This PR should lock in the persistence-scope contract before any new `agent_*` or `run_*` tables land. The implementation should be intentionally narrow: document the canonical model, make it easy for reviewers to reject scope-mixing proposals, and add one lightweight schema guardrail so future schema PRs fail fast if they violate the contract. No Alembic revisions, API changes, runtime behavior changes, or simulation cutovers belong in PR 1.

Plan assets should live under the generated plan folder for this work, following `docs/plans/2026-03-10_pr1_persistence_contract_<hash>/`.

## Happy Flow

1. A reviewer reads the new `Persistence scopes` rules in `[docs/RULES.md](docs/RULES.md)` and sees the canonical contract: editable current state lives in `agent_*`, immutable run-start state lives in `run_*`, and execution history lives in `turn_*` plus the legacy event tables `likes`, `comments`, `follows`, and `generated_feeds`.
2. The deeper rationale and migration semantics live in a new architecture note at `[docs/architecture/seed-state-run-snapshot-turn-events.md](docs/architecture/seed-state-run-snapshot-turn-events.md)`. That doc explains the legacy exceptions already present in the repo, especially `[db/schema.py](db/schema.py)` tables like `agent`, `agent_persona_bios`, `user_agent_profile_metadata`, `runs`, `run_metrics`, `turn_metadata`, `turn_metrics`, `generated_feeds`, `likes`, `comments`, and `follows`.
3. `[docs/README.md](docs/README.md)` links to the new architecture note so the contract becomes part of the discoverable documentation surface instead of living only in a temp memo.
4. A new linter at `[scripts/lint_schema_conventions.py](scripts/lint_schema_conventions.py)` imports `db.schema.metadata`, classifies tables by persistence scope, and enforces only the rules that are mechanically checkable today.
5. Focused tests in `[tests/lint/test_lint_schema_conventions.py](tests/lint/test_lint_schema_conventions.py)` prove the linter accepts the current schema baseline and rejects representative mixed-scope violations.
6. Pre-commit and CI run the new guard automatically via `[.pre-commit-config.yaml](.pre-commit-config.yaml)` and `[.github/workflows/ci.yml](.github/workflows/ci.yml)`, so later PRs adding schema can be blocked before review if they blur seed state, run snapshots, and turn events.

## Implementation Steps

### 1. Codify the contract in repo docs

Update `[docs/RULES.md](docs/RULES.md)` by adding a dedicated `Persistence scopes` subsection under or adjacent to the current `Persistence and model boundaries` guidance.

That section should state, in repo-rule language:

- New editable seed-state tables use the `agent_*` namespace.
- New immutable run-start snapshot tables use the `run_*` namespace.
- New per-turn execution tables use the `turn_*` namespace.
- Existing `likes`, `comments`, `follows`, and `generated_feeds` are legacy-named turn-event tables and must keep their current semantics.
- Existing `agent`, `agent_persona_bios`, and `user_agent_profile_metadata` remain current-state tables even though they predate the naming convention.
- Historical run reads must not derive behaviorally relevant state from live current-state tables.
- Do not mix seed state and run/turn history in one table via nullable `run_id`, nullable `turn_number`, or a lifecycle-collapsing `source = manual | simulation` pattern.
- Counts are caches or summaries; row-level identities may only be migrated from row-level source data.

Add a durable architecture note at `[docs/architecture/seed-state-run-snapshot-turn-events.md](docs/architecture/seed-state-run-snapshot-turn-events.md)`. Keep it narrow and contract-focused rather than turning it into a full migration plan. Recommended sections:

- Problem statement
- Canonical scopes: current state, run snapshot, turn event
- Existing-table mapping from `[db/schema.py](db/schema.py)`
- Naming rules for new tables vs legacy exceptions
- Backfill contract: counts vs row-level facts
- Non-goals for PR 1

Update `[docs/README.md](docs/README.md)` to add an `Architecture` or `Data architecture` entry so this document is discoverable.

Do not land updates to `[temp/2026-03-08_data_architecture_rules/](temp/2026-03-08_data_architecture_rules/)` as part of PR 1. Those files are planning inputs, not part of the permanent contract surface.

### 2. Add TDD coverage for the new guardrail

Before implementing the linter, create `[tests/lint/test_lint_schema_conventions.py](tests/lint/test_lint_schema_conventions.py)`.

Model the test shape after the existing custom-linter test pattern in `[tests/lint/test_lint_python_testing_syntax_conventions.py](tests/lint/test_lint_python_testing_syntax_conventions.py)`:

- unit-test the linter entrypoint directly
- build small temporary schema fixtures or source strings that simulate valid and invalid table definitions
- assert exit codes and exact rule IDs/messages for failures

Start with a small rule set that is truly enforceable from schema metadata:

- `SCHEMA-1`: `agent_*` tables must not declare `run_id` or `turn_number`.
- `SCHEMA-2`: `run_*` tables must declare non-null `run_id`.
- `SCHEMA-3`: `turn_*` tables and legacy turn-event tables (`generated_feeds`, `likes`, `comments`, `follows`, `turn_metadata`, `turn_metrics`) must declare non-null `run_id` and non-null `turn_number`.
- `SCHEMA-4`: lifecycle rules are prefix-based for new tables, with explicit allowlists for legacy tables that predate the convention.

Do not try to encode every conceptual rule in PR 1. Keep the linter limited to what can be checked deterministically from SQLAlchemy metadata.

### 3. Implement the schema-convention linter

Create `[scripts/lint_schema_conventions.py](scripts/lint_schema_conventions.py)`.

Implementation shape:

- Import `metadata` from `[db/schema.py](db/schema.py)` rather than regexing source text.
- Iterate the SQLAlchemy `Table` objects and inspect names, columns, and nullability.
- Use explicit classification helpers for:
  - new `agent_*` tables
  - new `run_*` tables
  - new `turn_*` tables
  - legacy allowlisted current-state tables
  - legacy allowlisted run/turn tables
  - out-of-scope/import/auth tables
- Emit stable `path:line:col [SCHEMA-x] message`-style output where feasible, or a consistent `db/schema.py [SCHEMA-x] ...` format if precise source locations are not worth the complexity.
- Print a single `OK (...)` success line on a clean run, matching the repo’s existing custom-linter ergonomics.

Keep this linter scoped to schema conventions only. Do not fold service-boundary enforcement into PR 1. Python-layer historical-read rules can come later, once `agent_*` and `run_*` repositories actually exist.

### 4. Wire the guard into the existing quality gates

Add the new linter to `[.pre-commit-config.yaml](.pre-commit-config.yaml)` as a local hook with a clear name such as `db_schema_conventions`.

Update `[.github/workflows/ci.yml](.github/workflows/ci.yml)` so the same command runs in CI. The cleanest placement is the existing `schema` job because this check is about `db/schema.py` conventions, not DI wiring.

If the team wants a short local run command documented, make the smallest possible update to `[docs/runbooks/PRE_COMMIT_AND_LINTING.md](docs/runbooks/PRE_COMMIT_AND_LINTING.md)` so developers know to run:

- `uv run python scripts/lint_schema_conventions.py`
- `uv run pre-commit run --all-files`

That runbook change is optional but reasonable; prefer one short addition over a brand-new runbook.

### 5. Keep PR 1 intentionally narrow

Explicitly exclude the following from this PR:

- changes to `[db/schema.py](db/schema.py)` table definitions
- Alembic revisions under `[db/migrations/versions/](db/migrations/versions/)`
- repository or adapter additions under `[db/repositories/](db/repositories/)` or `[db/adapters/sqlite/](db/adapters/sqlite/)`
- API changes under `[simulation/api/](simulation/api/)`
- runtime/simulation behavior changes under `[simulation/core/](simulation/core/)`
- DB schema docs regeneration under `[docs/db/](docs/db/)` unless a real schema change happens

The only code changes in PR 1 should be guardrail code and its tests. Everything else is documentation.

## Manual Verification

- Read `[docs/RULES.md](docs/RULES.md)` and confirm the new `Persistence scopes` section clearly distinguishes current-state, run-snapshot, and turn-event storage, including the legacy exceptions already present in `[db/schema.py](db/schema.py)`.
- Read `[docs/architecture/seed-state-run-snapshot-turn-events.md](docs/architecture/seed-state-run-snapshot-turn-events.md)` and confirm it documents the contract and non-goals for PR 1 without drifting into later PR implementation details.
- Run `uv run pytest tests/lint/test_lint_schema_conventions.py -q` and confirm the focused linter tests pass.
- Run `uv run python scripts/lint_schema_conventions.py` and confirm the output is a single success line such as `OK (...)` against the current schema.
- Run `uv run pre-commit run markdownlint --files docs/RULES.md docs/README.md docs/architecture/seed-state-run-snapshot-turn-events.md` and confirm markdown checks pass.
- If `[docs/runbooks/PRE_COMMIT_AND_LINTING.md](docs/runbooks/PRE_COMMIT_AND_LINTING.md)` is edited, run `uv run python scripts/check_docs_metadata.py docs/runbooks/PRE_COMMIT_AND_LINTING.md` and confirm metadata validation passes.
- Run `uv run pre-commit run --all-files` and confirm the new schema-convention guard participates cleanly with the existing repo checks.
- Confirm no Alembic revision, runtime service, API schema, or UI file changed in the PR diff.

## Alternative Approaches

- Docs-only PR with no enforcement: rejected because PR 1 is explicitly supposed to establish a contract reviewers can enforce mechanically, not just describe in prose.
- Extend `[scripts/lint_architecture.py](scripts/lint_architecture.py)` instead of creating a schema-specific linter: possible, but less clear because the contract here is about persisted table shape rather than DI or Python service wiring. A dedicated schema linter fits the concern better.
- Defer all enforcement to later migration PRs: rejected because that leaves PR 2 and PR 3 without a hard guardrail during the highest-risk modeling phase.
- Add broader Python-layer service-boundary rules now: deferred because the future `agent_*` and `run_*` repositories/services do not exist yet, so the rule surface would mostly be speculative in PR 1.

