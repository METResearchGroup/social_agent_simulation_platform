---
description: How to add new Python tests (pytest) using deterministic test factories (Faker + Hypothesis).
tags: [testing, pytest, python, factories, faker, hypothesis, uv]
---

# Create New Python Tests Runbook

This runbook documents the preferred workflow for adding new Python tests in this repo.

## Prerequisites

From the repo root:

```bash
uv sync --extra test
```

## Run tests (always via uv)

Run all tests:

```bash
uv run pytest
```

Run a specific file:

```bash
uv run pytest tests/path/to/test_file.py
```

Run a single test:

```bash
uv run pytest tests/path/to/test_file.py::test_name
```

## Prefer test factories over inline model construction

When tests need domain models (posts, runs, agents, action rows, etc.), prefer the factories in:

- `tests/factories/`

These factories provide:

- **Deterministic defaults** via a **per-test seeded** `faker.Faker()` (wired by an autouse fixture in `tests/conftest.py`).
- A consistent API: `XFactory.create(...)` and `XFactory.create_batch(n, ...)`.

### Example: create posts

```python
from tests.factories import PostFactory


def test_post_defaults_are_valid():
    post = PostFactory.create()
    assert post.uri
    assert post.author_handle
```

Override only what matters:

```python
from tests.factories import PostFactory


def test_can_override_uri_and_counts():
    post = PostFactory.create(
        uri="at://did:plc:example/app.bsky.feed.post/post1",
        like_count=10,
        reply_count=2,
    )
    assert post.like_count == 10
    assert post.reply_count == 2
```

### Example: create generated actions

```python
from tests.factories import GeneratedLikeFactory, GenerationMetadataFactory


def test_generated_like_can_be_built_with_explicit_metadata():
    generated = GeneratedLikeFactory.create(
        agent_id="agent_1",
        post_id="post_1",
        metadata=GenerationMetadataFactory.create(created_at="2024_01_01-12:00:00"),
    )
    assert generated.like.post_id == "post_1"
```

### Example: create persisted action rows

```python
from tests.factories import PersistedLikeFactory


def test_persisted_like_row_shape():
    row = PersistedLikeFactory.create(run_id="run_1", turn_number=0)
    assert row.run_id == "run_1"
    assert row.turn_number == 0
```

## Property tests (Hypothesis)

When a test is about **invariants** (validation rules, ordering, edge cases), prefer Hypothesis.

### Use provided strategies when available

Strategies live in:

- `tests/factories/strategies.py`

Example:

```python
from hypothesis import given, settings

from tests.factories.strategies import bluesky_post_strategy


@given(post=bluesky_post_strategy())
@settings(max_examples=50, deadline=None)
def test_post_invariants(post):
    assert post.uri
    assert post.id == post.uri
```

## Where to put new tests

- Unit tests should live under `tests/` mirroring the source layout.
- Prefer adding tests next to similar tests to reuse fixtures and patterns.

## Quality gates

Before pushing a test change:

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
uv run pyright .
uv run pre-commit run --all-files
```
