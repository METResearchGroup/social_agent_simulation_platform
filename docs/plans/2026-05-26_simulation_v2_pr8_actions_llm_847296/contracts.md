# PR 8 Actions LLM — Contract Freeze

| Symbol | Location | Contract |
|--------|----------|----------|
| `ActionType` | `simulation_v2/actions/models.py` | `Literal["like_post", "write_post", "follow_user", "comment_on_post"]` |
| Structured outputs | `simulation_v2/actions/models.py` | `LlmLikePostOutput(post_ids)`, `LlmWritePostOutput(content)`, `LlmFollowUserOutput(user_ids)`, `LlmCommentOnPostOutput(parent_post_id, content)` |
| `GenerationStatus` | `simulation_v2/actions/models.py` | `Literal["completed", "failed", "schema_failed"]` |
| `LlmGenerationResult` | `simulation_v2/actions/models.py` | Pydantic model: `status`, `parsed`, `latency_ms`, token/cost fields, `error`, `raw_response_json` |
| Prompts | `simulation_v2/actions/prompts.py` | `LIKE_POSTS_PROMPT`, `WRITE_POST_PROMPT`, `FOLLOW_USERS_PROMPT` ported from legacy; `COMMENT_ON_POST_PROMPT` added |
| `get_chat_model` | `simulation_v2/actions/llm.py` | `(llm_config: LlmConfig) -> ChatOpenAI` using `lib.load_env_vars` |
| `invoke_structured_generation` | `simulation_v2/actions/llm.py` | LangChain + tenacity + Opik wrapper; returns `LlmGenerationResult`; retries transient failures (max 3, exponential jitter) |
| `generate_and_persist_llm_actions` | `simulation_v2/actions/service.py` | `(snapshot, feed_records, action_config, llm_config, repos, conn, *, trace_ctx=None) -> list[GenerationRecord]` |
| `list_generations_for_turn` | `simulation_v2/db/repositories.py` | `(run_id, turn_id, conn) -> list[GenerationRecord]` |
| `list_llm_proposed_actions_for_turn` | `simulation_v2/db/repositories.py` | `(run_id, turn_id, conn) -> list[LlmProposedActionRecord]` |
| `execute_turn` (behavior change) | `simulation_v2/worker/turn_executor.py` | After feeds, call `generate_and_persist_llm_actions` |

## Data-model invariants (frozen)

- Structured LLM schemas live in `actions/models.py`; DB rows use `GenerationRecord` / `LlmProposedActionRecord` from `simulation_v2/db/models/actions.py`.
- One `GenerationRecord` per enabled action invocation per user per turn (not per retry attempt).
- `action_type` column uses frozen `ActionType` strings (`like_post`, not legacy `like_posts`).
- `LlmProposedActionRecord` mapping:
  - `like_post`: one row per `post_id` (`target_type="post"`, `target_id=post_id`)
  - `write_post`: one row (`target_type="post"`, `target_content=content`)
  - `follow_user`: one row per `user_id` (`target_type="user"`, `target_id=user_id`)
  - `comment_on_post`: one row (`target_type="post"`, `target_id=parent_post_id`, `target_content=content`)
- Schema failures: `status="schema_failed"`, `parsed_response_json=None`, `error` populated; still insert the generation row.
- Provider failures after retries: `status="failed"`, `error` populated.

## File-interaction invariants (frozen)

| Owner | Allowed callers | Forbidden |
|-------|-----------------|-----------|
| `actions.llm` | `actions.service`, tests | Must not import repositories or write SQLite |
| `actions.service` | `worker.turn_executor`, tests | Must not import LangChain/Opik/tenacity directly |
| `actions.models`, `actions.prompts` | `actions.llm`, `actions.service`, tests | No DB access |
| `worker.turn_executor` | `run_executor`, tests | Must not call LangChain or map LLM outputs directly |
| Legacy `simulation_v2/agents/*` | unchanged until PR 15 | Do not modify in PR 8 |

## Out of scope (explicit)

- `actions/validators.py`, `actions/executor.py`, `actions/noise.py` (PRs 9–10)
- `memory/service.py` — inline `_format_memory_for_prompt` in `actions/service.py`
- Stochastic action filtering
- `proposed_actions` table writes
- Eval plugins
