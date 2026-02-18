from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from simulation.core.models.json_types import JsonObject, JsonValue

if TYPE_CHECKING:
    from db.repositories.interfaces import MetricsRepository, RunRepository


class MetricScope(str, Enum):
    TURN = "turn"
    RUN = "run"


@dataclass(frozen=True)
class MetricContext:
    run_id: str
    turn_number: int | None = None


@dataclass(frozen=True)
class MetricDeps:
    """Dependencies that metrics can use to compute values.

    Keep this narrow; add fields only when a metric needs them.
    """

    run_repo: "RunRepository"
    metrics_repo: "MetricsRepository"
    sql_executor: "MetricsSqlExecutor | None" = None


class MetricsSqlExecutor(ABC):
    """DB query executor for SQL-backed metrics.

    Metrics must supply parameterized SQL and parameters; implementations must not
    interpolate raw values into SQL strings.
    """

    @abstractmethod
    def fetch_one(self, *, sql: str, params: dict[str, JsonValue]) -> JsonObject | None:
        raise NotImplementedError

    @abstractmethod
    def fetch_all(self, *, sql: str, params: dict[str, JsonValue]) -> list[JsonObject]:
        raise NotImplementedError


class Metric(ABC):
    @property
    @abstractmethod
    def key(self) -> str: ...

    @property
    @abstractmethod
    def scope(self) -> MetricScope: ...

    @property
    def requires(self) -> tuple[str, ...]:
        return ()

    @abstractmethod
    def compute(
        self,
        *,
        ctx: MetricContext,
        deps: MetricDeps,
        prior: JsonObject,
    ) -> JsonValue: ...
