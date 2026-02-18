from typing import TypeAlias

from pydantic import BaseModel
from pydantic import JsonValue as PydanticJsonValue

GenerationMetadataPayload: TypeAlias = dict[str, PydanticJsonValue]


class GenerationMetadata(BaseModel):
    """Metadata about AI generation process."""

    model_used: str | None = None
    generation_metadata: GenerationMetadataPayload | None = None
    created_at: str
