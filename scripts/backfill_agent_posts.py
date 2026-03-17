"""Backfill agent_posts from feed_posts for internal agents.

This script performs explicit, idempotent data movement from the canonical
feed_posts ingest catalog into the editable seed-state agent_posts table.

Scope:
- Only posts whose feed_posts.author_handle matches an internal agent.handle.
- Derived cache: updates user_agent_profile_metadata.posts_count from agent_posts.
"""

from __future__ import annotations

import logging

from db.adapters.sqlite.sqlite import get_connection
from db.backfills.agent_posts import backfill_agent_posts_from_feed_posts
from lib.timestamp_utils import get_current_timestamp

logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    now = get_current_timestamp()

    conn = get_connection()
    try:
        conn.execute("BEGIN")
        result = backfill_agent_posts_from_feed_posts(conn=conn, now_timestamp=now)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()

    logger.info(
        "Backfilled agent_posts from feed_posts. feed_posts_total=%s feed_posts_internal=%s "
        "agent_posts_inserted=%s internal_agents_total=%s",
        result.feed_posts_total,
        result.feed_posts_internal,
        result.agent_posts_inserted,
        result.internal_agents_total,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
