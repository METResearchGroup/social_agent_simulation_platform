"""Simple script to view all generated feeds in the database."""

from collections import Counter

from db.adapters.sqlite.sqlite import SqliteTransactionProvider
from db.repositories.generated_feed_repository import (
    create_sqlite_generated_feed_repository,
)


def main():
    print("=" * 80)
    print("GENERATED FEEDS VIEWER")
    print("=" * 80)

    # Read all generated feeds
    tx = SqliteTransactionProvider()
    generated_feed_repo = create_sqlite_generated_feed_repository(
        transaction_provider=tx
    )
    feeds = generated_feed_repo.list_all_generated_feeds()

    # 1. Total number of generated feeds
    total_feeds = len(feeds)
    print("\n📊 TOTAL GENERATED FEEDS")
    print("=" * 80)
    print(f"Total number of generated feeds: {total_feeds}")

    if not feeds:
        print("\nNo generated feeds found in database.")
        return

    # 2. Total number of generated feeds per run_id
    run_id_counts = Counter(feed.run_id for feed in feeds)

    print("\n\n📝 GENERATED FEEDS PER RUN_ID")
    print("=" * 80)
    print(f"{'Run ID':<50} {'Count':<10}")
    print("-" * 80)

    for run_id, count in sorted(run_id_counts.items()):
        print(f"{run_id:<50} {count:<10}")

    # 3. Total number of generated feeds per handle
    handle_counts = Counter(feed.agent_handle for feed in feeds)

    print("\n\n📝 GENERATED FEEDS PER HANDLE")
    print("=" * 80)
    print(f"{'Handle':<50} {'Count':<10}")
    print("-" * 80)

    for handle, count in sorted(handle_counts.items()):
        print(f"{handle:<50} {count:<10}")

    print("=" * 80)


if __name__ == "__main__":
    main()
