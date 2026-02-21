"""SQLite implementation of app_user repository."""

import uuid

from db.adapters.base import AppUserDatabaseAdapter
from db.repositories.interfaces import AppUserRepository
from lib.timestamp_utils import get_current_timestamp
from simulation.core.models.app_user import AppUser


class SQLiteAppUserRepository(AppUserRepository):
    """SQLite implementation of AppUserRepository."""

    def __init__(self, db_adapter: AppUserDatabaseAdapter):
        self._db_adapter = db_adapter

    def upsert_from_auth(
        self,
        *,
        auth_provider_id: str,
        email: str | None = None,
        display_name: str | None = None,
    ) -> AppUser:
        """Create or update app_user from auth claims; return the app_user."""
        ts = get_current_timestamp()
        existing = self._db_adapter.read_by_auth_provider_id(auth_provider_id)
        if existing is not None:
            self._db_adapter.update_last_seen(
                app_user_id=existing.id,
                last_seen_at=ts,
                email=email,
                display_name=display_name,
            )
            return AppUser(
                id=existing.id,
                auth_provider_id=existing.auth_provider_id,
                email=email,
                display_name=display_name,
                created_at=existing.created_at,
                last_seen_at=ts,
            )
        app_user_id = str(uuid.uuid4())
        app_user = AppUser(
            id=app_user_id,
            auth_provider_id=auth_provider_id,
            email=email,
            display_name=display_name,
            created_at=ts,
            last_seen_at=ts,
        )
        self._db_adapter.insert_app_user(app_user)
        return app_user


def create_sqlite_app_user_repository() -> SQLiteAppUserRepository:
    """Factory to create SQLiteAppUserRepository with default adapter."""
    from db.adapters.sqlite import SQLiteAppUserAdapter

    return SQLiteAppUserRepository(db_adapter=SQLiteAppUserAdapter())
