from db.repositories.interfaces import (
    FeedPostRepository,
    GeneratedFeedRepository,
    RunRepository,
)
from simulation.core.exceptions import RunNotFoundError
from simulation.core.models.posts import BlueskyFeedPost
from simulation.core.models.runs import Run
from simulation.core.models.turns import TurnData, TurnMetadata
from simulation.core.validators import validate_run_id, validate_turn_number


class SimulationQueryService:
    """Query service for retrieving simulation run and turn data."""

    def __init__(
        self,
        run_repo: RunRepository,
        feed_post_repo: FeedPostRepository,
        generated_feed_repo: GeneratedFeedRepository,
    ):
        self.run_repo = run_repo
        self.feed_post_repo = feed_post_repo
        self.generated_feed_repo = generated_feed_repo

    def get_run(self, run_id: str) -> Run | None:
        """Get a run by its ID."""
        validate_run_id(run_id)
        return self.run_repo.get_run(run_id)

    def list_runs(self) -> list[Run]:
        """List all runs."""
        return self.run_repo.list_runs()

    def get_turn_metadata(self, run_id: str, turn_number: int) -> TurnMetadata | None:
        """Get turn metadata for a specific run and turn number."""
        validate_run_id(run_id)
        validate_turn_number(turn_number)
        return self.run_repo.get_turn_metadata(run_id, turn_number)

    def list_turn_metadata(self, run_id: str) -> list[TurnMetadata]:
        """List all turn metadata for a run in turn order."""
        validate_run_id(run_id)
        metadata_list: list[TurnMetadata] = self.run_repo.list_turn_metadata(
            run_id=run_id
        )
        return sorted(metadata_list, key=lambda metadata: metadata.turn_number)

    def get_turn_data(self, run_id: str, turn_number: int) -> TurnData | None:
        """Returns full turn data with feeds and posts."""
        validate_run_id(run_id)
        validate_turn_number(turn_number)

        run = self.run_repo.get_run(run_id)
        if run is None:
            raise RunNotFoundError(run_id)

        feeds = self.generated_feed_repo.read_feeds_for_turn(run_id, turn_number)
        if not feeds:
            return None

        post_uris_set: set[str] = set()
        for feed in feeds:
            post_uris_set.update(feed.post_uris)

        post_uris_list = list(post_uris_set)
        posts = self.feed_post_repo.read_feed_posts_by_uris(post_uris_list)

        uri_to_post = {post.uri: post for post in posts}

        feeds_dict: dict[str, list[BlueskyFeedPost]] = {}
        for feed in feeds:
            hydrated_posts = []
            for post_uri in feed.post_uris:
                if post_uri in uri_to_post:
                    hydrated_posts.append(uri_to_post[post_uri])
            feeds_dict[feed.agent_handle] = hydrated_posts

        return TurnData(
            turn_number=turn_number,
            agents=[],
            feeds=feeds_dict,
            actions={},
        )
