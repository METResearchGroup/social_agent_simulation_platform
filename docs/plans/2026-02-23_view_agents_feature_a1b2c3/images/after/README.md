---
description: Notes describing the after-screenshots captured for the View Agents feature implementation.
tags: [plan, images, ui, view-agents]
---

# After Screenshots

Captured after implementing the View Agents feature. Run with `DISABLE_AUTH=1` (backend) and `NEXT_PUBLIC_DISABLE_AUTH=true` (frontend) per docs/runbooks/LOCAL_DEV_AUTH.md.

- `view_runs_toggle.png`: View runs | View agents toggle at top-left, with "View runs" active. Sidebar shows Run History, run list, and Start New Run. Main area shows Start New Simulation form.
- `view_agents_mode.png`: "View agents" active. Sidebar shows Agents list; main area shows "Select an agent to view details".
- `view_agents_agent_detail.png`: Agent "Alice Chen" selected. AgentDetail with metadata (Name, Bio, Generated Bio, Followers, Following, Posts) expanded; Feed (0), Liked Posts (0), Comments (0) collapsed.
