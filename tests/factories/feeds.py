from __future__ import annotations

from datetime import timezone

from simulation.core.models.feeds import GeneratedFeed
from tests.factories.base import BaseFactory
from tests.factories.context import get_faker


def _timestamp_utc_iso() -> str:
    fake = get_faker()
    dt = fake.date_time(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


class GeneratedFeedFactory(BaseFactory[GeneratedFeed]):
    @classmethod
    def create(
        cls,
        *,
        feed_id: str | None = None,
        run_id: str | None = None,
        turn_number: int = 0,
        agent_handle: str | None = None,
        post_uris: list[str] | None = None,
        created_at: str | None = None,
    ) -> GeneratedFeed:
        fake = get_faker()
        run_id_value = run_id if run_id is not None else f"run_{fake.uuid4()}"
        agent_value = (
            agent_handle
            if agent_handle is not None
            else f"{fake.user_name()}.bsky.social"
        )
        feed_id_value = feed_id if feed_id is not None else f"feed_{fake.uuid4()}"
        post_uris_value = (
            post_uris
            if post_uris is not None
            else [f"at://did:plc:{fake.uuid4()}/app.bsky.feed.post/{fake.uuid4()}"]
        )
        created_at_value = (
            created_at if created_at is not None else _timestamp_utc_iso()
        )
        return GeneratedFeed(
            feed_id=feed_id_value,
            run_id=run_id_value,
            turn_number=turn_number,
            agent_handle=agent_value,
            post_uris=post_uris_value,
            created_at=created_at_value,
        )
