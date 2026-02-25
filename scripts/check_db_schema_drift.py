#!/usr/bin/env python3
"""Fail if db/schema.py metadata drifts from Alembic migrations at HEAD.

Alembic autogenerate uses `db/schema.py` as the metadata source-of-truth. If it
diverges from the schema produced by applying migrations, autogenerate diffs become
misleading and drift can accumulate.

This script applies migrations to a temporary SQLite database, then uses Alembic's
autogenerate comparison to check for diffs against `db.schema.metadata`.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _alembic_upgrade_head(*, repo_root: Path, sqlite_path: Path) -> None:
    env = os.environ.copy()
    env["SIM_DB_PATH"] = str(sqlite_path)
    completed = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "alembic",
            "-c",
            "pyproject.toml",
            "upgrade",
            "head",
        ],
        cwd=str(repo_root),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Alembic upgrade failed.\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}\n"
        )


def main() -> int:
    repo_root = _repo_root()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from db.schema import metadata as target_metadata  # noqa: PLC0415

    with tempfile.TemporaryDirectory(prefix="sim-schema-drift-") as tmpdir:
        sqlite_path = Path(tmpdir) / "schema.sqlite"
        _alembic_upgrade_head(repo_root=repo_root, sqlite_path=sqlite_path)

        engine = sa.create_engine(f"sqlite:///{sqlite_path}")
        with engine.connect() as connection:
            ctx = MigrationContext.configure(
                connection,
                opts={
                    "compare_type": True,
                    "compare_server_default": True,
                    "render_as_batch": True,
                },
            )
            diffs = compare_metadata(ctx, target_metadata)

    if not diffs:
        return 0

    print(
        "ERROR: `db/schema.py` differs from the schema produced by migrations at HEAD."
    )
    print("Fix: update `db/schema.py` to match HEAD (or fix the migration).")
    print("")
    print("Diff summary (first 50 items):")
    for i, diff in enumerate(diffs[:50], start=1):
        print(f"{i:02d}. {diff!r}")
    if len(diffs) > 50:
        print(f"... and {len(diffs) - 50} more.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
