"""Helpers that hydrate the agent catalog used to bootstrap simulations.

These helpers load agents, bios, and profile metadata into the same structures
used when building the default set of seeded agents that starts every simulation,
allowing callers to hydrate the whole catalog or a curated subset by handle
before running a scenario that depends on that initial state.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from db.repositories.interfaces import (
    AgentBioRepository,
    AgentRepository,
    UserAgentProfileMetadataRepository,
)
from simulation.core.models.agent import Agent
from simulation.core.models.agent_bio import AgentBio
from simulation.core.models.user_agent_profile_metadata import UserAgentProfileMetadata


@dataclass(frozen=True)
class HydratedSeedState:
    """Structured hydration results for the seed-state catalog."""

    ordered_agents: list[Agent]
    agent_by_handle: dict[str, Agent]
    latest_bios: dict[str, AgentBio | None]
    metadata_by_agent_id: dict[str, UserAgentProfileMetadata | None]


def hydrate_seed_state(
    *,
    agent_repo: AgentRepository,
    agent_bio_repo: AgentBioRepository,
    user_agent_profile_metadata_repo: UserAgentProfileMetadataRepository,
    handles: Iterable[str] | None = None,
) -> HydratedSeedState:
    """Hydrate agents, bios, and metadata from the catalog.

    When `handles` is provided we only hydrate the requested subset in the
    supplied order. Otherwise we hydrate every agent from `list_all_agents`.
    """
    if handles is None:
        ordered_agents = agent_repo.list_all_agents()
        agent_by_handle = {agent.handle: agent for agent in ordered_agents}
    else:
        ordered_handles = list(handles)
        if not ordered_handles:
            return HydratedSeedState([], {}, {}, {})
        agent_by_handle = agent_repo.get_agents_by_handles(ordered_handles)
        missing_handles = [
            handle for handle in ordered_handles if handle not in agent_by_handle
        ]
        if missing_handles:
            raise ValueError(
                "Selected agents are missing from the seed-state agent catalog: "
                f"{missing_handles}"
            )
        ordered_agents = [agent_by_handle[handle] for handle in ordered_handles]

    agent_ids = [agent.agent_id for agent in ordered_agents]
    latest_bios = agent_bio_repo.get_latest_bios_by_agent_ids(agent_ids)
    metadata_by_agent_id = user_agent_profile_metadata_repo.get_metadata_by_agent_ids(
        agent_ids
    )

    return HydratedSeedState(
        ordered_agents=ordered_agents,
        agent_by_handle=agent_by_handle,
        latest_bios=latest_bios,
        metadata_by_agent_id=metadata_by_agent_id,
    )
