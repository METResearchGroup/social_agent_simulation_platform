"""SQLite implementation of profile database adapter."""

import sqlite3

from db.adapters.base import ProfileDatabaseAdapter
from db.adapters.sqlite.schema_utils import ordered_column_names, required_column_names
from db.adapters.sqlite.sqlite import get_connection, validate_required_fields
from db.schema import bluesky_profiles
from simulation.core.models.profiles import BlueskyProfile
from simulation.core.validators import validate_handle_exists

PROFILE_COLUMNS = ordered_column_names(bluesky_profiles)
PROFILE_REQUIRED_FIELDS = required_column_names(bluesky_profiles)
_INSERT_PROFILE_SQL = (
    f"INSERT OR REPLACE INTO bluesky_profiles ({', '.join(PROFILE_COLUMNS)}) "
    f"VALUES ({', '.join('?' for _ in PROFILE_COLUMNS)})"
)


class SQLiteProfileAdapter(ProfileDatabaseAdapter):
    """SQLite implementation of ProfileDatabaseAdapter.

    This implementation raises SQLite-specific exceptions. See method docstrings
    for details on specific exception types.
    """

    def write_profile(self, profile: BlueskyProfile) -> None:
        """Write a profile to SQLite.

        Args:
            profile: BlueskyProfile model to write

        Raises:
            sqlite3.IntegrityError: If handle violates constraints
            sqlite3.OperationalError: If database operation fails
        """
        with get_connection() as conn:
            conn.execute(
                _INSERT_PROFILE_SQL,
                tuple(getattr(profile, col) for col in PROFILE_COLUMNS),
            )
            conn.commit()

    def _validate_profile_row(self, row: sqlite3.Row) -> None:
        """Validate that all required profile fields are not NULL.

        Args:
            row: SQLite Row object containing profile data

        Raises:
            ValueError: If any required field is NULL
        """
        validate_required_fields(row, PROFILE_REQUIRED_FIELDS)

    def read_profile(self, handle: str) -> BlueskyProfile | None:
        """Read a profile from SQLite.

        Args:
            handle: Profile handle to look up

        Returns:
            BlueskyProfile if found, None otherwise.

        Raises:
            ValueError: If handle is empty
            ValueError: If the profile data is invalid (NULL fields)
            sqlite3.OperationalError: If database operation fails
            KeyError: If required columns are missing from the database row
        """
        validate_handle_exists(handle)
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM bluesky_profiles WHERE handle = ?", (handle,)
            ).fetchone()

            if row is None:
                return None

            self._validate_profile_row(row)

            return BlueskyProfile(
                handle=row["handle"],
                did=row["did"],
                display_name=row["display_name"],
                bio=row["bio"],
                followers_count=row["followers_count"],
                follows_count=row["follows_count"],
                posts_count=row["posts_count"],
            )

    def read_all_profiles(self) -> list[BlueskyProfile]:
        """Read all profiles from SQLite.

        Returns:
            List of BlueskyProfile models.

        Raises:
            ValueError: If any profile data is invalid (NULL fields)
            sqlite3.OperationalError: If database operation fails
            KeyError: If required columns are missing from any database row
        """
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM bluesky_profiles").fetchall()

            profiles = []
            for row in rows:
                self._validate_profile_row(row)

                profiles.append(
                    BlueskyProfile(
                        handle=row["handle"],
                        did=row["did"],
                        display_name=row["display_name"],
                        bio=row["bio"],
                        followers_count=row["followers_count"],
                        follows_count=row["follows_count"],
                        posts_count=row["posts_count"],
                    )
                )

            return profiles
