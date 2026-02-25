from __future__ import annotations

from datetime import timezone

from simulation.core.models.generated.base import GenerationMetadata
from simulation.core.models.generated.bio import GeneratedBio
from tests.factories.base import BaseFactory
from tests.factories.context import get_faker


def _timestamp_utc_compact() -> str:
    fake = get_faker()
    dt = fake.date_time(tzinfo=timezone.utc)
    return dt.strftime("%Y_%m_%d-%H:%M:%S")


class GenerationMetadataFactory(BaseFactory[GenerationMetadata]):
    @classmethod
    def create(
        cls,
        *,
        created_at: str | None = None,
        model_used: str | None = None,
        generation_metadata: dict[str, object] | None = None,
    ) -> GenerationMetadata:
        return GenerationMetadata(
            created_at=created_at
            if created_at is not None
            else _timestamp_utc_compact(),
            model_used=model_used,
            generation_metadata=generation_metadata,
        )


class GeneratedBioFactory(BaseFactory[GeneratedBio]):
    @classmethod
    def create(
        cls,
        *,
        handle: str | None = None,
        generated_bio: str | None = None,
        metadata: GenerationMetadata | None = None,
    ) -> GeneratedBio:
        fake = get_faker()
        return GeneratedBio(
            handle=handle if handle is not None else f"{fake.user_name()}.bsky.social",
            generated_bio=generated_bio
            if generated_bio is not None
            else fake.sentence(nb_words=10),
            metadata=metadata
            if metadata is not None
            else GenerationMetadataFactory.create(),
        )
