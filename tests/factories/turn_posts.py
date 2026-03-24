from __future__ import annotations

from lib.agent_id import canonical_agent_id
from simulation.core.models.turn_posts import TurnPostSnapshot
from tests.factories.base import BaseFactory
from tests.factories.context import get_faker


class TurnPostSnapshotFactory(BaseFactory[TurnPostSnapshot]):
    @classmethod
    def create(
        cls,
        *,
        turn_post_id: str | None = None,
        run_id: str | None = None,
        turn_number: int = 0,
        author_agent_id: str | None = None,
        author_handle_at_time: str | None = None,
        author_display_name_at_time: str | None = None,
        body_text: str = "Turn-authored body",
        created_at: str = "2024-01-01T00:00:00Z",
        explanation: str | None = None,
        model_used: str | None = None,
        generation_metadata_json: str | None = None,
        generation_created_at: str | None = None,
    ) -> TurnPostSnapshot:
        fake = get_faker()
        resolved_author = (
            author_agent_id
            if author_agent_id is not None
            else canonical_agent_id("turn_post_default_author")
        )
        return TurnPostSnapshot(
            turn_post_id=turn_post_id
            if turn_post_id is not None
            else f"tp_{fake.uuid4()}",
            run_id=run_id if run_id is not None else "run_123",
            turn_number=turn_number,
            author_agent_id=resolved_author,
            author_handle_at_time=(
                author_handle_at_time
                if author_handle_at_time is not None
                else "author.bsky.social"
            ),
            author_display_name_at_time=(
                author_display_name_at_time
                if author_display_name_at_time is not None
                else "Author"
            ),
            body_text=body_text,
            created_at=created_at,
            explanation=explanation,
            model_used=model_used,
            generation_metadata_json=generation_metadata_json,
            generation_created_at=generation_created_at,
        )
