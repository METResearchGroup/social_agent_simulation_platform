# After screenshots

Captured after implementing the Metrics selector with **display_name** (required) and **Turn-level / Run-level** collapsible sections. Servers started per [LOCAL_DEV_AUTH.md](../../../../runbooks/LOCAL_DEV_AUTH.md) and [LOCAL_DEVELOPMENT.md](../../../../runbooks/LOCAL_DEVELOPMENT.md):

- **Backend:** `DISABLE_AUTH=1 PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload --port 8000`
- **Frontend:** `NEXT_PUBLIC_DISABLE_AUTH=true` in `ui/.env.local`, then `cd ui && npm run dev`

1. **after-1.png** – Start New Simulation with Metrics expanded: "▾ Turn-level metrics" and "▾ Run-level metrics" sub-sections, each with Select all / Clear and a grid of cards. Cards show **display name** (e.g. "Actions by type (turn)", "Total actions (run)") and **Scope: turn** / **Scope: run**.
2. **after-2-selection.png** – Same form with one metric toggled off to show selected vs unselected styling (accent border/background on selected cards).
