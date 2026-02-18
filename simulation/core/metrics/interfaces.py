from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, Protocol

from simulation.core.models.json_types import JsonObject, JsonValue

if TYPE_CHECKING:
    from db.repositories.interfaces import MetricsRepository, RunRepository


class MetricOutputAdapter(Protocol):
    """Pydantic TypeAdapter-compatible validator for a metric's output.

    Metrics should typically implement this by returning a `pydantic.TypeAdapter`
    constructed from the metric's expected output shape (e.g. `int`,
    `dict[str, int]`).
    """

    def validate_python(
        self,
        __input: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any: ...

    def json_schema(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...


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
    KEY: ClassVar[str]
    SCOPE: ClassVar[MetricScope]
    DEFAULT_ENABLED: ClassVar[bool] = True

    @property
    def key(self) -> str:
        return self.KEY

    @property
    def scope(self) -> MetricScope:
        return self.SCOPE

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls is Metric:
            return

        key = getattr(cls, "KEY", None)
        if not isinstance(key, str) or not key.strip():
            raise TypeError(
                f"{cls.__module__}.{cls.__name__} must define non-empty class var KEY"
            )

        scope = getattr(cls, "SCOPE", None)
        if not isinstance(scope, MetricScope):
            raise TypeError(
                f"{cls.__module__}.{cls.__name__} must define class var SCOPE as MetricScope"
            )

        default_enabled = getattr(cls, "DEFAULT_ENABLED", True)
        if not isinstance(default_enabled, bool):
            raise TypeError(
                f"{cls.__module__}.{cls.__name__} DEFAULT_ENABLED must be a bool"
            )

    @property
    @abstractmethod
    def output_adapter(self) -> MetricOutputAdapter:
        """Validator for this metric's output value."""

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
