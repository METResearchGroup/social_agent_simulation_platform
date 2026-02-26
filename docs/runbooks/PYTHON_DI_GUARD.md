---
description: Dependency Injection Guard (Semgrep + AST) for Python (DI architecture enforcement).
tags: [python, dependency-injection, architecture, semgrep, linting, pre-commit, ci]
---

# Python Dependency Injection Guard

This repo enforces dependency injection (DI) as an architecture rule (see `docs/RULES.md`).
Concrete infrastructure wiring must live only in composition roots.

The DI guard runs in both pre-commit and CI and consists of:

1) Semgrep rules in `lint/semgrep/`
2) An AST linter in `scripts/lint_architecture.py`

## Run locally

From repo root:

```bash
uv tool run semgrep --config lint/semgrep --error
uv run --extra test python scripts/lint_architecture.py
```

Expected output:

- Semgrep: `0 findings`
- AST linter: `OK (N files checked)`

## Composition roots (allowed wiring locations)

Concrete wiring is permitted only in:

- `simulation/core/factories/**`
- `simulation/api/main.py`
- `db/**`
- `jobs/**`
- `simulation/local_dev/**`
- `tests/**`

## Common fixes

- **Concrete infra constructed in business logic**: move construction into a factory (or `simulation/api/main.py`) and inject the dependency.
- **Dependency defaults in non-factory code** (e.g. `dep = dep or ConcreteDep()`): make the dependency required; default it only in a factory.
- **Optional infra dependency (`Dep | None = None`)**: make it required at the business-logic boundary.
