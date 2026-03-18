from pydantic import BaseModel


class EmotionLabel(BaseModel):
    text_id: str
    text: str
    anger_score: float
    disgust_score: float
    fear_score: float
    joy_score: float
    neutral_score: float
    sadness_score: float
    surprise_score: float
    label_timestamp: str
