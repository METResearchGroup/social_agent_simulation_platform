"""Given the database of Bluesky profiles and feed posts, create a list of agents."""

from db.adapters.sqlite.sqlite import SqliteTransactionProvider
from db.repositories.feed_post_repository import create_sqlite_feed_post_repository
from db.repositories.generated_bio_repository import (
    create_sqlite_generated_bio_repository,
)
from db.repositories.profile_repository import create_sqlite_profile_repository
from simulation.core.models.agents import SocialMediaAgent
from simulation.core.models.generated.bio import GeneratedBio
from simulation.core.models.posts import BlueskyFeedPost
from simulation.core.models.profiles import BlueskyProfile


def create_initial_agents() -> list[SocialMediaAgent]:
    """Create a list of agents from the database of Bluesky profiles and feed
    posts and pass into the network."""
    tx = SqliteTransactionProvider()
    profile_repo = create_sqlite_profile_repository(transaction_provider=tx)
    feed_post_repo = create_sqlite_feed_post_repository(transaction_provider=tx)
    generated_bio_repo = create_sqlite_generated_bio_repository(transaction_provider=tx)
    profiles: list[BlueskyProfile] = profile_repo.list_profiles()
    feed_posts: list[BlueskyFeedPost] = feed_post_repo.list_all_feed_posts()
    generated_bios: list[GeneratedBio] = generated_bio_repo.list_all_generated_bios()

    handle_to_feed_posts: dict[str, list[BlueskyFeedPost]] = {}
    for post in feed_posts:
        handle_to_feed_posts.setdefault(post.author_handle, []).append(post)

    handle_to_generated_bio: dict[str, GeneratedBio] = {
        bio.handle: bio for bio in generated_bios
    }
    agents: list[SocialMediaAgent] = []

    for profile in profiles:
        agent = SocialMediaAgent(profile.handle)
        agent.bio = profile.bio
        agent.followers = profile.followers_count
        agent.following = profile.follows_count
        agent.posts_count = profile.posts_count
        agent.posts = handle_to_feed_posts.get(profile.handle, [])
        agent.likes = []
        agent.comments = []
        agent.follows = []
        if profile.handle in handle_to_generated_bio:
            agent.generated_bio = handle_to_generated_bio[profile.handle].generated_bio
        else:
            agent.generated_bio = ""
        agents.append(agent)
    return agents


if __name__ == "__main__":
    pass
