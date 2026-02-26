"""SQLite implementation of generated bio repositories."""

from db.adapters.base import GeneratedBioDatabaseAdapter, TransactionProvider
from db.repositories.interfaces import GeneratedBioRepository
from simulation.core.models.generated.bio import GeneratedBio
from simulation.core.utils.validators import validate_handle_exists


class SQLiteGeneratedBioRepository(GeneratedBioRepository):
    """SQLite implementation of GeneratedBioRepository.

    Uses dependency injection to accept a database adapter,
    decoupling it from concrete implementations.
    """

    def __init__(
        self,
        *,
        db_adapter: GeneratedBioDatabaseAdapter,
        transaction_provider: TransactionProvider,
    ):
        """Initialize repository with injected dependencies.

        Args:
            db_adapter: Database adapter for generated bio operations
            transaction_provider: Provider for transactions
        """
        self._db_adapter = db_adapter
        self._transaction_provider = transaction_provider

    def create_or_update_generated_bio(self, bio: GeneratedBio) -> GeneratedBio:
        """Create or update a generated bio in SQLite.

        Args:
            bio: GeneratedBio model to create or update

        Returns:
            The created or updated GeneratedBio object

        Raises:
            ValueError: If bio.handle is empty (validated by Pydantic model if added)
            sqlite3.IntegrityError: If handle violates constraints (from adapter)
            sqlite3.OperationalError: If database operation fails (from adapter)
        """
        # Validation will be handled by Pydantic model if validators are added
        with self._transaction_provider.run_transaction() as c:
            self._db_adapter.write_generated_bio(bio, conn=c)
        return bio

    def get_generated_bio(self, handle: str) -> GeneratedBio | None:
        """Get a generated bio from SQLite.

        Args:
            handle: Profile handle to look up

        Returns:
            GeneratedBio model if found, None otherwise.

        Raises:
            ValueError: If handle is empty or None

        Note:
            Pydantic validators only run when creating models. Since this method accepts a raw string
            parameter (not a GeneratedBio model), we validate handle here.
        """
        validate_handle_exists(handle=handle)
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_generated_bio(handle, conn=c)

    def list_all_generated_bios(self) -> list[GeneratedBio]:
        """List all generated bios from SQLite.

        Returns:
            List of all GeneratedBio models.
        """
        with self._transaction_provider.run_transaction() as c:
            return self._db_adapter.read_all_generated_bios(conn=c)


def create_sqlite_generated_bio_repository(
    *,
    transaction_provider: TransactionProvider,
) -> SQLiteGeneratedBioRepository:
    """Factory function to create a SQLiteGeneratedBioRepository with default dependencies.

    Returns:
        SQLiteGeneratedBioRepository configured with SQLite adapter
    """
    from db.adapters.sqlite import SQLiteGeneratedBioAdapter

    return SQLiteGeneratedBioRepository(
        db_adapter=SQLiteGeneratedBioAdapter(),
        transaction_provider=transaction_provider,
    )
