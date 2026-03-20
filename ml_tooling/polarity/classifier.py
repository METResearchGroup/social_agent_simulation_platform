import uuid
from collections.abc import Callable
from typing import Final, Literal, cast

import torch
from scipy.special import softmax
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from lib.timestamp_utils import get_current_timestamp
from ml_tooling.polarity.models import PolarityLabel, PolarityValue

RawPolarity = dict[str, float]
PolarityBatchResponse = list[list[RawPolarity]]
PolaritySingleResponse = list[RawPolarity]
PolarityResponse = PolarityBatchResponse | PolaritySingleResponse

PolarityCallable = Callable[[str | list[str]], PolarityResponse]

POLARITY_TASK: Final[Literal["sentiment-analysis"]] = "sentiment-analysis"
POLARITY_MODEL: Final[str] = "cardiffnlp/twitter-roberta-base-sentiment-latest"


class PolarityPipeline:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained(POLARITY_MODEL)
        self.model = AutoModelForSequenceClassification.from_pretrained(POLARITY_MODEL)
        self.labels = ["negative", "neutral", "positive"]

    def _preprocess(self, text: str) -> str:
        tokens = []
        for t in text.split(" "):
            if t.startswith("@") and len(t) > 1:
                t = "@user"
            if t.startswith("http"):
                t = "http"
            tokens.append(t)
        return " ".join(tokens)

    def __call__(self, text: str | list[str]) -> PolarityResponse:
        is_single = isinstance(text, str)

        input_list = [text] if is_single else text

        normalized_inputs = [self._preprocess(t) for t in input_list]
        encoded = self.tokenizer(
            normalized_inputs, return_tensors="pt", padding=True, truncation=True
        )

        with torch.no_grad():
            output = self.model(**encoded)

        logits = output.logits.numpy()
        probs_batch = softmax(logits, axis=1)

        results = []
        for probs in probs_batch:
            results.append(
                [
                    {"label": label, "score": score}
                    for label, score in zip(self.labels, probs, strict=True)
                ]
            )

        return results[0] if is_single else results


def build_default_polarity_pipeline() -> PolarityCallable:
    return cast(PolarityCallable, PolarityPipeline())


class PolarityModel:
    def __init__(self, polarity_pipeline: PolarityCallable | None = None) -> None:
        self._polarity_pipeline: PolarityCallable = (
            build_default_polarity_pipeline()
            if polarity_pipeline is None
            else polarity_pipeline
        )

    def _to_polarity_label(
        self, polarity_distribution: PolaritySingleResponse, text: str
    ) -> PolarityLabel:
        timestamp = get_current_timestamp()
        text_id = str(uuid.uuid4())

        polarity_prob = -float("inf")
        polarity_label = None
        for dictionary in polarity_distribution:
            if dictionary["score"] > polarity_prob:
                polarity_prob = dictionary["score"]
                polarity_label = dictionary["label"]

        return PolarityLabel(
            text_id=text_id,
            text=text,
            polarity_label=cast(PolarityValue, polarity_label),
            polarity_prob=polarity_prob,
            label_timestamp=timestamp,
        )

    def extract_polarity(self, text: str) -> PolarityLabel:
        response = cast(PolaritySingleResponse, self._polarity_pipeline(text))
        return self._to_polarity_label(response, text)

    def extract_polarity_batch(self, texts: list[str]) -> list[PolarityLabel]:
        response = cast(PolarityBatchResponse, self._polarity_pipeline(texts))
        if len(response) != len(texts):
            raise ValueError("Polarity pipeline returned unexpected batch size")
        return [
            self._to_polarity_label(response[i], text) for i, text in enumerate(texts)
        ]
