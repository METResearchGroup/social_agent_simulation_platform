import uuid
from datetime import datetime

import pytest

from ml_tooling.emotion.classifier import EmotionModel
from ml_tooling.emotion.models import EmotionLabel


@pytest.fixture(scope="class")
def normal_case():
    def pipeline(text):
        return [
            [
                {"label": "anger", "score": 0.1},
                {"label": "disgust", "score": 0.2},
                {"label": "fear", "score": 0.3},
                {"label": "joy", "score": 0.1},
                {"label": "neutral", "score": 0.1},
                {"label": "sadness", "score": 0.1},
                {"label": "surprise", "score": 0.1},
            ]
        ]

    return EmotionModel(pipeline)


@pytest.fixture(scope="class")
def batch_size_two_case():
    def pipeline(text):
        return [
            [
                {"label": "anger", "score": 0.1},
                {"label": "disgust", "score": 0.2},
                {"label": "fear", "score": 0.3},
                {"label": "joy", "score": 0.1},
                {"label": "neutral", "score": 0.1},
                {"label": "sadness", "score": 0.1},
                {"label": "surprise", "score": 0.1},
            ],
            [
                {"label": "anger", "score": 0.1},
                {"label": "disgust", "score": 0.2},
                {"label": "fear", "score": 0.3},
                {"label": "joy", "score": 0.1},
                {"label": "neutral", "score": 0.1},
                {"label": "sadness", "score": 0.1},
                {"label": "surprise", "score": 0.1},
            ],
        ]

    return EmotionModel(pipeline)


class TestToEmotionLabel:
    def test_missing_emotion(self, normal_case):
        with pytest.raises(
            ValueError,
            match="Emotion pipeline response missing expected labels: \\{'surprise'\\}",
        ):
            normal_case._to_emotion_label(
                [
                    {"label": "anger", "score": 0.1},
                    {"label": "disgust", "score": 0.2},
                    {"label": "fear", "score": 0.3},
                    {"label": "joy", "score": 0.1},
                    {"label": "neutral", "score": 0.1},
                    {"label": "sadness", "score": 0.1},
                ],
                "some text",
            )

    def test_wrong_emotion(self, normal_case):
        with pytest.raises(
            ValueError,
            match="Emotion pipeline response missing expected labels: \\{'surprise'\\}",
        ):
            normal_case._to_emotion_label(
                [
                    {"label": "anger", "score": 0.1},
                    {"label": "disgust", "score": 0.2},
                    {"label": "fear", "score": 0.3},
                    {"label": "joy", "score": 0.1},
                    {"label": "neutral", "score": 0.1},
                    {"label": "sadness", "score": 0.1},
                    {"label": "not surprise", "score": 0.1},
                ],
                "some text",
            )

    def _run_normal_case(self, normal_case) -> EmotionLabel:
        result: EmotionLabel = normal_case._to_emotion_label(
            [
                {"label": "anger", "score": 0.1},
                {"label": "disgust", "score": 0.2},
                {"label": "fear", "score": 0.3},
                {"label": "joy", "score": 0.1},
                {"label": "neutral", "score": 0.1},
                {"label": "sadness", "score": 0.1},
                {"label": "surprise", "score": 0.1},
            ],
            "some text",
        )
        return result

    def test_normal_case_all_correct_emotions(self, normal_case):
        result = self._run_normal_case(normal_case)

        expected = (0.1, 0.2, 0.3, 0.1, 0.1, 0.1, 0.1)

        actual = (
            result.anger_score,
            result.disgust_score,
            result.fear_score,
            result.joy_score,
            result.neutral_score,
            result.sadness_score,
            result.surprise_score,
        )

        assert actual == expected

    def test_normal_case_valid_timestamp(self, normal_case):
        result = self._run_normal_case(normal_case)
        datetime.strptime(result.label_timestamp, "%Y_%m_%d-%H:%M:%S")

    def test_normal_case_valid_uuid(self, normal_case):
        result = self._run_normal_case(normal_case)
        uuid.UUID(result.text_id)

    def test_normal_case_text_kept(self, normal_case):
        result = self._run_normal_case(normal_case)
        expected = "some text"
        actual = result.text

        assert actual == expected


class TestExtractEmotions:
    def test_normal_case_text_kept(self, normal_case):
        res = normal_case.extract_emotions("random text")
        actual = res.text

        assert actual == "random text"


class TestExtractEmotionsBatch:
    def test_too_many_results(self, batch_size_two_case):
        with pytest.raises(
            ValueError,
            match="Emotion pipeline returned unexpected batch size",
        ):
            batch_size_two_case.extract_emotions_batch(["text2"])

    def test_too_few_results(self, normal_case):
        with pytest.raises(
            ValueError,
            match="Emotion pipeline returned unexpected batch size",
        ):
            normal_case.extract_emotions_batch(["text1", "text2"])

    def test_normal_case_all_texts_kept(self, normal_case):
        actual = normal_case.extract_emotions_batch(["hey"])
        assert actual[0].text == "hey"

    def empty_list(self, normal_case):
        assert normal_case.extract_emotions_batch(None) == []
        assert normal_case.extract_emotions_batch([]) == []
