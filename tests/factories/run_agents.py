from __future__ import annotations

from simulation.core.models.run_agents import RunAgentSnapshot
from tests.factories.base import BaseFactory
from tests.factories.context import get_faker


class RunAgentSnapshotFactory(BaseFactory[RunAgentSnapshot]):
    @classmethod
    def create(
        cls,
        *,
        run_id: str | None = None,
        agent_id: str | None = None,
        selection_order: int = 0,
        handle_at_start: str | None = None,
        display_name_at_start: str | None = None,
        persona_bio_at_start: str | None = None,
        followers_count_at_start: int = 0,
        follows_count_at_start: int = 0,
        posts_count_at_start: int = 0,
        created_at: str = "2024-01-01T00:00:00Z",
    ) -> RunAgentSnapshot:
        fake = get_faker()
        handle = (
            handle_at_start
            if handle_at_start is not None
            else f"{fake.user_name()}.bsky.social"
        )
        return RunAgentSnapshot(
            run_id=run_id if run_id is not None else "run_123",
            agent_id=agent_id if agent_id is not None else f"did:plc:{fake.uuid4()}",
            selection_order=selection_order,
            handle_at_start=handle,
            display_name_at_start=display_name_at_start or handle,
            persona_bio_at_start=persona_bio_at_start
            or "Persona bio at the start of the run.",
            followers_count_at_start=followers_count_at_start,
            follows_count_at_start=follows_count_at_start,
            posts_count_at_start=posts_count_at_start,
            created_at=created_at,
        )
