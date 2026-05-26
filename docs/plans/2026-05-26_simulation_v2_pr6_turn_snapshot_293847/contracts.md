# PR 6 Turn Snapshot — Contract Freeze

| Symbol | Location | Contract |
|--------|----------|----------|
| `TurnStateSnapshot` | `simulation_v2/worker/state.py` | Pydantic model with `run_id`, `turn_id`, `turn_number`, `config: LocalSimulationConfig`, `users: dict[str, UserRecord]`, `posts: dict[str, PostRecord]`, `likes: list[LikeRecord]`, `follows: list[FollowRecord]`, `comments: list[CommentRecord]`, `agent_memories: dict[str, AgentMemoryRecord]`, `prior_generated_feeds: list[GeneratedFeedRecord]` |
| `PendingTurnDiffs` | `simulation_v2/worker/state.py` | Pydantic model with default-empty lists: `posts`, `likes`, `follows`, `comments`, `memory_diffs` using existing db record types |
| `load_turn_snapshot` | `simulation_v2/worker/state.py` | `(run_id: str, turn_id: str, repos: SimulationRepositories, conn: sqlite3.Connection) -> TurnStateSnapshot` |
| `list_users_for_run` | `simulation_v2/db/repositories.py` | `(run_id, conn) -> list[UserRecord]` |
| `list_posts_for_run` | same | `(run_id, conn) -> list[PostRecord]` |
| `list_likes_for_run` | same | `(run_id, conn) -> list[LikeRecord]` |
| `list_follows_for_run` | same | `(run_id, conn) -> list[FollowRecord]` |
| `list_comments_for_run` | same | `(run_id, conn) -> list[CommentRecord]` |
| `list_agent_memories_for_run` | same | `(run_id, conn) -> list[AgentMemoryRecord]` |
| `list_generated_feeds_for_run` | same | `(run_id, conn) -> list[GeneratedFeedRecord]` |
| `execute_run` | `simulation_v2/worker/run_executor.py` | `(run_id, config, conn, repos) -> None`; preserves skip-completed-turn retry semantics |
| `execute_turn` | `simulation_v2/worker/turn_executor.py` | `(run_id, turn_number, config, conn, repos) -> TurnStateSnapshot \| None`; loads snapshot, calls stub, completes turn; returns `None` when turn already completed |

## Cumulative-state rule (frozen)

- Include posts/likes/follows/comments where `created_at_turn < turn_number` (seed rows use `created_at_turn=0`, so turn 1 sees all seed social entities).
- Include all users and agent memories for the run (not turn-filtered).
- Include generated feeds whose turn has `turn_number < current_turn_number` (resolve via `repos.list_turns_for_run` + feed rows, or filter in `load_turn_snapshot` after listing feeds).

## File-interaction invariants

| Owner | Allowed callers | Forbidden |
|-------|-----------------|-----------|
| `worker.state` | `worker.turn_executor`, tests | Must not import feeds/actions/memory/eval; must not execute SQL directly |
| `db.repositories` list helpers | `worker.state`, seed loader (future), tests | Must not import worker/feed/action/eval |
| `worker.turn_executor` | `worker.run_executor`, tests | Must not build snapshots itself |
| `worker.run_executor` | `worker.service`, tests | Must not load snapshots directly |

**Important:** `load_turn_snapshot` lives in `worker/state.py`, not `repositories.py`. Repositories expose bulk reads; snapshot assembly/filtering lives in worker state.
