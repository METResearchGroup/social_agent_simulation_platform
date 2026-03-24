---
name: Pin LiteLLM 1.81.15
description: "Pin LiteLLM to PyPI 1.81.15, remove git from the API Docker image, and document supply-chain context plus verification."
tags: [plan, security, dependencies, litellm]
overview: "Replace the unpinned GitHub Git URL for LiteLLM with litellm==1.81.15 from PyPI, drop git from Dockerfile, and record risk context and manual verification."
todos:
  - id: py-deps-pin
    content: "Set litellm==1.81.15 in pyproject.toml (remove Git URL)"
    status: completed
  - id: docker-nogit
    content: "Remove git from Dockerfile; update LiteLLM/uv comments"
    status: completed
  - id: docs-plan-litellm
    content: "This plan document with notes + front matter"
    status: completed
  - id: py-lockverify
    content: "uv lock, sync, ruff, pyright, pytest; check_docs_metadata on this plan"
    status: completed
isProject: false
---

# Pin LiteLLM to 1.81.15

## What changed

- **[pyproject.toml](pyproject.toml):** `litellm @ git+https://github.com/BerriAI/litellm.git` replaced with `litellm==1.81.15` (PyPI).
- **[Dockerfile](Dockerfile):** Removed `git` from the image; runtime dependencies resolve via `uv` from PyPI / lockfile only.

## Risk context

- **PyPI incident (2025 reporting):** Malicious **PyPI** releases (commonly cited as **1.82.7** / **1.82.8**) with obfuscated proxy code and **`.pth`**-style startup behavior; mitigated by not installing those versions and by pinning a known-good release ([CyberInsider summary](https://cyberinsider.com/new-supply-chain-attack-hits-litellm-with-95m-monthly-downloads/), [XDA overview](https://www.xda-developers.com/popular-python-library-backdoor-machine/)). **1.81.15** is outside that reported malicious pair.
- **CVE-2025-0330:** Langfuse-related leakage in **proxy** paths ([GitLab advisory](https://advisories.gitlab.com/pkg/pypi/litellm/CVE-2025-0330)); this app uses **`litellm.completion`** / **`batch_completion`** in [ml_tooling/llm/llm_service.py](ml_tooling/llm/llm_service.py), not the LiteLLM proxy server—lower relevance but note for future proxy use.
- **Official LiteLLM Docker images:** CVE discussions on upstream images ([issue #11829](https://github.com/BerriAI/litellm/issues/11829)); this repo builds from **`python:3.12-slim`** + `uv`, not those images.
- **Prior setup:** Unpinned **`main`** from GitHub; **CI jobs that run `uv lock` before `uv sync`** ([.github/workflows/ci.yml](.github/workflows/ci.yml)) re-resolved that moving target each run. PyPI `==` pin stabilizes resolution.
- **`uv.lock` gitignored:** Reproducibility across clones is weaker until the lockfile is committed; optional follow-up—stop ignoring `uv.lock` and commit it.

## Follow-up (optional)

- Commit **`uv.lock`** and stop gitignoring it for stronger reproducibility with Docker `--frozen` and CI.

## Manual verification

Run from repo root (with dev extras as needed):

- `uv lock` — success; local `uv.lock` should show `litellm` **1.81.15** from `https://pypi.org/simple`.
- `uv sync --extra test --extra ner --extra polarity` — success.
- `uv run ruff check .` — exit 0.
- `uv run ruff format --check .` — exit 0.
- `uv run pyright .` — exit 0.
- `uv run pytest` — exit 0.
- `uv run python scripts/check_docs_metadata.py docs/plans/2026-03-24_pin_litellm_1_81_15_481527/plan.md` — exit 0.
- Optional: `docker build -t sim-api:litellm-test .` — success without installing `git` in the image.

## Acceptance

- No `git+https://github.com/BerriAI/litellm` in `pyproject.toml`.
- Dockerfile does not install `git` for LiteLLM.
