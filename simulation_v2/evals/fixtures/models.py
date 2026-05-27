"""Pydantic models and loader for golden eval fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

DEFAULT_GOLDEN_FIXTURE_PATH = Path(__file__).resolve().parent / "golden_v1.json"


class GoldenCase(BaseModel):
    case_id: str
    user_id: str
    expected_like_post_ids: list[str] | None = None
    expected_follow_user_ids: list[str] | None = None
    expected_write_topic: str | None = None


class GoldenFixtureFile(BaseModel):
    schema_version: int
    cases: list[GoldenCase] = Field(default_factory=list)

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: int) -> int:
        if value != 1:
            raise ValueError(f"unsupported schema_version: {value}")
        return value


def load_golden_fixture(path: Path | None = None) -> GoldenFixtureFile:
    fixture_path = path or DEFAULT_GOLDEN_FIXTURE_PATH
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    return GoldenFixtureFile.model_validate(raw)
