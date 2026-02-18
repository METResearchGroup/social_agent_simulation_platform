"""SQLite implementation of generated bio database adapter."""

import sqlite3

from db.adapters.base import GeneratedBioDatabaseAdapter
from db.adapters.sqlite.schema_utils import ordered_column_names, required_column_names
from db.adapters.sqlite.sqlite import get_connection, validate_required_fields
from db.schema import agent_bios
from lib.timestamp_utils import get_current_timestamp
from simulation.core.models.generated.base import GenerationMetadata
from simulation.core.models.generated.bio import GeneratedBio
from simulation.core.validators import validate_handle_exists

AGENT_BIOS_COLUMNS = ordered_column_names(agent_bios)
AGENT_BIOS_REQUIRED_FIELDS = required_column_names(agent_bios)
_INSERT_AGENT_BIOS_SQL = (
    f"INSERT OR REPLACE INTO agent_bios ({', '.join(AGENT_BIOS_COLUMNS)}) "
    f"VALUES ({', '.join('?' for _ in AGENT_BIOS_COLUMNS)})"
)


class SQLiteGeneratedBioAdapter(GeneratedBioDatabaseAdapter):
    """SQLite implementation of GeneratedBioDatabaseAdapter.

    This implementation raises SQLite-specific exceptions. See method docstrings
    for details on specific exception types.
    """

    def _validate_generated_bio_row(
        self, row: sqlite3.Row, context: str | None = None
    ) -> None:
        """Validate that all required generated bio fields are not NULL.

        Args:
            row: SQLite Row object containing generated bio data
            context: Optional context string to include in error messages
                     (e.g., "generated bio handle=user.bsky.social")

        Raises:
            ValueError: If any required field is NULL. Error message includes
                        the field name and optional context.
        """
        validate_required_fields(
            row,
            AGENT_BIOS_REQUIRED_FIELDS,
            context=context,
        )

    def write_generated_bio(self, bio: GeneratedBio) -> None:
        """Write a generated bio to SQLite.

        Args:
            bio: GeneratedBio model to write

        Raises:
            sqlite3.IntegrityError: If handle violates constraints
            sqlite3.OperationalError: If database operation fails
        """
        created_at = bio.metadata.created_at or get_current_timestamp()
        row_values = tuple(
            created_at if col == "created_at" else getattr(bio, col)
            for col in AGENT_BIOS_COLUMNS
        )
        with get_connection() as conn:
            conn.execute(_INSERT_AGENT_BIOS_SQL, row_values)
            conn.commit()

    def read_generated_bio(self, handle: str) -> GeneratedBio | None:
        """Read a generated bio from SQLite.

        Args:
            handle: Profile handle to look up

        Returns:
            GeneratedBio if found, None otherwise.

        Raises:
            ValueError: If handle is empty
            ValueError: If the bio data is invalid (NULL fields)
            sqlite3.OperationalError: If database operation fails
            KeyError: If required columns are missing from the database row
        """
        validate_handle_exists(handle)
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM agent_bios WHERE handle = ?", (handle,)
            ).fetchone()

            if row is None:
                return None

            # Validate required fields are not NULL
            context = f"generated bio handle={handle}"
            self._validate_generated_bio_row(row, context=context)

            return GeneratedBio(
                handle=row["handle"],
                generated_bio=row["generated_bio"],
                metadata=GenerationMetadata(
                    model_used=None,
                    generation_metadata=None,
                    created_at=row["created_at"],
                ),
            )

    def read_all_generated_bios(self) -> list[GeneratedBio]:
        """Read all generated bios from SQLite.

        Returns:
            List of GeneratedBio models.

        Raises:
            ValueError: If any bio data is invalid (NULL fields)
            sqlite3.OperationalError: If database operation fails
            KeyError: If required columns are missing from any database row
        """
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM agent_bios").fetchall()

            bios = []
            for row in rows:
                # Validate required fields are not NULL
                handle_value = row["handle"] if row["handle"] is not None else "unknown"
                context = f"generated bio handle={handle_value}"
                self._validate_generated_bio_row(row, context=context)

                bios.append(
                    GeneratedBio(
                        handle=row["handle"],
                        generated_bio=row["generated_bio"],
                        metadata=GenerationMetadata(
                            model_used=None,
                            generation_metadata=None,
                            created_at=row["created_at"],
                        ),
                    )
                )

            return bios
