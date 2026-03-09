from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.posts import Post


class SocialMediaAgent:
    def __init__(self, handle: str):
        self.handle: str = handle
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
        return GeneratedFeed(
            feed_id=GeneratedFeed.generate_feed_id(),
            run_id=run_id,
            turn_number=turn_number,
            agent_handle=self.handle,
            post_ids=[],
            created_at=created_at,
        )
