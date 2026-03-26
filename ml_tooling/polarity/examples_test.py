from typing import cast

from transformers import logging as transformers_logging

from ml_tooling.polarity.classifier import PolarityModel
from ml_tooling.polarity.models import PolarityLabel
from ml_tooling.verification.helpers import (
    evaluate_model_performance,
    init_model,
    print_table,
)

transformers_logging.set_verbosity_error()


def print_polarity_table(label: PolarityLabel, case_name: str) -> None:
    col_values = [(label.polarity_label.value, f"{label.polarity_prob:.4f}")]
    print_table(case_name, label.text, ["label", "prob"], col_values)


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


if __name__ == "__main__":
    print("\n")  # noqa: T201

    polarity_model: PolarityModel = cast(PolarityModel, init_model(PolarityModel))

    verify_diff_cases(polarity_model)

    evaluate_model_performance(
        polarity_model.extract_polarity,
        "This is absolutely the most wonderful, joyful, and amazing day of my life!",
    )

    print("\n")  # noqa: T201
