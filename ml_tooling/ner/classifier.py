from transformers import pipeline

from lib.timestamp_utils import get_current_timestamp
from ml_tooling.ner.models import EntitySpan


class NERModel:
    def __init__(self):
        self.ner = pipeline(
            "token-classification",
            model="dslim/bert-base-NER",
            aggregation_strategy="simple",
        )

    def to_entity_span(self, entities) -> list[EntitySpan]:
        timestamp = get_current_timestamp()

        lo_entity_span = []
        for entity in entities:
            text = entity["word"]
            label = entity["entity_group"]
            score = float(entity["score"])

            lo_entity_span.append(
                EntitySpan(text=text, label=label, score=score, timestamp=timestamp)
            )
        return lo_entity_span

    def extract_entities(self, text: str) -> list[EntitySpan]:
        response = self.ner(text)

        return self.to_entity_span(response)

    def extract_entities_batch(self, texts: list[str]) -> list[list[EntitySpan]]:
        response = self.ner(texts)

        lolo_entity_span = [self.to_entity_span(entity) for entity in response]
        return lolo_entity_span
