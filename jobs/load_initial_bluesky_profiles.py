"""Job for initializing the agents.

For now, what this looks like is:
- Getting a series of Bluesky profiles from a list of handles.
- Using that information to create a bio for the agent.
- Persisting the agent to the SQLite database.
"""

from db.adapters.sqlite.sqlite import initialize_database
from db.repositories.feed_post_repository import create_sqlite_feed_post_repository
from db.repositories.profile_repository import create_sqlite_profile_repository
from lib.bluesky_client import BlueskyClient
from simulation.core.models.posts import BlueskyFeedPost
from simulation.core.models.profiles import BlueskyProfile

bsky_client = BlueskyClient()

BLUESKY_PROFILE_URLS = [
    "https://bsky.app/profile/aoc.bsky.social",
    "https://bsky.app/profile/did:plc:ks3gpa6ftoyaq7hmf6c4qx4c",
    "https://bsky.app/profile/did:plc:77lswp42lgjyw36ozuo7kt7e",
    "https://bsky.app/profile/did:plc:ksjfbda7262bbqmuoly54lww",
    "https://bsky.app/profile/did:plc:2q2hs5o42jhbd23pp6lkiauh",
    "https://bsky.app/profile/did:plc:j37zetcnytvnfjlk4ca3d2yv",
    "https://bsky.app/profile/did:plc:zbrhmanjs62oyqywjwdazxz3",
]

BLUESKY_PROFILES = [url.split("/")[-1] for url in BLUESKY_PROFILE_URLS]


def transform_bsky_profile(profile: dict) -> BlueskyProfile:
    """Transform raw Bluesky profile data into BlueskyProfile model.

    Args:
        profile: Profile view dictionary from Bluesky API

    Returns:
        BlueskyProfile model
    """
    return BlueskyProfile(
        handle=profile["handle"],
        did=profile["did"],
        display_name=profile["display_name"],
        bio=profile.get("description") or "",
        followers_count=profile["followers_count"],
        follows_count=profile["follows_count"],
        posts_count=profile["posts_count"],
    )


def transform_bsky_author_feed(author_feed: list[dict]) -> list[BlueskyFeedPost]:
    """Transform raw Bluesky author feed data into BlueskyFeedPost models.

    Args:
        author_feed: List of post view dictionaries from Bluesky API

    Returns:
        List of BlueskyFeedPost models
    """
    transformed_posts = []

    for post_view in author_feed:
        post = BlueskyFeedPost(
            id=post_view["uri"],
            uri=post_view["uri"],
            author_display_name=post_view["author"]["display_name"],
            author_handle=post_view["author"]["handle"],
            text=post_view["record"]["text"],
            bookmark_count=post_view["bookmark_count"],
            like_count=post_view["like_count"],
            quote_count=post_view["quote_count"],
            reply_count=post_view["reply_count"],
            repost_count=post_view["repost_count"],
            created_at=post_view["record"]["created_at"],
        )
        transformed_posts.append(post)

    return transformed_posts


def get_bsky_profile_information(handle: str) -> dict:
    profile = bsky_client.get_profile(handle)
    author_feed = bsky_client.get_author_feed(handle)
    return {
        "profile": profile,
        "author_feed": author_feed,
    }


def main():
    initialize_database()
    profile_repo = create_sqlite_profile_repository()
    feed_post_repo = create_sqlite_feed_post_repository()
    for handle in BLUESKY_PROFILES:
        print(f"Getting profile information for {handle}...")
        profile_info = get_bsky_profile_information(handle)

        profile = transform_bsky_profile(profile_info["profile"])
        profile_repo.create_or_update_profile(profile)
        feed_posts = transform_bsky_author_feed(profile_info["author_feed"])
        feed_post_repo.create_or_update_feed_posts(feed_posts)

        print(f"Profile information for {handle} written to database.")


if __name__ == "__main__":
    print("Initializing agents...")
    main()
    print("Agents initialized successfully.")
