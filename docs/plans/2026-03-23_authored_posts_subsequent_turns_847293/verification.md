---
description: Verification checklist for authored posts subsequent-turn slice.
tags: [plan, verification, simulation, turns]
---

# Verification — authored posts (subsequent turns)

- [x] `TurnPostRepository` write + list APIs with SQLite adapter and integration tests
- [x] `SimulationPersistenceService.write_turn` persists `turn_posts` in the turn transaction
- [x] Feed candidates merge `run_posts` + prior `turn_posts` (`turn_number <` current feed turn)
- [x] `TurnAction.POST`, `GeneratedPost`, API mapping, `total_actions` read compatibility
- [x] `get_turn_data` includes authored posts and fixes empty-turn guard
- [x] Architecture doc updated (`turn-feed-post-id-contract.md`)
