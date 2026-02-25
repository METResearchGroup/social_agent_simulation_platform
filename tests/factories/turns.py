from __future__ import annotations

from simulation.core.models.actions import TurnAction
from simulation.core.models.turns import TurnMetadata, TurnResult
from tests.factories.base import BaseFactory
from tests.factories.context import get_faker


class TurnResultFactory(BaseFactory[TurnResult]):
    @classmethod
    def create(
        cls,
        *,
        turn_number: int = 0,
        total_actions: dict[TurnAction, int] | None = None,
        execution_time_ms: int | None = None,
    ) -> TurnResult:
        return TurnResult(
            turn_number=turn_number,
            total_actions=total_actions or {},
            execution_time_ms=execution_time_ms,
        )


class TurnMetadataFactory(BaseFactory[TurnMetadata]):
    @classmethod
    def create(
        cls,
        *,
        run_id: str | None = None,
        turn_number: int = 0,
        total_actions: dict[TurnAction, int] | None = None,
        created_at: str = "2024_01_01-12:00:00",
    ) -> TurnMetadata:
        fake = get_faker()
        run_id_value = run_id if run_id is not None else f"run_{fake.uuid4()}"
        return TurnMetadata(
            run_id=run_id_value,
            turn_number=turn_number,
            total_actions=total_actions or {},
            created_at=created_at,
        )
