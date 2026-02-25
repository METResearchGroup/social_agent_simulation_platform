from __future__ import annotations

from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.posts import BlueskyFeedPost
from tests.factories.base import BaseFactory
from tests.factories.context import get_faker


class AgentFactory(BaseFactory[SocialMediaAgent]):
    @classmethod
    def create(
        cls,
        *,
        handle: str | None = None,
        posts: list[BlueskyFeedPost] | None = None,
        followers: int | None = None,
        following: int | None = None,
        posts_count: int | None = None,
    ) -> SocialMediaAgent:
        fake = get_faker()
        agent = SocialMediaAgent(
            handle=handle if handle is not None else f"{fake.user_name()}.bsky.social"
        )
        if posts is not None:
            agent.posts = list(posts)
        if followers is not None:
            agent.followers = followers
        if following is not None:
            agent.following = following
        if posts_count is not None:
            agent.posts_count = posts_count
        return agent
