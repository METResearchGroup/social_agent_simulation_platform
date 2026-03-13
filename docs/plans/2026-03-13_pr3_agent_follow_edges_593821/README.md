---
description: Planning notes and verification references for the agent_follow_edges seed-state PR.
tags: [plan, database, api, agent-follow-edges, seed-state]
---

# PR-3 agent follow edges

- Assets directory reserved for implementation notes and verification artifacts for the
  `agent_follow_edges` seed-state table rollout.
- This PR keeps legacy `follows` as the immutable run-turn event log and adds
  `agent_follow_edges` for editable pre-run internal agent-to-agent follows.
