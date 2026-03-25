from typing import cast

from transformers import logging as transformers_logging

from ml_tooling.emotion.classifier import EmotionModel
from ml_tooling.emotion.models import EmotionLabel
from ml_tooling.verification.helpers import (
    print_table,
    run_model_track_time,
    track_init_time,
)

transformers_logging.set_verbosity_error()


def print_emotion_table(label: EmotionLabel, case_name: str) -> None:
    col_values = [
        ("anger", f"{label.anger_score:.4f}"),
        ("disgust", f"{label.disgust_score:.4f}"),
        ("fear", f"{label.fear_score:.4f}"),
        ("joy", f"{label.joy_score:.4f}"),
        ("neutral", f"{label.neutral_score:.4f}"),
        ("sadness", f"{label.sadness_score:.4f}"),
        ("surprise", f"{label.surprise_score:.4f}"),
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
    emotion_model: EmotionModel = cast(EmotionModel, track_init_time(EmotionModel))

    verify_diff_cases(emotion_model)

    run_model_track_time(
        emotion_model.extract_emotions,
        "This is the best day of my life, I am so happy!",
    )
