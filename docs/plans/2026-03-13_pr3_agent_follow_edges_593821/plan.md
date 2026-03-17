---
description: Plan notes for introducing the agent_follow_edges seed-state table and related API/repository wiring.
tags: [plan, database, api, follows, seed-state]
---

# PR 3: `agent_follow_edges`

## Asset directory

- Canonical plan asset directory: `docs/plans/2026-03-13_pr3_agent_follow_edges_593821/`

## Scope notes

- Add `agent_follow_edges` as the first true editable seed-state row table.
- Keep legacy `follows` as the immutable run-turn event log.
- Recompute `user_agent_profile_metadata.followers_count` and `.follows_count`
  transactionally from `agent_follow_edges` writes only.
- Keep initial scope internal agent-to-agent only.

## Flow

```mermaid
flowchart TD
  ApiRoute[simulation.api.routes.simulation] --> QuerySvc[agent_follows_query_service]
  ApiRoute --> CmdSvc[agent_follows_command_service]

  QuerySvc --> AgentRepo[AgentRepository]
  QuerySvc --> FollowRepo[AgentFollowEdgeRepository]

  CmdSvc --> Tx[TransactionProvider]
  CmdSvc --> AgentRepo
  CmdSvc --> FollowRepo
  CmdSvc --> MetadataRepo[UserAgentProfileMetadataRepository]
```
