from __future__ import annotations

from ml_tooling.ner.classifier import NERModel


def test_extract_entities_uses_injected_pipeline():
    observed_texts: list[str | list[str]] = []

    def fake_pipeline(text_or_texts: str | list[str]):
        observed_texts.append(text_or_texts)
        return [
            {
                "word": "Berlin",
                "entity_group": "LOC",
                "score": 0.99,
            }
        ]

    classifier = NERModel(ner_pipeline=fake_pipeline)

    result = classifier.extract_entities("My name is Wolfgang and I live in Berlin")

    expected_result = 1
    assert len(result) == expected_result
    assert observed_texts == ["My name is Wolfgang and I live in Berlin"]
    assert result[0].text == "Berlin"
    assert result[0].label == "LOC"


def test_extract_entities_batch_uses_injected_pipeline():
    observed_texts: list[str | list[str]] = []

    def fake_pipeline(text_or_texts: str | list[str]):
        observed_texts.append(text_or_texts)
        return [
            [{"word": "Wolfgang", "entity_group": "PER", "score": 0.95}],
            [{"word": "Berlin", "entity_group": "LOC", "score": 0.98}],
        ]

    classifier = NERModel(ner_pipeline=fake_pipeline)

    result = classifier.extract_entities_batch(
        ["My name is Wolfgang", "I live in Berlin"]
    )

    expected_result = 2
    assert len(result) == expected_result
    assert observed_texts == [["My name is Wolfgang", "I live in Berlin"]]
    assert result[0][0].label == "PER"
    assert result[1][0].label == "LOC"
