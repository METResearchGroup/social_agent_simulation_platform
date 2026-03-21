---
name: Agent ID Hardening
description: Harden persistence boundaries so canonical agent IDs are required end-to-end; display handles stay non-authoritative; query/API normalization deferred.
tags:
  - planning
  - agent-id
  - persistence
  - repositories
  - sqlite
overview: Finish the remaining adapter/repository cleanup after the merged agent_id work. The storage schema and most runtime semantics are already canonical; this unit hardens persistence boundaries so canonical IDs are required end-to-end, display handles stay non-authoritative, and the broader query/API boundary change remains a separate follow-up.
todos:
  - id: freeze-persistence-contracts
    content: Freeze canonical-ID persistence contracts and decide any compatibility wrappers before parallel work starts
    status: pending
  - id: packet-action-persistence
    content: Remove handle-to-agent_id resolution from action persistence adapters/repositories and add negative-path tests
    status: pending
  - id: packet-generated-feed
    content: Make generated-feed repository/adapter validation consistently canonical and document handle fields as display-only
    status: pending
  - id: packet-feed-post-author
    content: Convert feed-post author lookup semantics to author_agent_id or an explicitly named compatibility wrapper
    status: pending
  - id: integrate-and-verify
    content: Run cross-packet repository/integration verification and record deferred boundary/API follow-up
    status: pending
isProject: false
---

# Agent ID Persistence Hardening

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- Maximum safely delegable parallelism
- Delegated tasks must be impossible to misread

## Overview

After reviewing `strategy_planning/2026-03-20_agent_id_migration/proposal.md` plus merged PRs `#268`, `#269`, `#270`, `#272`, `#274`, and `#275`, the core identity migration is already in place: canonical helper/validation, canonical creation paths, PK/FK rewrite, action/feed schema updates, runtime history keyed by `agent_id`, and required `Post.author_agent_id`. The remaining repository-layer work is narrower than the original proposal section suggests: remove permissive handle-to-ID resolution at persistence boundaries, make canonical-ID validation consistent across repository/adapter entrypoints, finish author lookup semantics for feed posts, and leave the higher-risk query/API boundary conversion for a separate follow-up.

## Happy Flow

1. Runtime-generated `GeneratedLike`, `GeneratedComment`, and `GeneratedFollow` arrive at `db/repositories/like_repository.py`, `db/repositories/comment_repository.py`, and `db/repositories/follow_repository.py` with canonical `agent_id` / `target_agent_id` already populated by runtime code; repository and adapter boundaries reject handles instead of translating them.
2. `db/adapters/sqlite/like_adapter.py`, `db/adapters/sqlite/comment_adapter.py`, and `db/adapters/sqlite/follow_adapter.py` write canonical IDs directly into `likes.agent_id`, `comments.agent_id`, and `follows.{agent_id,target_agent_id}` with no fallback through `db/adapters/sqlite/agent_id_resolve.py`.
3. `db/repositories/generated_feed_repository.py` and `db/adapters/sqlite/generated_feed_adapter.py` continue to persist and look up generated feeds by canonical `agent_id`; `agent_handle` stays as display metadata only.
4. `db/repositories/feed_post_repository.py` and `db/adapters/sqlite/feed_post_adapter.py` stop treating `author_handle` as the authoritative author lookup key; canonical author lookup becomes `author_agent_id`-based, with any temporary compatibility path explicitly named and documented.
5. Repository and integration tests under `tests/db/repositories/` prove malformed handles and non-canonical IDs are rejected before DB writes/reads occur, while canonical IDs still round-trip cleanly.

## Interface Or Contract Freeze

- Any repository or adapter boundary that accepts an `agent_id` or `target_agent_id` as an identifier must validate canonical 16-character lowercase hex IDs via `validate_canonical_agent_id()` or equivalent model validation.
- No action persistence adapter in this unit may call `resolve_agent_id_sqlite()` during a write.
- `GeneratedFeed.agent_handle` may remain on the model as display metadata, but no repository lookup, uniqueness rule, or persistence key semantics may depend on it.
- `Post.author_agent_id` is authoritative identity; `author_handle` is display-only.
- Out of scope for this unit: `simulation/core/services/query_service.py`, `simulation/core/models/turns.py`, `simulation/api/services/run_query_service.py`, `simulation/api/schemas/simulation.py`, and all `ui/` files.

## Serial Coordination Spine

1. Inventory current callers before edits so the public contract is explicit:
  - Search for `resolve_agent_id_sqlite(`.
  - Search for `get_post_ids_for_run(`.
  - Search for `list_feed_posts_by_author(`.
  - Search for `read_feed_posts_by_author(`.
2. Freeze the compatibility decision for feed-post author reads:
  - Preferred: rename to an `author_agent_id`-based API and update callers now.
  - Only if caller churn is wider than expected: keep a narrow compatibility wrapper with an explicit handle-based name and documentation that it is display/query-only.
3. Freeze which boundaries must reject malformed IDs now:
  - Action write paths.
  - Generated-feed lookup/read helpers that take raw `agent_id` parameters.
  - Feed-post author lookup if converted to `author_agent_id`.
4. After the parallel packets merge, run the combined verification suite and record the deferred query/API follow-up in the plan notes so the next unit starts from a stable persistence contract.

## Parallel Task Packets

### Packet A: Action Persistence Canonical-Only

- Task ID: `packet-action-persistence`
- Objective: remove handle-to-ID resolution from persisted like/comment/follow writes and make action persistence canonical-only.
- Why parallelizable: touches only action persistence adapters/repositories and their dedicated repository tests.
- Exact files to inspect:
  - `db/adapters/sqlite/like_adapter.py`
  - `db/adapters/sqlite/comment_adapter.py`
  - `db/adapters/sqlite/follow_adapter.py`
  - `db/adapters/sqlite/agent_id_resolve.py`
  - `db/repositories/like_repository.py`
  - `db/repositories/comment_repository.py`
  - `db/repositories/follow_repository.py`
  - `simulation/core/models/actions.py`
  - `simulation/core/models/generated/like.py`
  - `simulation/core/models/generated/comment.py`
  - `simulation/core/models/generated/follow.py`
  - `tests/db/repositories/test_action_repositories_integration.py`
- Exact files allowed to change:
  - `db/adapters/sqlite/like_adapter.py`
  - `db/adapters/sqlite/comment_adapter.py`
  - `db/adapters/sqlite/follow_adapter.py`
  - `db/adapters/sqlite/agent_id_resolve.py`
  - `db/repositories/like_repository.py`
  - `db/repositories/comment_repository.py`
  - `db/repositories/follow_repository.py`
  - `tests/db/repositories/test_action_repositories_integration.py`
- Exact files forbidden to change:
  - `db/adapters/sqlite/generated_feed_adapter.py`
  - `db/repositories/generated_feed_repository.py`
  - `db/adapters/sqlite/feed_post_adapter.py`
  - `db/repositories/feed_post_repository.py`
  - `simulation/core/services/query_service.py`
  - `simulation/api/services/run_query_service.py`
- Preconditions:
  - The runtime/model layer already emits canonical IDs for `GeneratedLike`, `GeneratedComment`, and `GeneratedFollow`.
  - The contract freeze above is accepted.
- Dependency tasks: `freeze-persistence-contracts`
- Required contracts and invariants:
  - Do not silently resolve handles inside action write paths.
  - Do not change persisted column names or ordering.
  - Preserve deterministic read ordering by `agent_id`, `post_id`, and `target_agent_id`.
- Step-by-step implementation instructions:
  1. Confirm the underlying generated action models already validate canonical IDs; if they do not, stop and move the gap back to the serial spine instead of adding hidden normalization here.
  2. Replace `resolve_agent_id_sqlite(conn, g.like.agent_id)` / `resolve_agent_id_sqlite(conn, g.comment.agent_id)` / `resolve_agent_id_sqlite(conn, g.follow.agent_id)` with direct use of the canonical fields.
  3. Replace `resolve_agent_id_sqlite(conn, g.follow.target_agent_id)` with direct use of `g.follow.target_agent_id`.
  4. Remove now-unused imports and keep `db/adapters/sqlite/agent_id_resolve.py` only if it still serves another caller outside this packet; do not delete it unless it becomes unused everywhere.
  5. Extend integration tests so writes with canonical IDs still round-trip and writes with handles or malformed IDs fail before persistence.
  6. Add negative-path assertions that the database row set is unchanged after invalid writes.
- Exact verification commands:
  - `uv run pytest tests/db/repositories/test_action_repositories_integration.py -q`
  - `uv run ruff check db/adapters/sqlite/like_adapter.py db/adapters/sqlite/comment_adapter.py db/adapters/sqlite/follow_adapter.py db/repositories/like_repository.py db/repositories/comment_repository.py db/repositories/follow_repository.py tests/db/repositories/test_action_repositories_integration.py`
- Expected outputs from verification:
  - Pytest exits `0`.
  - Canonical action writes/readbacks still pass.
  - Invalid handle/non-canonical ID tests raise `ValueError` (or the existing explicit validation exception) before any row is persisted.
  - Ruff exits `0`.
- Done-when checklist:
  - No action write path calls `resolve_agent_id_sqlite()`.
  - All action repository tests use canonical IDs as the accepted input.
  - Negative tests prove handles are rejected.
- Coordinator review checklist:
  - Verify no shared ownership edits landed outside the allowed file list.
  - Verify action persistence still round-trips existing canonical fixtures.
  - Verify invalid handle inputs do not get silently converted.

### Packet B: Generated Feed Canonical Boundary

- Task ID: `packet-generated-feed`
- Objective: make generated-feed repository and adapter validation consistently canonical while keeping `agent_handle` explicitly display-only.
- Why parallelizable: touches only generated-feed files/tests and does not overlap Packet A or Packet C file ownership.
- Exact files to inspect:
  - `simulation/core/models/feeds.py`
  - `db/adapters/sqlite/generated_feed_adapter.py`
  - `db/repositories/generated_feed_repository.py`
  - `tests/db/repositories/test_generated_feed_repository.py`
  - `tests/db/repositories/test_generated_feed_repository_integration.py`
  - `tests/simulation/core/test_query_service.py`
- Exact files allowed to change:
  - `simulation/core/models/feeds.py`
  - `db/adapters/sqlite/generated_feed_adapter.py`
  - `db/repositories/generated_feed_repository.py`
  - `tests/db/repositories/test_generated_feed_repository.py`
  - `tests/db/repositories/test_generated_feed_repository_integration.py`
- Exact files forbidden to change:
  - `db/adapters/sqlite/like_adapter.py`
  - `db/adapters/sqlite/comment_adapter.py`
  - `db/adapters/sqlite/follow_adapter.py`
  - `db/adapters/sqlite/feed_post_adapter.py`
  - `db/repositories/feed_post_repository.py`
  - `simulation/core/services/query_service.py`
  - `simulation/api/services/run_query_service.py`
- Preconditions:
  - `GeneratedFeed.agent_id` remains the canonical key field.
  - This packet does not move the read/query boundary to `agent_id`-keyed maps.
- Dependency tasks: `freeze-persistence-contracts`
- Required contracts and invariants:
  - Public repository methods that accept raw `agent_id` must reject handles.
  - `agent_handle` may be present on the model, but it cannot change lookup semantics.
  - Do not change `generated_feeds` schema in this unit.
- Step-by-step implementation instructions:
  1. Audit every generated-feed adapter/repository method that accepts raw `agent_id` and align it to canonical validation, not generic non-empty-string validation.
  2. Update docstrings and error text so the contract consistently says generated-feed lookups are keyed by `agent_id`.
  3. Decide whether `_resolve_display_handle()` remains as a temporary compatibility/read-model fallback. If retained, document it as display-only and add tests proving stale or missing display handles do not affect `agent_id`-based lookups.
  4. Add negative-path repository tests that pass a handle to `get_generated_feed()` / `get_post_ids_for_run()` and assert the adapter is not called.
  5. Add or update integration coverage for mismatched `agent_handle` vs `agent_id` display scenarios without changing key semantics.
- Exact verification commands:
  - `uv run pytest tests/db/repositories/test_generated_feed_repository.py tests/db/repositories/test_generated_feed_repository_integration.py -q`
  - `uv run ruff check simulation/core/models/feeds.py db/adapters/sqlite/generated_feed_adapter.py db/repositories/generated_feed_repository.py tests/db/repositories/test_generated_feed_repository.py tests/db/repositories/test_generated_feed_repository_integration.py`
- Expected outputs from verification:
  - Pytest exits `0`.
  - Handle-shaped `agent_id` inputs are rejected before adapter calls.
  - Generated feed lookups still succeed with canonical IDs even when display handles differ from run-start handles.
  - Ruff exits `0`.
- Done-when checklist:
  - No generated-feed repository method accepts non-canonical IDs.
  - Tests explicitly cover canonical rejection and display-handle drift.
  - The display-handle fallback, if retained, is clearly documented as non-authoritative.
- Coordinator review checklist:
  - Verify no query/API files changed.
  - Verify `agent_handle` remains metadata, not a key.
  - Verify integration tests still pass against real SQLite.

### Packet C: Feed Post Author Lookup Canonicalization

- Task ID: `packet-feed-post-author`
- Objective: make feed-post author lookup semantics align with required `Post.author_agent_id`.
- Why parallelizable: touches only feed-post repository/adapter surface and its tests.
- Exact files to inspect:
  - `simulation/core/models/posts.py`
  - `db/repositories/interfaces.py`
  - `db/repositories/feed_post_repository.py`
  - `db/adapters/sqlite/feed_post_adapter.py`
  - `tests/db/repositories/test_feed_post_repository.py`
  - `tests/db/repositories/test_feed_post_repository_integration.py`
  - `docs/architecture/post-author-agent-id.md`
- Exact files allowed to change:
  - `db/repositories/interfaces.py`
  - `db/repositories/feed_post_repository.py`
  - `db/adapters/sqlite/feed_post_adapter.py`
  - `tests/db/repositories/test_feed_post_repository.py`
  - `tests/db/repositories/test_feed_post_repository_integration.py`
- Exact files forbidden to change:
  - `db/adapters/sqlite/like_adapter.py`
  - `db/adapters/sqlite/comment_adapter.py`
  - `db/adapters/sqlite/follow_adapter.py`
  - `db/adapters/sqlite/generated_feed_adapter.py`
  - `db/repositories/generated_feed_repository.py`
  - `simulation/core/services/query_service.py`
  - `simulation/api/services/run_query_service.py`
- Preconditions:
  - `Post.author_agent_id` is already required and `feed_posts.author_agent_id` already exists with an FK.
  - The serial spine has frozen whether to rename the public method or keep a compatibility wrapper.
- Dependency tasks: `freeze-persistence-contracts`
- Required contracts and invariants:
  - Canonical author identity is `author_agent_id`.
  - `author_handle` remains display data.
  - Do not regress existing post hydration fields or ordering.
- Step-by-step implementation instructions:
  1. Prefer replacing `list_feed_posts_by_author(author_handle)` / `read_feed_posts_by_author(author_handle)` with `author_agent_id`-based names and signatures.
  2. If a handle-based helper must remain for compatibility, rename it so the API surface makes the difference explicit instead of overloading `author` to mean handle.
  3. Update SQL in `db/adapters/sqlite/feed_post_adapter.py` to query `feed_posts.author_agent_id` for the canonical path.
  4. Update repository tests to use canonical author IDs and add negative-path assertions that handle inputs are rejected on the canonical path.
  5. Keep `docs/architecture/post-author-agent-id.md` as the source-of-truth reference if a small wording update is needed to reflect the final repository contract.
- Exact verification commands:
  - `uv run pytest tests/db/repositories/test_feed_post_repository.py tests/db/repositories/test_feed_post_repository_integration.py -q`
  - `uv run ruff check db/repositories/interfaces.py db/repositories/feed_post_repository.py db/adapters/sqlite/feed_post_adapter.py tests/db/repositories/test_feed_post_repository.py tests/db/repositories/test_feed_post_repository_integration.py`
- Expected outputs from verification:
  - Pytest exits `0`.
  - Canonical author-ID queries return the expected posts.
  - Handle-shaped inputs fail on the canonical path before DB reads.
  - Ruff exits `0`.
- Done-when checklist:
  - Feed-post author lookup has an explicit canonical-ID API.
  - Any compatibility wrapper is clearly named and documented.
  - Tests assert author identity by `author_agent_id`, not `author_handle`.
- Coordinator review checklist:
  - Verify no query/API files changed.
  - Verify `author_agent_id` is the only authoritative author lookup key.
  - Verify any compatibility helper cannot be mistaken for canonical identity semantics.

## Integration Order

1. Complete the serial contract freeze and caller inventory.
2. Land Packet A.
3. Land Packet B.
4. Land Packet C.
5. Re-run the combined repository suite.
6. Re-check for any remaining handle-based persistence seams with:
  - `rg -n "resolve_agent_id_sqlite|list_feed_posts_by_author\(|read_feed_posts_by_author\(|validate_agent_id\(" db/adapters/sqlite db/repositories`
7. Document the deferred read/query/API normalization follow-up once this unit is green.

## Final Verification

- Repository and migration safety checks:
  - `uv run pytest tests/db/test_agent_id_pk_migration.py -q`
  - Expected: exit `0`.
- Action persistence round-trip and rejection tests:
  - `uv run pytest tests/db/repositories/test_action_repositories_integration.py -q`
  - Expected: exit `0`.
- Generated-feed repository checks:
  - `uv run pytest tests/db/repositories/test_generated_feed_repository.py tests/db/repositories/test_generated_feed_repository_integration.py -q`
  - Expected: exit `0`.
- Feed-post repository checks:
  - `uv run pytest tests/db/repositories/test_feed_post_repository.py tests/db/repositories/test_feed_post_repository_integration.py -q`
  - Expected: exit `0`.
- Cross-layer regression smoke for persisted feeds/actions hydration:
  - `uv run pytest tests/simulation/core/test_query_service.py tests/feeds/test_feed_generator.py -q`
  - Expected: exit `0`.
- Lint for touched code:
  - `uv run ruff check db/adapters/sqlite db/repositories tests/db/repositories tests/simulation/core tests/feeds`
  - Expected: exit `0`.

## Manual Verification

- Run `uv run pytest tests/db/repositories/test_action_repositories_integration.py -q` and confirm canonical action IDs still round-trip.
- Run `uv run pytest tests/db/repositories/test_generated_feed_repository.py tests/db/repositories/test_generated_feed_repository_integration.py -q` and confirm generated-feed lookups reject handles passed as `agent_id`.
- Run `uv run pytest tests/db/repositories/test_feed_post_repository.py tests/db/repositories/test_feed_post_repository_integration.py -q` and confirm author-based feed-post reads are keyed by `author_agent_id`.
- Run `uv run pytest tests/simulation/core/test_query_service.py tests/feeds/test_feed_generator.py -q` and confirm no regression in persisted feed/action hydration.
- Run `uv run ruff check db/adapters/sqlite db/repositories tests/db/repositories tests/simulation/core tests/feeds` and confirm no new lint failures.
- Run `rg -n "resolve_agent_id_sqlite|list_feed_posts_by_author\(|read_feed_posts_by_author\(" db/adapters/sqlite db/repositories` and confirm any remaining matches are either removed or explicitly compatibility-named/documented.

## Alternative Approaches

- Keep handle-to-ID resolution in adapters for compatibility.
  - Rejected because it silently reintroduces the exact mixed-identity semantics the earlier migration work removed.
- Limit this unit to action repositories only.
  - Rejected because `generated_feeds` and feed-post author reads would still leave repository contracts semantically inconsistent with the landed `agent_id` / `author_agent_id` model changes.
- Jump straight to query/API boundary normalization.
  - Deferred because it changes external/read-model contracts and is best handled as a separate unit after persistence boundaries are fully strict.
