"""Read-side CQRS service for seed-state agent follow edges."""

from db.repositories.interfaces import AgentFollowEdgeRepository, AgentRepository
from simulation.api.errors import ApiAgentNotFoundError
from simulation.api.schemas.simulation import (
    AgentFollowEdgeSchema,
    ListAgentFollowsResponse,
)
from simulation.core.models.agent import Agent
from simulation.core.models.agent_follow_edge import AgentFollowEdge
from simulation.core.utils.handle_utils import normalize_handle


def list_agent_follows(
    handle: str,
    *,
    agent_repo: AgentRepository,
    agent_follow_edge_repo: AgentFollowEdgeRepository,
    limit: int,
    offset: int,
) -> ListAgentFollowsResponse:
    """Return paginated seed-state follow edges for the given follower handle."""
    follower_handle = normalize_handle(handle)
    follower_agent = agent_repo.get_agent_by_handle(follower_handle)
    if follower_agent is None:
        raise ApiAgentNotFoundError(follower_handle)

    total = agent_follow_edge_repo.count_edges_by_follower_agent_id(
        follower_agent.agent_id
    )
    edges = agent_follow_edge_repo.list_edges_by_follower_agent_id(
        follower_agent.agent_id,
        limit=limit,
        offset=offset,
    )
    items = [
        _edge_to_schema(edge, follower_agent=follower_agent, agent_repo=agent_repo)
        for edge in edges
    ]
    return ListAgentFollowsResponse(total=total, items=items)


def _edge_to_schema(
    edge: AgentFollowEdge,
    *,
    follower_agent: Agent,
    agent_repo: AgentRepository,
) -> AgentFollowEdgeSchema:
    """Map a persisted follow edge to the API schema."""
    target_agent = agent_repo.get_agent(edge.target_agent_id)
    if target_agent is None:
        raise RuntimeError(
            "agent_follow_edges row points to a missing target agent_id. "
            f"target_agent_id={edge.target_agent_id}"
        )
    return AgentFollowEdgeSchema(
        agent_follow_edge_id=edge.agent_follow_edge_id,
        follower_handle=follower_agent.handle,
        target_handle=target_agent.handle,
        created_at=edge.created_at,
    )
