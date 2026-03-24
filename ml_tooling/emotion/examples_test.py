from typing import cast

from transformers import logging as transformers_logging

from ml_tooling.emotion.classifier import EmotionModel
from ml_tooling.emotion.models import EmotionLabel
from ml_tooling.verification.helpers import run_same_prompt, track_init_time

transformers_logging.set_verbosity_error()

EMOTIONS = ["anger", "disgust", "fear", "joy", "neutral", "sadness", "surprise"]


def print_emotion_table(label: EmotionLabel, case_name: str) -> None:
    col_text = "text"
    col_emotion = "emotion"
    col_score = "score"
    wrap_width = 40
    w_text = max(len(col_text), wrap_width)
    w_emotion = max(len(col_emotion), max(len(e) for e in EMOTIONS))
    w_score = max(len(col_score), 8)

    f"+{'-' * (w_text + 2)}+{'-' * (w_emotion + 2)}+{'-' * (w_score + 2)}+"

    # wrap text into lines of wrap_width
    text = label.text
    text_lines = [text[i : i + wrap_width] for i in range(0, len(text), wrap_width)]

    for i, _emotion in enumerate(EMOTIONS):
        text_lines[i] if i < len(text_lines) else ""

    # print any remaining text lines with empty emotion/score columns
    for _text_line in text_lines[len(EMOTIONS) :]:
        pass


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


def run_model_track_time(emotion_model: EmotionModel) -> None:
    counts = [1, 10, 100, 1000, 10000]
    results = [
        (
            n,
            run_same_prompt(
                emotion_model.extract_emotions,
                "This is the best day of my life, I am so happy!",
                n,
            ),
        )
        for n in counts
    ]

    col1, col2, col3 = "iters", "total (s)", "iters/sec"
    w1, w2, w3 = max(len(col1), 6), max(len(col2), 10), max(len(col3), 10)
    f"+{'-' * (w1 + 2)}+{'-' * (w2 + 2)}+{'-' * (w3 + 2)}+"

    for n, elapsed in results:
        n / elapsed if elapsed > 0 else float("inf")


if __name__ == "__main__":
    emotion_model: EmotionModel = cast(EmotionModel, track_init_time(EmotionModel))

    verify_diff_cases(emotion_model)

    run_model_track_time(emotion_model)
