from enum import Enum

from pydantic import BaseModel


class PolarityValue(Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class PolarityLabel(BaseModel):
    text_id: str
    text: str
    polarity_label: PolarityValue
    polarity_prob: float  # probability of the highest label class
    label_timestamp: str  # use lib/timestamp_utils.py to get the timestamp
