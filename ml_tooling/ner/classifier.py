from collections.abc import Callable
from typing import Final, Literal, cast

from transformers import pipeline

from lib.timestamp_utils import get_current_timestamp
from ml_tooling.ner.models import EntitySpan

RawEntity = dict[str, str | float]
NerBatchResponse = list[list[RawEntity]]
NerSingleResponse = list[RawEntity]
NerResponse = NerSingleResponse | NerBatchResponse
NerCallable = Callable[[str | list[str]], NerResponse]

NER_TASK: Final[Literal["token-classification"]] = "token-classification"
NER_MODEL: str = "dslim/bert-base-NER"
NER_AGGREGATION_STRATEGY: Final[Literal["simple"]] = "simple"


def build_default_ner_pipeline() -> NerCallable:
    return cast(
        NerCallable,
        pipeline(
            NER_TASK,
            model=NER_MODEL,
            aggregation_strategy=NER_AGGREGATION_STRATEGY,
        ),
    )


class NERModel:
    def __init__(self, ner_pipeline: NerCallable | None = None) -> None:
        self._ner_pipeline: NerCallable = (
            build_default_ner_pipeline() if ner_pipeline is None else ner_pipeline
        )

    def _to_entity_span(self, entities: NerSingleResponse) -> list[EntitySpan]:
        timestamp = get_current_timestamp()

        entity_spans: list[EntitySpan] = []
        for entity in entities:
            text = str(entity["word"])
            label = str(entity["entity_group"])
            score = float(entity["score"])

            entity_spans.append(
                EntitySpan(text=text, label=label, score=score, timestamp=timestamp)
            )
        return entity_spans

    def extract_entities(self, text: str) -> list[EntitySpan]:
        response = cast(NerSingleResponse, self._ner_pipeline(text))

        return self._to_entity_span(response)

    def extract_entities_batch(self, texts: list[str]) -> list[list[EntitySpan]]:
        response = cast(NerBatchResponse, self._ner_pipeline(texts))

        batch_entity_spans = [self._to_entity_span(entity) for entity in response]
        return batch_entity_spans
