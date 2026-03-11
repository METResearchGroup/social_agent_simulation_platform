from pydantic import BaseModel


class EntitySpan(BaseModel):
    text: str  # (surface form)
    label: str  # (e.g. PER, ORG, LOC, MISC, or model-provided label)
    score: float
    timestamp: str  # (use the get_current_timestamp in lib/timestamp_utils.py to calculate this)
