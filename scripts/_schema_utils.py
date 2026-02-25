from __future__ import annotations

import os
import subprocess
from pathlib import Path


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
