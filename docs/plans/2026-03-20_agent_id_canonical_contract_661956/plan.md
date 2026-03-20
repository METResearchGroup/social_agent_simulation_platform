---
name: canonical-agent-id-contract
description: Plan to define and validate a canonical 16-character lowercase hex agent_id contract and helper API before any persistence-layer migration work.
tags:
  - planning
  - agent-id
  - architecture
  - testing
overview: Define and validate a single canonical agent ID contract (16-char lowercase hex) and helper API so all later identity migration work can safely depend on one deterministic generation/validation surface without changing persisted data yet.
todos: []
isProject: false
---

# Canonical Agent ID Contract Plan

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- Maximum safely delegable parallelism
- Delegated tasks must be impossible to misread
- UI changes: agent captures before/after screenshots itself (no README or instructions for the user)

## Overview

Establish one canonical `agent_id` contract first: a deterministic helper API for generating/validating 16-character lowercase hex IDs, plus explicit model-boundary behavior in `Agent` so downstream creation-path updates and DB rewrites can proceed against a stable identity contract. This unit intentionally avoids schema/migration/runtime persistence changes and focuses on contract correctness, test coverage, and rollout-safe compatibility decisions.

## Context Carried Forward

- Canonical storage format is strict regex `^[0-9a-f]{16}$` and disallows DID/UUID/handle/`agent_*` forms.
- Canonical helper API target:
  - `canonical_agent_id(source: str | None = None) -> str`
  - `is_canonical_agent_id(value: str) -> bool`
- Deterministic behavior is required when `source` is provided; entropy-based generation is allowed when omitted.
- This unit must not mutate persisted IDs or require DB migration support yet.

## Happy Flow

1. Add canonical helper functions in `[/Users/mark/Documents/work/agent_simulation_platform_worktree/lib/agent_id.py](/Users/mark/Documents/work/agent_simulation_platform_worktree/lib/agent_id.py)` that normalize input, hash, and emit a 16-char lowercase hex ID.
2. Add/adjust `Agent` model guardrails in `[/Users/mark/Documents/work/agent_simulation_platform_worktree/simulation/core/models/agent.py](/Users/mark/Documents/work/agent_simulation_platform_worktree/simulation/core/models/agent.py)` to enforce or compatibly gate canonical-ID expectations without breaking current persisted data reads.
3. Add focused unit tests under `[/Users/mark/Documents/work/agent_simulation_platform_worktree/tests/](/Users/mark/Documents/work/agent_simulation_platform_worktree/tests/)` proving deterministic generation, canonical formatting, and validator correctness.
4. Run targeted tests and type/lint checks to freeze this contract for all downstream identity work.

## Interface or Contract Freeze

- Frozen API surface:
  - `canonical_agent_id(source: str | None = None) -> str`
  - `is_canonical_agent_id(value: str) -> bool`
- Frozen canonical format: `^[0-9a-f]{16}$` only.
- Frozen non-goals in this unit:
  - No edits to `[/Users/mark/Documents/work/agent_simulation_platform_worktree/db/schema.py](/Users/mark/Documents/work/agent_simulation_platform_worktree/db/schema.py)`
  - No edits to migration files under `[/Users/mark/Documents/work/agent_simulation_platform_worktree/db/migrations/versions/](/Users/mark/Documents/work/agent_simulation_platform_worktree/db/migrations/versions/)`
  - No runtime action/feed adapter rewrites

## Serial Coordination Spine

1. Define contract behavior and compatibility stance for `Agent` validation (hard reject vs temporary compatibility mode) before coding.
2. Land helper implementation and tests first to create a single importable source of truth.
3. Land model-boundary validation changes only after helper tests pass.
4. Re-run targeted tests and then broader safety checks.

## Parallel Task Packets

### Packet P1 — Canonical helper + tests

- **Task ID:** `P1-helper-contract`
- **Objective:** Implement canonical generation/validation helpers and their unit tests.
- **Why parallelizable:** Isolated utility + tests with no schema/runtime ownership overlap.
- **Inspect files:**
  - `[/Users/mark/Documents/work/agent_simulation_platform_worktree/lib/](/Users/mark/Documents/work/agent_simulation_platform_worktree/lib/)`
  - `[/Users/mark/Documents/work/agent_simulation_platform_worktree/tests/](/Users/mark/Documents/work/agent_simulation_platform_worktree/tests/)`
- **Allowed to change:**
  - `[/Users/mark/Documents/work/agent_simulation_platform_worktree/lib/agent_id.py](/Users/mark/Documents/work/agent_simulation_platform_worktree/lib/agent_id.py)`
  - New/updated helper tests in `[/Users/mark/Documents/work/agent_simulation_platform_worktree/tests/](/Users/mark/Documents/work/agent_simulation_platform_worktree/tests/)`
- **Forbidden to change:**
  - `[/Users/mark/Documents/work/agent_simulation_platform_worktree/db/schema.py](/Users/mark/Documents/work/agent_simulation_platform_worktree/db/schema.py)`
  - `[/Users/mark/Documents/work/agent_simulation_platform_worktree/db/migrations/versions/](/Users/mark/Documents/work/agent_simulation_platform_worktree/db/migrations/versions/)`
  - `[/Users/mark/Documents/work/agent_simulation_platform_worktree/simulation/core/models/agent.py](/Users/mark/Documents/work/agent_simulation_platform_worktree/simulation/core/models/agent.py)`
- **Preconditions:** Contract freeze accepted.
- **Dependencies:** None.
- **Required contracts/invariants:** Deterministic with source, canonical regex output always, no external side effects.
- **Implementation steps:**
  1. Implement `canonical_agent_id` with source normalization (`strip`) and SHA-256 truncation to 16 lowercase hex chars.
  2. Implement `is_canonical_agent_id` regex validator.
  3. Add tests for same-input determinism, different-input divergence, omitted-source canonical shape, and validator pass/fail matrix.
- **Verification commands:**
  - `uv run pytest tests -k "agent_id" -v`
- **Expected outputs:** all helper-related tests pass; no flaky entropy-format failures.
- **Done when:** helper functions exist, tests are green, contract semantics are explicit in test names/docstrings.
- **Coordinator review checklist:** API signatures exact, regex exact, no non-canonical outputs in tests.

### Packet P2 — Agent model boundary semantics

- **Task ID:** `P2-agent-model-guardrails`
- **Objective:** Align `Agent` model validation behavior with canonical helper contract while preserving rollout safety.
- **Why parallelizable:** Single-file model concern once helper contract is frozen.
- **Inspect files:**
  - `[/Users/mark/Documents/work/agent_simulation_platform_worktree/simulation/core/models/agent.py](/Users/mark/Documents/work/agent_simulation_platform_worktree/simulation/core/models/agent.py)`
  - Helper API from `[/Users/mark/Documents/work/agent_simulation_platform_worktree/lib/agent_id.py](/Users/mark/Documents/work/agent_simulation_platform_worktree/lib/agent_id.py)`
- **Allowed to change:**
  - `[/Users/mark/Documents/work/agent_simulation_platform_worktree/simulation/core/models/agent.py](/Users/mark/Documents/work/agent_simulation_platform_worktree/simulation/core/models/agent.py)`
  - Targeted model tests under `[/Users/mark/Documents/work/agent_simulation_platform_worktree/tests/](/Users/mark/Documents/work/agent_simulation_platform_worktree/tests/)`
- **Forbidden to change:**
  - DB schema/migrations
  - API command services
  - runtime action/feed code
- **Preconditions:** `P1-helper-contract` merged or available locally.
- **Dependencies:** `P1-helper-contract`.
- **Required contracts/invariants:** No persisted-ID rewrites; compatibility choice is explicit and tested.
- **Implementation steps:**
  1. Import and use `is_canonical_agent_id` at the model boundary.
  2. Implement chosen validation policy (strict or temporary compatibility gate) behind explicit code path.
  3. Add tests that prove intended accept/reject behavior and prevent accidental silent semantics drift.
- **Verification commands:**
  - `uv run pytest tests -k "agent and agent_id" -v`
- **Expected outputs:** model behavior matches policy, no regressions in relevant model tests.
- **Done when:** model behavior is explicit, tested, and documented in code comments where non-obvious.
- **Coordinator review checklist:** no DB touches, no hidden coercion, failure modes are deterministic.

## Integration Order

1. Complete `P1-helper-contract` and pass helper tests.
2. Integrate `P2-agent-model-guardrails` against frozen helper API.
3. Run combined targeted suite:
  - `uv run pytest tests -k "agent_id or simulation/core/models/agent" -v`
4. Run repo safety gates relevant to touched files:
  - `uv run ruff check lib/agent_id.py simulation/core/models/agent.py tests`
  - `uv run pyright lib simulation/core tests`

## Manual Verification

- Run helper tests: `uv run pytest tests -k "agent_id" -v` (expected: all pass)
- Run model semantics tests: `uv run pytest tests -k "agent and agent_id" -v` (expected: pass with explicit validation behavior)
- Spot-check canonical output from REPL/script by calling helper with representative inputs (`did:...`, UUID-like string, whitespace-padded input) and confirm all outputs match `^[0-9a-f]{16}$`
- Confirm no DB/migration changes are introduced in this unit (`git diff -- db/schema.py db/migrations/versions/` shows no edits)
- Run lint/type checks for touched modules:
  - `uv run ruff check lib/agent_id.py simulation/core/models/agent.py tests`
  - `uv run pyright lib simulation/core tests`
  - expected: no new errors from touched code

## Final Verification

- Helper API exists at one canonical import path in `[/Users/mark/Documents/work/agent_simulation_platform_worktree/lib/agent_id.py](/Users/mark/Documents/work/agent_simulation_platform_worktree/lib/agent_id.py)`
- Validator semantics are test-locked
- `Agent` model behavior is explicit and rollout-safe
- No persistence-layer or migration-layer changes are included
- This contract is ready to unblock downstream creation-path normalization and full FK migration work

## Alternative approaches

- **Chosen:** freeze helper+model contract first, with tests, before touching creation paths or DB.
  - Why: minimizes blast radius and gives downstream work a stable interface.
- **Not chosen:** immediately update creation paths and DB together.
  - Why not: conflates contract definition with migration risk, making regressions harder to isolate.

## Plan Asset Storage

Store implementation notes and any optional validation artifacts in:

- `docs/plans/2026-03-20_agent_id_canonical_contract_661956/`
- (No UI screenshots required because this unit has no `ui/` changes.)
