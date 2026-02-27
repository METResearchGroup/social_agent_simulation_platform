"""SQLite implementation of app_user database adapter."""

from db.adapters.base import AppUserDatabaseAdapter
from db.adapters.sqlite.sqlite import get_connection
from simulation.core.models.app_user import AppUser


class SQLiteAppUserAdapter(AppUserDatabaseAdapter):
    """SQLite implementation of AppUserDatabaseAdapter."""

    def read_by_auth_provider_id(self, auth_provider_id: str) -> AppUser | None:
        """Read app_user by auth_provider_id."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id, auth_provider_id, email, display_name, created_at, last_seen_at "
                "FROM app_users WHERE auth_provider_id = ?",
                (auth_provider_id,),
            ).fetchone()
            if row is None:
                return None
            return AppUser(
                id=row["id"],
                auth_provider_id=row["auth_provider_id"],
                email=row["email"],
                display_name=row["display_name"],
                created_at=row["created_at"],
                last_seen_at=row["last_seen_at"],
            )

    def insert_app_user(self, app_user: AppUser) -> None:
        """Insert a new app_user row."""
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO app_users (id, auth_provider_id, email, display_name, created_at, last_seen_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    app_user.id,
                    app_user.auth_provider_id,
                    app_user.email,
                    app_user.display_name,
                    app_user.created_at,
                    app_user.last_seen_at,
                ),
            )
            conn.commit()

    def update_last_seen(
        self,
        app_user_id: str,
        last_seen_at: str,
        email: str,
        display_name: str,
    ) -> None:
        """Update last_seen_at, email, display_name for an app_user."""
        with get_connection() as conn:
            conn.execute(
                "UPDATE app_users SET last_seen_at = ?, email = ?, display_name = ? WHERE id = ?",
                (last_seen_at, email, display_name, app_user_id),
            )
            conn.commit()
