from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.posts import Post


class SimulationAgent:
    """The in-memory runtime object used during simulation turns. It carries
    hydrated profile/runtime state and mutable per-run collections like posts
    and generated actions."""

    def __init__(
        self,
        handle: str,
        *,
        agent_id: str | None = None,
        display_name: str | None = None,
    ):
        self.handle: str = handle
        # Immutable seed identity fields (when hydrated from seed catalog).
        self.agent_id: str | None = agent_id
        self.display_name: str | None = display_name
        self.bio: str = ""
        self.generated_bio: str = ""
        self.followers: int = 0
        self.following: int = 0
        self.posts_count: int = 0
        self.posts: list[Post] = []
        self.likes: list[GeneratedLike] = []
        self.comments: list[GeneratedComment] = []
        self.follows: list[GeneratedFollow] = []

    def get_feed(
        self, run_id: str, turn_number: int = 0, *, created_at: str
    ) -> GeneratedFeed:
        """Get a feed for this agent.

        Args:
            run_id: The ID of the simulation run (required for validation)
            turn_number: The turn number for this feed (default: 0)
            created_at: Timestamp for the feed (caller supplies; use lib.timestamp_utils in app layer).

        Returns:
            A GeneratedFeed instance for this agent
        """
        if self.agent_id is None:
            raise ValueError(
                "SimulationAgent.agent_id must be set to build a GeneratedFeed"
            )
        return GeneratedFeed(
            feed_id=GeneratedFeed.generate_feed_id(),
            run_id=run_id,
            turn_number=turn_number,
            agent_id=self.agent_id,
            agent_handle=self.handle,
            post_ids=[],
            created_at=created_at,
        )
