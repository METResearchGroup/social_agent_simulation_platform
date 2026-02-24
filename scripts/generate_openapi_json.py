#!/usr/bin/env python3
"""Generate OpenAPI JSON from the FastAPI app without running the server.

Usage (from repo root):
  python scripts/generate_openapi_json.py --out ui/openapi.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate OpenAPI JSON for the API")
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Path to write OpenAPI JSON (e.g. ui/openapi.json)",
    )
    args = parser.parse_args()

    repo_root = _repo_root()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from simulation.api.main import app  # noqa: PLC0415

    spec = app.openapi()

    out_path: Path = args.out
    if not out_path.is_absolute():
        out_path = (Path.cwd() / out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(spec, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
