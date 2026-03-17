"""Read-side CQRS service for seed-state agent follow edges."""

from db.repositories.interfaces import AgentFollowEdgeRepository, AgentRepository
from simulation.api.errors import ApiAgentNotFoundError
from simulation.api.schemas.simulation import (
    AgentFollowEdgeSchema,
    ListAgentFollowsResponse,
)
from simulation.core.models.agent_follow_edge import AgentFollowEdgeWithTargetHandle
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

    edge_page = agent_follow_edge_repo.get_edge_page_by_follower_agent_id(
        follower_agent.agent_id,
        limit=limit,
        offset=offset,
    )
    items = [
        _edge_to_schema(edge, follower_handle=follower_agent.handle)
        for edge in edge_page.items
    ]
    return ListAgentFollowsResponse(total=edge_page.total, items=items)


def _edge_to_schema(
    edge: AgentFollowEdgeWithTargetHandle,
    *,
    follower_handle: str,
) -> AgentFollowEdgeSchema:
    """Map a joined follow-edge row to the API schema."""
    return AgentFollowEdgeSchema(
        agent_follow_edge_id=edge.agent_follow_edge_id,
        follower_handle=follower_handle,
        target_handle=edge.target_handle,
        created_at=edge.created_at,
    )
