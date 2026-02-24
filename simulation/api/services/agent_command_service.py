"""Write-side CQRS service for simulation agent creation."""

import uuid

from db.adapters.base import TransactionProvider
from db.adapters.sqlite.sqlite import SqliteTransactionProvider
from db.repositories.agent_bio_repository import create_sqlite_agent_bio_repository
from db.repositories.agent_liked_post_repository import (
    create_sqlite_agent_liked_post_repository,
)
from db.repositories.agent_linked_agent_repository import (
    create_sqlite_agent_linked_agent_repository,
)
from db.repositories.agent_profile_comment_repository import (
    create_sqlite_agent_profile_comment_repository,
)
from db.repositories.agent_repository import create_sqlite_agent_repository
from db.repositories.interfaces import (
    AgentBioRepository,
    AgentLikedPostRepository,
    AgentLinkedAgentRepository,
    AgentProfileCommentRepository,
    AgentRepository,
    UserAgentProfileMetadataRepository,
)
from db.repositories.user_agent_profile_metadata_repository import (
    create_sqlite_user_agent_profile_metadata_repository,
)
from lib.timestamp_utils import get_current_timestamp
from simulation.api.schemas.simulation import (
    AgentSchema,
    CommentEntry,
    CreateAgentRequest,
)
from simulation.core.exceptions import (
    HandleAlreadyExistsError,
    LinkedAgentHandleNotFoundError,
)
from simulation.core.handle_utils import normalize_handle
from simulation.core.models.agent import Agent, PersonaSource
from simulation.core.models.agent_bio import AgentBio, PersonaBioSource
from simulation.core.models.agent_liked_post import AgentLikedPost
from simulation.core.models.agent_linked_agent import AgentLinkedAgent
from simulation.core.models.agent_profile_comment import AgentProfileComment
from simulation.core.models.user_agent_profile_metadata import UserAgentProfileMetadata


def create_agent(
    req: CreateAgentRequest,
    *,
    transaction_provider: TransactionProvider | None = None,
    agent_repo: AgentRepository | None = None,
    bio_repo: AgentBioRepository | None = None,
    metadata_repo: UserAgentProfileMetadataRepository | None = None,
    comment_repo: AgentProfileCommentRepository | None = None,
    liked_post_repo: AgentLikedPostRepository | None = None,
    linked_agent_repo: AgentLinkedAgentRepository | None = None,
) -> AgentSchema:
    """Create a user-generated agent with bio, metadata, comments, likes, and links.

    Atomic multi-table write. Validates linked_agent_handles exist before persisting.
    """
    handle = normalize_handle(req.handle)
    display_name = req.display_name.strip()
    bio_text = (req.bio or "").strip() or "No bio provided."

    if (
        transaction_provider is None
        or agent_repo is None
        or bio_repo is None
        or metadata_repo is None
        or comment_repo is None
        or liked_post_repo is None
        or linked_agent_repo is None
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
        comment_repo = comment_repo or create_sqlite_agent_profile_comment_repository(
            transaction_provider=transaction_provider
        )
        liked_post_repo = liked_post_repo or create_sqlite_agent_liked_post_repository(
            transaction_provider=transaction_provider
        )
        linked_agent_repo = linked_agent_repo or (
            create_sqlite_agent_linked_agent_repository(
                transaction_provider=transaction_provider
            )
        )

    # TODO: that this can cause a slight race condition if we do this check
    # before the below context manager for writing the agent to the database.
    # This is a known issue, and we'll revisit this in the future.
    if agent_repo.get_agent_by_handle(handle) is not None:
        raise HandleAlreadyExistsError(handle)

    for h in req.linked_agent_handles or []:
        normalized = normalize_handle(h)
        if agent_repo.get_agent_by_handle(normalized) is None:
            raise LinkedAgentHandleNotFoundError(h)

    comments_filtered = [
        c
        for c in req.comments or []
        if (c.text or "").strip() or (c.post_uri or "").strip()
    ]
    liked_uris_filtered = [
        u.strip() for u in req.liked_post_uris or [] if (u or "").strip()
    ]
    linked_handles_normalized = [
        normalize_handle(h) for h in req.linked_agent_handles or []
    ]

    agent_id = _generate_agent_id()
    now = get_current_timestamp()

    agent = _generate_agent(agent_id, handle, display_name, now)
    agent_bio = _generate_agent_bio(agent_id, bio_text, now)
    metadata = _generate_user_agent_profile_metadata(agent_id, now)
    profile_comments = _generate_agent_profile_comments(
        agent_id, comments_filtered, now
    )
    liked_posts = _generate_agent_liked_posts(agent_id, liked_uris_filtered)
    linked_agents = _generate_agent_linked_agents(agent_id, linked_handles_normalized)

    with transaction_provider.run_transaction() as conn:
        agent_repo.create_or_update_agent(agent, conn=conn)
        bio_repo.create_agent_bio(agent_bio, conn=conn)
        metadata_repo.create_or_update_metadata(metadata, conn=conn)
        comment_repo.create_comments(profile_comments, conn=conn)
        liked_post_repo.create_liked_posts(liked_posts, conn=conn)
        linked_agent_repo.create_linked_agents(linked_agents, conn=conn)

    return _build_agent_schema(
        agent.handle,
        agent.display_name,
        bio_text,
        comments=[
            CommentEntry(text=c.text, post_uri=c.post_uri) for c in comments_filtered
        ],
        liked_post_uris=liked_uris_filtered,
        linked_agent_handles=linked_handles_normalized,
    )


def _build_agent_schema(
    handle: str,
    display_name: str,
    bio_text: str,
    *,
    comments: list[CommentEntry] | None = None,
    liked_post_uris: list[str] | None = None,
    linked_agent_handles: list[str] | None = None,
) -> AgentSchema:
    """Build AgentSchema for a newly created agent (zero counts)."""
    return AgentSchema(
        handle=handle,
        name=display_name,
        bio=bio_text,
        generated_bio="",
        followers=0,
        following=0,
        posts_count=0,
        comments=comments or [],
        liked_post_uris=liked_post_uris or [],
        linked_agent_handles=linked_agent_handles or [],
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


def _generate_agent_profile_comments(
    agent_id: str,
    comments: list[CommentEntry],
    timestamp: str,
) -> list[AgentProfileComment]:
    """Build AgentProfileComment models from filtered comment entries."""
    return [
        AgentProfileComment(
            id=uuid.uuid4().hex,
            agent_id=agent_id,
            post_uri=(c.post_uri or "").strip(),
            text=(c.text or "").strip(),
            created_at=timestamp,
            updated_at=timestamp,
        )
        for c in comments
    ]


def _generate_agent_liked_posts(
    agent_id: str, post_uris: list[str]
) -> list[AgentLikedPost]:
    """Build AgentLikedPost models from post URIs."""
    return [AgentLikedPost(agent_id=agent_id, post_uri=uri) for uri in post_uris]


def _generate_agent_linked_agents(
    agent_id: str, linked_handles: list[str]
) -> list[AgentLinkedAgent]:
    """Build AgentLinkedAgent models from linked handles."""
    return [
        AgentLinkedAgent(agent_id=agent_id, linked_agent_handle=h)
        for h in linked_handles
    ]
