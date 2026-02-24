# After screenshots

Captured after implementing the Metrics selector (Part 3). Servers started per [LOCAL_DEV_AUTH.md](../../../../runbooks/LOCAL_DEV_AUTH.md) and [LOCAL_DEVELOPMENT.md](../../../../runbooks/LOCAL_DEVELOPMENT.md):

- **Backend:** `DISABLE_AUTH=1 PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload --port 8000`
- **Frontend:** `NEXT_PUBLIC_DISABLE_AUTH=true` in `ui/.env.local`, then `cd ui && npm run dev`

1. **after-1.png** – Start New Simulation form with Metrics section expanded: collapsible "▾ Metrics", Select all / Clear, grid of four metric cards (run.actions.total, run.actions.total_by_type, turn.actions.counts_by_type, turn.actions.total), Number of Agents/Turns, Start Simulation button.
2. **after-2-selection.png** – Same form with one metric card toggled off to show selected vs unselected styling (accent border/background on selected cards).
