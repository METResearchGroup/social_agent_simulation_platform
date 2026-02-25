from __future__ import annotations

import os
import subprocess
from pathlib import Path

_ALEMBIC_TIMEOUT_ENV = "SCHEMA_DOCS_ALEMBIC_TIMEOUT_SECONDS"
_DEFAULT_ALEMBIC_TIMEOUT_SECONDS = 120.0


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _alembic_upgrade_head(
    *, repo_root: Path, sqlite_path: Path, timeout_seconds: float | None = None
) -> None:
    env = os.environ.copy()
    env["SIM_DB_PATH"] = str(sqlite_path)

    timeout = timeout_seconds
    if timeout is None:
        raw_timeout = os.environ.get(_ALEMBIC_TIMEOUT_ENV)
        if raw_timeout is None or raw_timeout.strip() == "":
            timeout = _DEFAULT_ALEMBIC_TIMEOUT_SECONDS
        else:
            try:
                timeout = float(raw_timeout)
            except ValueError as e:
                raise RuntimeError(
                    f"Invalid {_ALEMBIC_TIMEOUT_ENV}={raw_timeout!r}; must be a number."
                ) from e

    argv = [
        "uv",
        "run",
        "python",
        "-m",
        "alembic",
        "-c",
        "pyproject.toml",
        "upgrade",
        "head",
    ]

    try:
        completed = subprocess.run(
            argv,
            cwd=str(repo_root),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout
        stderr = e.stderr
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        raise RuntimeError(
            "Alembic upgrade timed out.\n"
            f"timeout_seconds={timeout}\n"
            f"cwd={repo_root}\n"
            f"command={argv!r}\n"
            f"SIM_DB_PATH={env.get('SIM_DB_PATH')}\n"
            f"SIM_DATABASE_URL={env.get('SIM_DATABASE_URL')}\n"
            f"stdout:\n{stdout or ''}\n"
            f"stderr:\n{stderr or ''}\n"
            f"Hint: increase timeout via {_ALEMBIC_TIMEOUT_ENV}.\n"
        ) from e
    if completed.returncode != 0:
        raise RuntimeError(
            "Alembic upgrade failed.\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}\n"
        )
