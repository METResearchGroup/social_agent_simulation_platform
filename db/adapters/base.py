"""Base adapter interfaces."""

from abc import ABC, abstractmethod
from typing import Iterable, Optional

from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.generated.bio import GeneratedBio
from simulation.core.models.posts import BlueskyFeedPost
from simulation.core.models.profiles import BlueskyProfile
from simulation.core.models.runs import Run
from simulation.core.models.turns import TurnMetadata


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
        """
        raise NotImplementedError

    @abstractmethod
    def read_run(self, run_id: str) -> Optional[Run]:
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
        self, run_id: str, status: str, completed_at: Optional[str] = None
    ) -> None:
        """Update a run's status.

        Args:
            run_id: Unique identifier for the run to update
            status: New status value (should be a valid RunStatus enum value as string)
            completed_at: Optional timestamp when the run was completed.
                         Should be set when status is 'completed', None otherwise.

        Raises:
            RunNotFoundError: If no run exists with the given run_id
            Exception: Database-specific exception if constraints are violated or
                      the operation fails. Implementations should document the
                      specific exception types they raise.
        """
        raise NotImplementedError

    @abstractmethod
    def read_turn_metadata(
        self, run_id: str, turn_number: int
    ) -> Optional[TurnMetadata]:
        """Read turn metadata for a specific run and turn.

        Args:
            run_id: The ID of the run
            turn_number: The turn number (0-indexed)

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
    def write_turn_metadata(self, turn_metadata: TurnMetadata) -> None:
        """Write turn metadata to the database.

        Writes to the `turn_metadata` table. Uses INSERT.

        Args:
            turn_metadata: TurnMetadata model to write

        Raises:
            DuplicateTurnMetadataError: If turn metadata already exists
            Exception: Database-specific exception if constraints are violated or
                      the operation fails. Implementations should document the
                      specific exception types they raise.
        """
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
        """
        raise NotImplementedError

    @abstractmethod
    def read_profile(self, handle: str) -> Optional[BlueskyProfile]:
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
        """
        raise NotImplementedError

    @abstractmethod
    def read_generated_bio(self, handle: str) -> Optional[GeneratedBio]:
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
