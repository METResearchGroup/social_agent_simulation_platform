import logging
from typing import Optional

from db.exceptions import RunNotFoundError, RunStatusUpdateError
from db.repositories.feed_post_repository import FeedPostRepository
from db.repositories.generated_bio_repository import GeneratedBioRepository
from db.repositories.generated_feed_repository import GeneratedFeedRepository
from db.repositories.profile_repository import ProfileRepository
from db.repositories.run_repository import RunRepository
from simulation.core.models.agents import SocialMediaAgent
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
        agents: list[SocialMediaAgent] = self._create_agents_for_run(run_config)

        for turn_number in range(run.total_turns):
            turn_result: TurnResult = self._simulate_turn(run.run_id, turn_number, agents)
            self._write_turn_result(turn_result)

        self._update_run_status_safely(run.run_id, RunStatus.COMPLETED)

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
        self, run_id: str, turn_number: int, agents: list[SocialMediaAgent]
    ) -> TurnResult:
        """Simulate a single turn of the simulation.

        Args:
            run_id: The ID of the run.
            turn_number: The turn number (0-indexed).
            agents: The list of agents participating in the turn.

        Returns:
            The result of the turn execution.
        """
        raise NotImplementedError  # Stub for PR 1

    def _create_agents_for_run(self, config: RunConfig) -> list[SocialMediaAgent]:
        """Create agents for a simulation run.

        Args:
            config: The run configuration.

        Returns:
            A list of agents for the run.
        """
        raise NotImplementedError  # Stub for PR 1

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
