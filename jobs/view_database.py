"""Simple script to view all profiles and posts in the database."""

from db.adapters.sqlite.sqlite import SqliteTransactionProvider
from db.repositories.feed_post_repository import create_sqlite_feed_post_repository
from db.repositories.profile_repository import create_sqlite_profile_repository


def print_profile(profile):
    """Print a profile in a readable format."""
    display_name = getattr(profile, "display_name", "N/A")
    handle = getattr(profile, "handle", "N/A")
    bio = getattr(profile, "bio", "") or ""
    followers_count = getattr(profile, "followers_count", 0)
    follows_count = getattr(profile, "follows_count", 0)
    posts_count = getattr(profile, "posts_count", 0)

    print(  # noqa: T201
        f"Profile: {display_name} (@{handle}) | "
        f"followers={followers_count:,} following={follows_count:,} posts={posts_count:,}"
    )
    print(f"Bio: {bio}")  # noqa: T201
    print("-" * 80)  # noqa: T201


def print_post(post, show_full_text=True):
    """Print a post in a readable format."""
    snippet = (
        post.text
        if show_full_text
        else (post.text if len(post.text) <= 150 else post.text[:150] + "...")
    )
    print(f"{post.author_handle}: {snippet}")  # noqa: T201


def main():

    # Read and display profiles
    tx = SqliteTransactionProvider()
    profile_repo = create_sqlite_profile_repository(transaction_provider=tx)
    profiles = profile_repo.list_profiles()

    if not profiles:
        pass
    else:
        for profile in profiles:
            print_profile(profile)

    # Read and display posts
    feed_post_repo = create_sqlite_feed_post_repository(transaction_provider=tx)
    posts = feed_post_repo.list_all_feed_posts()

    if not posts:
        pass
    else:
        for post in posts:
            print_post(post, show_full_text=False)


if __name__ == "__main__":
    main()
