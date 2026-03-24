import time
from typing import cast

from transformers import logging as transformers_logging

from ml_tooling.polarity.classifier import PolarityModel
from ml_tooling.polarity.constants import POLARITIES
from ml_tooling.polarity.models import PolarityLabel
from ml_tooling.verification.helpers import track_init_time

transformers_logging.set_verbosity_error()


def print_polarity_table(label: PolarityLabel, case_name: str) -> None:
    col_text = "text"
    col_label = "label"
    col_prob = "prob"
    wrap_width = 40
    w_text = max(len(col_text), wrap_width)
    w_label = max(len(col_label), max(len(p) for p in POLARITIES))
    w_prob = max(len(col_prob), 8)

    sep = f"+{'-' * (w_text + 2)}+{'-' * (w_label + 2)}+{'-' * (w_prob + 2)}+"
    header = f"| {col_text:<{w_text}} | {col_label:<{w_label}} | {col_prob:<{w_prob}} |"

    text = label.text
    text_lines = [text[i : i + wrap_width] for i in range(0, len(text), wrap_width)]

    print(f"[{case_name}]")  # noqa: T201
    print(sep)  # noqa: T201
    print(header)  # noqa: T201
    print(sep)  # noqa: T201

    first_line = text_lines[0] if text_lines else ""
    print(  # noqa: T201
        f"| {first_line:<{w_text}} | {label.polarity_label.value:<{w_label}} | {label.polarity_prob:<{w_prob}.4f} |"
    )

    for text_line in text_lines[1:]:
        print(f"| {text_line:<{w_text}} | {'':{w_label}} | {'':{w_prob}} |")  # noqa: T201

    print(sep)  # noqa: T201
    print()  # noqa: T201


def verify_diff_cases(polarity_model: PolarityModel) -> None:
    cases = [
        (
            "This is absolutely the most wonderful, joyful, and amazing day of my life!",
            "positive",
        ),
        (
            "The file was saved to the directory at 3pm.",
            "neutral",
        ),
        (
            "This is utterly terrible, disgusting, and the worst experience I have ever had.",
            "negative",
        ),
    ]

    for text, case_name in cases:
        result = polarity_model.extract_polarity(text)
        print_polarity_table(result, case_name)


def run_same_prompt(polarity_model: PolarityModel, iters: int) -> float:
    start = time.perf_counter()
    for _ in range(iters):
        polarity_model.extract_polarity(
            "This is absolutely the most wonderful, joyful, and amazing day of my life!"
        )
    return time.perf_counter() - start


def run_model_track_time(polarity_model: PolarityModel) -> None:
    counts = [1, 10, 100, 1000, 10000]
    results = [(n, run_same_prompt(polarity_model, n)) for n in counts]

    col1, col2, col3 = "iters", "total (s)", "iters/sec"
    w1, w2, w3 = max(len(col1), 6), max(len(col2), 10), max(len(col3), 10)
    sep = f"+{'-' * (w1 + 2)}+{'-' * (w2 + 2)}+{'-' * (w3 + 2)}+"
    header = f"| {col1:<{w1}} | {col2:<{w2}} | {col3:<{w3}} |"

    print(sep)  # noqa: T201
    print(header)  # noqa: T201
    print(sep)  # noqa: T201
    for n, elapsed in results:
        throughput = n / elapsed if elapsed > 0 else float("inf")
        print(f"| {n:<{w1}} | {elapsed:<{w2}.4f} | {throughput:<{w3}.2f} |")  # noqa: T201
    print(sep)  # noqa: T201


if __name__ == "__main__":
    polarity_model: PolarityModel = cast(PolarityModel, track_init_time(PolarityModel))
    print("\n")  # noqa: T201

    verify_diff_cases(polarity_model)
    print("\n")  # noqa: T201

    run_model_track_time(polarity_model)
