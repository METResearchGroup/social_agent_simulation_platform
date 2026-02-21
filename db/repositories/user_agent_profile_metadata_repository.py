"""SQLite implementation of user agent profile metadata repositories."""

from db.adapters.base import UserAgentProfileMetadataDatabaseAdapter
from db.repositories.interfaces import UserAgentProfileMetadataRepository
from lib.validation_utils import validate_non_empty_string
from simulation.core.models.user_agent_profile_metadata import UserAgentProfileMetadata


class SQLiteUserAgentProfileMetadataRepository(UserAgentProfileMetadataRepository):
    """SQLite implementation of UserAgentProfileMetadataRepository."""

    def __init__(self, db_adapter: UserAgentProfileMetadataDatabaseAdapter):
        """Initialize repository with injected dependencies."""
        self._db_adapter = db_adapter

    def create_or_update_metadata(
        self, metadata: UserAgentProfileMetadata
    ) -> UserAgentProfileMetadata:
        """Create or update user agent profile metadata in SQLite."""
        self._db_adapter.write_user_agent_profile_metadata(metadata)
        return metadata

    def get_by_agent_id(self, agent_id: str) -> UserAgentProfileMetadata | None:
        """Get metadata by agent_id."""
        validate_non_empty_string(agent_id, "agent_id")
        return self._db_adapter.read_by_agent_id(agent_id)


def create_sqlite_user_agent_profile_metadata_repository() -> (
    SQLiteUserAgentProfileMetadataRepository
):
    """Factory to create SQLiteUserAgentProfileMetadataRepository with default dependencies."""
    from db.adapters.sqlite import SQLiteUserAgentProfileMetadataAdapter

    return SQLiteUserAgentProfileMetadataRepository(
        db_adapter=SQLiteUserAgentProfileMetadataAdapter()
    )
