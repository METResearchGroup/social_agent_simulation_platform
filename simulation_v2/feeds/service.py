"""Feed generation orchestration and persistence."""

from __future__ import annotations

import sqlite3

from simulation_v2.config import FeedConfig
from simulation_v2.db.models import GeneratedFeedRecord
from simulation_v2.db.repositories import SimulationRepositories
from simulation_v2.feeds.interfaces import get_feed_generator
from simulation_v2.feeds.validators import validate_feed
from simulation_v2.ids import new_feed_id
from simulation_v2.lib.decorators import progress_items
from simulation_v2.time import get_current_timestamp
from simulation_v2.worker.state import TurnStateSnapshot


def generate_and_persist_feeds(
    snapshot: TurnStateSnapshot,
    feed_config: FeedConfig,
    repos: SimulationRepositories,
    conn: sqlite3.Connection,
) -> list[GeneratedFeedRecord]:
    generator = get_feed_generator(feed_config.algorithm)
    records: list[GeneratedFeedRecord] = []
    user_ids = list(snapshot.users.keys())

    for user_id in progress_items(
        user_ids,
        desc=f"Turn {snapshot.turn_number} (feeds)",
        unit="feed",
        leave=False,
    ):
        views = generator.generate(snapshot, user_id, feed_config)
        validate_feed(user_id, views)
        record = GeneratedFeedRecord(
            feed_id=new_feed_id(),
            run_id=snapshot.run_id,
            turn_id=snapshot.turn_id,
            user_id=user_id,
            algorithm=generator.name,
            feed_post_ids=[view.post_id for view in views],
            feed_posts=views,
            created_at=get_current_timestamp(),
        )
        repos.insert_generated_feed(record, conn)
        records.append(record)

    return records
