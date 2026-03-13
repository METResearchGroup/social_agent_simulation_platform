"""Write-side service for editable pre-run agent follow edges."""

from __future__ import annotations

import uuid

from db.adapters.base import TransactionProvider
from db.repositories.agent_follow_edge_repository import DuplicateAgentFollowEdgeError
from db.repositories.interfaces import (
    AgentFollowEdgeRepository,
    AgentRepository,
    UserAgentProfileMetadataRepository,
)
from lib.timestamp_utils import get_current_timestamp
from simulation.api.errors import (
    ApiAgentFollowEdgeAlreadyExistsError,
    ApiAgentFollowEdgeNotFoundError,
    ApiAgentNotFoundError,
    ApiSelfFollowNotAllowedError,
    ApiTargetAgentNotFoundError,
)
from simulation.api.schemas.simulation import (
    AgentFollowEdgeSchema,
    CreateAgentFollowRequest,
)
from simulation.core.models.agent import Agent
from simulation.core.models.agent_follow_edge import AgentFollowEdge
from simulation.core.models.user_agent_profile_metadata import UserAgentProfileMetadata
from simulation.core.utils.handle_utils import normalize_handle

DEFAULT_METADATA_POSTS_COUNT: int = 0


def create_agent_follow(
    handle: str,
    req: CreateAgentFollowRequest,
    *,
    transaction_provider: TransactionProvider,
    agent_repo: AgentRepository,
    agent_follow_edge_repo: AgentFollowEdgeRepository,
    metadata_repo: UserAgentProfileMetadataRepository,
) -> AgentFollowEdgeSchema:
    """Create one editable pre-run follow edge and sync cached counts."""
    follower_handle = normalize_handle(handle)
    target_handle = normalize_handle(req.target_handle)
    now = get_current_timestamp()

    with transaction_provider.run_transaction() as conn:
        follower, target = _resolve_follower_and_target_agents(
            follower_handle=follower_handle,
            target_handle=target_handle,
            agent_repo=agent_repo,
            conn=conn,
        )
        if follower.agent_id == target.agent_id:
            raise ApiSelfFollowNotAllowedError(follower_handle)

        edge = AgentFollowEdge(
            agent_follow_edge_id=uuid.uuid4().hex,
            follower_agent_id=follower.agent_id,
            target_agent_id=target.agent_id,
            created_at=now,
        )
        try:
            agent_follow_edge_repo.create_agent_follow_edge(edge, conn=conn)
        except DuplicateAgentFollowEdgeError as exc:
            raise ApiAgentFollowEdgeAlreadyExistsError(
                follower.handle,
                target.handle,
            ) from exc

        _sync_follow_counts(
            agent_ids=[follower.agent_id, target.agent_id],
            now=now,
            agent_follow_edge_repo=agent_follow_edge_repo,
            metadata_repo=metadata_repo,
            conn=conn,
        )

    return AgentFollowEdgeSchema(
        agent_follow_edge_id=edge.agent_follow_edge_id,
        follower_handle=follower.handle,
        target_handle=target.handle,
        created_at=edge.created_at,
    )


def delete_agent_follow(
    handle: str,
    target_handle: str,
    *,
    transaction_provider: TransactionProvider,
    agent_repo: AgentRepository,
    agent_follow_edge_repo: AgentFollowEdgeRepository,
    metadata_repo: UserAgentProfileMetadataRepository,
) -> None:
    """Delete one editable pre-run follow edge and sync cached counts."""
    normalized_follower_handle = normalize_handle(handle)
    normalized_target_handle = normalize_handle(target_handle)
    now = get_current_timestamp()

    with transaction_provider.run_transaction() as conn:
        follower, target = _resolve_follower_and_target_agents(
            follower_handle=normalized_follower_handle,
            target_handle=normalized_target_handle,
            agent_repo=agent_repo,
            conn=conn,
        )
        deleted = agent_follow_edge_repo.delete_agent_follow_edge(
            follower.agent_id,
            target.agent_id,
            conn=conn,
        )
        if not deleted:
            raise ApiAgentFollowEdgeNotFoundError(follower.handle, target.handle)

        _sync_follow_counts(
            agent_ids=[follower.agent_id, target.agent_id],
            now=now,
            agent_follow_edge_repo=agent_follow_edge_repo,
            metadata_repo=metadata_repo,
            conn=conn,
        )


def _resolve_follower_and_target_agents(
    *,
    follower_handle: str,
    target_handle: str,
    agent_repo: AgentRepository,
    conn: object,
) -> tuple[Agent, Agent]:
    """Resolve handles to internal agent rows for follow-edge commands."""
    follower = agent_repo.get_agent_by_handle(follower_handle, conn=conn)
    if follower is None:
        raise ApiAgentNotFoundError(follower_handle)

    target = agent_repo.get_agent_by_handle(target_handle, conn=conn)
    if target is None:
        raise ApiTargetAgentNotFoundError(target_handle)

    return follower, target


def _sync_follow_counts(
    *,
    agent_ids: list[str],
    now: str,
    agent_follow_edge_repo: AgentFollowEdgeRepository,
    metadata_repo: UserAgentProfileMetadataRepository,
    conn: object,
) -> None:
    """Recompute cached follow counts for the affected agents inside one transaction."""
    for agent_id in sorted(set(agent_ids)):
        existing_metadata = metadata_repo.get_by_agent_id(agent_id, conn=conn)
        followers_count = (
            agent_follow_edge_repo.count_agent_follow_edges_by_target_agent_id(
                agent_id,
                conn=conn,
            )
        )
        follows_count = (
            agent_follow_edge_repo.count_agent_follow_edges_by_follower_agent_id(
                agent_id,
                conn=conn,
            )
        )

        metadata_repo.create_or_update_metadata(
            UserAgentProfileMetadata(
                id=existing_metadata.id if existing_metadata else uuid.uuid4().hex,
                agent_id=agent_id,
                followers_count=followers_count,
                follows_count=follows_count,
                posts_count=(
                    existing_metadata.posts_count
                    if existing_metadata
                    else DEFAULT_METADATA_POSTS_COUNT
                ),
                created_at=existing_metadata.created_at if existing_metadata else now,
                updated_at=now,
            ),
            conn=conn,
        )
