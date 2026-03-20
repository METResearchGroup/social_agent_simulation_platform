"""SQLite database infrastructure.

This module provides SQLite-specific infrastructure functions:
- Database connection management
- Database initialization
- Database path configuration
"""

import contextlib
import logging
import os
import sqlite3
from typing import Any

from db.adapters.base import TransactionProvider
from lib.constants import REPO_ROOT
from lib.env_utils import is_local_mode

SIM_DB_PATH_ENV: str = "SIM_DB_PATH"
DB_PATH = os.path.join(REPO_ROOT, "db", "db.sqlite")
LOCAL_DEV_DB_FILENAME: str = "dev_dummy_data_db.sqlite"
LOCAL_DEV_DB_PATH: str = os.path.join(REPO_ROOT, "db", LOCAL_DEV_DB_FILENAME)

logger = logging.getLogger(__name__)


def get_db_path() -> str:
    """Return the runtime SQLite path."""
    if is_local_mode():
        return _override_custom_db_path()
    configured_path = os.environ.get(SIM_DB_PATH_ENV)
    if configured_path:
        return configured_path
    return DB_PATH


def get_connection() -> sqlite3.Connection:
    """Get a database connection.

    Returns:
        SQLite connection to db.sqlite with foreign key enforcement enabled
    """
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextlib.contextmanager
def run_transaction():
    """Context manager for a single database transaction.

    Opens a connection, yields it to the block, commits on normal exit,
    rolls back on exception, and closes the connection in a finally block.
    SQLite starts a transaction implicitly on first statement; no explicit BEGIN.
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class SqliteTransactionProvider(TransactionProvider):
    """SQLite implementation of TransactionProvider using the default DB path."""

    def run_transaction(self):
        return run_transaction()


def validate_required_fields(
    row: sqlite3.Row, fields: list[str], context: str | None = None
) -> None:
    """Validate that all required fields in a database row are not NULL.

    Args:
        row: SQLite Row object to validate
        fields: List of required field names to validate.
                For example: ["handle", "did"] or ["uri", "text"]
        context: Optional context string to include in error messages
                 (e.g., "feed post uri=at://did:plc:...")

    Raises:
        ValueError: If any required field is NULL. Error message includes
                   the field name and optional context.
        KeyError: If a field name in fields list is missing from the row
    """
    for field_name in fields:
        if row[field_name] is None:
            error_msg = f"{field_name} cannot be NULL"
            if context:
                error_msg = f"{error_msg} (context: {context})"
            raise ValueError(error_msg)


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    """Return True if the given table exists in the database."""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def _has_alembic_version(conn: sqlite3.Connection) -> bool:
    """Return True if alembic_version table exists and has a version."""
    if not _table_exists(conn, "alembic_version"):
        return False
    row = conn.execute("SELECT version_num FROM alembic_version LIMIT 1").fetchone()
    return row is not None and bool(row[0])


def _has_any_app_tables(conn: sqlite3.Connection) -> bool:
    """Return True if any core app table exists (runs, generated_feeds, turn_metadata)."""
    for name in (
        "runs",
        "generated_feeds",
        "turn_metadata",
        "turn_metrics",
        "run_metrics",
    ):
        if _table_exists(conn, name):
            return True
    return False


def _log_sqlite_alembic_revision(db_path: str) -> None:
    """Log the Alembic version row after migrate (best-effort)."""
    try:
        with sqlite3.connect(db_path) as conn:
            if not _table_exists(conn, "alembic_version"):
                logger.warning(
                    "No alembic_version table after migrate (%s); "
                    "database may not be initialized correctly",
                    db_path,
                )
                return
            row = conn.execute(
                "SELECT version_num FROM alembic_version LIMIT 1"
            ).fetchone()
        if row and row[0]:
            logger.info("SQLite Alembic revision: %s (%s)", row[0], db_path)
        else:
            logger.warning("alembic_version row missing after migrate (%s)", db_path)
    except OSError as exc:
        logger.warning("Could not read Alembic revision from %s: %s", db_path, exc)


def _apply_migrations(
    cfg: Any, db_path: str, has_version: bool, has_tables: bool
) -> None:
    """Apply every pending Alembic revision through ``head`` for ``db_path``.

    Normal path: ``upgrade head`` applies the full revision chain (all prior
    migrations) in order—required before data-only migrations run.

    Legacy path: a pre-Alembic file may have application tables but no
    ``alembic_version`` row. Stamp the baseline (initial) revision, then
    ``upgrade head`` so missing DDL runs.
    """
    from alembic import command
    from alembic.script import ScriptDirectory

    if not has_version and has_tables:
        logger.info(
            "Database %s has application tables but no alembic_version; "
            "stamping initial revision, then upgrading to head",
            db_path,
        )
        script = ScriptDirectory.from_config(cfg)
        revisions = list(script.walk_revisions())
        baseline_revision = revisions[-1].revision
        command.stamp(cfg, baseline_revision)
    command.upgrade(cfg, "head")
    _log_sqlite_alembic_revision(db_path)


def _restore_sim_db_env(
    old_sim_db_path: str | None, old_sim_db_url: str | None
) -> None:
    """Restore SIM_DB_PATH and SIM_DATABASE_URL to their previous values."""
    if old_sim_db_path is None:
        os.environ.pop("SIM_DB_PATH", None)
    else:
        os.environ["SIM_DB_PATH"] = old_sim_db_path
    if old_sim_db_url is None:
        os.environ.pop("SIM_DATABASE_URL", None)
    else:
        os.environ["SIM_DATABASE_URL"] = old_sim_db_url


def initialize_database() -> None:
    """Initialize the database by applying Alembic migrations to HEAD.

    Always runs ``alembic upgrade head`` against the configured SQLite file so
    every prior revision (DDL and data) is applied in order before the API or
    jobs use the DB. Safe to call repeatedly; when already at HEAD, Alembic is a
    no-op.
    """
    from alembic.config import Config

    db_path: str = get_db_path()
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    pyproject_toml = os.path.join(REPO_ROOT, "pyproject.toml")
    cfg = Config(toml_file=str(pyproject_toml))

    with sqlite3.connect(db_path) as conn:
        has_version = _has_alembic_version(conn)
        has_tables = _has_any_app_tables(conn)

    old_sim_db_path = os.environ.get("SIM_DB_PATH")
    old_sim_db_url = os.environ.get("SIM_DATABASE_URL")
    if is_local_mode():
        _override_custom_db_path()
    elif old_sim_db_url is None and old_sim_db_path is None:
        os.environ["SIM_DB_PATH"] = db_path
    try:
        _apply_migrations(cfg, db_path, has_version, has_tables)
    finally:
        _restore_sim_db_env(old_sim_db_path, old_sim_db_url)


def _override_custom_db_path():
    configured_path = os.environ.get(SIM_DB_PATH_ENV)
    if configured_path:
        logger.warning(
            "LOCAL=true overrides %s=%s; using %s",
            SIM_DB_PATH_ENV,
            configured_path,
            LOCAL_DEV_DB_PATH,
        )
    os.environ["SIM_DB_PATH"] = LOCAL_DEV_DB_PATH
    os.environ.pop("SIM_DATABASE_URL", None)
    return LOCAL_DEV_DB_PATH
