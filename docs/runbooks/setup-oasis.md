---
description: Set up CAMEL and OASIS from PyPI for experiments with reliable Pyright import/type resolution.
tags: [oasis, camel, pyright, experiments, setup]
---

# Setup OASIS from PyPI

This runbook sets up `camel-ai` and `camel-oasis` from PyPI, then configures Pyright so imports resolve in experiment scripts.

## Why this is needed

- `camel-ai` and `camel-oasis` do not currently provide complete static typing metadata for every symbol.

## Prerequisites

- Python (recommended: 3.11 for OASIS compatibility)
- `uv` installed: [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)
- Repository root as current working directory

## 1) Install project dependencies

From repository root:

```bash
uv sync --extra test
```

## 2) Install CAMEL + OASIS from PyPI

From repository root:

```bash
uv pip install camel-ai camel-oasis
```

Verify both packages:

```bash
uv run python -c "import camel, oasis; print('camel:', camel.__file__); print('oasis:', oasis.__file__)"
```

## 3) Pyright configuration

This repository includes `pyrightconfig.json` with:

- `venvPath` and `venv` targeting local `.venv`
- `reportMissingTypeStubs = false`

This avoids unnecessary stub warnings for third-party libraries.

## 4) Ensure Cursor/Pyright uses the correct interpreter

In Cursor/VS Code:

- Select interpreter: `./.venv/bin/python`
- Restart language server (or reload window) after dependency changes

If the wrong interpreter is selected, imports may fail even when installation is correct.

## 5) Validate import resolution

Run Pyright for just the experiment file:

```bash
uv run pyright experiments/oasis_simulator_2026_03_25/misinformation/simulation.py
```

If import errors persist:

- Confirm `uv pip show camel-ai` and `uv pip show camel-oasis` in the same environment.
- Confirm `import oasis` resolves from site-packages.
- Restart the language server.

## Known caveat: partial type hints

Even with correct setup, autocomplete and inferred types may remain partial for some `camel` and `oasis` APIs because those packages do not ship comprehensive typing metadata.

For strict typing on high-use APIs, add local stubs under a `typings/` folder and point Pyright `stubPath` there.
