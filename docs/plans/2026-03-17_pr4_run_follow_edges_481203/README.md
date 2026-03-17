---
description: Assets and notes for PR 4 run_follow_edges implementation and verification.
tags: [plan, follow-edges, run-snapshot, verification]
---

# PR 4 assets

This directory records implementation notes and verification artifacts for the
`run_follow_edges` snapshot slice.

- `run_follow_edges` freezes the selected agents' internal follow graph at run
  start.
- Historical run-start follow reads should use the frozen `run_follow_edges`
  snapshot, not live `agent_follow_edges`.
