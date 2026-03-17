---
description: Configure Cursor Cloud startup so repo-wide quality gates run without manual Python installs.
tags: [cursor, cloud, onboarding, environment, pre-commit, pyright]
---

# Cursor Cloud Environment Setup

Use this runbook when configuring Cursor Cloud or any other ephemeral agent environment for this repo.

## Goal

Make these repo-wide quality gates work without manual Python installs:

- `uv run pre-commit run --all-files`
- `uv run pyright .`

## Recommended startup command

From the repository root, run:

```bash
bash scripts/setup_cursor_cloud_env.sh
```

That script installs the Python dependencies needed for repo-wide linting and type checking:

```bash
uv sync --frozen --extra test --extra ner
```

## Why `--extra ner` is required

Whole-repo type checking touches `ml_tooling/ner/`, which imports `transformers`.

- `pre-commit`, `pyright`, and other quality tools live in the `test` extra.
- `transformers` (and `torch`) live in the `ner` extra.

If Cursor Cloud only installs `--extra test`, `uv run pyright .` can fail on missing NER imports.

## Verify the environment

After startup completes, run:

```bash
uv run pre-commit run --all-files
uv run pyright .
```

## Minimal fallback

There is no smaller project-managed extra combination that still guarantees both commands pass. If startup time is a concern, keep the startup command the same and rely on caching rather than dropping `--extra ner`.

Do not replace `--extra ner` with an ad-hoc `pip install transformers`; keep dependency resolution in `uv` so agents and CI stay aligned.
