"""SQLite implementation of user agent profile metadata repositories."""

from db.adapters.base import (
    TransactionProvider,
    UserAgentProfileMetadataDatabaseAdapter,
)
from db.repositories.interfaces import UserAgentProfileMetadataRepository
from lib.validation_decorators import validate_inputs
from simulation.core.models.user_agent_profile_metadata import UserAgentProfileMetadata
from simulation.core.validators import validate_agent_id


class SQLiteUserAgentProfileMetadataRepository(UserAgentProfileMetadataRepository):
    """SQLite implementation of UserAgentProfileMetadataRepository."""

    def __init__(
        self,
        *,
        db_adapter: UserAgentProfileMetadataDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        """Initialize repository with injected dependencies."""
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    def create_or_update_metadata(
        self, metadata: UserAgentProfileMetadata
    ) -> UserAgentProfileMetadata:
        """Create or update user agent profile metadata in SQLite."""
        with self._transaction_provider.run_transaction() as c:
            self._db_adapter.write_user_agent_profile_metadata(metadata, conn=c)
        return metadata

    @validate_inputs((validate_agent_id, "agent_id"))
    def get_by_agent_id(self, agent_id: str) -> UserAgentProfileMetadata | None:
        """Get metadata by agent_id."""
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_by_agent_id(agent_id, conn=c)


def create_sqlite_user_agent_profile_metadata_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteUserAgentProfileMetadataRepository:
    """Factory to create SQLiteUserAgentProfileMetadataRepository with default dependencies."""
    from db.adapters.sqlite import SQLiteUserAgentProfileMetadataAdapter

    return SQLiteUserAgentProfileMetadataRepository(
        db_adapter=SQLiteUserAgentProfileMetadataAdapter(),
        transaction_provider=transaction_provider,
    )
