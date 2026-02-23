"""Shared pytest fixtures for the full test suite."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator

import pytest


@pytest.fixture
def temp_db(monkeypatch: pytest.MonkeyPatch) -> Generator[str, None, None]:
    """Create a temporary SQLite database, initialize schema, then clean up.

    This fixture:
    - Creates a temp .sqlite file path
    - Ensures all SQLite consumers point at it (DB_PATH + SIM_DB_PATH)
    - Applies Alembic migrations via initialize_database()
    - Deletes the file on teardown
    """
    fd, temp_path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)

    import db.adapters.sqlite.sqlite as sqlite_module
    from db.adapters.sqlite.sqlite import initialize_database

    monkeypatch.setattr(sqlite_module, "DB_PATH", temp_path)
    monkeypatch.setenv(sqlite_module.SIM_DB_PATH_ENV, temp_path)

    initialize_database()

    try:
        yield temp_path
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
