"""SQLite implementation of profile repositories."""

from db.adapters.base import ProfileDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import ProfileRepository
from simulation.core.models.profiles import BlueskyProfile
from simulation.core.utils.validators import validate_handle_exists


class SQLiteProfileRepository(ProfileRepository):
    """SQLite implementation of ProfileRepository.

    Uses dependency injection to accept a database adapter,
    decoupling it from concrete implementations.
    """

    def __init__(
        self,
        *,
        db_adapter: ProfileDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        """Initialize repository with injected dependencies.

        Args:
            db_adapter: Database adapter for profile operations
            transaction_provider: Provider for transactions
        """
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    def create_or_update_profile(self, profile: BlueskyProfile) -> BlueskyProfile:
        """Create or update a profile in SQLite.

        Args:
            profile: BlueskyProfile model to create or update

        Returns:
            The created or updated BlueskyProfile object

        Raises:
            ValueError: If profile.handle is empty (validated by Pydantic model)
            sqlite3.IntegrityError: If handle violates constraints (from adapter)
            sqlite3.OperationalError: If database operation fails (from adapter)
        """
        # Validation is handled by Pydantic model (BlueskyProfile.validate_handle)
        with self._transaction_provider.run_transaction() as c:
            self._db_adapter.write_profile(profile, conn=c)
        return profile

    def get_profile(self, handle: str) -> BlueskyProfile | None:
        """Get a profile from SQLite.

        Args:
            handle: Unique identifier for the profile

        Returns:
            BlueskyProfile model if found, None otherwise.

        Raises:
            ValueError: If handle is empty or None

        Note:
            Pydantic validators only run when creating models. Since this method accepts a raw string
            parameter (not a BlueskyProfile model), we validate handle here.
        """
        validate_handle_exists(handle=handle)
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_profile(handle, conn=c)

    def list_profiles(self) -> list[BlueskyProfile]:
        """List all profiles from SQLite.

        Returns:
            List of all BlueskyProfile models.
        """
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_all_profiles(conn=c)


def create_sqlite_profile_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteProfileRepository:
    """Factory function to create a SQLiteProfileRepository with default dependencies.

    Returns:
        SQLiteProfileRepository configured with SQLite adapter
    """
    from db.adapters.sqlite import SQLiteProfileAdapter

    return SQLiteProfileRepository(
        db_adapter=SQLiteProfileAdapter(),
        transaction_provider=transaction_provider,
    )
