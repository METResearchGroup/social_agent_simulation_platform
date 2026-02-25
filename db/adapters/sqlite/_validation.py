"""Shared validation helpers for SQLite adapters."""

from __future__ import annotations

import sqlite3


def _require_sqlite_connection(conn: object) -> sqlite3.Connection:
    if not isinstance(conn, sqlite3.Connection):
        raise TypeError("SQLite adapter requires sqlite3.Connection")
    return conn
