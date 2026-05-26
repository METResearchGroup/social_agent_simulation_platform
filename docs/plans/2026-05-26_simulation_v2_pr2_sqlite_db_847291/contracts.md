# simulation_v2 PR2 SQLite contracts

Frozen interface for parallel model/repository work.

## Tables (15)

| Table | Primary key | Uniqueness |
|-------|-------------|------------|
| runs | run_id | — |
| turns | turn_id | UNIQUE(run_id, turn_number) |
| users | (run_id, user_id) | per-run user scope |
| posts | (run_id, post_id) | — |
| likes | like_id | UNIQUE(run_id, author_id, post_id) |
| comments | comment_id | — |
| follows | follow_id | UNIQUE(run_id, follower_id, followee_id) |
| agent_memories | (run_id, user_id) | UNIQUE(run_id, user_id) |
| memory_diffs | memory_diff_id | append-only |
| generated_feeds | feed_id | UNIQUE(run_id, turn_id, user_id) |
| generations | generation_id | append-only |
| llm_proposed_actions | llm_proposed_action_id | FK generation_id |
| proposed_actions | action_id | append-only; FK generation_id nullable |
| eval_runs | eval_run_id | — |
| eval_metrics | eval_metric_id | FK eval_run_id |

## Status enums

- RunStatus: queued, running, completed, failed
- TurnStatus: pending, running, completed, failed
- ProposedActionRecordKind: validated, rejected
- RejectionStage: llm_schema, business_rules
- EvalScope: turn, run
- MemoryType: episodic, personalized, social

## JSON columns

Stored via json.dumps / json.loads: config_json, seed_metadata_json, profile_json, metadata_json, preferences_json, feed_post_ids_json, feed_posts_json, parsed_response_json, raw_response_json.

## Repository methods (insert + get only)

SimulationRepositories exposes insert_* / get_* for all 15 record types. Repositories receive conn; they never open their own path.

## ID helpers (simulation_v2/ids.py)

new_run_id, new_turn_id, new_action_id, new_feed_id, new_generation_id, new_memory_diff_id (existing); new_user_id, new_post_id, new_like_id, new_comment_id, new_follow_id, new_llm_proposed_action_id, new_eval_run_id, new_eval_metric_id (added in PR2).
