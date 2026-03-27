from typing import cast

from transformers import logging as transformers_logging

from ml_tooling.ner.classifier import NERModel
from ml_tooling.ner.models import EntitySpan
from ml_tooling.verification.helpers import (
    evaluate_model_performance,
    init_model,
    print_table,
)

transformers_logging.set_verbosity_error()


def print_ner_table(entities: list[EntitySpan], case_name: str, text: str) -> None:
    col_values = [(e.text, e.label, f"{e.score:.4f}") for e in entities]
    print_table(case_name, text, ["entity", "label", "score"], col_values)


def verify_diff_cases(ner_model: NERModel) -> None:
    cases = [
        ("My name is Wolfgang and I live in Berlin", "perfect"),
        ("my name is wolfgang and i live in berlin", "lowercase"),
        ("this is a sentence and it is about to end right about now", "zero entities"),
        (
            "I am Mayor Mamdani of New York and I just got elected very recently",
            "recent entity",
        ),
    ]

    for text, case_name in cases:
        result = ner_model.extract_entities(text)
        print_ner_table(result, case_name, text)


if __name__ == "__main__":
    print("\n")  # noqa: T201
    ner_model: NERModel = cast(NERModel, init_model(NERModel))

    verify_diff_cases(ner_model)

    evaluate_model_performance(
        ner_model.extract_entities, "My name is Wolfgang and I live in Berlin"
    )

    print("\n")  # noqa: T201
