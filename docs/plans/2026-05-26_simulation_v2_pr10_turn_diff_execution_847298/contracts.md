# PR 10: Turn Diff Execution — Contract Freeze

## Frozen symbols

| Symbol | Location | Contract |
| --- | --- | --- |
| `build_pending_turn_diffs` | `simulation_v2/actions/executor.py` | `(validated_actions: list[ProposedActionRecord], snapshot: TurnStateSnapshot) -> PendingTurnDiffs` |
| `persist_turn_diffs` | `simulation_v2/db/repositories.py` | `(diffs: PendingTurnDiffs, conn: sqlite3.Connection) -> None` |
| `execute_turn` (behavior change) | `simulation_v2/worker/turn_executor.py` | After `validate_and_persist_proposed_actions`, call `build_pending_turn_diffs` then `persist_turn_diffs` on the same `conn` |
| `PendingTurnDiffs` | `simulation_v2/worker/state.py` | **Unchanged** (PR 6 freeze) |
| `validate_and_persist_proposed_actions` | `simulation_v2/actions/service.py` | **Unchanged** (PR 9 freeze) |

## Validated action → entity mapping

| `action_type` | Required fields on validated row | Output record |
| --- | --- | --- |
| `like_post` | `target_id` = post_id | `LikeRecord(like_id=new_like_id(), author_id=user_id, post_id=target_id, created_at_turn=snapshot.turn_number, ...)` |
| `follow_user` | `target_id` = followee user_id | `FollowRecord(follow_id=new_follow_id(), follower_id=user_id, followee_id=target_id, ...)` |
| `write_post` | `target_content` non-empty | `PostRecord(post_id=new_post_id(), author_id=user_id, content=target_content, ...)` |
| `comment_on_post` | `target_id` = parent_post_id, `target_content` non-empty | `CommentRecord(comment_id=new_comment_id(), author_id=user_id, parent_post_id=target_id, content=target_content, ...)` |

Shared fields for all outputs:

- `run_id = snapshot.run_id`
- `created_at = get_current_timestamp()` (from `simulation_v2/time.py`)
- `created_at_turn = snapshot.turn_number`
- `metadata_json = {"proposed_action_id": action.action_id}` (traceability; optional `generation_id`)

Processing rules:

- Input list order preserved (matches PR 9 ordering: `created_at`, `action_id`).
- Skip / never pass rejected rows (caller filters).
- Raise `ValueError` on validated row with unknown `action_type` (programmer error, not user-facing).
- `memory_diffs` always `[]` in PR 10.

## File-interaction invariants

| Owner | Allowed callers | Forbidden |
| --- | --- | --- |
| `actions.executor` | `worker.turn_executor`, tests | No repository imports, no SQLite, no validator rules |
| `db.repositories.persist_turn_diffs` | `worker.turn_executor`, tests | Must not build diffs or read `proposed_actions` |
| `worker.turn_executor` | `run_executor`, tests | Must not map action types inline; must not update `agent_memories` |
| `actions.validators`, `actions.service` (validation) | unchanged | Do not modify (PR 9 freeze) |
| Legacy `simulation_v2/agents/*` | unchanged | Do not modify |

## Out of scope (explicit)

- `actions/noise.py` stochastic gating
- `memory/service.py`, memory diff construction, `agent_memories` updates (PR 11)
- Eval plugins
- Schema changes / new tables
- Modifying PR 8–9 frozen LLM/validator contracts
