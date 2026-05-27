# PR 7 Feed Service — Contract Freeze

| Symbol | Location | Contract |
|--------|----------|----------|
| `FeedGenerator` | `simulation_v2/feeds/interfaces.py` | Protocol: `name: str`, `generate(snapshot, user_id, config: FeedConfig) -> list[FeedPostView]` |
| `get_feed_generator` | `simulation_v2/feeds/interfaces.py` | `(algorithm: str) -> FeedGenerator`; raises `ValueError` for unknown algorithm |
| `validate_feed` | `simulation_v2/feeds/validators.py` | `(user_id, views: list[FeedPostView]) -> None`; raises `FeedValidationError` on duplicate `post_id` or self-authored post |
| `post_like_counts` | `simulation_v2/feeds/interfaces.py` | `(snapshot: TurnStateSnapshot) -> dict[str, int]` counting `snapshot.likes` by `post_id` |
| `hydrate_feed_post_view` | `simulation_v2/feeds/interfaces.py` | `(post: PostRecord, *, like_count: int) -> FeedPostView` |
| `generate_and_persist_feeds` | `simulation_v2/feeds/service.py` | `(snapshot, feed_config, repos, conn) -> list[GeneratedFeedRecord]` — one record per user, inserts via `repos.insert_generated_feed` |
| `execute_turn` (behavior change) | `simulation_v2/worker/turn_executor.py` | After snapshot load, call `generate_and_persist_feeds`; remove `_execute_turn_stub` |

## Data-model invariants (frozen)

- Plugins return `FeedPostView`; only `feeds.service` writes `GeneratedFeedRecord`.
- `feed_post_ids` on record == `[v.post_id for v in feed_posts]` (same order).
- `algorithm` column == plugin `name` (e.g. `"most_liked"`).
- Unique `(run_id, turn_id, user_id)` enforced by schema — service must not double-insert on retry within same committed turn (whole-run transaction makes partial inserts unlikely; completed-turn skip still returns `None` without re-inserting).

## File-interaction invariants (frozen)

| Owner | Allowed callers | Forbidden |
|-------|-----------------|-----------|
| `feeds.service` | `worker.turn_executor`, tests | Must not import worker/actions/memory/eval |
| `feeds.*` plugins | `feeds.service`, tests | Must not import `db.repositories` or write SQLite |
| `feeds.validators` | `feeds.service`, tests | No DB access |
| `worker.turn_executor` | `run_executor`, tests | Must not call plugins directly; must not build feeds |
| `worker.state` | unchanged PR 6 contract | No feed imports |

## Plugin behavior (frozen)

- **`most_liked`:** Port from `simulation_v2/legacy_feeds.py`: candidates = all `snapshot.posts` sorted by like count desc; skip `author_id == user_id`; include each eligible post with probability `config.include_probability` until `config.max_posts`; use `random.random()` (tests patch RNG or set `include_probability=1.0`).
- **`reverse_chronological`:** Sort posts by `created_at` desc (tie-break `post_id` asc); skip self posts; take first `config.max_posts` — **deterministic**, no randomness.
- **Seen-post filtering:** out of scope.

## PR 6 dependencies (do not change)

`TurnStateSnapshot`, `load_turn_snapshot`, cumulative-state rule in PR 6 contracts.
