# PR 11 Memory Service — Contract Freeze

| Symbol | Location | Contract |
| --- | --- | --- |
| `fetch_memory_for_prompt` | `simulation_v2/memory/service.py` | `(memory: AgentMemoryRecord \| None) -> str` — prompt-ready markdown block (same sections as legacy `agents/memory/main.py`) |
| `build_memory_diffs` | `simulation_v2/memory/service.py` | `(validated_actions: list[ProposedActionRecord], snapshot: TurnStateSnapshot) -> list[MemoryDiffRecord]` — one or more diffs **per user with ≥1 validated action**; episodic required when actions exist |
| `apply_memory_diff` | `simulation_v2/memory/service.py` | `(current: AgentMemoryRecord, diff: MemoryDiffRecord) -> AgentMemoryRecord` — append `diff.content` to the matching field; set `updated_at=get_current_timestamp()` |
| `build_pending_turn_diffs` | `simulation_v2/actions/executor.py` | **Extended:** `memory_diffs=build_memory_diffs(...)`; social mapping unchanged |
| `update_agent_memory` | `simulation_v2/db/repositories.py` | `(record: AgentMemoryRecord, conn) -> None` — `UPDATE agent_memories SET episodic=?, personalized=?, social=?, updated_at=? WHERE run_id=? AND user_id=?` |
| `persist_turn_diffs` | `simulation_v2/db/repositories.py` | **Extended:** after each `insert_memory_diff`, load current row, `apply_memory_diff`, `update_agent_memory` |
| `PendingTurnDiffs` | `simulation_v2/worker/state.py` | **Unchanged** (PR 6 freeze) |
| Legacy `simulation_v2/agents/*` | — | **Do not modify** (PR 10 freeze) |

## Deterministic diff content rules

Group validated actions by `user_id` (stable sort: `user_id`, then input order). For each user with actions on `snapshot.turn_number`:

- **Episodic (required):** single line appended as diff content, e.g. `Turn 1: liked post p2; wrote post "hello world"; followed user u2; commented on p1 "nice post"`. Use `target_id` / `target_content` from actions; no LLM.
- **Personalized (minimal):** if user has `write_post`, append line like `Turn 1: posted "hello world"` to `personalized` field via diff.
- **Social (minimal):** if user has `follow_user`, append line like `Turn 1: followed u2` to `social` field via diff.

Each diff row: `memory_diff_id=new_memory_diff_id()`, `run_id`, `turn_id=snapshot.turn_id`, `user_id`, `memory_type`, `content` (the new segment only), `created_at=get_current_timestamp()`.

Users with **zero** validated actions produce **zero** memory diffs.

## File-interaction invariants

| Owner | Allowed callers | Forbidden |
| --- | --- | --- |
| `memory.service`, `memory/episodic.py`, `memory/personalized.py`, `memory/social.py` | `actions.service`, `actions.executor`, `db.repositories.persist_turn_diffs`, tests | No LangChain/LLM imports; no direct SQLite in submodules |
| `actions.executor` | `worker.turn_executor`, tests | No inline memory string formatting |
| `actions.service` | `worker.turn_executor`, tests | Must call `memory.service.fetch_memory_for_prompt`; must not format memory inline |
| `db.repositories.persist_turn_diffs` | `worker.turn_executor`, tests | Must not encode memory merge rules inline; delegate to `memory.service.apply_memory_diff` |
