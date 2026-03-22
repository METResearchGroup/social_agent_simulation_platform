from __future__ import annotations

from lib.agent_id import canonical_agent_id
from simulation.core.models.run_follow_edges import RunFollowEdgeSnapshot
from tests.factories.base import BaseFactory


class RunFollowEdgeSnapshotFactory(BaseFactory[RunFollowEdgeSnapshot]):
    @classmethod
    def create(
        cls,
        *,
        run_id: str | None = None,
        follower_agent_id: str | None = None,
        target_agent_id: str | None = None,
        created_at: str = "2024-01-01T00:00:00Z",
    ) -> RunFollowEdgeSnapshot:
        return RunFollowEdgeSnapshot(
            run_id=run_id if run_id is not None else "run_123",
            follower_agent_id=follower_agent_id
            if follower_agent_id is not None
            else canonical_agent_id("run_follow_follower"),
            target_agent_id=target_agent_id
            if target_agent_id is not None
            else canonical_agent_id("run_follow_target"),
            created_at=created_at,
        )
