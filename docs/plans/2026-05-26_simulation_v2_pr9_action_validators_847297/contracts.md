# PR 9 Contract Freeze — Action Validators

## Frozen Symbols

| Symbol | Location | Contract |
| --- | --- | --- |
| `FilterId` | `simulation_v2/actions/validators.py` | Stable string literals for eval grouping (see table below) |
| `ActionValidationOutcome` | `simulation_v2/actions/validators.py` | `accepted: bool`, optional `filter_id: FilterId`, optional `filter_reason: str` |
| `validate_like_post_action` | `simulation_v2/actions/validators.py` | Pure function; one LLM like row in, outcome out |
| `validate_follow_user_action` | `simulation_v2/actions/validators.py` | Pure function; follow row in, outcome out |
| `validate_write_post_action` | `simulation_v2/actions/validators.py` | Pure function; write row in, outcome out |
| `validate_comment_on_post_action` | `simulation_v2/actions/validators.py` | Pure function; comment row in, outcome out |
| `validate_and_persist_proposed_actions` | `simulation_v2/actions/service.py` | `(snapshot, feed_records, action_config, repos, conn) -> list[ProposedActionRecord]` |
| `list_proposed_actions_for_turn` | `simulation_v2/db/repositories.py` | `(run_id, turn_id, conn) -> list[ProposedActionRecord]` ordered by `created_at`, `action_id` |
| `execute_turn` (behavior change) | `simulation_v2/worker/turn_executor.py` | After `generate_and_persist_llm_actions`, call `validate_and_persist_proposed_actions` |

## Frozen `FilterId` Values

| filter_id | When | filter_reason (example) |
| --- | --- | --- |
| `no_self_like` | like target authored by acting user | `Cannot like your own post` |
| `duplicate_like` | same post already liked (snapshot or earlier accepted this turn) | `Duplicate like for post {post_id}` |
| `missing_target_post` | like/comment target not in user's generated feed | `Post {post_id} not in feed` |
| `no_self_follow` | follow target is acting user | `Cannot follow yourself` |
| `duplicate_follow` | already following (snapshot or earlier accepted this turn) | `Duplicate follow for user {user_id}` |
| `missing_target_user` | follow target not in feed-derived candidate set | `User {user_id} not in follow candidates` |
| `empty_content` | write/comment content blank after strip | `Action content is empty` |
| `missing_parent_post` | comment parent not in feed | `Parent post {post_id} not in feed` |
| `max_actions_per_turn` | per-type cap from `ActionConfig` exceeded | `Exceeded max {action_type} per turn ({max})` |

## Data-Model Invariants

- One `ProposedActionRecord` per `LlmProposedActionRecord` processed (1:1 for this PR).
- Rejected rows still populate `target_type`, `target_id`, `target_content` from the LLM row.
- `generation_id` copied from source LLM row.
- Only business-rule rejections in this PR (`rejection_stage="business_rules"`).

## File-Interaction Invariants

| Owner | Allowed callers | Forbidden |
| --- | --- | --- |
| `actions.validators` | `actions.service`, tests | No repository imports, no SQLite |
| `actions.service` (validation path) | `worker.turn_executor`, tests | Must not import LangChain/Opik/tenacity |
| `worker.turn_executor` | `run_executor`, tests | Must not implement validator rules inline |
| Legacy `simulation_v2/agents/*` | unchanged | Do not modify |

## Out of Scope

- `actions/executor.py`, `actions/noise.py` (PR 10–11)
- Stochastic action filtering
- Eval plugins
- Schema-failure → `proposed_actions` rows (`rejection_stage="llm_schema"`)
- Modifying PR 8 frozen LLM contracts
