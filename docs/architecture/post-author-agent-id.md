# Post author identity (`author_agent_id`)

`Post.author_agent_id` is the **required** stable identifier for who wrote a post. It matches `agent.agent_id` when the author exists in the `agent` table (foreign key on `feed_posts.author_agent_id`).

It is **not** derived from `author_handle` at runtime. Algorithms that need “who wrote this post?” use `post.author_agent_id` only (for example follow targets, follow history keys, and excluding self-authored posts in feed candidate filtering).

## Persistence

- **`feed_posts`**: `author_agent_id` is stored and backfilled from `agent` via `feed_posts.author_handle = agent.handle` (see migration `e7f3a9c2d1b4_add_feed_posts_author_agent_id`). Rows with no matching `agent` were removed during migration.
- **`run_posts` snapshots**: `author_agent_id` is part of the run-scoped snapshot and maps into `Post` via `run_post_snapshot_to_post`.

## How `agent.agent_id` is derived

`Post.author_agent_id` is whatever was stored for that post (FK to `agent.agent_id`). It is **not** computed from `author_handle` in application logic.

**Runtime `agent` rows** get `agent_id` from other flows, for example:

- **User-created agents** (`simulation/api/services/agent_command_service.py`): `agent_id = canonical_agent_id()` with **no argument** — a new 16-character lowercase hex id from cryptographic randomness (see `lib/agent_id.py`: `secrets.token_hex` when `source is None`).

**Tests** frequently call `canonical_agent_id("some.handle")` to get a **deterministic** hex id for fixtures so the same handle always maps to the same id — that is convenience for tests, not post-author inference in production.

## Related code

| Location | Role |
|----------|------|
| `simulation/core/models/posts.py` | `Post.author_agent_id` (required) |
| `db/adapters/sqlite/feed_post_adapter.py` | Read/write `feed_posts` including `author_agent_id` |
| `feeds/candidate_generation.py` | Self-exclusion via `author_agent_id` vs `agent.agent_id` |
| `simulation/core/action_policy/candidate_filter.py` | Follow history key uses `post.author_agent_id` |
| `lib/agent_id.py` | `canonical_agent_id` (hash-based ids + optional random), `is_canonical_agent_id` |
| `scripts/migrations/agent_id_migration.py` | `stable_source_for_agent_row` + `canonical_agent_id` for data migrations |
| `simulation/api/services/agent_command_service.py` | New agents: `canonical_agent_id()` (random id) |
