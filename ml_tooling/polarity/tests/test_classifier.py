# bandit: ignore: B101
import uuid
from datetime import datetime

import pytest

from ml_tooling.polarity.classifier import PolarityModel
from ml_tooling.polarity.models import PolarityLabel, PolarityValue


@pytest.fixture(scope="class")
def random_model():
    def pipeline(text):
        return [
            {"label": PolarityValue.NEGATIVE, "score": 0.33},
            {"label": PolarityValue.NEUTRAL, "score": 0.34},
            {"label": PolarityValue.POSITIVE, "score": 0.33},
        ]

    return PolarityModel(pipeline)


@pytest.fixture(scope="class")
def batch_size_two_case():
    def pipeline(text):
        return [
            [
                {"label": PolarityValue.NEGATIVE, "score": 0.33},
                {"label": PolarityValue.NEUTRAL, "score": 0.34},
                {"label": PolarityValue.POSITIVE, "score": 0.33},
            ],
            [
                {"label": PolarityValue.NEGATIVE, "score": 0.33},
                {"label": PolarityValue.NEUTRAL, "score": 0.34},
                {"label": PolarityValue.POSITIVE, "score": 0.33},
            ],
        ]

    return PolarityModel(pipeline)


class TestToPolarityLabel:
    def test_negative_case(self, random_model):
        result: PolarityLabel = random_model._to_polarity_label(
            [
                {"label": PolarityValue.NEGATIVE, "score": 0.9},
                {"label": PolarityValue.NEUTRAL, "score": 0.05},
                {"label": PolarityValue.POSITIVE, "score": 0.05},
            ],
            "so negative...",
        )

        expected_label = PolarityValue.NEGATIVE
        expected_prob = 0.9
        assert result.polarity_label == expected_label  # nosec B101
        assert result.polarity_prob == expected_prob  # nosec B101

    def test_neutral_case(self, random_model):
        result: PolarityLabel = random_model._to_polarity_label(
            [
                {"label": PolarityValue.NEGATIVE, "score": 0.1},
                {"label": PolarityValue.NEUTRAL, "score": 0.8},
                {"label": PolarityValue.POSITIVE, "score": 0.1},
            ],
            "this is neutral",
        )

        expected_label = PolarityValue.NEUTRAL
        expected_prob = 0.8
        assert result.polarity_label == expected_label  # nosec B101
        assert result.polarity_prob == expected_prob  # nosec B101

    def test_positive_case(self, random_model):
        result: PolarityLabel = random_model._to_polarity_label(
            [
                {"label": PolarityValue.NEGATIVE, "score": 0.15},
                {"label": PolarityValue.NEUTRAL, "score": 0.15},
                {"label": PolarityValue.POSITIVE, "score": 0.7},
            ],
            "positive talk!",
        )

        expected_label = PolarityValue.POSITIVE
        expected_prob = 0.7
        assert result.polarity_label == expected_label  # nosec B101
        assert result.polarity_prob == expected_prob  # nosec B101

    def _run_to_polarity_label(self, random_model) -> PolarityLabel:
        result: PolarityLabel = random_model._to_polarity_label(
            [
                {"label": PolarityValue.NEGATIVE, "score": 0.34},
                {"label": PolarityValue.NEUTRAL, "score": 0.33},
                {"label": PolarityValue.POSITIVE, "score": 0.33},
            ],
            "some text",
        )
        return result

    def test_valid_timestamp(self, random_model):
        result: PolarityLabel = self._run_to_polarity_label(random_model)
        assert datetime.strptime(result.label_timestamp, "%Y_%m_%d-%H:%M:%S")  # nosec B101

    def test_valid_uuid(self, random_model):
        result: PolarityLabel = self._run_to_polarity_label(random_model)
        assert uuid.UUID(result.text_id)  # nosec B101

    def test_text_kept(self, random_model):
        result: PolarityLabel = self._run_to_polarity_label(random_model)
        expected = "some text"
        actual = result.text

        assert actual == expected  # nosec B101


class TestExtractPolarity:
    def test_text_kept(self, random_model):
        result: PolarityLabel = random_model.extract_polarity("polarity")
        assert result.text == "polarity"  # nosec B101


class TextExtractPolarityBatch:
    def test_too_many_results(self, batch_size_two_case):
        with pytest.raises(
            ValueError,
            match="Polarity pipeline returned unexpected batch size",
        ):
            batch_size_two_case.extract_emotions_batch(["text1"])

    def test_too_few_results(self, random_model):
        with pytest.raises(
            ValueError,
            match="Polarity pipeline returned unexpected batch size",
        ):
            random_model.extract_emotions_batch(["text1", "text2"])

    def test_all_texts_kept(self, batch_size_two_case):
        actual = batch_size_two_case.extract_emotions_batch(["text1", "text2"])
        assert actual[0].text == "text1"  # nosec B101
        assert actual[1].text == "text2"  # nosec B101
