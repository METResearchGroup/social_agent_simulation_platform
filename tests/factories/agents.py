from __future__ import annotations

from lib.agent_id import canonical_agent_id
from simulation.core.models.agents import SimulationAgent
from simulation.core.models.posts import Post
from tests.factories.base import BaseFactory
from tests.factories.context import get_faker


class AgentFactory(BaseFactory[SimulationAgent]):
    @classmethod
    def create(
        cls,
        *,
        handle: str | None = None,
        posts: list[Post] | None = None,
        followers: int | None = None,
        following: int | None = None,
        posts_count: int | None = None,
    ) -> SimulationAgent:
        fake = get_faker()
        resolved_handle = (
            handle if handle is not None else f"{fake.user_name()}.bsky.social"
        )
        agent = SimulationAgent(
            handle=resolved_handle,
            agent_id=canonical_agent_id(resolved_handle),
        )
        if posts is not None:
            agent.posts = list(posts)
            if posts_count is None:
                agent.posts_count = len(agent.posts)
        if followers is not None:
            agent.followers = followers
        if following is not None:
            agent.following = following
        if posts_count is not None:
            agent.posts_count = posts_count
        return agent
