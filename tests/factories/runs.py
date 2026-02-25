from __future__ import annotations

from pydantic import JsonValue

from simulation.core.metrics.defaults import get_default_metric_keys
from simulation.core.models.runs import Run, RunConfig, RunStatus
from tests.factories.base import BaseFactory
from tests.factories.context import get_faker


class RunConfigFactory(BaseFactory[RunConfig]):
    @classmethod
    def create(
        cls,
        *,
        num_agents: int = 1,
        num_turns: int = 1,
        feed_algorithm: str = "chronological",
        feed_algorithm_config: dict[str, JsonValue] | None = None,
        metric_keys: list[str] | None = None,
    ) -> RunConfig:
        return RunConfig(
            num_agents=num_agents,
            num_turns=num_turns,
            feed_algorithm=feed_algorithm,
            feed_algorithm_config=feed_algorithm_config,
            metric_keys=metric_keys,
        )


class RunFactory(BaseFactory[Run]):
    @classmethod
    def create(
        cls,
        *,
        run_id: str | None = None,
        created_at: str | None = None,
        total_turns: int = 1,
        total_agents: int = 1,
        feed_algorithm: str = "chronological",
        metric_keys: list[str] | None = None,
        started_at: str | None = None,
        status: RunStatus = RunStatus.COMPLETED,
        completed_at: str | None = None,
    ) -> Run:
        fake = get_faker()
        created = created_at if created_at is not None else "2024_01_01-12:00:00"
        run_id_value = run_id if run_id is not None else f"run_{created}_{fake.uuid4()}"
        started = started_at if started_at is not None else created
        if status == RunStatus.COMPLETED and completed_at is None:
            completed_at = created
        return Run(
            run_id=run_id_value,
            created_at=created,
            total_turns=total_turns,
            total_agents=total_agents,
            feed_algorithm=feed_algorithm,
            metric_keys=metric_keys
            if metric_keys is not None
            else get_default_metric_keys(),
            started_at=started,
            status=status,
            completed_at=completed_at,
        )
