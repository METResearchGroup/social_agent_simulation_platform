---
description: Add Opik LLM observability to simulation_v2 with per-user traces, in-process cost/latency aggregation, and turn/run summary traces.
tags: [plan, simulation_v2, opik, telemetry, observability]
---

# Simulation v2 Opik Telemetry Implementation Plan

Plan asset folder: [`docs/plans/2026-05-24_simulation_v2_opik_telemetry_847293/`](docs/plans/2026-05-24_simulation_v2_opik_telemetry_847293/)

## Overview

Implement end-to-end Opik telemetry for `simulation_v2` under project **`simulation_engine_v2`**. Opik traces only LLM generation (`propose_*` / `invoke_structured`): per-user spans, per write-post attempt, `thread_id=run_id`, and `turn_number` metadata on every trace. An in-process metrics collector records latency and cost per call; at turn end and run end, computed aggregates (per-action and overall: request count, total cost, p50/p90/p99 latency) are logged as standalone summary traces to Opik. Stochastic keep/drop outcomes (`determine_*` / `PROB_*`) are recorded separately via structured logging — not Opik.

## Happy Flow

1. [`simulation_v2/simulate_run.py`](simulation_v2/simulate_run.py) generates `run_id = str(uuid.uuid4())`, calls `configure_opik()`, creates `SimulationTraceContext`, and loops turns with a run-level tqdm bar.
2. Each turn, [`simulation_v2/simulate_turn.py`](simulation_v2/simulate_turn.py) sets `context.turn_number`, resets the turn-level LLM collector, runs feeds (no Opik), then calls `get_agents_actions(..., trace_ctx=context)` with a per-turn agent tqdm bar.
3. For each user in [`simulation_v2/agents/actions.py`](simulation_v2/agents/actions.py):
   - `@opik.track(name="agent_turn")` wraps per-user work with `metadata={turn_number, run_id}`.
   - `determine_*` functions apply stochastic filters; they append to `SimulationMetricsCollector` (proposed vs kept counts) and call `propose_*` only when LLM is invoked.
   - `propose_*` functions call `invoke_structured(..., trace_ctx=..., action_type=..., user_id=...)`.
4. [`simulation_v2/agents/llm.py`](simulation_v2/agents/llm.py) `invoke_structured`:
   - Starts wall-clock timer.
   - Invokes chain with `[OpikTracer(...), LlmMetricsCallbackHandler(...)]`.
   - Appends `LlmCallRecord` to turn collector.
   - Never raises on telemetry failure (log warning, continue).
5. End of turn: `log_turn_llm_summary_to_opik(context)` emits a summary trace; turn summary rolls into run collector; `log_turn_simulation_metrics(context)` writes JSON lines for kept/dropped counts.
6. End of run: `log_run_llm_summary_to_opik(context)` + `flush_opik()`.

## Manual Verification

### Automated (required before merge)

- `uv sync --extra test`
- `uv run pytest tests/simulation_v2/telemetry/ -v` — all pass
- `uv run ruff check simulation_v2/telemetry/ simulation_v2/agents/llm.py simulation_v2/agents/actions.py simulation_v2/simulate_run.py simulation_v2/simulate_turn.py`
- `uv run pyright simulation_v2/telemetry/ simulation_v2/agents/llm.py simulation_v2/agents/actions.py`
- `uv run python scripts/check_docs_metadata.py docs/plans/2026-05-24_simulation_v2_opik_telemetry_847293/plan.md`
- `OPIK_DISABLED=1 PYTHONPATH=. uv run python simulation_v2/main.py` — completes without traceback

### Live smoke (primary)

```bash
PYTHONPATH=. uv run python simulation_v2/main.py
```

Default config: **10 users**, **5 posts/user**, **3 turns**. Progress bars show turn completion (run-level) and agent completion (turn-level). Structured logs emit per-user start/complete and simulation outcome JSON lines.

### Experiment script (secondary)

```bash
PYTHONPATH=. uv run python simulation_v2/agents/experiment_agents.py
```

5 agents, 20 posts, single turn. Exercises `@opik.track` spans, stochastic filters, and simulation metrics without full orchestration loop.

---

## Live Run Results

Smoke run executed via `simulation_v2/main.py` on branch `add-opik-telemetry-v2-design`.

| Field | Value |
|-------|-------|
| **run_id** | `f8af41d3-5e83-483e-9517-e1a07063ef61` |
| **Opik project** | `simulation_engine_v2` |
| **Config** | 10 users, 50 posts, 3 turns |
| **Total wall time** | 18.2 min |
| **Exit code** | 0 |

### Run timing (from logs)

| Turn | Wall time | LLM calls | Opik cost |
|------|-----------|-----------|-----------|
| 1 | 6.4 min | 22 | $0.024 |
| 2 | 5.9 min | 22 | $0.024 |
| 3 | 5.9 min | 22 | $0.023 |
| **Total** | **18.2 min** | **66** | **$0.070** |

Turns were stable: 22 LLM calls per turn (10 agents × ~2.2 calls each).

### LLM metrics — run-level averages (Opik `agent_turn` traces)

Queried via Opik Python SDK: `search_traces(project_name="simulation_engine_v2", filter_string='thread_id = "f8af41d3-…"')`. 30 `agent_turn` traces (10 users × 3 turns), 66 total LLM spans.

| Metric | Per LLM call | Per agent-turn (1 user, 1 turn) | Run total |
|--------|--------------|----------------------------------|-----------|
| Cost | $0.00106 | $0.00234 | $0.070 |
| Prompt tokens | 1,133 | 2,493 | 74,802 |
| Completion tokens | 2,512 | 5,526 | 165,779 |
| Total tokens | 3,645 | 8,019 | 240,581 |
| Wall duration | — | 36.3 s (p50 34.3 s) | 1,089 s |

Each agent-turn averaged **2.20 LLM calls** (like + follow every turn; write only when `PROB_WRITE_POST` triggers).

### Simulation outcome metrics — run-level averages (structured logs)

90 JSON lines emitted (`simulation_v2.simulation_metrics` logger): 10 users × 3 actions × 3 turns.

| Action | Avg proposed / user-turn | Avg kept / user-turn | Keep rate |
|--------|--------------------------|----------------------|-----------|
| `like_posts` | 8.67 | 2.53 | 29.2% |
| `follow_users` | 5.00 | 0.07 | 1.3% |
| `write_post` | 0.20 | 0.20 | 100% (6 LLM calls total) |

Run totals: 260 likes proposed → 76 kept; 150 follows proposed → 2 kept; 6 write attempts → 6 kept.

Stochastic filters (`PROB_LIKE_POST=0.25`, `PROB_FOLLOW_USER=0.02`, `PROB_WRITE_POST=0.05`) are working as designed — LLM proposes generously, simulation keeps a small fraction.

### Opik UI verification

| Check | Result |
|-------|--------|
| Thread grouping | All 30 traces share `thread_id = run_id` |
| Per-user spans | 30× `agent_turn` parent traces with nested `propose_*` LLM spans |
| Metadata | `turn_number`, `run_id` present on agent traces |
| Token usage | Visible on generation spans; cost estimated by Opik |
| `metrics_summary` traces | **Not found** via `search_traces` (see Findings) |

### Progress and logging

- Run-level tqdm: `Simulation run (turns): 3/3`
- Turn-level tqdm: `Turn N (agents): X/10`
- INFO logs: turn start/finish, per-user agent start/complete, simulation metrics JSON lines
- Opik configure: non-interactive after fix (see Findings)

---

## Findings

### What worked

1. **End-to-end telemetry path** — Opik traces, in-process collectors, simulation outcome logs, and progress bars all function together without aborting the simulation.
2. **Per-user Opik spans** — 30 `agent_turn` traces with correct `thread_id`, turn metadata, token counts, and cost estimates.
3. **Simulation metrics separation** — 90 outcome JSON lines correctly capture proposed vs kept counts outside Opik.
4. **Non-interactive Opik configure** — passing `project_name="simulation_engine_v2"` and `automatic_approvals=True` to `opik.configure()` prevents the blocking *Do you want to use "simulation_engine_v2" project name?* prompt.
5. **Stable per-turn LLM volume** — 22 calls/turn is predictable for 10 agents (like + follow baseline, sparse writes).

### Issues / follow-ups

1. **`metrics_summary` traces not searchable in Opik** — `turn_metrics_summary` and `run_metrics_summary` traces were logged (flush succeeded, no warnings in stdout), but `search_traces(tags contains "metrics_summary")` returned 0 results. Investigate batching/`Trace.end()` timing (Opik warns about data loss when ending traces shortly after creation with batching enabled). May need to flush before `trace.end()` or use a different update pattern.
2. **Local `cost_usd=None` in collector** — in-process `LlmCallRecord.cost_usd` is null; Opik estimates cost on its side ($0.001/call avg). Acceptable for v1 per plan, but run-summary cost aggregates in local collector will be zero unless we backfill from Opik or add a pricing table.
3. **High completion-token ratio** — avg 2,512 completion vs 1,133 prompt tokens per call suggests significant reasoning-token overhead on `gpt-5-nano`. Worth monitoring at scale.
4. **Verbose httpx/opik INFO logging** — terminal output is noisy during runs; consider raising log level for `httpx` and `opik` in `main.py` for cleaner progress display.
5. **Experiment script not re-run post-progress-bars** — live validation used `main.py` (10×3 config). `experiment_agents.py` (5 agents, 20 posts) remains as secondary smoke.

### Residual risks (unchanged from plan)

- p99 latency omitted when N < 30 per action bucket.
- Volume at 100 users ≈ 220 LLM calls/turn — acceptable for dev, may need sampling at 5k scale.
