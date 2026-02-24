"""Repository interfaces.

Abstract repository port definitions live here, close to but decoupled from
implementations in this package. Concrete implementations (e.g. SQLite*)
implement these interfaces.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable

from simulation.core.models.agent import Agent
from simulation.core.models.agent_bio import AgentBio
from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.generated.bio import GeneratedBio
from simulation.core.models.metrics import RunMetrics, TurnMetrics
from simulation.core.models.posts import BlueskyFeedPost
from simulation.core.models.profiles import BlueskyProfile
from simulation.core.models.runs import Run, RunConfig, RunStatus
from simulation.core.models.turns import TurnMetadata
from simulation.core.models.user_agent_profile_metadata import UserAgentProfileMetadata


class AgentRepository(ABC):
    """Abstract base class defining the interface for agent repositories."""

    @abstractmethod
    def create_or_update_agent(self, agent: Agent, conn: object | None = None) -> Agent:
        """Create or update an agent."""
        raise NotImplementedError

    @abstractmethod
    def get_agent(self, agent_id: str) -> Agent | None:
        """Get an agent by ID."""
        raise NotImplementedError

    @abstractmethod
    def get_agent_by_handle(self, handle: str) -> Agent | None:
        """Get an agent by handle."""
        raise NotImplementedError

    @abstractmethod
    def list_all_agents(self) -> list[Agent]:
        """List all agents, ordered by handle for deterministic output."""
        raise NotImplementedError


class AgentBioRepository(ABC):
    """Abstract base class defining the interface for agent bio repositories."""

    @abstractmethod
    def create_agent_bio(self, bio: AgentBio, conn: object | None = None) -> AgentBio:
        """Create an agent bio."""
        raise NotImplementedError

    @abstractmethod
    def get_latest_agent_bio(self, agent_id: str) -> AgentBio | None:
        """Get the latest bio for an agent."""
        raise NotImplementedError

    @abstractmethod
    def list_agent_bios(self, agent_id: str) -> list[AgentBio]:
        """List all bios for an agent, ordered by created_at DESC."""
        raise NotImplementedError

    @abstractmethod
    def get_latest_bios_by_agent_ids(
        self, agent_ids: Iterable[str]
    ) -> dict[str, AgentBio | None]:
        """Return the latest bio per agent_id for the given agent IDs.

        Keys are agent_ids; value is the latest AgentBio or None if none exists.
        Missing agent_ids are omitted; caller should treat absence as None.
        """
        raise NotImplementedError


class UserAgentProfileMetadataRepository(ABC):
    """Abstract base class defining the interface for user agent profile metadata repositories."""

    @abstractmethod
    def create_or_update_metadata(
        self, metadata: UserAgentProfileMetadata, conn: object | None = None
    ) -> UserAgentProfileMetadata:
        """Create or update user agent profile metadata."""
        raise NotImplementedError

    @abstractmethod
    def get_by_agent_id(self, agent_id: str) -> UserAgentProfileMetadata | None:
        """Get metadata by agent_id."""
        raise NotImplementedError

    @abstractmethod
    def get_metadata_by_agent_ids(
        self, agent_ids: Iterable[str]
    ) -> dict[str, UserAgentProfileMetadata | None]:
        """Return metadata per agent_id for the given agent IDs.

        Keys are agent_ids; value is metadata or None if none exists.
        """
        raise NotImplementedError


class RunRepository(ABC):
    """Abstract base class defining the interface for run repositories."""

    @abstractmethod
    def create_run(self, config: RunConfig) -> Run:
        """Create a new run."""
        raise NotImplementedError

    @abstractmethod
    def get_run(self, run_id: str) -> Run | None:
        """Get a run by ID."""
        raise NotImplementedError

    @abstractmethod
    def list_runs(self) -> list[Run]:
        """List all runs."""
        raise NotImplementedError

    @abstractmethod
    def update_run_status(
        self,
        run_id: str,
        status: RunStatus,
        conn: object | None = None,
    ) -> None:
        """Update a run's status.

        Raises:
            RunNotFoundError: If the run with the given ID does not exist
            InvalidTransitionError: If the status transition is invalid
            RunStatusUpdateError: If the status update fails due to a database error
        """
        raise NotImplementedError

    @abstractmethod
    def get_turn_metadata(self, run_id: str, turn_number: int) -> TurnMetadata | None:
        """Get turn metadata for a specific run and turn.

        Args:
            run_id: The ID of the run
            turn_number: The turn number (0-indexed)

        Returns:
            TurnMetadata if found, None otherwise

        Raises:
            ValueError: If run_id is empty or turn_number is negative
        """
        raise NotImplementedError

    @abstractmethod
    def list_turn_metadata(self, run_id: str) -> list[TurnMetadata]:
        """List all turn metadata for a run in turn order.

        Args:
            run_id: The ID of the run

        Returns:
            List of TurnMetadata ordered by turn_number ascending.
            Returns empty list if no metadata exists for this run.

        Raises:
            ValueError: If run_id is empty
        """
        raise NotImplementedError

    @abstractmethod
    def write_turn_metadata(
        self,
        turn_metadata: TurnMetadata,
        conn: object | None = None,
    ) -> None:
        """Write turn metadata to the database.

        Args:
            turn_metadata: TurnMetadata model to write

        Raises:
            ValueError: If turn_metadata is invalid
            DuplicateTurnMetadataError: If turn metadata already exists
        """
        raise NotImplementedError


class MetricsRepository(ABC):
    """Abstract base class defining the interface for metrics repositories."""

    @abstractmethod
    def write_turn_metrics(
        self,
        turn_metrics: TurnMetrics,
        conn: object | None = None,
    ) -> None:
        """Write computed metrics for a specific run/turn.

        Note:
            This write is idempotent: an existing row with the same (run_id,
            turn_number) may be replaced. Callers can safely retry or recompute;
            duplicate writes do not raise. Implementations (e.g. SQLite) may use
            INSERT OR REPLACE (delete+insert semantics).
        """
        raise NotImplementedError

    @abstractmethod
    def get_turn_metrics(self, run_id: str, turn_number: int) -> TurnMetrics | None:
        """Get computed metrics for a specific run/turn."""
        raise NotImplementedError

    @abstractmethod
    def list_turn_metrics(self, run_id: str) -> list[TurnMetrics]:
        """List computed metrics for a run in turn order."""
        raise NotImplementedError

    @abstractmethod
    def write_run_metrics(
        self,
        run_metrics: RunMetrics,
        conn: object | None = None,
    ) -> None:
        """Write computed metrics for a run.

        Note:
            This write is idempotent: an existing row with the same run_id may be
            replaced. Callers can safely retry or recompute; duplicate writes do
            not raise. Implementations (e.g. SQLite) may use INSERT OR REPLACE
            (delete+insert semantics).
        """
        raise NotImplementedError

    @abstractmethod
    def get_run_metrics(self, run_id: str) -> RunMetrics | None:
        """Get computed metrics for a run."""
        raise NotImplementedError


class ProfileRepository(ABC):
    """Abstract base class defining the interface for profile repositories."""

    @abstractmethod
    def create_or_update_profile(self, profile: BlueskyProfile) -> BlueskyProfile:
        """Create or update a profile.

        Args:
            profile: BlueskyProfile model to create or update

        Returns:
            The created or updated BlueskyProfile object
        """
        raise NotImplementedError

    @abstractmethod
    def get_profile(self, handle: str) -> BlueskyProfile | None:
        """Get a profile by handle.

        Args:
            handle: Profile handle to look up

        Returns:
            BlueskyProfile model if found, None otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def list_profiles(self) -> list[BlueskyProfile]:
        """List all profiles.

        Returns:
            List of all BlueskyProfile models.
        """
        raise NotImplementedError


class FeedPostRepository(ABC):
    """Abstract base class defining the interface for feed post repositories."""

    @abstractmethod
    def create_or_update_feed_post(self, post: BlueskyFeedPost) -> BlueskyFeedPost:
        """Create or update a feed post.

        Args:
            post: BlueskyFeedPost model to create or update

        Returns:
            The created or updated BlueskyFeedPost object
        """
        raise NotImplementedError

    @abstractmethod
    def create_or_update_feed_posts(
        self, posts: list[BlueskyFeedPost]
    ) -> list[BlueskyFeedPost]:
        """Create or update multiple feed posts (batch operation).

        Args:
            posts: List of BlueskyFeedPost models to create or update

        Returns:
            List of created or updated BlueskyFeedPost objects
        """
        raise NotImplementedError

    @abstractmethod
    def get_feed_post(self, uri: str) -> BlueskyFeedPost:
        """Get a feed post by URI.

        Args:
            uri: Post URI to look up

        Returns:
            BlueskyFeedPost model if found.

        Raises:
            ValueError: If uri is empty or if no feed post is found for the given URI
        """
        raise NotImplementedError

    @abstractmethod
    def list_feed_posts_by_author(self, author_handle: str) -> list[BlueskyFeedPost]:
        """List all feed posts by a specific author.

        Args:
            author_handle: Author handle to filter by

        Returns:
            List of BlueskyFeedPost models for the author.
        """
        raise NotImplementedError

    @abstractmethod
    def list_all_feed_posts(self) -> list[BlueskyFeedPost]:
        """List all feed posts.

        Returns:
            List of all BlueskyFeedPost models.
        """
        raise NotImplementedError

    @abstractmethod
    def read_feed_posts_by_uris(self, uris: Iterable[str]) -> list[BlueskyFeedPost]:
        """Read feed posts by URIs.

        Args:
            uris: Iterable of post URIs to look up

        Returns:
            List of BlueskyFeedPost models for the given URIs.
            Returns empty list if no URIs provided or if no posts found.
            Missing URIs are silently skipped (only existing posts are returned).
        """
        raise NotImplementedError


class GeneratedFeedRepository(ABC):
    """Abstract base class defining the interface for generated feed repositories."""

    @abstractmethod
    def write_generated_feed(self, feed: GeneratedFeed) -> GeneratedFeed:
        """Write a generated feed (insert or replace by composite key).

        Args:
            feed: GeneratedFeed model to create or update

        Returns:
            The created or updated GeneratedFeed object

        Note:
            This write is idempotent: an existing row with the same composite
            key (agent_handle, run_id, turn_number) may be replaced. Callers can
            safely retry or recompute; duplicate writes do not raise.
            Implementations (e.g. SQLite) may use INSERT OR REPLACE
            (delete+insert semantics).
        """
        raise NotImplementedError

    @abstractmethod
    def get_generated_feed(
        self, agent_handle: str, run_id: str, turn_number: int
    ) -> GeneratedFeed:
        """Get a generated feed by composite key.

        Args:
            agent_handle: Agent handle to look up
            run_id: Run ID to look up
            turn_number: Turn number to look up

        Returns:
            GeneratedFeed model for the specified agent, run, and turn.

        Raises:
            ValueError: If no feed is found for the given composite key
        """
        raise NotImplementedError

    @abstractmethod
    def list_all_generated_feeds(self) -> list[GeneratedFeed]:
        """List all generated feeds.

        Returns:
            List of all GeneratedFeed models.
        """
        raise NotImplementedError

    @abstractmethod
    def get_post_uris_for_run(self, agent_handle: str, run_id: str) -> set[str]:
        """Get all post URIs from generated feeds for a specific agent and run.

        Args:
            agent_handle: Agent handle to filter by
            run_id: Run ID to filter by

        Returns:
            Set of post URIs from all generated feeds matching the agent and run.
            Returns empty set if no feeds found.

        Raises:
            ValueError: If agent_handle or run_id is empty
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
        """
        raise NotImplementedError


class GeneratedBioRepository(ABC):
    """Abstract base class defining the interface for generated bio repositories."""

    @abstractmethod
    def create_or_update_generated_bio(self, bio: GeneratedBio) -> GeneratedBio:
        """Create or update a generated bio.

        Args:
            bio: GeneratedBio model to create or update

        Returns:
            The created or updated GeneratedBio object
        """
        raise NotImplementedError

    @abstractmethod
    def get_generated_bio(self, handle: str) -> GeneratedBio | None:
        """Get a generated bio by handle.

        Args:
            handle: Profile handle to look up

        Returns:
            GeneratedBio model if found, None otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def list_all_generated_bios(self) -> list[GeneratedBio]:
        """List all generated bios.

        Returns:
            List of all GeneratedBio models.
        """
        raise NotImplementedError
