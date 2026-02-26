"""Given the database of Bluesky profiles and feed posts, create a list of agents."""

from db.adapters.sqlite.sqlite import SqliteTransactionProvider
from db.repositories.agent_bio_repository import create_sqlite_agent_bio_repository
from db.repositories.agent_repository import create_sqlite_agent_repository
from db.repositories.feed_post_repository import create_sqlite_feed_post_repository
from db.repositories.generated_bio_repository import (
    create_sqlite_generated_bio_repository,
)
from db.repositories.profile_repository import create_sqlite_profile_repository
from db.repositories.user_agent_profile_metadata_repository import (
    create_sqlite_user_agent_profile_metadata_repository,
)
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.generated.bio import GeneratedBio
from simulation.core.models.posts import BlueskyFeedPost
from simulation.core.models.profiles import BlueskyProfile


def create_initial_agents() -> list[SocialMediaAgent]:
    """Create a list of agents from the database and pass into the simulation.

    Preference order:
    1) New agent schema (`agent`, `agent_persona_bios`, `user_agent_profile_metadata`)
    2) Legacy Bluesky profiles (`bluesky_profiles`) as a fallback when no agents exist
    """
    tx = SqliteTransactionProvider()
    feed_post_repo = create_sqlite_feed_post_repository(transaction_provider=tx)
    generated_bio_repo = create_sqlite_generated_bio_repository(transaction_provider=tx)
    feed_posts: list[BlueskyFeedPost] = feed_post_repo.list_all_feed_posts()
    generated_bios: list[GeneratedBio] = generated_bio_repo.list_all_generated_bios()

    handle_to_feed_posts: dict[str, list[BlueskyFeedPost]] = {}
    for post in feed_posts:
        handle_to_feed_posts.setdefault(post.author_handle, []).append(post)

    handle_to_generated_bio: dict[str, GeneratedBio] = {
        bio.handle: bio for bio in generated_bios
    }
    agents: list[SocialMediaAgent] = []

    agent_repo = create_sqlite_agent_repository(transaction_provider=tx)
    agent_bio_repo = create_sqlite_agent_bio_repository(transaction_provider=tx)
    metadata_repo = create_sqlite_user_agent_profile_metadata_repository(
        transaction_provider=tx
    )
    persisted_agents = agent_repo.list_all_agents()

    if persisted_agents:
        agent_ids = [a.agent_id for a in persisted_agents]
        bio_map = agent_bio_repo.get_latest_bios_by_agent_ids(agent_ids)
        metadata_map = metadata_repo.get_metadata_by_agent_ids(agent_ids)
        for a in persisted_agents:
            sm_agent = SocialMediaAgent(a.handle)
            latest_bio = bio_map.get(a.agent_id)
            meta = metadata_map.get(a.agent_id)
            sm_agent.bio = latest_bio.persona_bio if latest_bio else ""
            sm_agent.followers = meta.followers_count if meta else 0
            sm_agent.following = meta.follows_count if meta else 0
            sm_agent.posts_count = meta.posts_count if meta else 0
            sm_agent.posts = handle_to_feed_posts.get(a.handle, [])
            sm_agent.likes = []
            sm_agent.comments = []
            sm_agent.follows = []
            sm_agent.generated_bio = (
                handle_to_generated_bio[a.handle].generated_bio
                if a.handle in handle_to_generated_bio
                else ""
            )
            agents.append(sm_agent)
    else:
        profile_repo = create_sqlite_profile_repository(transaction_provider=tx)
        profiles: list[BlueskyProfile] = profile_repo.list_profiles()
        for profile in profiles:
            sm_agent = SocialMediaAgent(profile.handle)
            sm_agent.bio = profile.bio
            sm_agent.followers = profile.followers_count
            sm_agent.following = profile.follows_count
            sm_agent.posts_count = profile.posts_count
            sm_agent.posts = handle_to_feed_posts.get(profile.handle, [])
            sm_agent.likes = []
            sm_agent.comments = []
            sm_agent.follows = []
            sm_agent.generated_bio = (
                handle_to_generated_bio[profile.handle].generated_bio
                if profile.handle in handle_to_generated_bio
                else ""
            )
            agents.append(sm_agent)
    return agents


if __name__ == "__main__":
    pass
