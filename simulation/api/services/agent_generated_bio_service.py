"""Service responsible for generating AI bios for user-created agents."""

import uuid
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, field_validator

from db.adapters.base import TransactionProvider
from db.adapters.sqlite.sqlite import SqliteTransactionProvider
from db.repositories.agent_bio_repository import create_sqlite_agent_bio_repository
from db.repositories.agent_generated_bio_repository import (
    create_sqlite_agent_generated_bio_repository,
)
from db.repositories.agent_repository import create_sqlite_agent_repository
from db.repositories.interfaces import (
    AgentBioRepository,
    AgentGeneratedBioRepository,
    AgentRepository,
    UserAgentProfileMetadataRepository,
)
from db.repositories.user_agent_profile_metadata_repository import (
    create_sqlite_user_agent_profile_metadata_repository,
)
from lib.timestamp_utils import get_current_timestamp
from lib.validation_utils import validate_non_empty_string
from ml_tooling.llm.config.model_registry import ModelConfigRegistry
from ml_tooling.llm.llm_service import LLMService, get_llm_service
from simulation.core.handle_utils import normalize_handle
from simulation.core.models.agent_generated_bio import AgentGeneratedBio
from simulation.core.models.generated.base import GenerationMetadata


class AgentGeneratedBioPrediction(BaseModel):
    """Structured response expected from the LLM."""

    bio: str

    @field_validator("bio")
    @classmethod
    def validate_bio(cls, value: str) -> str:
        return validate_non_empty_string(value, "bio")


AGENT_BIO_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You write concise, third-person persona bios for AI agents. The bio should be
    1-2 paragraphs long, grounded in the agent's stats, and suitable for a social media persona.
    Respond with JSON that contains a single string field named "bio".""",
        ),
        (
            "human",
            """Generate a new agent bio using the data below.

    Display Name: {display_name}
    Handle: @{handle}
    Current Bio: {current_bio}
    Followers: {followers_count}
    Following: {follows_count}
    Total Posts: {posts_count}

    Return JSON: {{ "bio": "<your new bio>" }}
    """,
        ),
    ]
)


def create_generated_bio_for_agent(
    *,
    handle: str,
    agent_repo: AgentRepository | None = None,
    bio_repo: AgentBioRepository | None = None,
    metadata_repo: UserAgentProfileMetadataRepository | None = None,
    generated_bio_repo: AgentGeneratedBioRepository | None = None,
    transaction_provider: TransactionProvider | None = None,
    llm_service: LLMService | None = None,
    model: str | None = None,
) -> AgentGeneratedBio:
    """Generate and persist a new AI-generated bio for the requested agent handle."""
    normalized_handle = normalize_handle(handle)
    if (
        transaction_provider is None
        or agent_repo is None
        or bio_repo is None
        or metadata_repo is None
        or generated_bio_repo is None
    ):
        transaction_provider = transaction_provider or SqliteTransactionProvider()
        agent_repo = agent_repo or create_sqlite_agent_repository(
            transaction_provider=transaction_provider
        )
        bio_repo = bio_repo or create_sqlite_agent_bio_repository(
            transaction_provider=transaction_provider
        )
        metadata_repo = (
            metadata_repo
            or create_sqlite_user_agent_profile_metadata_repository(
                transaction_provider=transaction_provider
            )
        )
        generated_bio_repo = (
            generated_bio_repo
            or create_sqlite_agent_generated_bio_repository(
                transaction_provider=transaction_provider
            )
        )

    assert agent_repo is not None
    assert bio_repo is not None
    assert metadata_repo is not None
    assert generated_bio_repo is not None

    agent = agent_repo.get_agent_by_handle(normalized_handle)
    if agent is None:
        raise LookupError(f"Agent '{normalized_handle}' not found")

    persona_bio_obj = bio_repo.get_latest_agent_bio(agent.agent_id)
    current_bio = persona_bio_obj.persona_bio if persona_bio_obj else "No bio provided."
    metadata = metadata_repo.get_by_agent_id(agent.agent_id)
    followers = metadata.followers_count if metadata else 0
    follows = metadata.follows_count if metadata else 0
    posts = metadata.posts_count if metadata else 0

    prompt = AGENT_BIO_PROMPT.format_messages(
        display_name=agent.display_name,
        handle=agent.handle.lstrip("@"),
        current_bio=current_bio,
        followers_count=followers,
        follows_count=follows,
        posts_count=posts,
    )
    messages: list[dict[str, Any]] = [message.dict() for message in prompt]

    llm = llm_service or get_llm_service()
    response = llm.structured_completion(
        messages=messages,
        response_model=AgentGeneratedBioPrediction,
        model=model,
    )

    generated_bio_text = response.bio.strip()
    model_used = model or ModelConfigRegistry.get_default_model()
    metadata_payload = GenerationMetadata(
        model_used=model_used,
        generation_metadata={
            "followers_count": followers,
            "following_count": follows,
            "posts_count": posts,
        },
        created_at=get_current_timestamp(),
    )
    agent_generated_bio = AgentGeneratedBio(
        id=uuid.uuid4().hex,
        agent_id=agent.agent_id,
        generated_bio=generated_bio_text,
        metadata=metadata_payload,
    )

    return generated_bio_repo.create_agent_generated_bio(agent_generated_bio)


def list_agent_generated_bios_for_agent(
    *,
    handle: str,
    agent_repo: AgentRepository | None = None,
    generated_bio_repo: AgentGeneratedBioRepository | None = None,
    transaction_provider: TransactionProvider | None = None,
) -> list[AgentGeneratedBio]:
    """Return persisted bios for the requested agent handle."""
    normalized_handle = normalize_handle(handle)
    transaction_provider = transaction_provider or SqliteTransactionProvider()
    agent_repo = agent_repo or create_sqlite_agent_repository(
        transaction_provider=transaction_provider
    )
    generated_bio_repo = (
        generated_bio_repo
        or create_sqlite_agent_generated_bio_repository(
            transaction_provider=transaction_provider
        )
    )
    agent = agent_repo.get_agent_by_handle(normalized_handle)
    if agent is None:
        raise LookupError(f"Agent '{normalized_handle}' not found")

    return generated_bio_repo.list_agent_generated_bios(agent.agent_id)
