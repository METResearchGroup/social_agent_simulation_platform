"""Write-side CQRS service for simulation agent creation."""

import uuid

from db.adapters.base import TransactionProvider
from db.adapters.sqlite.sqlite import SqliteTransactionProvider
from db.repositories.agent_bio_repository import create_sqlite_agent_bio_repository
from db.repositories.agent_repository import create_sqlite_agent_repository
from db.repositories.agent_seed_comment_repository import (
    create_sqlite_agent_seed_comment_repository,
)
from db.repositories.agent_seed_follow_repository import (
    create_sqlite_agent_seed_follow_repository,
)
from db.repositories.agent_seed_like_repository import (
    create_sqlite_agent_seed_like_repository,
)
from db.repositories.interfaces import (
    AgentBioRepository,
    AgentRepository,
    AgentSeedCommentRepository,
    AgentSeedFollowRepository,
    AgentSeedLikeRepository,
    UserAgentProfileMetadataRepository,
)
from db.repositories.user_agent_profile_metadata_repository import (
    create_sqlite_user_agent_profile_metadata_repository,
)
from lib.timestamp_utils import get_current_timestamp
from simulation.api.schemas.simulation import AgentSchema, CreateAgentRequest
from simulation.core.exceptions import HandleAlreadyExistsError
from simulation.core.handle_utils import normalize_handle
from simulation.core.models.agent import Agent, PersonaSource
from simulation.core.models.agent_bio import AgentBio, PersonaBioSource
from simulation.core.models.agent_seed_actions import (
    AgentSeedComment,
    AgentSeedFollow,
    AgentSeedLike,
)
from simulation.core.models.user_agent_profile_metadata import UserAgentProfileMetadata


def create_agent(
    req: CreateAgentRequest,
    *,
    transaction_provider: TransactionProvider | None = None,
    agent_repo: AgentRepository | None = None,
    bio_repo: AgentBioRepository | None = None,
    metadata_repo: UserAgentProfileMetadataRepository | None = None,
    seed_like_repo: AgentSeedLikeRepository | None = None,
    seed_comment_repo: AgentSeedCommentRepository | None = None,
    seed_follow_repo: AgentSeedFollowRepository | None = None,
) -> AgentSchema:
    """Create a user-generated agent with bio and metadata. Atomic multi-table write."""
    handle = normalize_handle(req.handle)
    display_name = req.display_name.strip()
    bio_text = (req.bio or "").strip() or "No bio provided."

    if (
        transaction_provider is None
        or agent_repo is None
        or bio_repo is None
        or metadata_repo is None
    ):
        transaction_provider = transaction_provider or SqliteTransactionProvider()
        agent_repo = agent_repo or create_sqlite_agent_repository(
            transaction_provider=transaction_provider
        )
        bio_repo = bio_repo or create_sqlite_agent_bio_repository(
            transaction_provider=transaction_provider
        )
        metadata_repo = metadata_repo or (
            create_sqlite_user_agent_profile_metadata_repository(
                transaction_provider=transaction_provider
            )
        )
        seed_like_repo = seed_like_repo or create_sqlite_agent_seed_like_repository(
            transaction_provider=transaction_provider
        )
        seed_comment_repo = (
            seed_comment_repo
            or create_sqlite_agent_seed_comment_repository(
                transaction_provider=transaction_provider
            )
        )
        seed_follow_repo = (
            seed_follow_repo
            or create_sqlite_agent_seed_follow_repository(
                transaction_provider=transaction_provider
            )
        )

    # TODO: that this can cause a slight race condition if we do this check
    # before the below context manager for writing the agent to the database.
    # This is a known issue, and we'll revisit this in the future.
    if agent_repo.get_agent_by_handle(handle) is not None:
        raise HandleAlreadyExistsError(handle)

    agent_id = _generate_agent_id()
    now = get_current_timestamp()

    agent = _generate_agent(agent_id, handle, display_name, now)
    agent_bio = _generate_agent_bio(agent_id, bio_text, now)
    metadata = _generate_user_agent_profile_metadata(agent_id, now)

    seed_likes: list[AgentSeedLike] = []
    seen_post_uris: set[str] = set()
    for uri in req.liked_post_uris or []:
        u = (uri or "").strip()
        if not u or u in seen_post_uris:
            continue
        seen_post_uris.add(u)
        seed_likes.append(
            AgentSeedLike(
                seed_like_id=uuid.uuid4().hex,
                agent_handle=handle,
                post_uri=u,
                created_at=now,
            )
        )

    seed_comments: list[AgentSeedComment] = []
    for c in req.comments or []:
        text = (c.text or "").strip()
        if not text:
            continue
        post_uri = (c.post_uri or "").strip() or None
        seed_comments.append(
            AgentSeedComment(
                seed_comment_id=uuid.uuid4().hex,
                agent_handle=handle,
                post_uri=post_uri,
                text=text,
                created_at=now,
            )
        )

    seed_follows: list[AgentSeedFollow] = []
    seen_user_ids: set[str] = set()
    for raw in req.linked_agent_handles or []:
        raw_s = (raw or "").strip()
        if not raw_s:
            continue
        user_id = normalize_handle(raw_s)
        if user_id == handle or user_id in seen_user_ids:
            continue
        seen_user_ids.add(user_id)
        seed_follows.append(
            AgentSeedFollow(
                seed_follow_id=uuid.uuid4().hex,
                agent_handle=handle,
                user_id=user_id,
                created_at=now,
            )
        )

    with transaction_provider.run_transaction() as conn:
        agent_repo.create_or_update_agent(agent, conn=conn)
        bio_repo.create_agent_bio(agent_bio, conn=conn)
        metadata_repo.create_or_update_metadata(metadata, conn=conn)
        if seed_like_repo is not None and seed_likes:
            seed_like_repo.write_agent_seed_likes(seed_likes, conn=conn)
        if seed_comment_repo is not None and seed_comments:
            seed_comment_repo.write_agent_seed_comments(seed_comments, conn=conn)
        if seed_follow_repo is not None and seed_follows:
            seed_follow_repo.write_agent_seed_follows(seed_follows, conn=conn)

    return _build_agent_schema(agent.handle, agent.display_name, bio_text)


def _build_agent_schema(handle: str, display_name: str, bio_text: str) -> AgentSchema:
    """Build AgentSchema for a newly created agent (zero counts)."""
    return AgentSchema(
        handle=handle,
        name=display_name,
        bio=bio_text,
        generated_bio="",
        followers=0,
        following=0,
        posts_count=0,
    )


def _generate_agent_id() -> str:
    """Generate a new unique agent ID."""
    return uuid.uuid4().hex


def _generate_agent(
    agent_id: str, handle: str, display_name: str, timestamp: str
) -> Agent:
    """Build an Agent model for user-generated creation."""
    return Agent(
        agent_id=agent_id,
        handle=handle,
        persona_source=PersonaSource.USER_GENERATED,
        display_name=display_name,
        created_at=timestamp,
        updated_at=timestamp,
    )


def _generate_agent_bio(agent_id: str, bio_text: str, timestamp: str) -> AgentBio:
    """Build an AgentBio model for user-provided creation."""
    return AgentBio(
        id=uuid.uuid4().hex,
        agent_id=agent_id,
        persona_bio=bio_text,
        persona_bio_source=PersonaBioSource.USER_PROVIDED,
        created_at=timestamp,
        updated_at=timestamp,
    )


def _generate_user_agent_profile_metadata(
    agent_id: str, timestamp: str
) -> UserAgentProfileMetadata:
    """Build UserAgentProfileMetadata with zero counts for new agents."""
    return UserAgentProfileMetadata(
        id=uuid.uuid4().hex,
        agent_id=agent_id,
        followers_count=0,
        follows_count=0,
        posts_count=0,
        created_at=timestamp,
        updated_at=timestamp,
    )
