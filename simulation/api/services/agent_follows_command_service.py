"""Write-side CQRS service for seed-state agent follow edges."""

import sqlite3
import uuid

from db.adapters.base import TransactionProvider
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
from simulation.core.utils.handle_utils import normalize_handle


def create_agent_follow(
    follower_handle: str,
    req: CreateAgentFollowRequest,
    *,
    transaction_provider: TransactionProvider,
    agent_repo: AgentRepository,
    agent_follow_edge_repo: AgentFollowEdgeRepository,
    metadata_repo: UserAgentProfileMetadataRepository,
) -> AgentFollowEdgeSchema:
    """Create one internal-only seed-state follow edge and sync cached counts."""
    follower_agent = _get_follower_agent(follower_handle, agent_repo=agent_repo)
    target_agent = _get_target_agent(req.target_handle, agent_repo=agent_repo)
    if follower_agent.agent_id == target_agent.agent_id:
        raise ApiSelfFollowNotAllowedError(follower_agent.handle)

    now = get_current_timestamp()
    edge = AgentFollowEdge(
        agent_follow_edge_id=uuid.uuid4().hex,
        follower_agent_id=follower_agent.agent_id,
        target_agent_id=target_agent.agent_id,
        created_at=now,
    )

    try:
        with transaction_provider.run_transaction() as conn:
            agent_follow_edge_repo.create_edge(edge, conn=conn)
            sync_follow_counts_for_agents(
                agent_ids=[follower_agent.agent_id, target_agent.agent_id],
                now=now,
                metadata_repo=metadata_repo,
                agent_follow_edge_repo=agent_follow_edge_repo,
                conn=conn,
            )
    except sqlite3.IntegrityError as exc:
        _raise_follow_write_error(
            exc,
            follower_agent=follower_agent,
            target_agent=target_agent,
            agent_repo=agent_repo,
        )

    return _edge_to_schema(
        edge,
        follower_handle=follower_agent.handle,
        target_handle=target_agent.handle,
    )


def delete_agent_follow(
    follower_handle: str,
    target_handle: str,
    *,
    transaction_provider: TransactionProvider,
    agent_repo: AgentRepository,
    agent_follow_edge_repo: AgentFollowEdgeRepository,
    metadata_repo: UserAgentProfileMetadataRepository,
) -> None:
    """Delete one seed-state follow edge and sync cached counts."""
    follower_agent = _get_follower_agent(follower_handle, agent_repo=agent_repo)
    target_agent = _get_target_agent(target_handle, agent_repo=agent_repo)

    with transaction_provider.run_transaction() as conn:
        deleted = agent_follow_edge_repo.delete_edge(
            follower_agent.agent_id,
            target_agent.agent_id,
            conn=conn,
        )
        if not deleted:
            raise ApiAgentFollowEdgeNotFoundError(
                follower_agent.handle,
                target_agent.handle,
            )
        sync_follow_counts_for_agents(
            agent_ids=[follower_agent.agent_id, target_agent.agent_id],
            now=get_current_timestamp(),
            metadata_repo=metadata_repo,
            agent_follow_edge_repo=agent_follow_edge_repo,
            conn=conn,
        )


def sync_follow_counts_for_agents(
    *,
    agent_ids: list[str],
    now: str,
    metadata_repo: UserAgentProfileMetadataRepository,
    agent_follow_edge_repo: AgentFollowEdgeRepository,
    conn: object,
) -> None:
    """Recompute cached follow counts from edge rows for the given agent IDs."""
    for agent_id in sorted(set(agent_ids)):
        followers_count = agent_follow_edge_repo.count_edges_by_target_agent_id(
            agent_id,
            conn=conn,
        )
        follows_count = agent_follow_edge_repo.count_edges_by_follower_agent_id(
            agent_id,
            conn=conn,
        )
        metadata_repo.sync_follow_counts(
            agent_id=agent_id,
            followers_count=followers_count,
            follows_count=follows_count,
            updated_at=now,
            conn=conn,
        )


def _get_follower_agent(raw_handle: str, *, agent_repo: AgentRepository) -> Agent:
    follower_handle = normalize_handle(raw_handle)
    follower_agent = agent_repo.get_agent_by_handle(follower_handle)
    if follower_agent is None:
        raise ApiAgentNotFoundError(follower_handle)
    return follower_agent


def _get_target_agent(raw_handle: str, *, agent_repo: AgentRepository) -> Agent:
    target_handle = normalize_handle(raw_handle)
    target_agent = agent_repo.get_agent_by_handle(target_handle)
    if target_agent is None:
        raise ApiTargetAgentNotFoundError(target_handle)
    return target_agent


def _raise_follow_write_error(
    exc: sqlite3.IntegrityError,
    *,
    follower_agent: Agent,
    target_agent: Agent,
    agent_repo: AgentRepository,
) -> None:
    """Translate SQLite integrity errors into stable API-layer exceptions."""
    message = str(exc)
    if (
        "UNIQUE constraint failed" in message
        or "uq_agent_follow_edges_follower_target" in message
    ):
        raise ApiAgentFollowEdgeAlreadyExistsError(
            follower_agent.handle,
            target_agent.handle,
        ) from exc
    if (
        "CHECK constraint failed" in message
        or "ck_agent_follow_edges_no_self_follow" in message
    ):
        raise ApiSelfFollowNotAllowedError(follower_agent.handle) from exc
    if "FOREIGN KEY constraint failed" in message:
        if agent_repo.get_agent(follower_agent.agent_id) is None:
            raise ApiAgentNotFoundError(follower_agent.handle) from exc
        if agent_repo.get_agent(target_agent.agent_id) is None:
            raise ApiTargetAgentNotFoundError(target_agent.handle) from exc
    raise exc


def _edge_to_schema(
    edge: AgentFollowEdge,
    *,
    follower_handle: str,
    target_handle: str,
) -> AgentFollowEdgeSchema:
    """Build the API response schema for a follow edge."""
    return AgentFollowEdgeSchema(
        agent_follow_edge_id=edge.agent_follow_edge_id,
        follower_handle=follower_handle,
        target_handle=target_handle,
        created_at=edge.created_at,
    )
