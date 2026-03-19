"""Simple script to view all generated feeds in the database."""

from collections import Counter

from db.adapters.sqlite.sqlite import SqliteTransactionProvider
from db.repositories.generated_feed_repository import (
    create_sqlite_generated_feed_repository,
)


def main():

    # Read all generated feeds
    tx = SqliteTransactionProvider()
    generated_feed_repo = create_sqlite_generated_feed_repository(
        transaction_provider=tx
    )
    feeds = generated_feed_repo.list_all_generated_feeds()

    # 1. Total number of generated feeds
    len(feeds)

    if not feeds:
        return

    # 2. Total number of generated feeds per run_id
    run_id_counts = Counter(feed.run_id for feed in feeds)

    for _run_id, _count in sorted(run_id_counts.items()):
        pass

    # 3. Total number of generated feeds per handle
    handle_counts = Counter(feed.agent_handle for feed in feeds)

    for _handle, _count in sorted(handle_counts.items()):
        pass


if __name__ == "__main__":
    main()
