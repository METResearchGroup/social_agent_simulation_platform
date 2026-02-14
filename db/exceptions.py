"""Database-specific exceptions only.

Domain exceptions (RunNotFoundError, InvalidTransitionError, RunCreationError,
RunStatusUpdateError, DuplicateTurnMetadataError) live in simulation.core.exceptions.
The DB layer (adapters, repositories) maps low-level DB failures to those domain
exceptions; use simulation.core.exceptions for imports.
"""


class DatabaseError(Exception):
    """Base for truly database-specific errors (e.g. connection, schema, driver)."""

    def __init__(self, message: str, cause: Exception | None = None):
        self.message = message
        self.cause = cause
        super().__init__(message)
        if cause is not None:
            self.__cause__ = cause
