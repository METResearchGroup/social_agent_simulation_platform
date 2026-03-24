from typing import Protocol


class RunIdRow(Protocol):
    run_id: str


class HasGenerationMetadataFields(Protocol):
    """Structural type for rows carrying generation-metadata columns."""

    model_used: str | None
    generation_metadata_json: str | None
    generation_created_at: str | None
    created_at: str
