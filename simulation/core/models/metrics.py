from __future__ import annotations

from pydantic import BaseModel, ValidationInfo, field_validator

from lib.validation_utils import (
    validate_non_empty_string,
    validate_nonnegative_value,
)
from simulation.core.models.json_types import JsonObject


def _field_name(info: ValidationInfo | None) -> str:
    return getattr(info, "field_name", None) or "field"


class TurnMetrics(BaseModel):
    run_id: str
    turn_number: int
    metrics: JsonObject
    created_at: str

    @field_validator("run_id", "created_at", mode="before")
    @classmethod
    def _validate_non_empty(cls, v: str, info: ValidationInfo) -> str:
        return validate_non_empty_string(v, _field_name(info))

    @field_validator("turn_number")
    @classmethod
    def _validate_turn_number(cls, v: int) -> int:
        return validate_nonnegative_value(v, "turn_number")

    model_config = {"frozen": True}


class RunMetrics(BaseModel):
    run_id: str
    metrics: JsonObject
    created_at: str

    @field_validator("run_id", "created_at", mode="before")
    @classmethod
    def _validate_non_empty(cls, v: str, info: ValidationInfo) -> str:
        return validate_non_empty_string(v, _field_name(info))

    model_config = {"frozen": True}
