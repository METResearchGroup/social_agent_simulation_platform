"""Opt-in Railway/demo bootstrap: reset SQLite on new deployment identity, migrate, seed.

See docs/runbooks/RAILWAY_DEPLOYMENT.md for environment variables and caveats.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from db.adapters.sqlite.sqlite import get_db_path, initialize_database
from lib.env_utils import is_local_mode, parse_bool_env
from simulation.local_dev.seed_loader import seed_database_from_fixtures_if_needed

logger = logging.getLogger(__name__)

RESET_DEMO_DB_ON_DEPLOY_ENV = "RESET_DEMO_DB_ON_DEPLOY"
RAILWAY_DEPLOYMENT_ID_ENV = "RAILWAY_DEPLOYMENT_ID"
MARKER_FILENAME = ".last_railway_deploy_id"


def marker_path_for_db(db_path: Path) -> Path:
    """Path to the deploy-id marker file (same directory as the SQLite file)."""
    return db_path.parent / MARKER_FILENAME


def _delete_sqlite_cluster(db_path: Path) -> None:
    """Remove the main DB file and SQLite WAL/SHM sidecars if present."""
    candidates = (
        db_path,
        Path(f"{db_path}-wal"),
        Path(f"{db_path}-shm"),
    )
    for path in candidates:
        if path.is_file():
            path.unlink()
            logger.info("Removed %s", path)


def _read_marker(path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").strip() or None


def _write_marker(path: Path, deploy_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(deploy_id + "\n", encoding="utf-8")


def run_railway_demo_deploy_bootstrap() -> None:
    """When enabled, reset SQLite on new ``RAILWAY_DEPLOYMENT_ID``, migrate, and seed.

    No-ops when the opt-in flag is unset, when ``LOCAL`` is truthy, or when
    ``RAILWAY_DEPLOYMENT_ID`` is missing (cannot compare deploy identity).
    No-ops when the marker already matches the current deployment id (ordinary
    restarts do not wipe data).
    """
    if not parse_bool_env(RESET_DEMO_DB_ON_DEPLOY_ENV):
        logger.debug(
            "%s not enabled; skipping demo deploy bootstrap.",
            RESET_DEMO_DB_ON_DEPLOY_ENV,
        )
        return
    if is_local_mode():
        logger.info("LOCAL=true: skipping demo deploy bootstrap (hard guard).")
        return

    deploy_id = os.environ.get(RAILWAY_DEPLOYMENT_ID_ENV, "").strip()
    if not deploy_id:
        logger.warning(
            "%s is enabled but %s is absent; skipping deploy-bound reset.",
            RESET_DEMO_DB_ON_DEPLOY_ENV,
            RAILWAY_DEPLOYMENT_ID_ENV,
        )
        return

    db_path_str = get_db_path()
    db_path = Path(db_path_str)
    marker = marker_path_for_db(db_path)
    previous = _read_marker(marker)
    if previous == deploy_id:
        logger.info(
            "Demo deploy bootstrap: marker matches current %s; skipping reset.",
            RAILWAY_DEPLOYMENT_ID_ENV,
        )
        return

    logger.info(
        "Demo deploy bootstrap: new deployment; resetting SQLite at %s",
        db_path_str,
    )
    _delete_sqlite_cluster(db_path)
    initialize_database()
    seed_database_from_fixtures_if_needed(db_path=db_path_str)
    _write_marker(marker, deploy_id)
    logger.info("Demo deploy bootstrap: wrote marker %s", marker)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
    )
    run_railway_demo_deploy_bootstrap()


if __name__ == "__main__":
    main()
