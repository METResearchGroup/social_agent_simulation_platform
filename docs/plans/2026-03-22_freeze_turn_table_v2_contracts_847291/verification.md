---
description: Working verification record for the turn-table v2 contract-freeze docs milestone (metadata script + touched paths).
tags: [plan, verification, turns, architecture, documentation]
---

# Turn-table v2 contract freeze — verification

Executed per the Cursor plan *freeze_turn-table_v2_contracts*. Docs-only scope; no changes under `db/`, `simulation/`, `feeds/`, or `ui/`.

## Commands

```bash
uv run python scripts/check_docs_metadata.py \
  docs/architecture/agents-turns-runs-data-model.md \
  docs/architecture/seed-state-run-snapshot-turn-events.md \
  docs/architecture/turn-feed-post-id-contract.md \
  strategy_planning/2026-03-22_v2_refactor_turn_tables/proposal.md \
  docs/plans/2026-03-22_freeze_turn_table_v2_contracts_847291/verification.md
```

**Expected:** `Docs metadata validation succeeded.`

## Spot-check

- Strategy proposal contains **Frozen contract (v2 milestone)** and explicit **defer** of `TurnAction.POST` / authored-post generation.
- Architecture docs align on `turns` parent, `turn_*` targets, and post-ID namespace; optional `turn-feed-post-id-contract.md` cross-linked.
