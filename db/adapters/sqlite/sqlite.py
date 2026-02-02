"""SQLite database infrastructure.

This module provides SQLite-specific infrastructure functions:
- Database connection management
- Database initialization
- Database path configuration
"""

import os
import sqlite3
from pathlib import Path

DB_PATH = os.path.abspath(
    os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "db.sqlite"))
)


def get_connection() -> sqlite3.Connection:
    """Get a database connection.

    Returns:
        SQLite connection to db.sqlite with foreign key enforcement enabled
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def validate_required_fields(
    row: sqlite3.Row, fields: dict[str, str], context: str | None = None
) -> None:
    """Validate that all required fields in a database row are not NULL.

    Args:
        row: SQLite Row object to validate
        fields: Dictionary mapping field names to their descriptions for error messages.
                For example: {"handle": "handle", "did": "did"} or
                {"uri": "feed post URI", "text": "post text"}
        context: Optional context string to include in error messages
                 (e.g., "feed post uri=at://did:plc:...")

    Raises:
        ValueError: If any required field is NULL. Error message includes
                   the field description and optional context.
        KeyError: If a field name in fields dict is missing from the row
    """
    for field_name, description in fields.items():
        if row[field_name] is None:
            error_msg = f"{description} cannot be NULL"
            if context:
                error_msg = f"{error_msg} (context: {context})"
            raise ValueError(error_msg)


def initialize_database() -> None:
    """Initialize the database by applying Alembic migrations to HEAD.

    This is safe to call repeatedly; if the database is already at HEAD, Alembic
    will make no changes.
    """

    from alembic import command
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    # Ensure parent directory exists (especially for test temp DB paths).
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    repo_root = Path(__file__).resolve().parents[3]
    pyproject_toml = repo_root / "pyproject.toml"

    cfg = Config(toml_file=str(pyproject_toml))

    def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        ).fetchone()
        return row is not None

    def _has_alembic_version(conn: sqlite3.Connection) -> bool:
        if not _table_exists(conn, "alembic_version"):
            return False
        row = conn.execute(
            "SELECT version_num FROM alembic_version LIMIT 1"
        ).fetchone()
        return row is not None and bool(row[0])

    def _has_any_app_tables(conn: sqlite3.Connection) -> bool:
        # A minimal heuristic: if any core table exists, treat DB as pre-existing.
        for name in ("runs", "generated_feeds", "turn_metadata"):
            if _table_exists(conn, name):
                return True
        return False

    with sqlite3.connect(DB_PATH) as conn:
        has_version = _has_alembic_version(conn)
        has_tables = _has_any_app_tables(conn)

    # Ensure Alembic targets the same DB_PATH used by runtime code.
    # Respect explicit configuration if the caller already set it.
    old_sim_db_path = os.environ.get("SIM_DB_PATH")
    old_sim_db_url = os.environ.get("SIM_DATABASE_URL")
    try:
        if old_sim_db_url is None and old_sim_db_path is None:
            os.environ["SIM_DB_PATH"] = DB_PATH

        if has_version or not has_tables:
            # Normal case: versioned DB or an empty DB.
            command.upgrade(cfg, "head")
        else:
            # Legacy case: tables exist but Alembic version table is missing.
            # Assume the schema matches the initial baseline revision, then
            # upgrade through subsequent migrations (e.g., adding FKs).
            script = ScriptDirectory.from_config(cfg)
            revisions = list(script.walk_revisions())
            baseline_revision = revisions[-1].revision  # down_revision is None
            command.stamp(cfg, baseline_revision)
            command.upgrade(cfg, "head")
    finally:
        if old_sim_db_path is None:
            os.environ.pop("SIM_DB_PATH", None)
        else:
            os.environ["SIM_DB_PATH"] = old_sim_db_path

        if old_sim_db_url is None:
            os.environ.pop("SIM_DATABASE_URL", None)
        else:
            os.environ["SIM_DATABASE_URL"] = old_sim_db_url
