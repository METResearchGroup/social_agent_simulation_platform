# Social Media AI Agent Simulation Platform

## Quick start

- **Setup:** `uv sync --extra test`
- **Cursor Cloud / repo-wide lint + type checks:** `bash scripts/setup_cursor_cloud_env.sh`
- **Run API:** `PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload`
- **Health check:** `http://localhost:8000/health` — API docs at `http://localhost:8000/docs`

## Documentation

See [docs/README.md](docs/README.md) for runbooks and references.
