import logging
import time
from typing import Optional

from db.exceptions import (
    DuplicateTurnMetadataError,
    RunNotFoundError,
)
from db.repositories.feed_post_repository import FeedPostRepository
from db.repositories.generated_bio_repository import GeneratedBioRepository
from db.repositories.generated_feed_repository import GeneratedFeedRepository
from db.repositories.profile_repository import ProfileRepository
from db.repositories.run_repository import RunRepository
from feeds.feed_generator import generate_feeds
from lib.utils import get_current_timestamp
from simulation.core.exceptions import InsufficientAgentsError
from simulation.core.models.actions import TurnAction
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.posts import BlueskyFeedPost
from simulation.core.models.runs import Run, RunConfig, RunStatus
from simulation.core.models.turns import TurnData, TurnMetadata, TurnResult

logger = logging.getLogger(__name__)


class SimulationEngine:
    """Orchestrates simulation execution and provides query methods for UI/API.

    This class serves two purposes:
    1. **Execution**: Runs simulations via `execute_run()` and related methods
    2. **Query**: Provides read-only methods (`get_*`, `list_*`) for UI/API consumption

    Query methods (e.g., `get_turn_data()`, `get_turn_metadata()`) are not used
    during simulation execution but are consumed by the FastAPI backend layer.

    Currently, we decide to couple query and execution methods in the same class
    because the implementation is simple and premature abstraction right now
    leads to a lot of duplication of code.
    """

    def __init__(
        self,
        run_repo: RunRepository,
        profile_repo: ProfileRepository,
        feed_post_repo: FeedPostRepository,
        generated_bio_repo: GeneratedBioRepository,
        generated_feed_repo: GeneratedFeedRepository,
    ):
        self.run_repo = run_repo
        self.profile_repo = profile_repo
        self.feed_post_repo = feed_post_repo
        self.generated_bio_repo = generated_bio_repo
        self.generated_feed_repo = generated_feed_repo

    ## Public API ##

    def execute_run(self, run_config: RunConfig) -> Run:
        """Execute a simulation run.

        Args:
            run_config: The configuration for the run.

        Returns:
            The run that was executed.
        """
        run: Run = self.run_repo.create_run(run_config)
        agents: list[SocialMediaAgent] = self._create_agents_for_run(
            run_config, run.run_id
        )

        for turn_number in range(run.total_turns):
            self._simulate_turn(
                run.run_id,
                turn_number,
                agents,
                run_config.feed_algorithm,
            )

        self._update_run_status_safely(run.run_id, RunStatus.COMPLETED)
        return run

    def get_run(self, run_id: str) -> Optional[Run]:
        """Get a run by its ID.

        Args:
            run_id: The ID of the run to get.

        Returns:
            The run if found, None otherwise.
        """
        if not run_id or not run_id.strip():
            raise ValueError("run_id cannot be empty")
        return self.run_repo.get_run(run_id)

    def list_runs(self) -> list[Run]:
        """List all runs.

        Returns:
            A list of all runs.
        """
        return self.run_repo.list_runs()

    def get_turn_metadata(
        self, run_id: str, turn_number: int
    ) -> Optional[TurnMetadata]:
        """Get turn metadata for a specific run and turn number.

        Args:
            run_id: The ID of the run.
            turn_number: The turn number (0-indexed).

        Returns:
            The turn metadata if found, None otherwise.
        """
        if not run_id or not run_id.strip():
            raise ValueError("run_id cannot be empty")
        if turn_number is None or turn_number < 0:
            raise ValueError("turn_number cannot be negative")
        return self.run_repo.get_turn_metadata(run_id, turn_number)

    def get_turn_data(self, run_id: str, turn_number: int) -> Optional[TurnData]:
        """Returns full turn data with feeds and posts.

        This is a read-only query method for UI/API consumption. It reads
        pre-computed feeds from the database that were written by `generate_feeds()`
        during simulation execution. This method is NOT used during simulation execution.

        Args:
            run_id: The ID of the run.
            turn_number: The turn number (0-indexed).

        Returns:
            Complete turn data including all feeds and hydrated posts.
            Returns None if the turn doesn't exist (no feeds found).
            Used in the UI for detailed views or full turn history.

        Raises:
            ValueError: If run_id is empty or turn_number is negative.
            RunNotFoundError: If the run with the given run_id does not exist.
        """
        if not run_id or not run_id.strip():
            raise ValueError("run_id cannot be empty")
        if turn_number is None or turn_number < 0:
            raise ValueError("turn_number cannot be negative")

        # Check run exists
        run = self.run_repo.get_run(run_id)
        if run is None:
            raise RunNotFoundError(run_id)

        # Query feeds for this turn
        feeds = self.generated_feed_repo.read_feeds_for_turn(run_id, turn_number)
        if not feeds:
            # No feeds means turn doesn't exist
            return None

        # Collect all post URIs from all feeds
        post_uris_set: set[str] = set()
        for feed in feeds:
            post_uris_set.update(feed.post_uris)

        # Batch load posts
        post_uris_list = list(post_uris_set)
        posts = self.feed_post_repo.read_feed_posts_by_uris(post_uris_list)

        # Build URI to post mapping for efficient lookup
        uri_to_post = {post.uri: post for post in posts}

        # Build feeds dict: {agent_handle: [BlueskyFeedPost, ...]}
        feeds_dict: dict[str, list] = {}
        for feed in feeds:
            hydrated_posts = []
            for post_uri in feed.post_uris:
                if post_uri in uri_to_post:
                    hydrated_posts.append(uri_to_post[post_uri])
                # Skip missing posts silently (may have been deleted after feed generation)
            feeds_dict[feed.agent_handle] = hydrated_posts

        # Construct TurnData
        return TurnData(
            turn_number=turn_number,
            agents=[],  # TODO: Agents not stored yet, will be populated when agent storage is added
            feeds=feeds_dict,  # May be empty if all posts missing, but turn exists
            actions={},  # TODO: Actions not stored yet
        )

    ## Private Methods ##

    def _simulate_turn(
        self,
        run_id: str,
        turn_number: int,
        agents: list[SocialMediaAgent],
        feed_algorithm: str,
    ) -> TurnResult:
        """Simulate a single turn of the simulation.

        Args:
            run_id: The ID of the run.
            turn_number: The turn number (0-indexed).
            agents: The list of agents participating in the turn.
            feed_algorithm: The algorithm to use for generating feeds.

        Returns:
            The result of the turn execution.

        Raises:
            RunNotFoundError: If the run doesn't exist.
            ValueError: If duplicate likes are detected or unknown action type.
        """
        # Start execution timer
        start_time = time.time()

        # Validate run exists
        run = self.run_repo.get_run(run_id)
        if run is None:
            raise RunNotFoundError(run_id)

        # Generate feeds
        agent_to_hydrated_feeds: dict[str, list[BlueskyFeedPost]] = generate_feeds(
            agents=agents,
            run_id=run_id,
            turn_number=turn_number,
            generated_feed_repo=self.generated_feed_repo,
            feed_post_repo=self.feed_post_repo,
            feed_algorithm=feed_algorithm,
        )

        # Handle empty/missing feeds gracefully
        empty_feed_count = 0
        for agent in agents:
            feed = agent_to_hydrated_feeds.get(agent.handle, [])
            if not feed:
                empty_feed_count += 1
                logger.warning(
                    f"Empty feed for agent {agent.handle} in run {run_id}, turn {turn_number}"
                )

        # Log systemic issue if >25% of feeds are empty
        if agents and (empty_feed_count / len(agents)) > 0.25:
            logger.warning(
                f"Systemic issue: {empty_feed_count}/{len(agents)} feeds are empty "
                f"for run {run_id}, turn {turn_number}"
            )

        # Initialize action tracking
        total_actions: dict[str, int] = {
            "likes": 0,
            "comments": 0,
            "follows": 0,
        }
        all_actions: dict[str, list] = {
            "likes": [],
            "comments": [],
            "follows": [],
        }

        # Loop through agents and execute actions
        for agent in agents:
            feed = agent_to_hydrated_feeds.get(agent.handle, [])

            # Skip agent if feed is empty
            if not feed:
                continue

            # Execute actions
            likes = agent.like_posts(feed)
            comments = agent.comment_posts(feed)
            follows = agent.follow_users(feed)

            # Validate actions: check for duplicate likes
            liked_uris = {like.like.post_id for like in likes}
            if len(liked_uris) != len(likes):
                # Find duplicates
                seen_uris = set()
                duplicates = []
                for like in likes:
                    post_id = like.like.post_id
                    if post_id in seen_uris:
                        duplicates.append(post_id)
                    seen_uris.add(post_id)
                raise ValueError(
                    f"Agent {agent.handle} liked the same post multiple times "
                    f"in run {run_id}, turn {turn_number}. Duplicate post URIs: {duplicates}"
                )

            # Store individual actions (for future storage)
            all_actions["likes"].extend(likes)
            all_actions["comments"].extend(comments)
            all_actions["follows"].extend(follows)

            # Accumulate totals
            total_actions["likes"] += len(likes)
            total_actions["comments"] += len(comments)
            total_actions["follows"] += len(follows)

        # Convert total_actions to dict[TurnAction, int] format
        converted_actions = self._convert_action_counts_to_enum(total_actions)

        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)

        # Create and write turn metadata
        turn_metadata = TurnMetadata(
            run_id=run_id,
            turn_number=turn_number,
            total_actions=converted_actions,
            created_at=get_current_timestamp(),
        )

        # Write turn metadata (handle duplicates gracefully)
        try:
            self.run_repo.write_turn_metadata(turn_metadata)
        except DuplicateTurnMetadataError as e:
            logger.warning(
                f"Turn metadata already exists for run {run_id}, turn {turn_number}. "
                f"This may indicate a retry or duplicate execution. Error: {e}"
            )
            # Don't re-raise - this is acceptable for idempotency

        # Return turn result
        return TurnResult(
            turn_number=turn_number,
            total_actions=converted_actions,
            execution_time_ms=execution_time_ms,
        )

    def _create_agents_for_run(
        self, config: RunConfig, run_id: str | None = None
    ) -> list[SocialMediaAgent]:
        """Create agents for a simulation run.

        Args:
            config: The run configuration.
            run_id: Optional. The ID of the run for error context.

        Returns:
            A list of agents for the run.

        Raises:
            InsufficientAgentsError: If fewer agents than requested are available.
            ValueError: If agent handles are not unique.
        """
        # TODO: Refactor to use injected agent_factory in PR 9
        from ai.create_initial_agents import create_initial_agents

        # Create all available agents
        all_agents = create_initial_agents()

        # Apply limit
        agents = all_agents[: config.num_agents]

        # Validate agent count
        if len(agents) < config.num_agents:
            raise InsufficientAgentsError(
                requested=config.num_agents,
                available=len(agents),
                run_id=run_id,
            )

        # Validate agent uniqueness
        handles = [agent.handle for agent in agents]
        if len(handles) != len(set(handles)):
            duplicates = [h for h in handles if handles.count(h) > 1]
            raise ValueError(
                f"Duplicate agent handles found: {set(duplicates)}. "
                "All agent handles must be unique."
            )

        logger.info(
            "Created %d agents (requested: %d) for run %s",
            len(agents),
            config.num_agents,
            run_id or "(no run_id)",
        )
        )

        return agents

    def _convert_action_counts_to_enum(
        self, action_counts: dict[str, int]
    ) -> dict[TurnAction, int]:
        """Convert action counts from string keys to TurnAction enum keys.

        Args:
            action_counts: Dictionary with string keys ("likes", "comments", "follows").

        Returns:
            Dictionary with TurnAction enum keys.

        Raises:
            ValueError: If unknown action type encountered.
        """
        converted: dict[TurnAction, int] = {}

        # Map string keys to enum
        mapping = {
            "likes": TurnAction.LIKE,
            "comments": TurnAction.COMMENT,
            "follows": TurnAction.FOLLOW,
        }

        # Validate all TurnAction enum values are represented
        all_enum_values = set(TurnAction)
        mapped_values = set(mapping.values())
        if all_enum_values != mapped_values:
            missing = all_enum_values - mapped_values
            raise ValueError(
                f"Missing mapping for TurnAction enum values: {missing}. "
                "All enum values must be mapped."
            )

        # Convert
        for key, count in action_counts.items():
            if key not in mapping:
                raise ValueError(f"Unknown action type: {key}")
            converted[mapping[key]] = count

        return converted

    def _update_run_status_safely(self, run_id: str, status: RunStatus) -> None:
        """Update run status without masking original exceptions.

        This is a best-effort status update method that never raises exceptions.
        It's designed for use in error handling paths where you want to update
        the run status (e.g., to FAILED) but don't want status update failures
        to mask the original exception.

        Args:
            run_id: The ID of the run.
            status: The new status.
        """
        try:
            self.run_repo.update_run_status(run_id, status)
        except Exception as e:
            logger.warning(f"Failed to update run {run_id} status to {status}: {e}")
