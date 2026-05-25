from __future__ import annotations

from pydantic import BaseModel, Field


class GeneratedFeedsModel(BaseModel):
    feeds_by_user_id: dict[str, list[dict[str, object]]] = Field(default_factory=dict)
