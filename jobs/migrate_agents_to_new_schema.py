"""One-off job to migrate data from bluesky_profiles and agent_bios to agent, agent_persona_bios, and user_agent_profile_metadata."""

import uuid

from db.adapters.sqlite.sqlite import initialize_database
from db.repositories.agent_bio_repository import create_sqlite_agent_bio_repository
from db.repositories.agent_repository import create_sqlite_agent_repository
from db.repositories.generated_bio_repository import (
    create_sqlite_generated_bio_repository,
)
from db.repositories.profile_repository import create_sqlite_profile_repository
from db.repositories.user_agent_profile_metadata_repository import (
    create_sqlite_user_agent_profile_metadata_repository,
)
from lib.timestamp_utils import get_current_timestamp
from simulation.core.models.agent import Agent, PersonaSource
from simulation.core.models.agent_bio import AgentBio, PersonaBioSource
from simulation.core.models.user_agent_profile_metadata import UserAgentProfileMetadata

_DEFAULT_BIO_WHEN_EMPTY: str = "No bio provided."


def main() -> None:
    """Migrate profiles and generated bios to new agent tables."""
    initialize_database()

    profile_repo = create_sqlite_profile_repository()
    generated_bio_repo = create_sqlite_generated_bio_repository()
    agent_repo = create_sqlite_agent_repository()
    agent_bio_repo = create_sqlite_agent_bio_repository()
    metadata_repo = create_sqlite_user_agent_profile_metadata_repository()

    profiles = profile_repo.list_profiles()
    generated_bios = {
        bio.handle: bio for bio in generated_bio_repo.list_all_generated_bios()
    }

    now = get_current_timestamp()

    for profile in profiles:
        agent = Agent(
            agent_id=profile.did,
            handle=profile.handle,
            persona_source=PersonaSource.SYNC_BLUESKY,
            display_name=profile.display_name,
            created_at=now,
            updated_at=now,
        )
        agent_repo.create_or_update_agent(agent)

        bio_text: str
        bio_source: PersonaBioSource
        if profile.handle in generated_bios:
            bio_text = generated_bios[profile.handle].generated_bio
            bio_source = PersonaBioSource.AI_GENERATED
        elif profile.bio and profile.bio.strip():
            bio_text = profile.bio.strip()
            bio_source = PersonaBioSource.USER_PROVIDED
        else:
            bio_text = _DEFAULT_BIO_WHEN_EMPTY
            bio_source = PersonaBioSource.USER_PROVIDED

        if agent_bio_repo.get_latest_agent_bio(profile.did) is None:
            agent_bio = AgentBio(
                id=uuid.uuid4().hex,
                agent_id=profile.did,
                persona_bio=bio_text,
                persona_bio_source=bio_source,
                created_at=now,
                updated_at=now,
            )
            agent_bio_repo.create_agent_bio(agent_bio)

        metadata = UserAgentProfileMetadata(
            id=uuid.uuid4().hex,
            agent_id=profile.did,
            followers_count=profile.followers_count,
            follows_count=profile.follows_count,
            posts_count=profile.posts_count,
            created_at=now,
            updated_at=now,
        )
        metadata_repo.create_or_update_metadata(metadata)

    print(f"Migrated {len(profiles)} agents.")


if __name__ == "__main__":
    main()
