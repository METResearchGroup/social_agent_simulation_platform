import uuid
from collections.abc import Callable
from typing import Final, Literal, cast

from transformers import pipeline

from lib.timestamp_utils import get_current_timestamp
from ml_tooling.emotion.models import EmotionLabel

RawEmotions = dict[str, str | float]
EmotionsBatchResponse = list[list[RawEmotions]]
EmotionsSingleResponse = list[RawEmotions]
EmotionsResponse = EmotionsSingleResponse | EmotionsBatchResponse
# NOTE: EmotionsCallable actually can only return an EmotionsBatchResponse with j-hartmann/emotion-english-distilroberta-base
EmotionsCallable = Callable[[str | list[list[str]]], EmotionsResponse]

EMOTIONS_TASK: Final[Literal["text-classification"]] = "text-classification"
EMOTIONS_MODEL: str = "j-hartmann/emotion-english-distilroberta-base"
EMOTIONS_RETURN_TOP_K: Final = None
NUM_EMOTIONS: Final = 7


def build_default_emotion_pipeline() -> EmotionsCallable:
    return cast(
        EmotionsCallable,
        pipeline(EMOTIONS_TASK, model=EMOTIONS_MODEL, top_k=EMOTIONS_RETURN_TOP_K),
    )


class EmotionModel:
    def __init__(self, emotions_pipeline: EmotionsCallable | None = None) -> None:
        self._emotions_pipeline: EmotionsCallable = (
            build_default_emotion_pipeline()
            if emotions_pipeline is None
            else emotions_pipeline
        )

    def _to_emotion_label(
        self, emotion_distribution: EmotionsSingleResponse, text: str
    ) -> EmotionLabel:
        timestamp = get_current_timestamp()
        text_id = str(uuid.uuid4())

        emotion_scores = {}
        for dictionary in emotion_distribution:
            emotion_scores[dictionary["label"]] = dictionary["score"]

        return EmotionLabel(
            text_id=text_id,
            text=text,
            anger_score=emotion_scores["anger"],
            disgust_score=emotion_scores["disgust"],
            fear_score=emotion_scores["fear"],
            joy_score=emotion_scores["joy"],
            neutral_score=emotion_scores["neutral"],
            sadness_score=emotion_scores["sadness"],
            surprise_score=emotion_scores["surprise"],
            label_timestamp=timestamp,
        )

    def extract_emotions(self, text: str) -> EmotionLabel:
        response = cast(EmotionsBatchResponse, self._emotions_pipeline(text))
        return self._to_emotion_label(response[0], text)

    def extract_emotions_batch(self, texts: list[str]) -> list[EmotionLabel]:
        batch_emotion_labels = [self.extract_emotions(text) for text in texts]
        return batch_emotion_labels
