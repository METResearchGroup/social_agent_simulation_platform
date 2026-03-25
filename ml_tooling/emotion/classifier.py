import uuid
from collections.abc import Callable
from typing import cast

from transformers import pipeline

from lib.timestamp_utils import get_current_timestamp
from ml_tooling.emotion.constants import (
    EMOTIONS_MODEL,
    EMOTIONS_RETURN_TOP_K,
    EMOTIONS_TASK,
    EXPECTED_EMOTIONS,
)
from ml_tooling.emotion.models import EmotionLabel

RawEmotions = dict[str, float]
EmotionsBatchResponse = list[list[RawEmotions]]
EmotionsSingleResponse = list[RawEmotions]
EmotionsResponse = EmotionsSingleResponse | EmotionsBatchResponse
# NOTE: EmotionsCallable actually can only return an EmotionsBatchResponse with j-hartmann/emotion-english-distilroberta-base
EmotionsCallable = Callable[[str | list[str]], EmotionsResponse]


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

        emotion_scores: dict[str, float] = {}
        for dictionary in emotion_distribution:
            label = str(dictionary["label"])
            emotion_scores[label] = dictionary["score"]

        missing = set(EXPECTED_EMOTIONS) - set(emotion_scores.keys())
        if missing:
            raise ValueError(
                f"Emotion pipeline response missing expected labels: {missing}"
            )

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

    def _normalize_single_response(
        self, raw: EmotionsResponse
    ) -> EmotionsSingleResponse:
        if not raw:
            raise ValueError("Emotion pipeline returned empty response")
        if isinstance(raw[0], dict):
            return cast(EmotionsSingleResponse, raw)
        return cast(EmotionsBatchResponse, raw)[0]

    def extract_emotions(self, text: str) -> EmotionLabel:
        raw = self._emotions_pipeline(text)
        return self._to_emotion_label(self._normalize_single_response(raw), text)

    def extract_emotions_batch(self, texts: list[str]) -> list[EmotionLabel]:
        if not texts:
            return []
        response = cast(EmotionsBatchResponse, self._emotions_pipeline(texts))
        if len(response) != len(texts):
            raise ValueError("Emotion pipeline returned unexpected batch size")
        return [
            self._to_emotion_label(response[i], text) for i, text in enumerate(texts)
        ]
