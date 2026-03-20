"""One-off job to migrate data from bluesky_profiles and agent_bios to agent, agent_persona_bios, and user_agent_profile_metadata."""

import sys
import uuid

from db.adapters.sqlite.sqlite import (
    SqliteTransactionProvider,
    initialize_database,
)
from db.repositories.agent_bio_repository import create_sqlite_agent_bio_repository
from db.repositories.agent_repository import create_sqlite_agent_repository
from db.repositories.generated_bio_repository import (
    create_sqlite_generated_bio_repository,
)
from db.repositories.profile_repository import create_sqlite_profile_repository
from db.repositories.user_agent_profile_metadata_repository import (
    create_sqlite_user_agent_profile_metadata_repository,
)
from lib.agent_id import canonical_agent_id
from lib.timestamp_utils import get_current_timestamp
from simulation.core.models.agent import Agent, PersonaSource
from simulation.core.models.agent_bio import AgentBio, PersonaBioSource
from simulation.core.models.generated.bio import GeneratedBio
from simulation.core.models.user_agent_profile_metadata import UserAgentProfileMetadata

_DEFAULT_BIO_WHEN_EMPTY: str = "No bio provided."


def _resolve_bio(
    profile, generated_bios: dict[str, GeneratedBio]
) -> tuple[str, PersonaBioSource]:
    """Resolve persona bio text/source for a profile."""
    if profile.handle in generated_bios:
        return generated_bios[
            profile.handle
        ].generated_bio, PersonaBioSource.AI_GENERATED
    if profile.bio and profile.bio.strip():
        return profile.bio.strip(), PersonaBioSource.USER_PROVIDED
    return _DEFAULT_BIO_WHEN_EMPTY, PersonaBioSource.USER_PROVIDED


def _build_agent(profile, now: str) -> Agent:
    """Build the canonical Agent model for a migrated profile."""
    return Agent(
        agent_id=canonical_agent_id(profile.did),
        handle=profile.handle,
        persona_source=PersonaSource.SYNC_BLUESKY,
        display_name=profile.display_name,
        created_at=now,
        updated_at=now,
    )


def _build_metadata(profile, canonical_id: str, now: str) -> UserAgentProfileMetadata:
    """Build profile metadata snapshot for the migrated agent."""
    return UserAgentProfileMetadata(
        id=uuid.uuid4().hex,
        agent_id=canonical_id,
        followers_count=profile.followers_count,
        follows_count=profile.follows_count,
        posts_count=profile.posts_count,
        created_at=now,
        updated_at=now,
    )


def _create_agent_bio_if_missing(
    *,
    agent_bio_repo,
    canonical_id: str,
    bio_text: str,
    bio_source: PersonaBioSource,
    now: str,
) -> None:
    """Create agent bio exactly once during migration."""
    if agent_bio_repo.get_latest_agent_bio(canonical_id) is not None:
        return

    agent_bio = AgentBio(
        id=uuid.uuid4().hex,
        agent_id=canonical_id,
        persona_bio=bio_text,
        persona_bio_source=bio_source,
        created_at=now,
        updated_at=now,
    )
    agent_bio_repo.create_agent_bio(agent_bio)


def _migrate_profile(
    *,
    profile,
    generated_bios: dict[str, GeneratedBio],
    agent_repo,
    agent_bio_repo,
    metadata_repo,
    now: str,
) -> None:
    """Migrate one legacy profile into canonical agent tables."""
    agent = _build_agent(profile=profile, now=now)
    canonical_id = agent.agent_id
    agent_repo.create_or_update_agent(agent)

    bio_text, bio_source = _resolve_bio(profile=profile, generated_bios=generated_bios)
    _create_agent_bio_if_missing(
        agent_bio_repo=agent_bio_repo,
        canonical_id=canonical_id,
        bio_text=bio_text,
        bio_source=bio_source,
        now=now,
    )
    metadata_repo.create_or_update_metadata(
        _build_metadata(profile=profile, canonical_id=canonical_id, now=now)
    )


def main() -> None:
    """Migrate profiles and generated bios to new agent tables."""
    initialize_database()

    tx_provider = SqliteTransactionProvider()
    profile_repo = create_sqlite_profile_repository(transaction_provider=tx_provider)
    generated_bio_repo = create_sqlite_generated_bio_repository(
        transaction_provider=tx_provider
    )
    agent_repo = create_sqlite_agent_repository(transaction_provider=tx_provider)
    agent_bio_repo = create_sqlite_agent_bio_repository(
        transaction_provider=tx_provider
    )
    metadata_repo = create_sqlite_user_agent_profile_metadata_repository(
        transaction_provider=tx_provider
    )

    profiles = profile_repo.list_profiles()
    generated_bios = {
        bio.handle: bio for bio in generated_bio_repo.list_all_generated_bios()
    }

    now = get_current_timestamp()

    migrated_agents = len(profiles)
    for profile in profiles:
        _migrate_profile(
            profile=profile,
            generated_bios=generated_bios,
            agent_repo=agent_repo,
            agent_bio_repo=agent_bio_repo,
            metadata_repo=metadata_repo,
            now=now,
        )
    sys.stdout.write(f"Migrated {migrated_agents} agents.\n")


if __name__ == "__main__":
    main()
