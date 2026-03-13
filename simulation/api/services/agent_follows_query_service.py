"""Read-side service for editable pre-run agent follow edges."""

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
    *,
    handle: str,
    agent_repo: AgentRepository,
    agent_follow_edge_repo: AgentFollowEdgeRepository,
    limit: int,
    offset: int,
) -> ListAgentFollowsResponse:
    """List editable follow edges for one follower handle."""
    normalized_handle = normalize_handle(handle)
    follower = agent_repo.get_agent_by_handle(normalized_handle)
    if follower is None:
        raise ApiAgentNotFoundError(normalized_handle)

    edges = agent_follow_edge_repo.list_agent_follow_edges_by_follower_agent_id(
        follower.agent_id,
        limit=limit,
        offset=offset,
    )
    total = agent_follow_edge_repo.count_agent_follow_edges_by_follower_agent_id(
        follower.agent_id
    )
    target_agents_by_id = agent_repo.get_agents_by_ids(
        [edge.target_agent_id for edge in edges]
    )

    return ListAgentFollowsResponse(
        total=total,
        items=[
            _edge_to_schema(
                edge=edge,
                follower=follower,
                target_agents_by_id=target_agents_by_id,
            )
            for edge in edges
        ],
    )


def _edge_to_schema(
    *,
    edge: AgentFollowEdge,
    follower: Agent,
    target_agents_by_id: dict[str, Agent | None],
) -> AgentFollowEdgeSchema:
    """Map a follow-edge row plus hydrated agents to the API schema."""
    target_agent = target_agents_by_id.get(edge.target_agent_id)
    if target_agent is None:
        raise RuntimeError(
            "agent_follow_edges row references missing target agent "
            f"{edge.target_agent_id}"
        )

    return AgentFollowEdgeSchema(
        agent_follow_edge_id=edge.agent_follow_edge_id,
        follower_handle=follower.handle,
        target_handle=target_agent.handle,
        created_at=edge.created_at,
    )
