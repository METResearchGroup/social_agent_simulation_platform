"""Build simulation agents from the seed-state agent catalog."""

from db.repositories.interfaces import (
    AgentBioRepository,
    AgentRepository,
    FeedPostRepository,
    UserAgentProfileMetadataRepository,
)
from simulation.core.models.agent import Agent
from simulation.core.models.agent_bio import AgentBio
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.posts import Post
from simulation.core.models.user_agent_profile_metadata import UserAgentProfileMetadata


def create_initial_agents(
    *,
    agent_repo: AgentRepository,
    agent_bio_repo: AgentBioRepository,
    user_agent_profile_metadata_repo: UserAgentProfileMetadataRepository,
    feed_post_repo: FeedPostRepository,
) -> list[SocialMediaAgent]:
    """Create simulation agents from immutable seed-state records."""
    agent_records: list[Agent] = agent_repo.list_all_agents()
    agent_ids: list[str] = [agent.agent_id for agent in agent_records]
    latest_bios: dict[str, AgentBio | None] = (
        agent_bio_repo.get_latest_bios_by_agent_ids(agent_ids)
    )
    metadata_by_agent_id: dict[str, UserAgentProfileMetadata | None] = (
        user_agent_profile_metadata_repo.get_metadata_by_agent_ids(agent_ids)
    )
    feed_posts: list[Post] = feed_post_repo.list_all_feed_posts()

    handle_to_feed_posts: dict[str, list[Post]] = {}
    for post in feed_posts:
        handle_to_feed_posts.setdefault(post.author_handle, []).append(post)

    agents: list[SocialMediaAgent] = []

    # Build agents from seed state so any later run snapshot can safely FK back
    # to the selected `agent.agent_id` rows.
    for agent_record in agent_records:
        latest_bio = latest_bios.get(agent_record.agent_id)
        if latest_bio is None:
            raise ValueError(
                f"Missing latest agent bio for seed agent {agent_record.agent_id}"
            )

        metadata = metadata_by_agent_id.get(agent_record.agent_id)
        if metadata is None:
            raise ValueError(
                "Missing user agent profile metadata for seed agent "
                f"{agent_record.agent_id}"
            )

        agent = SocialMediaAgent(agent_record.handle)
        agent.bio = latest_bio.persona_bio
        agent.followers = metadata.followers_count
        agent.following = metadata.follows_count
        agent.posts_count = metadata.posts_count
        agent.posts = handle_to_feed_posts.get(agent_record.handle, [])
        agent.likes = []
        agent.comments = []
        agent.follows = []
        agent.generated_bio = ""
        agents.append(agent)
    return agents


if __name__ == "__main__":
    pass
