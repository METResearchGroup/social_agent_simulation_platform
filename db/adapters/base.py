"""Base adapter interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from typing import Iterable

from simulation.core.models.agent import Agent
from simulation.core.models.agent_bio import AgentBio
from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.generated.bio import GeneratedBio
from simulation.core.models.metrics import RunMetrics, TurnMetrics
from simulation.core.models.posts import BlueskyFeedPost
from simulation.core.models.profiles import BlueskyProfile
from simulation.core.models.runs import Run
from simulation.core.models.turns import TurnMetadata
from simulation.core.models.user_agent_profile_metadata import UserAgentProfileMetadata


class TransactionProvider(ABC):
    """Abstract interface for running a database transaction.

    Implementations yield a connection for the duration of the transaction;
    callers use it and do not commit. The provider commits on normal exit
    and rolls back on exception.
    """

    @abstractmethod
    def run_transaction(self) -> AbstractContextManager[object]:
        """Enter a transaction and yield a connection.

        Commit on normal exit, roll back on exception. The yielded object
        is passed to repositories as their conn parameter.
        """
        raise NotImplementedError


class RunDatabaseAdapter(ABC):
    """Abstract interface for run database operations.

    This interface is database-agnostic. Concrete implementations should document
    the specific exceptions they raise, which may be database-specific.
    """

    @abstractmethod
    def write_run(self, run: Run) -> None:
        """Write a run to the database.

        Args:
            run: Run model to write

        Raises:
            Exception: Database-specific exception if constraints are violated or
                      the operation fails. Implementations should document the
                      specific exception types they raise.

        Note:
            This write is idempotent: an existing row with the same run_id may be
            replaced. Callers can safely retry or recompute; duplicate writes do
            not raise. Implementations (e.g. SQLite) may use INSERT OR REPLACE
            (delete+insert semantics).
        """
        raise NotImplementedError

    @abstractmethod
    def read_run(self, run_id: str) -> Run | None:
        """Read a run by ID.

        Args:
            run_id: Unique identifier for the run

        Returns:
            Run model if found, None otherwise

        Raises:
            ValueError: If the run data is invalid (NULL fields, invalid status)
            KeyError: If required columns are missing from the database row
            Exception: Database-specific exception if the operation fails.
                      Implementations should document the specific exception types
                      they raise.
        """
        raise NotImplementedError

    @abstractmethod
    def read_all_runs(self) -> list[Run]:
        """Read all runs.

        Returns:
            List of Run models, ordered by created_at descending (newest first).
            Returns empty list if no runs exist.

        Raises:
            ValueError: If any run data is invalid (NULL fields, invalid status)
            KeyError: If required columns are missing from any database row
            Exception: Database-specific exception if the operation fails.
                      Implementations should document the specific exception types
                      they raise.
        """
        raise NotImplementedError

    @abstractmethod
    def update_run_status(
        self,
        run_id: str,
        status: str,
        completed_at: str | None = None,
        conn: object | None = None,
    ) -> None:
        """Update a run's status.

        Args:
            run_id: Unique identifier for the run to update
            status: New status value (should be a valid RunStatus enum value as string)
            completed_at: Optional timestamp when the run was completed.
                         Should be set when status is 'completed', None otherwise.
            conn: Optional connection. When provided, use it and do not commit;
                  when None, use a new connection and commit.

        Raises:
            RunNotFoundError: If no run exists with the given run_id
            Exception: Database-specific exception if constraints are violated or
                      the operation fails. Implementations should document the
                      specific exception types they raise.
        """
        raise NotImplementedError

    @abstractmethod
    def read_turn_metadata(
        self,
        run_id: str,
        turn_number: int,
        conn: object | None = None,
    ) -> TurnMetadata | None:
        """Read turn metadata for a specific run and turn.

        Args:
            run_id: The ID of the run
            turn_number: The turn number (0-indexed)
            conn: Optional connection. When provided, use it and do not open/close
                  or commit; when None, use a new connection (caller manages lifecycle).

        Returns:
            TurnMetadata if found, None otherwise

        Raises:
            ValueError: If the turn metadata data is invalid (NULL fields, invalid action types)
            KeyError: If required columns are missing from the database row
            Exception: Database-specific exception if the operation fails.
                      Implementations should document the specific exception types
                      they raise.

        Note:
            The total_actions field is stored in the database as JSON with string keys
            (e.g., {"like": 5, "comment": 2}). Implementations should convert these
            string keys to TurnAction enum keys when constructing the TurnMetadata object.
        """
        raise NotImplementedError

    @abstractmethod
    def read_turn_metadata_for_run(self, run_id: str) -> list[TurnMetadata]:
        """Read all turn metadata for a specific run.

        Args:
            run_id: The ID of the run

        Returns:
            List of TurnMetadata ordered by turn_number ascending.
            Returns empty list if no rows are found for the run.

        Raises:
            ValueError: If run_id is invalid or any row contains invalid turn metadata
            KeyError: If required columns are missing from any database row
            Exception: Database-specific exception if the operation fails.
                      Implementations should document the specific exception types
                      they raise.
        """
        raise NotImplementedError

    @abstractmethod
    def write_turn_metadata(
        self,
        turn_metadata: TurnMetadata,
        conn: object | None = None,
    ) -> None:
        """Write turn metadata to the database.

        Writes to the `turn_metadata` table. Uses INSERT.

        Args:
            turn_metadata: TurnMetadata model to write
            conn: Optional connection. When provided, use it and do not commit;
                  when None, use a new connection and commit.

        Raises:
            DuplicateTurnMetadataError: If turn metadata already exists
            Exception: Database-specific exception if constraints are violated or
                      the operation fails. Implementations should document the
                      specific exception types they raise.
        """
        raise NotImplementedError


class MetricsDatabaseAdapter(ABC):
    """Abstract interface for computed metrics persistence."""

    @abstractmethod
    def write_turn_metrics(
        self,
        turn_metrics: TurnMetrics,
        conn: object | None = None,
    ) -> None:
        """Write turn metrics. When conn is provided, use it and do not commit.

        Note:
            This write is idempotent: an existing row with the same (run_id,
            turn_number) may be replaced. Callers can safely retry or recompute;
            duplicate writes do not raise. Implementations (e.g. SQLite) may use
            INSERT OR REPLACE (delete+insert semantics).
        """
        raise NotImplementedError

    @abstractmethod
    def read_turn_metrics(self, run_id: str, turn_number: int) -> TurnMetrics | None:
        raise NotImplementedError

    @abstractmethod
    def read_turn_metrics_for_run(self, run_id: str) -> list[TurnMetrics]:
        raise NotImplementedError

    @abstractmethod
    def write_run_metrics(
        self,
        run_metrics: RunMetrics,
        conn: object | None = None,
    ) -> None:
        """Write run metrics. When conn is provided, use it and do not commit.

        Note:
            This write is idempotent: an existing row with the same run_id may be
            replaced. Callers can safely retry or recompute; duplicate writes do
            not raise. Implementations (e.g. SQLite) may use INSERT OR REPLACE
            (delete+insert semantics).
        """
        raise NotImplementedError

    @abstractmethod
    def read_run_metrics(self, run_id: str) -> RunMetrics | None:
        raise NotImplementedError


class ProfileDatabaseAdapter(ABC):
    """Abstract interface for profile database operations.

    This interface is database-agnostic. Currently works with BlueskyProfile.
    Concrete implementations should document the specific exceptions they raise,
    which may be database-specific.
    """

    @abstractmethod
    def write_profile(self, profile: BlueskyProfile) -> None:
        """Write a profile to the database.

        Args:
            profile: BlueskyProfile model to write

        Raises:
            Exception: Database-specific exception if constraints are violated or
                      the operation fails. Implementations should document the
                      specific exception types they raise.

        Note:
            This write is idempotent: an existing row with the same handle may be
            replaced. Callers can safely retry or recompute; duplicate writes do
            not raise. Implementations (e.g. SQLite) may use INSERT OR REPLACE
            (delete+insert semantics).
        """
        raise NotImplementedError

    @abstractmethod
    def read_profile(self, handle: str) -> BlueskyProfile | None:
        """Read a profile by handle.

        Args:
            handle: Profile handle to look up

        Returns:
            BlueskyProfile model if found, None otherwise.

        Raises:
            ValueError: If the profile data is invalid (NULL fields)
            KeyError: If required columns are missing from the database row
            Exception: Database-specific exception if the operation fails.
                      Implementations should document the specific exception types
                      they raise.
        """
        raise NotImplementedError

    @abstractmethod
    def read_all_profiles(self) -> list[BlueskyProfile]:
        """Read all profiles.

        Returns:
            List of BlueskyProfile models. Returns empty list if no profiles exist.

        Raises:
            ValueError: If any profile data is invalid (NULL fields)
            KeyError: If required columns are missing from any database row
            Exception: Database-specific exception if the operation fails.
                      Implementations should document the specific exception types
                      they raise.
        """
        raise NotImplementedError


class FeedPostDatabaseAdapter(ABC):
    """Abstract interface for feed post database operations.

    This interface is database-agnostic. Currently works with BlueskyFeedPost.
    Concrete implementations should document the specific exceptions they raise,
    which may be database-specific.
    """

    @abstractmethod
    def write_feed_post(self, post: BlueskyFeedPost) -> None:
        """Write a feed post to the database.

        Args:
            post: BlueskyFeedPost model to write

        Raises:
            Exception: Database-specific exception if constraints are violated or
                      the operation fails. Implementations should document the
                      specific exception types they raise.

        Note:
            This write is idempotent: an existing row with the same URI may be
            replaced. Callers can safely retry or recompute; duplicate writes do
            not raise. Implementations (e.g. SQLite) may use INSERT OR REPLACE
            (delete+insert semantics).
        """
        raise NotImplementedError

    @abstractmethod
    def write_feed_posts(self, posts: list[BlueskyFeedPost]) -> None:
        """Write multiple feed posts to the database (batch operation).

        Args:
            posts: List of BlueskyFeedPost models to write

        Raises:
            Exception: Database-specific exception if constraints are violated or
                      the operation fails. Implementations should document the
                      specific exception types they raise.

        Note:
            Each write is idempotent: an existing row with the same URI may be
            replaced. Callers can safely retry or recompute; duplicate writes do
            not raise. Implementations (e.g. SQLite) may use INSERT OR REPLACE
            (delete+insert semantics).
        """
        raise NotImplementedError

    @abstractmethod
    def read_feed_post(self, uri: str) -> BlueskyFeedPost:
        """Read a feed post by URI.

        Args:
            uri: Post URI to look up

        Returns:
            BlueskyFeedPost model if found.

        Raises:
            ValueError: If uri is empty or if no feed post is found for the given URI
            ValueError: If the feed post data is invalid (NULL fields)
            KeyError: If required columns are missing from the database row
            Exception: Database-specific exception if the operation fails.
                      Implementations should document the specific exception types
                      they raise.
        """
        raise NotImplementedError

    @abstractmethod
    def read_feed_posts_by_author(self, author_handle: str) -> list[BlueskyFeedPost]:
        """Read all feed posts by a specific author.

        Args:
            author_handle: Author handle to filter by

        Returns:
            List of BlueskyFeedPost models for the author.

        Raises:
            ValueError: If any feed post data is invalid (NULL fields)
            KeyError: If required columns are missing from any database row
            Exception: Database-specific exception if the operation fails.
                      Implementations should document the specific exception types
                      they raise.
        """
        raise NotImplementedError

    @abstractmethod
    def read_all_feed_posts(self) -> list[BlueskyFeedPost]:
        """Read all feed posts.

        Returns:
            List of all BlueskyFeedPost models. Returns empty list if no posts exist.

        Raises:
            ValueError: If any feed post data is invalid (NULL fields)
            KeyError: If required columns are missing from any database row
            Exception: Database-specific exception if the operation fails.
                      Implementations should document the specific exception types
                      they raise.
        """
        raise NotImplementedError

    @abstractmethod
    def read_feed_posts_by_uris(self, uris: Iterable[str]) -> list[BlueskyFeedPost]:
        """Read feed posts by URIs.

        Args:
            uris: Iterable of post URIs to look up

        Returns:
            List of BlueskyFeedPost models for the given URIs.

        Raises:
            ValueError: If any feed post data is invalid (NULL fields)
            KeyError: If required columns are missing from any database row
            Exception: Database-specific exception if the operation fails.
                      Implementations should document the specific exception types
                      they raise.
        Note:
            This method is used to hydrate generated feeds. Implementations should
            ensure that the post URIs are valid and that the feed posts are returned
            in the same order as the URIs.
        """
        raise NotImplementedError


class GeneratedFeedDatabaseAdapter(ABC):
    """Abstract interface for generated feed database operations.

    This interface is database-agnostic. Currently works with GeneratedFeed.
    Concrete implementations should document the specific exceptions they raise,
    which may be database-specific.
    """

    @abstractmethod
    def write_generated_feed(self, feed: GeneratedFeed) -> None:
        """Write a generated feed to the database.

        Args:
            feed: GeneratedFeed model to write

        Raises:
            Exception: Database-specific exception if constraints are violated or
                      the operation fails. Implementations should document the
                      specific exception types they raise.

        Note:
            This write is idempotent: an existing row with the same composite
            key (agent_handle, run_id, turn_number) may be replaced. Callers can
            safely retry or recompute; duplicate writes do not raise.
            Implementations (e.g. SQLite) may use INSERT OR REPLACE
            (delete+insert semantics).
        """
        raise NotImplementedError

    @abstractmethod
    def read_generated_feed(
        self, agent_handle: str, run_id: str, turn_number: int
    ) -> GeneratedFeed:
        """Read a generated feed by composite key.

        Args:
            agent_handle: Agent handle to look up
            run_id: Run ID to look up
            turn_number: Turn number to look up

        Returns:
            GeneratedFeed model for the specified agent, run, and turn.

        Raises:
            ValueError: If no feed is found for the given composite key
            ValueError: If the feed data is invalid (NULL fields)
            KeyError: If required columns are missing from the database row
            Exception: Database-specific exception if the operation fails.
                      Implementations should document the specific exception types
                      they raise.
        """
        raise NotImplementedError

    @abstractmethod
    def read_all_generated_feeds(self) -> list[GeneratedFeed]:
        """Read all generated feeds.

        Returns:
            List of all GeneratedFeed models. Returns empty list if no feeds exist.

        Raises:
            ValueError: If any feed data is invalid (NULL fields)
            KeyError: If required columns are missing from any database row
            Exception: Database-specific exception if the operation fails.
                      Implementations should document the specific exception types
                      they raise.
        """
        raise NotImplementedError

    @abstractmethod
    def read_post_uris_for_run(self, agent_handle: str, run_id: str) -> set[str]:
        """Read all post URIs from generated feeds for a specific agent and run.

        Args:
            agent_handle: Agent handle to filter by
            run_id: Run ID to filter by

        Returns:
            Set of post URIs from all generated feeds matching the agent and run.
            Returns empty set if no feeds found.

        Raises:
            ValueError: If agent_handle or run_id is empty
            Exception: Database-specific exception if the operation fails.
                      Implementations should document the specific exception types
                      they raise.
        """
        raise NotImplementedError

    @abstractmethod
    def read_feeds_for_turn(self, run_id: str, turn_number: int) -> list[GeneratedFeed]:
        """Read all generated feeds for a specific run and turn.

        Args:
            run_id: The ID of the run
            turn_number: The turn number (0-indexed)

        Returns:
            List of GeneratedFeed models for the specified run and turn.
            Returns empty list if no feeds found.

        Raises:
            ValueError: If the feed data is invalid (NULL fields)
            KeyError: If required columns are missing from the database row
            Exception: Database-specific exception if the operation fails.
                      Implementations should document the specific exception types
                      they raise.
        """
        raise NotImplementedError


class GeneratedBioDatabaseAdapter(ABC):
    """Abstract interface for generated bio database operations.

    This interface is database-agnostic. Currently works with GeneratedBio.
    Concrete implementations should document the specific exceptions they raise,
    which may be database-specific.
    """

    @abstractmethod
    def write_generated_bio(self, bio: GeneratedBio) -> None:
        """Write a generated bio to the database.

        Args:
            bio: GeneratedBio model to write

        Raises:
            Exception: Database-specific exception if constraints are violated or
                      the operation fails. Implementations should document the
                      specific exception types they raise.

        Note:
            This write is idempotent: an existing row with the same handle may be
            replaced. Callers can safely retry or recompute; duplicate writes do
            not raise. Implementations (e.g. SQLite) may use INSERT OR REPLACE
            (delete+insert semantics).
        """
        raise NotImplementedError

    @abstractmethod
    def read_generated_bio(self, handle: str) -> GeneratedBio | None:
        """Read a generated bio by handle.

        Args:
            handle: Profile handle to look up

        Returns:
            GeneratedBio model if found, None otherwise.

        Raises:
            ValueError: If the bio data is invalid (NULL fields)
            KeyError: If required columns are missing from the database row
            Exception: Database-specific exception if the operation fails.
                      Implementations should document the specific exception types
                      they raise.
        """
        raise NotImplementedError

    @abstractmethod
    def read_all_generated_bios(self) -> list[GeneratedBio]:
        """Read all generated bios.

        Returns:
            List of all GeneratedBio models. Returns empty list if no bios exist.

        Raises:
            ValueError: If any bio data is invalid (NULL fields)
            KeyError: If required columns are missing from any database row
            Exception: Database-specific exception if the operation fails.
                      Implementations should document the specific exception types
                      they raise.
        """
        raise NotImplementedError


class AgentDatabaseAdapter(ABC):
    """Abstract interface for agent database operations."""

    @abstractmethod
    def write_agent(self, agent: Agent, conn: object | None = None) -> None:
        """Write an agent to the database.

        When conn is provided, use it and do not commit; when None, use a new
        connection and commit.

        Note:
            Idempotent: an existing row with the same agent_id may be replaced.
        """
        raise NotImplementedError

    @abstractmethod
    def read_agent(self, agent_id: str) -> Agent | None:
        """Read an agent by ID."""
        raise NotImplementedError

    @abstractmethod
    def read_agent_by_handle(self, handle: str) -> Agent | None:
        """Read an agent by handle."""
        raise NotImplementedError

    @abstractmethod
    def read_all_agents(self) -> list[Agent]:
        """Read all agents. Returns empty list if none exist."""
        raise NotImplementedError


class AgentBioDatabaseAdapter(ABC):
    """Abstract interface for agent persona bio database operations."""

    @abstractmethod
    def write_agent_bio(self, bio: AgentBio, conn: object | None = None) -> None:
        """Write an agent bio to the database.

        When conn is provided, use it and do not commit; when None, use a new
        connection and commit.
        """
        raise NotImplementedError

    @abstractmethod
    def read_latest_agent_bio(self, agent_id: str) -> AgentBio | None:
        """Read the latest bio for an agent by created_at DESC."""
        raise NotImplementedError

    @abstractmethod
    def read_agent_bios_by_agent_id(self, agent_id: str) -> list[AgentBio]:
        """Read all bios for an agent, ordered by created_at DESC."""
        raise NotImplementedError


class UserAgentProfileMetadataDatabaseAdapter(ABC):
    """Abstract interface for user agent profile metadata database operations."""

    @abstractmethod
    def write_user_agent_profile_metadata(
        self, metadata: UserAgentProfileMetadata, conn: object | None = None
    ) -> None:
        """Write user agent profile metadata.

        When conn is provided, use it and do not commit; when None, use a new
        connection and commit.

        Note:
            Idempotent: an existing row with the same agent_id may be replaced.
        """
        raise NotImplementedError

    @abstractmethod
    def read_by_agent_id(self, agent_id: str) -> UserAgentProfileMetadata | None:
        """Read metadata by agent_id."""
        raise NotImplementedError
