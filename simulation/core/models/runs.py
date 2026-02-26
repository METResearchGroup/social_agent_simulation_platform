from enum import Enum

from pydantic import BaseModel, JsonValue, field_validator

from lib.validation_utils import (
    validate_non_empty_iterable,
    validate_non_empty_string,
    validate_nonnegative_value,
)

DEFAULT_FEED_ALGORITHM: str = "chronological"


class RunConfig(BaseModel):
    """Configuration for a simulation run."""

    num_agents: int
    num_turns: int
    feed_algorithm: str
    feed_algorithm_config: dict[str, JsonValue] | None = None
    metric_keys: list[str] | None = None

    @field_validator("metric_keys")
    @classmethod
    def validate_metric_keys_config(cls, v: list[str] | None) -> list[str] | None:
        """Validate that metric_keys, when provided, is non-empty and contains non-empty strings.

        Note: registry-level validation belongs outside the domain models layer.
        """
        if v is None:
            return None
        validate_non_empty_iterable(v, "metric_keys")
        return [validate_non_empty_string(item, "metric_keys") for item in v]

    @field_validator("num_agents")
    @classmethod
    def validate_num_agents(cls, v: int) -> int:
        return validate_nonnegative_value(v, "num_agents", ok_equals_zero=False)

    @field_validator("num_turns")
    @classmethod
    def validate_num_turns(cls, v: int) -> int:
        return validate_nonnegative_value(v, "num_turns", ok_equals_zero=False)

    @field_validator("feed_algorithm")
    @classmethod
    def validate_feed_algorithm(cls, v: str) -> str:
        return validate_non_empty_string(v, "feed_algorithm")


class RunStatus(str, Enum):
    """
    Enum representing the state of a simulation run.

    State transitions:
      - RUNNING: The run is actively in progress. All runs start in this state.
      - COMPLETED: The run has finished successfully. Set when the simulation
        completes all turns and agents have completed their actions.
      - FAILED: The run has terminated abnormally due to an error or interruption.
        No further progress will be made.

    Valid transitions:
      - RUNNING -> COMPLETED: Normal successful completion.
      - RUNNING -> FAILED: Error or failure during simulation.
    """

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Run(BaseModel):
    run_id: str
    created_at: str
    total_turns: int
    total_agents: int
    feed_algorithm: str = DEFAULT_FEED_ALGORITHM
    metric_keys: list[str]
    started_at: str
    status: RunStatus
    completed_at: str | None = None

    @field_validator("metric_keys")
    @classmethod
    def validate_metric_keys_run(cls, v: list[str]) -> list[str]:
        validate_non_empty_iterable(v, "metric_keys")
        return [validate_non_empty_string(item, "metric_keys") for item in v]

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, v: str) -> str:
        """Validate that run_id is a non-empty string."""
        return validate_non_empty_string(v, "run_id")

    @field_validator("total_turns")
    @classmethod
    def validate_total_turns(cls, v: int) -> int:
        """Validate that total_turns is an integer greater than zero."""
        return validate_nonnegative_value(v, "total_turns", ok_equals_zero=False)

    @field_validator("total_agents")
    @classmethod
    def validate_total_agents(cls, v: int) -> int:
        """Validate that total_agents is an integer greater than zero."""
        return validate_nonnegative_value(v, "total_agents", ok_equals_zero=False)

    @field_validator("feed_algorithm")
    @classmethod
    def validate_feed_algorithm(cls, v: str) -> str:
        return validate_non_empty_string(v, "feed_algorithm")
