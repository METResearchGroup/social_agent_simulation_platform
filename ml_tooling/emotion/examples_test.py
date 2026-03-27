from typing import cast

from transformers import logging as transformers_logging

from ml_tooling.emotion.classifier import EmotionModel
from ml_tooling.emotion.constants import EXPECTED_EMOTIONS
from ml_tooling.emotion.models import EmotionLabel
from ml_tooling.verification.helpers import (
    evaluate_model_performance,
    init_model,
    print_table,
)

transformers_logging.set_verbosity_error()


def print_emotion_table(label: EmotionLabel, case_name: str) -> None:
    col_values = [
        (emotion, f"{getattr(label, f'{emotion}_score'):.4f}")
        for emotion in EXPECTED_EMOTIONS
    ]
    print_table(case_name, label.text, ["emotion", "score"], col_values)


def verify_diff_cases(emotion_model: EmotionModel) -> None:
    cases = [
        ("I want to destroy everything right now!", "anger"),
        ("That is absolutely revolting and disgusting.", "disgust"),
        ("I am terrified and I cannot stop shaking.", "fear"),
        ("This is the best day of my life, I am so happy!", "joy"),
        ("The meeting is scheduled for 3pm tomorrow.", "neutral"),
        ("I miss them so much, I just feel so empty inside.", "sadness"),
        ("I had no idea that was going to happen, I am shocked!", "surprise"),
    ]

    for text, case_name in cases:
        result = emotion_model.extract_emotions(text)
        print_emotion_table(result, case_name)


if __name__ == "__main__":
    print("\n")  # noqa: T201

    emotion_model: EmotionModel = cast(EmotionModel, init_model(EmotionModel))

    verify_diff_cases(emotion_model)

    evaluate_model_performance(
        emotion_model.extract_emotions,
        "This is the best day of my life, I am so happy!",
    )

    print("\n")  # noqa: T201
