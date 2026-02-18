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
            post_uris=[],
            created_at=created_at,
        )

    def like_posts(
        self,
        feed: list[BlueskyFeedPost],
        *,
        run_id: str,
        turn_number: int,
    ) -> list[GeneratedLike]:
        """Generate likes from feed using the configured like generator."""
        if not feed:
            return []
        from simulation.core.action_generators import get_like_generator

        generator = get_like_generator()
        return generator.generate(
            candidates=feed,
            run_id=run_id,
            turn_number=turn_number,
            agent_handle=self.handle,
        )

    def comment_posts(
        self,
        feed: list[BlueskyFeedPost],
        *,
        run_id: str,
        turn_number: int,
    ) -> list[GeneratedComment]:
        """Generate comments from feed using the configured comment generator."""
        if not feed:
            return []
        from simulation.core.action_generators import get_comment_generator

        generator = get_comment_generator()
        return generator.generate(
            candidates=feed,
            run_id=run_id,
            turn_number=turn_number,
            agent_handle=self.handle,
        )

    def follow_users(self, feed: list[BlueskyFeedPost]) -> list[GeneratedFollow]:
        if len(feed) == 0:
            print("[No-op for now] No users to follow.")
        return []
