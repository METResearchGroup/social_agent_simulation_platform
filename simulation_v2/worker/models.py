"""Worker job models."""

from __future__ import annotations

from pydantic import BaseModel


class RunJob(BaseModel):
    run_id: str
