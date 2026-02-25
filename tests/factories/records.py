from __future__ import annotations

from simulation.core.models.agent import Agent, PersonaSource
from simulation.core.models.agent_bio import AgentBio, PersonaBioSource
from simulation.core.models.user_agent_profile_metadata import UserAgentProfileMetadata
from tests.factories._helpers import _timestamp_utc_compact
from tests.factories.base import BaseFactory
from tests.factories.context import get_faker


class AgentRecordFactory(BaseFactory[Agent]):
    @classmethod
    def create(
        cls,
        *,
        agent_id: str | None = None,
        handle: str | None = None,
        persona_source: PersonaSource = PersonaSource.SYNC_BLUESKY,
        display_name: str | None = None,
        created_at: str | None = None,
        updated_at: str | None = None,
    ) -> Agent:
        fake = get_faker()
        agent_id_value = agent_id if agent_id is not None else f"did:plc:{fake.uuid4()}"
        handle_value = (
            handle if handle is not None else f"@{fake.user_name()}.bsky.social"
        )
        created_at_value = (
            created_at if created_at is not None else _timestamp_utc_compact()
        )
        updated_at_value = updated_at if updated_at is not None else created_at_value
        display_name_value = display_name if display_name is not None else handle_value
        return Agent(
            agent_id=agent_id_value,
            handle=handle_value,
            persona_source=persona_source,
            display_name=display_name_value,
            created_at=created_at_value,
            updated_at=updated_at_value,
        )


class AgentBioFactory(BaseFactory[AgentBio]):
    @classmethod
    def create(
        cls,
        *,
        bio_id: str | None = None,
        agent_id: str | None = None,
        persona_bio: str | None = None,
        persona_bio_source: PersonaBioSource = PersonaBioSource.AI_GENERATED,
        created_at: str | None = None,
        updated_at: str | None = None,
    ) -> AgentBio:
        fake = get_faker()
        agent_id_value = agent_id if agent_id is not None else f"did:plc:{fake.uuid4()}"
        created_at_value = (
            created_at if created_at is not None else _timestamp_utc_compact()
        )
        updated_at_value = updated_at if updated_at is not None else created_at_value
        return AgentBio(
            id=bio_id if bio_id is not None else f"bio_{fake.uuid4()}",
            agent_id=agent_id_value,
            persona_bio=persona_bio
            if persona_bio is not None
            else fake.sentence(nb_words=8),
            persona_bio_source=persona_bio_source,
            created_at=created_at_value,
            updated_at=updated_at_value,
        )


class UserAgentProfileMetadataFactory(BaseFactory[UserAgentProfileMetadata]):
    @classmethod
    def create(
        cls,
        *,
        metadata_id: str | None = None,
        agent_id: str | None = None,
        followers_count: int | None = None,
        follows_count: int | None = None,
        posts_count: int | None = None,
        created_at: str | None = None,
        updated_at: str | None = None,
    ) -> UserAgentProfileMetadata:
        fake = get_faker()
        agent_id_value = agent_id if agent_id is not None else f"did:plc:{fake.uuid4()}"
        created_at_value = (
            created_at if created_at is not None else _timestamp_utc_compact()
        )
        updated_at_value = updated_at if updated_at is not None else created_at_value
        return UserAgentProfileMetadata(
            id=metadata_id if metadata_id is not None else f"meta_{fake.uuid4()}",
            agent_id=agent_id_value,
            followers_count=followers_count
            if followers_count is not None
            else fake.random_int(0, 10_000),
            follows_count=follows_count
            if follows_count is not None
            else fake.random_int(0, 10_000),
            posts_count=posts_count
            if posts_count is not None
            else fake.random_int(0, 10_000),
            created_at=created_at_value,
            updated_at=updated_at_value,
        )
