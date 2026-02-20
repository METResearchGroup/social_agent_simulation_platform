---
description: Step-by-step guide to add a new feed ranking algorithm to the simulation framework (registry, metadata, implementation).
tags: [feeds, algorithms, development, simulation, python, registry]
---

# How to Create a New Feed Ranking Algorithm

To add a new feed ranking algorithm, you only need to touch:

1. `feeds/algorithms/implementations/<your_algorithm>.py` (create a new file)
2. `feeds/algorithms/registry.py` (register the algorithm in `_ALGORITHM_LOOKUP`)

Everything else (validation, API exposure, feed generation wiring) is handled by the framework.

## Step-by-step

### 1) Implement the algorithm (in `feeds/algorithms/implementations/`)

Your algorithm module must define a class that extends `FeedAlgorithm`:

- `ALGORITHM_ID = "your_algorithm_id"` — the stable string ID used in `feed_algorithm` requests and config.
- `METADATA: FeedAlgorithmMetadata` — a dict with:
  - `display_name`: human-readable name (shown in UI).
  - `description`: short description of what the algorithm does.
  - `config_schema` (optional): JSON Schema for per-algorithm config; use `None` if not needed.
- A class extending `FeedAlgorithm` with `metadata` property and `generate()` returning `FeedAlgorithmResult`.

The `generate` method must:

- Accept `candidate_posts: list[BlueskyFeedPost]`, `agent: SocialMediaAgent`, and `limit: int`.
- Return `FeedAlgorithmResult` with `feed_id`, `agent_handle`, `post_uris`.

## Ordering

`post_uris` must be in feed display order (first element = top of feed). Use deterministic tie-breaking (e.g. `uri` ascending) when primary sort keys tie so that runs are reproducible.

## Example template (copy/paste)

```python
"""Your algorithm description.

Brief docstring describing ranking logic.
"""

from feeds.algorithms.interfaces import (
    FeedAlgorithm,
    FeedAlgorithmMetadata,
    FeedAlgorithmResult,
)
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.posts import BlueskyFeedPost

ALGORITHM_ID = "my_algorithm"
METADATA: FeedAlgorithmMetadata = {
    "display_name": "My Algorithm",
    "description": "Brief description for the API and UI.",
    "config_schema": None,  # or a JSON Schema dict if configurable
}


class MyFeedAlgorithm(FeedAlgorithm):
    """Feed algorithm that ranks by your custom logic."""

    @property
    def metadata(self) -> FeedAlgorithmMetadata:
        return METADATA

    def generate(
        self,
        *,
        candidate_posts: list[BlueskyFeedPost],
        agent: SocialMediaAgent,
        limit: int,  # supplied by caller; see feeds.constants.MAX_POSTS_PER_FEED
    ) -> FeedAlgorithmResult:
        """Generate a feed using your ranking logic."""
        # Your ranking logic (e.g. sort, score, filter). Use uri for tie-breaking.
        ranked_posts = sorted(
            candidate_posts, key=lambda p: (-p.like_count, p.uri)
        )
        selected = ranked_posts[:limit]
        post_uris = [p.uri for p in selected]

        return FeedAlgorithmResult(
            feed_id=GeneratedFeed.generate_feed_id(),
            agent_handle=agent.handle,
            post_uris=post_uris,
        )
```

## What the output looks like

The `generate` method returns `FeedAlgorithmResult` that the framework wraps into `GeneratedFeed`:

| Field         | Type   | Description                                                                 |
|---------------|--------|-----------------------------------------------------------------------------|
| `feed_id`     | `str`  | Unique ID for the feed; use `GeneratedFeed.generate_feed_id()`              |
| `agent_handle`| `str`  | The agent's handle; use `agent.handle`                                      |
| `post_uris`   | `list[str]` | Ordered list of post URIs (first = top of feed). Use deterministic tie-breaking. |

The framework persists the feed, hydrates posts, and returns hydrated feeds to callers. Your algorithm only ranks and selects from `candidate_posts`.

## Register the algorithm (in `feeds/algorithms/registry.py`)

1. Import your implementation's algorithm class:

```python
from feeds.algorithms.implementations.my_algorithm import MyFeedAlgorithm
```

2. Add an entry to `_ALGORITHM_LOOKUP`:

```python
_ALGORITHM_LOOKUP: dict[str, FeedAlgorithm] = {
    "chronological": ChronologicalFeedAlgorithm(),
    "my_algorithm": MyFeedAlgorithm(),
}
```

`FEED_ALGORITHMS` is derived from `_ALGORITHM_LOOKUP.keys()`, so no extra registration is needed. Validators and `GET /v1/simulations/feed-algorithms` will pick it up automatically.

## Running checks locally

From repo root:

```bash
uv run pytest tests/feeds/ tests/api/test_feed_algorithms.py tests/api/test_simulation_run.py -v
uv run --extra test pre-commit run --all-files
```

To verify the new algorithm is exposed:

```bash
curl -s http://localhost:8000/v1/simulations/feed-algorithms
```

You should see your algorithm in the JSON response with `id`, `display_name`, `description`, and `config_schema`.

## Worked example: `engagement-feed-ranking`

This section walks through adding an algorithm that ranks posts by engagement (likes, reposts, replies).

### 1. Create the implementation file

**File:** `feeds/algorithms/implementations/engagement_feed_ranking.py`

Create this file:

```python
"""Engagement-based feed ranking.

Ranks posts by a weighted engagement score (likes, reposts, replies). Highest-engagement posts first.
"""

from feeds.algorithms.interfaces import (
    FeedAlgorithm,
    FeedAlgorithmMetadata,
    FeedAlgorithmResult,
)
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.posts import BlueskyFeedPost

ALGORITHM_ID = "engagement-feed-ranking"
METADATA: FeedAlgorithmMetadata = {
    "display_name": "Engagement",
    "description": "Posts ranked by engagement (likes, reposts, replies). Highest-engagement first. Up to 20 posts per feed.",
    "config_schema": None,
}

LIKE_WEIGHT = 1.0
REPOST_WEIGHT = 1.5
REPLY_WEIGHT = 1.2


def _engagement_score(post: BlueskyFeedPost) -> float:
    """Compute weighted engagement score for a post."""
    return (
        post.like_count * LIKE_WEIGHT
        + post.repost_count * REPOST_WEIGHT
        + post.reply_count * REPLY_WEIGHT
    )


class EngagementFeedAlgorithm(FeedAlgorithm):
    """Feed algorithm that ranks by engagement score."""

    @property
    def metadata(self) -> FeedAlgorithmMetadata:
        return METADATA

    def generate(
        self,
        *,
        candidate_posts: list[BlueskyFeedPost],
        agent: SocialMediaAgent,
        limit: int,
    ) -> FeedAlgorithmResult:
        """Generate a feed ranked by engagement score."""
        scored = [(_engagement_score(p), p) for p in candidate_posts]
        scored.sort(key=lambda x: (-x[0], x[1].uri))  # uri for tie-breaking
        selected = [p for _, p in scored[:limit]]
        post_uris = [p.uri for p in selected]

        return FeedAlgorithmResult(
            feed_id=GeneratedFeed.generate_feed_id(),
            agent_handle=agent.handle,
            post_uris=post_uris,
        )
```

### 2. Register in the registry

**File:** `feeds/algorithms/registry.py`

Add the import (alongside the existing chronological import):

```python
from feeds.algorithms.implementations.chronological import ChronologicalFeedAlgorithm
from feeds.algorithms.implementations.engagement_feed_ranking import (
    EngagementFeedAlgorithm,
)
```

Add the entry to `_ALGORITHM_LOOKUP`:

```python
_ALGORITHM_LOOKUP: dict[str, FeedAlgorithm] = {
    "chronological": ChronologicalFeedAlgorithm(),
    "engagement-feed-ranking": EngagementFeedAlgorithm(),
}
```

### 3. Verify

Run tests:

```bash
uv run pytest tests/feeds/ tests/api/test_feed_algorithms.py tests/api/test_simulation_run.py -v
```

Start the server and check the API:

```bash
# In one terminal
uv run uvicorn simulation.api.main:app --reload

# In another
curl -s http://localhost:8000/v1/simulations/feed-algorithms
```

Expected response includes your algorithm in the array, e.g.:

```json
{
  "id": "engagement-feed-ranking",
  "display_name": "Engagement",
  "description": "Posts ranked by engagement (likes, reposts, replies). Highest-engagement first. Up to 20 posts per feed.",
  "config_schema": null
}
```

Use it in a run:

```bash
curl -s -X POST http://localhost:8000/v1/simulations/run \
  -H "Content-Type: application/json" \
  -d '{"num_agents": 1, "num_turns": 1, "feed_algorithm": "engagement-feed-ranking"}'
```

### Summary of files touched

| Action  | File path                                                                 |
|---------|---------------------------------------------------------------------------|
| Create  | `feeds/algorithms/implementations/engagement_feed_ranking.py`             |
| Edit    | `feeds/algorithms/registry.py` (import + `_ALGORITHM_LOOKUP` entry)       |

No other files need changes. Validation, `GET /v1/simulations/feed-algorithms`, and `POST /v1/simulations/run` pick up the new algorithm automatically.

## Common pitfalls

- **Wrong return type**: `generate` must return `FeedAlgorithmResult`, not a dict; missing or wrong fields cause runtime errors when building `GeneratedFeed`.
- **Non-deterministic ordering**: When primary sort keys tie (e.g. same score or created_at), use a secondary sort by `uri` (ascending) so output is reproducible.
- **Wrong post_uris order**: `post_uris` is the feed display order; first element = top of feed. Ensure your sort preserves intent.
- **Forgetting `ALGORITHM_ID` or `METADATA`**: These are required for registry discovery and API exposure.
- **Using a duplicate `ALGORITHM_ID`**: Must match the key used in `_ALGORITHM_LOOKUP`.
- **Not registering in `registry.py`**: The implementation file alone is not enough; it must be added to `_ALGORITHM_LOOKUP`.
- **Mutating `candidate_posts`**: Prefer creating new lists; avoid modifying the input in place.
