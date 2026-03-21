# Post author identity (`author_agent_id`)

`Post.author_agent_id` is the **required** stable identifier for who wrote a post. It matches `agent.agent_id` when the author exists in the `agent` table (foreign key on `feed_posts.author_agent_id`).

It is **not** derived from `author_handle` at runtime. Algorithms that need “who wrote this post?” use `post.author_agent_id` only (for example follow targets, follow history keys, and excluding self-authored posts in feed candidate filtering).

## Persistence

- **`feed_posts`**: `author_agent_id` is stored and backfilled from `agent` via `feed_posts.author_handle = agent.handle` (see migration `e7f3a9c2d1b4_add_feed_posts_author_agent_id`). Rows with no matching `agent` were removed during migration.
- **`run_posts` snapshots**: `author_agent_id` is part of the run-scoped snapshot and maps into `Post` via `run_post_snapshot_to_post`.

## Deterministic test IDs

`lib/agent_id.canonical_agent_id` remains a **test-only helper** (and for other non-post flows) to build deterministic fake `agent_id` strings. It is **not** used to infer post authors from handles in production paths.

## Related code

| Location | Role |
|----------|------|
| `simulation/core/models/posts.py` | `Post.author_agent_id` (required) |
| `db/adapters/sqlite/feed_post_adapter.py` | Read/write `feed_posts` including `author_agent_id` |
| `feeds/candidate_generation.py` | Self-exclusion via `author_agent_id` vs `agent.agent_id` |
| `simulation/core/action_policy/candidate_filter.py` | Follow history key uses `post.author_agent_id` |
| `lib/agent_id.py` | `canonical_agent_id` / `is_canonical_agent_id` helpers (not post-author resolution) |
