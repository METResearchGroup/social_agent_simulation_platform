---
description: Implementation notes and legacy→canonical agent_id map for normalizing agent creation paths (API, migration job, local seed).
tags:
  - agent-id
  - canonical-ids
  - local-dev-seed
  - migrations
---

# Normalize agent creation paths — implementation notes

## Fixture ID map (deterministic)

Each legacy `agent_*` seed ID was replaced with `canonical_agent_id(legacy_id)` so cross-table references stay consistent.

| Legacy ID | Canonical ID |
| --------- | ------------ |
| `agent_0240dc0d4a4c7e73` | `9fd6a35a1132f8df` |
| `agent_0c75608c7dd8e6c7` | `6b89de43980a9096` |
| `agent_7b3e5a6b1b0394d1` | `d4bcb9799721fe93` |
| `agent_c2cf0fd46387f19a` | `3cb6d2d8b3398451` |
| `agent_d5aaff22974ebc2c` | `1ac36c05d0073285` |
| `agent_ce3084ff7dd186dc` | `00d362d6d1e30a9d` |
| `agent_98a2ebefd3059f7e` | `1bce8573405b322e` |
| `agent_10c2fc5dda9f71dc` | `488f872520320780` |

## Developer note

Updating seed fixtures changes `fixtures_sha256` in `simulation/local_dev/seed_loader.py`. Use `LOCAL_RESET_DB=1` to re-seed when the digest no longer matches (see local dev runbooks).
