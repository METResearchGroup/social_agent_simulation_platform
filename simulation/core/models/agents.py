from simulation.core.models.feeds import GeneratedFeed
from simulation.core.models.generated.comment import GeneratedComment
from simulation.core.models.generated.follow import GeneratedFollow
from simulation.core.models.generated.like import GeneratedLike
from simulation.core.models.posts import BlueskyFeedPost


class SocialMediaAgent:
    def __init__(self, handle: str):
        self.handle: str = handle
        self.bio: str = ""
        self.generated_bio: str = ""
        self.followers: int = 0
        self.following: int = 0
        self.posts_count: int = 0
        self.posts: list[BlueskyFeedPost] = []
        self.likes: list[GeneratedLike] = []
        self.comments: list[GeneratedComment] = []
        self.follows: list[GeneratedFollow] = []

    def get_feed(self, run_id: str, turn_number: int = 0) -> GeneratedFeed:
        """Get a feed for this agent.

        Args:
            run_id: The ID of the simulation run (required for validation)
            turn_number: The turn number for this feed (default: 0)

        Returns:
            A GeneratedFeed instance for this agent
        """
        from lib.utils import get_current_timestamp

        return GeneratedFeed(
            feed_id=GeneratedFeed.generate_feed_id(),
            run_id=run_id,
            turn_number=turn_number,
            agent_handle=self.handle,
            post_uris=[],
            created_at=get_current_timestamp(),
        )

    def like_posts(self, feed: list[BlueskyFeedPost]) -> list[GeneratedLike]:
        if len(feed) == 0:
            print("[No-op for now] No posts to like.")
            return []
        return []

    def comment_posts(self, feed: list[BlueskyFeedPost]) -> list[GeneratedComment]:
        if len(feed) == 0:
            print("[No-op for now] No posts to comment on.")
            return []
        return []

    def follow_users(self, feed: list[BlueskyFeedPost]) -> list[GeneratedFollow]:
        if len(feed) == 0:
            print("[No-op for now] No users to follow.")
        return []
