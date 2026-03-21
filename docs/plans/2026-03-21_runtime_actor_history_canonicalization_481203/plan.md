---
name: Runtime Actor IDs
overview: Tighten the remaining runtime seam of the agent ID migration by moving actor-side history, duplicate suppression, and seeded-history preload from `agent_handle` keys to canonical `agent_id` keys, while explicitly not redoing schema, creation-path, or query-display work that already landed in earlier PRs.
description: Runtime canonicalization of actor-side action history keys from agent_handle to agent_id across action_history, policy/validator, follow selection, and command_service preload—without redoing DB schema, creation paths, or query display.
tags:
  - agent-id
  - action-history
  - runtime
  - simulation
  - canonicalization
todos:
  - id: freeze-runtime-contract
    content: Freeze the runtime actor-history contract and proposal corrections before any edits.
    status: pending
  - id: history-core
    content: Migrate action-history interfaces/store/recording to use canonical actor agent_id keys.
    status: pending
  - id: policy-validator
    content: Update candidate filtering and rules validation to query history by actor agent_id.
    status: pending
  - id: follow-selection
    content: Finish canonical follow candidate selection/dedupe semantics without changing prompt/display handle usage.
    status: pending
  - id: command-service-integration
    content: Seed and consume runtime history from snapshots using canonical IDs, then run the targeted regression suite.
    status: pending
isProject: false
---

# Runtime Actor History Canonicalization

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- Maximum safely delegable parallelism
- Delegated tasks must be impossible to misread
- UI changes: agent captures before/after screenshots itself (no README or instructions for the user)

## Overview

Earlier work already established the canonical ID contract in `lib/agent_id.py`, normalized agent creation paths, rewrote the PK/FK graph, renamed action/feed schema to `agent_id` / `target_agent_id`, and tightened the generated-feed read boundary. The remaining gap is narrower: runtime action history, duplicate suppression, and seeded-history preload still key the acting agent by `agent_handle` in `simulation/core/action_history/interfaces.py`, `simulation/core/action_history/stores.py`, `simulation/core/action_policy/candidate_filter.py`, `simulation/core/action_policy/rules_validator.py`, and `simulation/core/services/command_service.py`. Resolving that actor-side history-key defect is required scope for this unit of work, because leaving it in place preserves alias-drift bugs even after the persistence layer has moved to canonical IDs. This plan focuses only on that remaining runtime seam and intentionally leaves query/display projection and DB schema work alone.

## Plan Asset Path

- `docs/plans/2026-03-21_runtime_actor_history_canonicalization_481203/`
- No `ui/` files are in scope, so screenshot capture is not applicable for this unit of work.

## Happy Flow

1. `SimulationCommandService._simulate_turn()` reads each `SimulationAgent` with both `agent.handle` and canonical `agent.agent_id`, then calls the existing generators through `simulation/core/agent_actions.py`.
2. `HistoryAwareActionFeedFilter.filter_candidates()` in `[simulation/core/action_policy/candidate_filter.py](simulation/core/action_policy/candidate_filter.py)` checks prior likes/comments/follows by `(run_id, agent_id, target)` rather than `(run_id, agent_handle, target)`.
3. `AgentActionRulesValidator.validate()` in `[simulation/core/action_policy/rules_validator.py](simulation/core/action_policy/rules_validator.py)` rejects duplicate or previously-seen actions using the same canonical actor key.
4. `record_action_targets()` in `[simulation/core/action_history/recording.py](simulation/core/action_history/recording.py)` writes validated targets into `[simulation/core/action_history/stores.py](simulation/core/action_history/stores.py)` under `(run_id, agent_id)`.
5. `SimulationCommandService.preload_like_history_from_snapshots()`, `preload_comment_history_from_snapshots()`, and `preload_follow_history_from_snapshots()` in `[simulation/core/services/command_service.py](simulation/core/services/command_service.py)` seed history directly from snapshot agent IDs and run-post IDs, without converting actor IDs back to handles.
6. Follow generators in `[simulation/core/action_generators/follow/algorithms/random_simple.py](simulation/core/action_generators/follow/algorithms/random_simple.py)` and `[simulation/core/action_generators/follow/algorithms/naive_llm/algorithm.py](simulation/core/action_generators/follow/algorithms/naive_llm/algorithm.py)` continue to use handles for prompt/display text, but dedupe, self-exclusion, and target selection resolve through canonical target IDs via `[simulation/core/action_generators/follow/utils.py](simulation/core/action_generators/follow/utils.py)`.
7. `[simulation/core/services/query_service.py](simulation/core/services/query_service.py)` remains the presentation boundary: it projects canonical IDs back to `run_agents.handle_at_start` for returned `TurnData`, and this plan does not rework that behavior.

## Review Findings That Change The Plan

- Already implemented and out of scope for this unit:
  - `[lib/agent_id.py](lib/agent_id.py)` canonical helper and validation
  - `[simulation/api/services/agent_command_service.py](simulation/api/services/agent_command_service.py)` creation-path normalization
  - `[jobs/migrate_agents_to_new_schema.py](jobs/migrate_agents_to_new_schema.py)` profile migration normalization
  - `[simulation/local_dev/seed_loader.py](simulation/local_dev/seed_loader.py)` seed canonicalization
  - `[db/migrations/versions/c3d5e7f9a0b2_rewrite_agent_primary_keys_and_fks.py](db/migrations/versions/c3d5e7f9a0b2_rewrite_agent_primary_keys_and_fks.py)` and `[db/migrations/versions/d4f8a1c3e5b7_action_feed_id_semantics.py](db/migrations/versions/d4f8a1c3e5b7_action_feed_id_semantics.py)`
  - `[db/repositories/generated_feed_repository.py](db/repositories/generated_feed_repository.py)` canonical read boundary
  - `[simulation/core/services/query_service.py](simulation/core/services/query_service.py)` handle projection from canonical IDs for display
- Proposal correction: do not re-plan generator signature changes for likes/comments/follows. `[simulation/core/action_generators/interfaces.py](simulation/core/action_generators/interfaces.py)` already accepts `agent_id` for all three generator types.
- Proposal correction: do not introduce a new runtime `handle -> agent_id` map for follow generation. The canonical source should remain `Post.author_agent_id` when present, with `canonical_agent_id(post.author_handle)` only as a compatibility fallback in `[simulation/core/action_generators/follow/utils.py](simulation/core/action_generators/follow/utils.py)`.
- Highest-risk remaining defect: the actor-side history key is still `agent_handle` throughout `[simulation/core/action_history/interfaces.py](simulation/core/action_history/interfaces.py)` and all of its callers, so duplicate suppression is still vulnerable to alias drift even though persisted rows now store canonical IDs.
- Scope decision: yes, resolving that defect is in-scope for this plan and is a mandatory outcome, not optional hardening.

## Serial Coordination Spine

1. Freeze the runtime contract: actor-side history keys become `agent_id` everywhere in `[simulation/core/action_history/interfaces.py](simulation/core/action_history/interfaces.py)` and its call graph; handles remain allowed only for prompt text, human-readable error messages, and presentation.
2. Land the action-history contract change first so parallel work has one stable interface.
3. Run the policy/validator packet and the follow-selection packet in parallel after the contract freeze.
4. Integrate `[simulation/core/services/command_service.py](simulation/core/services/command_service.py)` against the new history contract and rerun the targeted simulation tests.
5. Finish with a focused regression pass; only if a failing test proves it necessary should this unit widen into `[simulation/core/services/query_service.py](simulation/core/services/query_service.py)` or `feeds/`.

## Interface Or Contract Freeze

- Canonical actor key for runtime history: `agent_id: str`.
- Mandatory resolution: this unit is not done until `ActionHistoryStore` and all touched runtime callers stop using `agent_handle` as the durable actor-history key.
- Like/comment history target keys stay unchanged: `post_id` for generated actions and `run_post_id` for seeded snapshot preload.
- Follow history target key stays `target_agent_id: str` and must already be canonical by the time it reaches the history layer.
- `[simulation/core/agent_actions.py](simulation/core/agent_actions.py)` keeps both `agent_handle` and `agent_id` in public helper signatures; this plan does not widen those interfaces further.
- `[simulation/core/services/query_service.py](simulation/core/services/query_service.py)` and `[feeds/feed_generator.py](feeds/feed_generator.py)` are read-only unless a failing targeted test demonstrates a hard dependency.
- Touched tests should stop using raw placeholder actor IDs such as `"agent1"` where the assertion is about canonical actor-history behavior.

## Parallel Task Packets

### Packet `history-core`

- Objective: change the action-history contract and in-memory store from handle-keyed actor history to canonical actor-ID history.
- Why parallelizable: once the contract is frozen, this packet is isolated to the history core and its direct unit tests.
- Exact files to inspect:
  - `[simulation/core/action_history/interfaces.py](simulation/core/action_history/interfaces.py)`
  - `[simulation/core/action_history/stores.py](simulation/core/action_history/stores.py)`
  - `[simulation/core/action_history/recording.py](simulation/core/action_history/recording.py)`
  - `[tests/simulation/core/test_action_history_recording.py](tests/simulation/core/test_action_history_recording.py)`
- Exact files allowed to change:
  - `[simulation/core/action_history/interfaces.py](simulation/core/action_history/interfaces.py)`
  - `[simulation/core/action_history/stores.py](simulation/core/action_history/stores.py)`
  - `[simulation/core/action_history/recording.py](simulation/core/action_history/recording.py)`
  - `[tests/simulation/core/test_action_history_recording.py](tests/simulation/core/test_action_history_recording.py)`
- Exact files forbidden to change:
  - `[simulation/core/services/command_service.py](simulation/core/services/command_service.py)`
  - `[simulation/core/action_policy/candidate_filter.py](simulation/core/action_policy/candidate_filter.py)`
  - `[simulation/core/action_policy/rules_validator.py](simulation/core/action_policy/rules_validator.py)`
  - `[simulation/core/action_generators/follow/algorithms/random_simple.py](simulation/core/action_generators/follow/algorithms/random_simple.py)`
  - `[simulation/core/action_generators/follow/algorithms/naive_llm/algorithm.py](simulation/core/action_generators/follow/algorithms/naive_llm/algorithm.py)`
- Preconditions:
  - The contract freeze above is accepted.
- Dependency tasks:
  - `freeze-runtime-contract`
- Required contracts and invariants:
  - `ActionHistoryStore` method names may stay the same, but the actor argument must be `agent_id` everywhere.
  - The storage key shape is `(run_id, agent_id)` for all action types.
  - Follow targets remain canonical `target_agent_id` values.
  - This packet must not introduce any handle fallback inside the history layer.
- Step-by-step implementation instructions:
  1. Rename parameters and docstrings in `[simulation/core/action_history/interfaces.py](simulation/core/action_history/interfaces.py)` from `agent_handle` to `agent_id`.
  2. Update `[simulation/core/action_history/stores.py](simulation/core/action_history/stores.py)` to key likes/comments/follows by canonical actor ID and rename internal dicts accordingly.
  3. Update `[simulation/core/action_history/recording.py](simulation/core/action_history/recording.py)` so `record_action_targets()` records by `agent_id`.
  4. Rewrite `[tests/simulation/core/test_action_history_recording.py](tests/simulation/core/test_action_history_recording.py)` to assert canonical actor IDs are used in both write and read paths.
- Exact verification commands:
  - `uv run pytest tests/simulation/core/test_action_history_recording.py -q`
- Expected outputs from verification:
  - Pytest exits `0`.
  - The file reports all tests passed with no new failures.
- Done-when checklist:
  - No public method in `[simulation/core/action_history/interfaces.py](simulation/core/action_history/interfaces.py)` uses `agent_handle` as the actor-history key.
  - `[simulation/core/action_history/stores.py](simulation/core/action_history/stores.py)` uses canonical actor IDs for likes, comments, and follows.
  - `[tests/simulation/core/test_action_history_recording.py](tests/simulation/core/test_action_history_recording.py)` passes.
- Coordinator review checklist:
  - Search the touched files for `agent_handle` and confirm it appears only in comments or human-readable context, not as a history key.
  - Confirm the packet did not edit policy, command-service, or generator files.

### Packet `policy-validator`

- Objective: move history-aware filtering and duplicate validation onto canonical actor IDs while preserving the existing target semantics.
- Why parallelizable: after `history-core` lands, this packet is isolated to policy/validator code and its tests.
- Exact files to inspect:
  - `[simulation/core/action_policy/candidate_filter.py](simulation/core/action_policy/candidate_filter.py)`
  - `[simulation/core/action_policy/rules_validator.py](simulation/core/action_policy/rules_validator.py)`
  - `[tests/simulation/core/test_agent_action_feed_filter.py](tests/simulation/core/test_agent_action_feed_filter.py)`
  - `[tests/simulation/core/test_agent_action_rules_validator.py](tests/simulation/core/test_agent_action_rules_validator.py)`
- Exact files allowed to change:
  - `[simulation/core/action_policy/candidate_filter.py](simulation/core/action_policy/candidate_filter.py)`
  - `[simulation/core/action_policy/rules_validator.py](simulation/core/action_policy/rules_validator.py)`
  - `[tests/simulation/core/test_agent_action_feed_filter.py](tests/simulation/core/test_agent_action_feed_filter.py)`
  - `[tests/simulation/core/test_agent_action_rules_validator.py](tests/simulation/core/test_agent_action_rules_validator.py)`
- Exact files forbidden to change:
  - `[simulation/core/services/command_service.py](simulation/core/services/command_service.py)`
  - `[simulation/core/action_generators/follow/algorithms/random_simple.py](simulation/core/action_generators/follow/algorithms/random_simple.py)`
  - `[simulation/core/action_generators/follow/algorithms/naive_llm/algorithm.py](simulation/core/action_generators/follow/algorithms/naive_llm/algorithm.py)`
- Preconditions:
  - `history-core` is merged locally or available in the working branch.
- Dependency tasks:
  - `history-core`
- Required contracts and invariants:
  - `HistoryAwareActionFeedFilter.filter_candidates()` must call history methods with canonical actor ID.
  - `AgentActionRulesValidator.validate()` and all helper methods must use canonical actor ID as the cross-turn duplicate key.
  - Error messages may still include handles if that is materially useful, but history lookups must not use them.
  - Follow target derivation remains `_follow_target_key_for_history(post)` or an equivalent canonical helper.
- Step-by-step implementation instructions:
  1. Add `agent_id` to the relevant filter/validator method signatures and thread it through every history lookup.
  2. Update `[simulation/core/action_policy/rules_validator.py](simulation/core/action_policy/rules_validator.py)` dispatch helpers, validators, and error text to distinguish actor display text from actor history key if both are needed.
  3. Rewrite `[tests/simulation/core/test_agent_action_feed_filter.py](tests/simulation/core/test_agent_action_feed_filter.py)` to assert the mock store receives canonical actor IDs.
  4. Rewrite `[tests/simulation/core/test_agent_action_rules_validator.py](tests/simulation/core/test_agent_action_rules_validator.py)` to use canonical actor IDs in history assertions and avoid raw placeholder IDs where the test is about runtime semantics.
- Exact verification commands:
  - `uv run pytest tests/simulation/core/test_agent_action_feed_filter.py tests/simulation/core/test_agent_action_rules_validator.py -q`
- Expected outputs from verification:
  - Pytest exits `0`.
  - All filter/validator tests pass without relying on handle-keyed history.
- Done-when checklist:
  - No history lookup in `[simulation/core/action_policy/candidate_filter.py](simulation/core/action_policy/candidate_filter.py)` passes `agent_handle` as the actor key.
  - No cross-turn history check in `[simulation/core/action_policy/rules_validator.py](simulation/core/action_policy/rules_validator.py)` passes `agent_handle` as the actor key.
  - The two targeted test files pass.
- Coordinator review checklist:
  - Confirm the packet did not widen into command-service or feed/query files.
  - Confirm at least one test asserts canonical actor IDs reach the mock store.

### Packet `follow-selection`

- Objective: finish the remaining follow-generation semantics so self-exclusion and author dedupe are canonical-ID aware, while keeping handles only for prompt/display text.
- Why parallelizable: this packet does not depend on the action-history contract as long as the interface freeze is in place.
- Exact files to inspect:
  - `[simulation/core/action_generators/follow/utils.py](simulation/core/action_generators/follow/utils.py)`
  - `[simulation/core/action_generators/follow/algorithms/random_simple.py](simulation/core/action_generators/follow/algorithms/random_simple.py)`
  - `[simulation/core/action_generators/follow/algorithms/naive_llm/algorithm.py](simulation/core/action_generators/follow/algorithms/naive_llm/algorithm.py)`
  - `[tests/simulation/core/test_random_simple_follow_policy.py](tests/simulation/core/test_random_simple_follow_policy.py)`
  - `[tests/simulation/core/test_naive_llm_action_generators.py](tests/simulation/core/test_naive_llm_action_generators.py)`
- Exact files allowed to change:
  - `[simulation/core/action_generators/follow/utils.py](simulation/core/action_generators/follow/utils.py)`
  - `[simulation/core/action_generators/follow/algorithms/random_simple.py](simulation/core/action_generators/follow/algorithms/random_simple.py)`
  - `[simulation/core/action_generators/follow/algorithms/naive_llm/algorithm.py](simulation/core/action_generators/follow/algorithms/naive_llm/algorithm.py)`
  - `[tests/simulation/core/test_random_simple_follow_policy.py](tests/simulation/core/test_random_simple_follow_policy.py)`
  - `[tests/simulation/core/test_naive_llm_action_generators.py](tests/simulation/core/test_naive_llm_action_generators.py)`
- Exact files forbidden to change:
  - `[simulation/core/action_history/interfaces.py](simulation/core/action_history/interfaces.py)`
  - `[simulation/core/action_history/stores.py](simulation/core/action_history/stores.py)`
  - `[simulation/core/services/command_service.py](simulation/core/services/command_service.py)`
  - `[simulation/core/services/query_service.py](simulation/core/services/query_service.py)`
- Preconditions:
  - The interface freeze is accepted.
- Dependency tasks:
  - `freeze-runtime-contract`
- Required contracts and invariants:
  - Generated `Follow.agent_id` and `Follow.target_agent_id` remain canonical.
  - Author dedupe and self-exclusion should key on canonical target identity where possible, not only on `author_handle`.
  - LLM prompts may still present author handles, but the internal mapping from prompt IDs back to posts must not reintroduce handle-only semantics where a canonical ID is already present.
- Step-by-step implementation instructions:
  1. Review `[simulation/core/action_generators/follow/utils.py](simulation/core/action_generators/follow/utils.py)` and decide whether to add a second helper for “canonical author identity key” rather than overloading `derive_target_agent_id()`.
  2. Update `[simulation/core/action_generators/follow/algorithms/random_simple.py](simulation/core/action_generators/follow/algorithms/random_simple.py)` so dedupe and self-exclusion prefer canonical author IDs when present.
  3. Update `[simulation/core/action_generators/follow/algorithms/naive_llm/algorithm.py](simulation/core/action_generators/follow/algorithms/naive_llm/algorithm.py)` so internal author grouping/dedupe is canonical-aware even though prompt/display text still uses handles.
  4. Strengthen `[tests/simulation/core/test_random_simple_follow_policy.py](tests/simulation/core/test_random_simple_follow_policy.py)` and `[tests/simulation/core/test_naive_llm_action_generators.py](tests/simulation/core/test_naive_llm_action_generators.py)` to cover alias/self cases where `author_agent_id` and `author_handle` are intentionally different.
- Exact verification commands:
  - `uv run pytest tests/simulation/core/test_random_simple_follow_policy.py tests/simulation/core/test_naive_llm_action_generators.py -q`
- Expected outputs from verification:
  - Pytest exits `0`.
  - Follow-generation tests pass with canonical target assertions intact.
- Done-when checklist:
  - The two follow algorithms do not rely solely on `author_handle` for dedupe/self-exclusion.
  - The strengthened tests cover a canonical-ID-first author case.
  - No edits were made to history-store or query-service files.
- Coordinator review checklist:
  - Confirm prompt/display payloads still use handles where intended.
  - Confirm canonical target IDs are still the persisted semantics.

## Integration Order

1. Apply `history-core`.
2. Apply `policy-validator` and `follow-selection` in parallel.
3. Update `[simulation/core/services/command_service.py](simulation/core/services/command_service.py)` and `[simulation/core/agent_actions.py](simulation/core/agent_actions.py)` only where needed to satisfy the new actor-history contract.
4. Rerun the targeted runtime suite.
5. If, and only if, a failing test proves it necessary, make the smallest follow-up adjustment in `[tests/factories/](tests/factories/)` or a touched call site to keep runtime tests canonical-aware.

## Integration Details For Command Service

- Exact files to inspect:
  - `[simulation/core/services/command_service.py](simulation/core/services/command_service.py)`
  - `[simulation/core/agent_actions.py](simulation/core/agent_actions.py)`
  - `[tests/simulation/core/test_command_service.py](tests/simulation/core/test_command_service.py)`
- Exact files allowed to change:
  - `[simulation/core/services/command_service.py](simulation/core/services/command_service.py)`
  - `[simulation/core/agent_actions.py](simulation/core/agent_actions.py)`
  - `[tests/simulation/core/test_command_service.py](tests/simulation/core/test_command_service.py)`
- Exact files forbidden to change:
  - `[simulation/core/services/query_service.py](simulation/core/services/query_service.py)`
  - `[feeds/feed_generator.py](feeds/feed_generator.py)`
  - any file under `db/migrations/versions/`
- Required contracts and invariants:
  - Seeded history for likes/comments/follows must record actor `agent_id` directly from snapshots.
  - Follow preload must record `snapshot.target_agent_id` directly and must not round-trip through handle canonicalization.
  - `_simulate_turn()` must pass canonical actor IDs into filtering, validation, and history recording without changing existing prompt/display-handle behavior.
- Step-by-step implementation instructions:
  1. Update all `preload_*_history_from_snapshots()` helpers in `[simulation/core/services/command_service.py](simulation/core/services/command_service.py)` to record by snapshot agent IDs.
  2. Remove any `handle_by_agent_id` lookup that exists only to recover the actor history key.
  3. Preserve the guard that validates snapshot referential integrity, but make it validate missing canonical IDs rather than missing display handles where appropriate.
  4. Update `[tests/simulation/core/test_command_service.py](tests/simulation/core/test_command_service.py)` so seeded-history assertions prove the actor key is canonical and follow preload no longer re-derives the target ID from handle text.
- Exact verification commands:
  - `uv run pytest tests/simulation/core/test_command_service.py -q`
- Expected outputs from verification:
  - Pytest exits `0`.
  - Command-service runtime/preload tests pass with canonical actor-history assertions.
- Done-when checklist:
  - No history preload helper in `[simulation/core/services/command_service.py](simulation/core/services/command_service.py)` converts actor IDs back to handles only to seed history.
  - Follow preload records `snapshot.target_agent_id` directly.
  - The targeted command-service test file passes.
- Coordinator review checklist:
  - Confirm no accidental changes to query-service or feed-generation boundaries.
  - Confirm the only runtime key migration is actor-side history, not public API payload shape.

## Manual Verification

- Run the history core tests:
  - `uv run pytest tests/simulation/core/test_action_history_recording.py -q`
  - Expected: exit `0`; all tests pass.
- Run the policy and validator tests:
  - `uv run pytest tests/simulation/core/test_agent_action_feed_filter.py tests/simulation/core/test_agent_action_rules_validator.py -q`
  - Expected: exit `0`; all tests pass.
- Run the follow-generator tests:
  - `uv run pytest tests/simulation/core/test_random_simple_follow_policy.py tests/simulation/core/test_naive_llm_action_generators.py -q`
  - Expected: exit `0`; all tests pass.
- Run the command-service tests:
  - `uv run pytest tests/simulation/core/test_command_service.py -q`
  - Expected: exit `0`; all tests pass.
- Run the focused runtime regression suite:
  - `uv run pytest tests/simulation/core/test_action_history_recording.py tests/simulation/core/test_agent_action_feed_filter.py tests/simulation/core/test_agent_action_rules_validator.py tests/simulation/core/test_random_simple_follow_policy.py tests/simulation/core/test_naive_llm_action_generators.py tests/simulation/core/test_command_service.py tests/feeds/test_feed_generator.py -q`
  - Expected: exit `0`; no new failures.
- Run lint on the touched runtime surface:
  - `uv run ruff check simulation/core tests/simulation/core tests/feeds`
  - Expected: exit `0`; no new lint errors.

## Final Verification

- Confirm no remaining `ActionHistoryStore` call site passes `agent_handle` as the actor history key in the touched runtime files.
- Confirm `[simulation/core/services/command_service.py](simulation/core/services/command_service.py)` records snapshot history using canonical agent IDs directly.
- Confirm follow algorithms still emit canonical `target_agent_id` and at least one test exercises an `author_agent_id`-first path.
- Confirm `[simulation/core/services/query_service.py](simulation/core/services/query_service.py)` and `feeds/` stayed unchanged unless a failing targeted test required a small, explicit follow-up.

## Alternative Approaches

- Chosen: narrow this unit to actor-side runtime canonicalization, because schema, creation-path normalization, action/feed persistence semantics, and query display projection are already landed and redoing them would add churn without reducing the remaining risk.
- Rejected: widen this unit into query/feed boundary rewrites. That would duplicate earlier work, conflict with current test intent in `[tests/simulation/core/test_query_service.py](tests/simulation/core/test_query_service.py)`, and make the scope much harder to verify.
- Rejected: postpone actor-side history conversion and keep `agent_handle` as the runtime key a little longer. That would preserve the exact alias-drift and duplicate-suppression risk this migration is supposed to eliminate.
