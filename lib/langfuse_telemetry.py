"""Basic Langfuse telemetry."""

import os
from typing import Any

from langfuse import Langfuse


def get_langfuse_client() -> Langfuse | None:
    """Get Langfuse client if API keys are available."""
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    if not public_key or not secret_key:
        return None

    base_url = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
    return Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        base_url=base_url,
    )


def log_llm_request(
    client: Langfuse | None,
    model: str,
    input_data: dict[str, Any],
    output: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Log LLM request to Langfuse."""
    if not client:
        return

    try:
        with client.start_as_current_observation(
            as_type="span",
            name="generate_bio",
            metadata=metadata or {},
        ) as trace:
            with trace.start_as_current_observation(
                as_type="generation",
                name="bio_generation",
                model=model,
                input=input_data,
            ) as generation:
                generation.update(
                    output={"bio": output, "output_length": len(output)},
                )
    except Exception as e:
        raise Exception(f"Failed to log LLM request to Langfuse: {e}")
