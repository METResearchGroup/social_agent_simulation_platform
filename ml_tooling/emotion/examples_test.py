import time

from transformers import logging as transformers_logging

from ml_tooling.emotion.classifier import EmotionModel
from ml_tooling.emotion.models import EmotionLabel

transformers_logging.set_verbosity_error()

EMOTIONS = ["anger", "disgust", "fear", "joy", "neutral", "sadness", "surprise"]


def track_init_time():
    start = time.perf_counter()
    emotion_model = EmotionModel()
    print(f"[init] ({time.perf_counter() - start:.4f}s)\n\n")
    emotion_model.extract_emotions("")

    return emotion_model


def print_emotion_table(label: EmotionLabel, case_name: str) -> None:
    col_text = "text"
    col_emotion = "emotion"
    col_score = "score"
    wrap_width = 40
    w_text = max(len(col_text), wrap_width)
    w_emotion = max(len(col_emotion), max(len(e) for e in EMOTIONS))
    w_score = max(len(col_score), 8)

    sep = f"+{'-' * (w_text + 2)}+{'-' * (w_emotion + 2)}+{'-' * (w_score + 2)}+"
    header = f"| {col_text:<{w_text}} | {col_emotion:<{w_emotion}} | {col_score:<{w_score}} |"

    # wrap text into lines of wrap_width
    text = label.text
    text_lines = [text[i : i + wrap_width] for i in range(0, len(text), wrap_width)]

    scores = {
        "anger": label.anger_score,
        "disgust": label.disgust_score,
        "fear": label.fear_score,
        "joy": label.joy_score,
        "neutral": label.neutral_score,
        "sadness": label.sadness_score,
        "surprise": label.surprise_score,
    }

    print(f"[{case_name}]")
    print(sep)
    print(header)
    print(sep)

    for i, emotion in enumerate(EMOTIONS):
        row_text = text_lines[i] if i < len(text_lines) else ""
        print(
            f"| {row_text:<{w_text}} | {emotion:<{w_emotion}} | {scores[emotion]:<{w_score}.4f} |"
        )

    # print any remaining text lines with empty emotion/score columns
    for text_line in text_lines[len(EMOTIONS) :]:
        print(f"| {text_line:<{w_text}} | {'':{w_emotion}} | {'':{w_score}} |")

    print(sep)
    print()


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


def run_same_prompt(emotion_model: EmotionModel, iters: int) -> float:
    start = time.perf_counter()
    for _ in range(iters):
        emotion_model.extract_emotions(
            "This is the best day of my life, I am so happy!"
        )
    return time.perf_counter() - start


def run_model_track_time(emotion_model: EmotionModel) -> None:
    counts = [1, 10, 100, 1000, 10000]
    results = [(n, run_same_prompt(emotion_model, n)) for n in counts]

    col1, col2, col3 = "iters", "total (s)", "iters/sec"
    w1, w2, w3 = max(len(col1), 6), max(len(col2), 10), max(len(col3), 10)
    sep = f"+{'-' * (w1 + 2)}+{'-' * (w2 + 2)}+{'-' * (w3 + 2)}+"
    header = f"| {col1:<{w1}} | {col2:<{w2}} | {col3:<{w3}} |"

    print(sep)
    print(header)
    print(sep)
    for n, elapsed in results:
        throughput = n / elapsed if elapsed > 0 else float("inf")
        print(f"| {n:<{w1}} | {elapsed:<{w2}.4f} | {throughput:<{w3}.2f} |")
    print(sep)


if __name__ == "__main__":
    emotion_model = track_init_time()
    print("\n")

    verify_diff_cases(emotion_model)
    print("\n")

    run_model_track_time(emotion_model)
