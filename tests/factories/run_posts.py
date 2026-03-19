from __future__ import annotations

from simulation.core.models.run_posts import RunPostSnapshot
from tests.factories.base import BaseFactory
from tests.factories.context import get_faker


class RunPostSnapshotFactory(BaseFactory[RunPostSnapshot]):
    @classmethod
    def create(
        cls,
        *,
        run_post_id: str | None = None,
        run_id: str | None = None,
        agent_post_id: str | None = None,
        author_agent_id: str = "did:plc:author",
        author_handle_at_start: str | None = None,
        author_display_name_at_start: str | None = None,
        body_text_at_start: str = "Post body at start",
        published_at_start: str = "2024-01-01T00:00:00Z",
        source_post_id_at_start: str | None = None,
        source_at_start: str | None = None,
        source_uri_at_start: str | None = None,
        created_at: str = "2024-01-01T00:00:00Z",
    ) -> RunPostSnapshot:
        fake = get_faker()
        return RunPostSnapshot(
            run_post_id=run_post_id
            if run_post_id is not None
            else f"rp_{fake.uuid4()}",
            run_id=run_id if run_id is not None else "run_123",
            agent_post_id=agent_post_id
            if agent_post_id is not None
            else f"ap_{fake.uuid4()}",
            author_agent_id=author_agent_id,
            author_handle_at_start=(
                author_handle_at_start
                if author_handle_at_start is not None
                else "author.bsky.social"
            ),
            author_display_name_at_start=(
                author_display_name_at_start
                if author_display_name_at_start is not None
                else "Author Display"
            ),
            body_text_at_start=body_text_at_start,
            published_at_start=published_at_start,
            source_post_id_at_start=source_post_id_at_start,
            source_at_start=source_at_start,
            source_uri_at_start=source_uri_at_start,
            created_at=created_at,
        )
