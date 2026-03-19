"""Simple script to view all profiles and posts in the database."""

from db.adapters.sqlite.sqlite import SqliteTransactionProvider
from db.repositories.feed_post_repository import create_sqlite_feed_post_repository
from db.repositories.profile_repository import create_sqlite_profile_repository


def print_profile(profile):
    """Print a profile in a readable format."""


def print_post(post, show_full_text=True):
    """Print a post in a readable format."""

    if show_full_text:
        pass
    else:
        post.text[:150] + "..." if len(post.text) > 150 else post.text


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
