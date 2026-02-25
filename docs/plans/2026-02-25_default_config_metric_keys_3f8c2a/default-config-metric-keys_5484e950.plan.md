---
name: default-config-metric-keys
overview: Make `metric_keys` an always-present, contract-backed field returned by `GET /v1/simulations/config/default`, so the UI can consume it via generated OpenAPI types without unsafe casts and the default metric selection becomes explicit and deterministic.
todos:
  - id: before-screenshots
    content: Capture before UI screenshots and save to `docs/plans/2026-02-25_default_config_metric_keys_3f8c2a/images/before/` (Start New Simulation form / metrics section visible).
    status: completed
  - id: backend-schema
    content: "Update `simulation/api/schemas/simulation.py` `DefaultConfigSchema` to include required `metric_keys: list[str]` with non-empty validation using existing `validate_metric_keys`."
    status: completed
  - id: backend-defaults
    content: Update `simulation/api/constants.py` `DEFAULT_SIMULATION_CONFIG` to include `metric_keys=get_default_metric_keys()` so the route always returns the field.
    status: completed
  - id: backend-tests
    content: Update `tests/api/test_simulation_config.py` to assert `metric_keys` exists and is a non-empty `list[str]` (optionally sorted).
    status: completed
  - id: regen-openapi
    content: "Regenerate and verify UI OpenAPI artifacts: `cd ui && npm run generate:api && npm run check:api` (commit `ui/openapi.json` and `ui/types/api.generated.ts`)."
    status: completed
  - id: ui-mapping
    content: "Update `ui/lib/api/simulation.ts` `getDefaultConfig()` to remove the widening cast and return `metricKeys: api.metric_keys`."
    status: completed
  - id: after-screenshots
    content: Capture after UI screenshots and save to `docs/plans/2026-02-25_default_config_metric_keys_3f8c2a/images/after/` using the same happy flow as before.
    status: completed
isProject: false
---

# Always-present metric_keys in DefaultConfigSchema

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- UI changes: agent captures before/after screenshots itself (no README or instructions for the user)

## Overview

We will extend the backend response model for `GET /v1/simulations/config/default` so it always returns a required `metric_keys: list[str]` (sorted, validated, non-empty), regenerate `ui/openapi.json` + `ui/types/api.generated.ts`, and update the UI’s `getDefaultConfig()` mapping in `ui/lib/api/simulation.ts` to use the generated field directly (removing the unsafe widening cast).

## Happy Flow

1. UI calls `getDefaultConfig()` in `[ui/lib/api/simulation.ts](ui/lib/api/simulation.ts)` → HTTP `GET /v1/simulations/config/default`.
2. FastAPI route `[simulation/api/routes/simulation.py](simulation/api/routes/simulation.py)` returns `DEFAULT_SIMULATION_CONFIG`.
3. `DEFAULT_SIMULATION_CONFIG` (in `[simulation/api/constants.py](simulation/api/constants.py)`) is constructed from `DefaultConfigSchema` (in `[simulation/api/schemas/simulation.py](simulation/api/schemas/simulation.py)`) and now includes `metric_keys=get_default_metric_keys()`.
4. UI maps response → `RunConfig.metricKeys` (in `[ui/types/index.ts](ui/types/index.ts)`), and `ConfigForm` (in `[ui/components/form/ConfigForm.tsx](ui/components/form/ConfigForm.tsx)`) initializes `selectedMetricKeys` from `defaultConfig.metricKeys`.

## Implementation plan

### 1) Plan assets (required)

- Create plan folder: `docs/plans/2026-02-25_default_config_metric_keys_3f8c2a/`
  - `docs/plans/2026-02-25_default_config_metric_keys_3f8c2a/images/before/`
  - `docs/plans/2026-02-25_default_config_metric_keys_3f8c2a/images/after/`

### 2) Capture **before** UI screenshots (required)

- Using the browser tooling, capture the current “Start New Simulation” form state (happy path).
- Save screenshots to `docs/plans/2026-02-25_default_config_metric_keys_3f8c2a/images/before/`.

### 3) Backend: add `metric_keys` to `DefaultConfigSchema` (always present)

- Update `[simulation/api/schemas/simulation.py](simulation/api/schemas/simulation.py)`:
  - Extend `class DefaultConfigSchema(BaseModel)` to include `metric_keys: list[str]`.
  - Add a `@field_validator("metric_keys")` that:
    - Calls `simulation.core.validators.validate_metric_keys`.
    - Enforces **non-empty** (since list is always present).
  - Ensure the field remains deterministic (order): `get_default_metric_keys()` already returns sorted keys.

### 4) Backend: return metric keys from the default config route

- Update `[simulation/api/constants.py](simulation/api/constants.py)`:
  - Construct `DEFAULT_SIMULATION_CONFIG` with `metric_keys=get_default_metric_keys()` (import from `simulation.core.metrics.defaults`).
- No route refactor required because `[simulation/api/routes/simulation.py](simulation/api/routes/simulation.py)` already returns `DEFAULT_SIMULATION_CONFIG` in `_execute_get_default_config`.

### 5) Backend tests: update expected response shape

- Update `[tests/api/test_simulation_config.py](tests/api/test_simulation_config.py)`:
  - Stop asserting exact dict equality.
  - Assert:
    - `num_agents` and `num_turns` unchanged.
    - `metric_keys` exists, is a `list[str]`, is non-empty.
    - Optional: assert it is sorted and contains only registered keys (stronger contract).

### 6) Regenerate OpenAPI + UI generated types

- Run (from repo root):

```bash
cd ui
npm run generate:api
npm run check:api
```

- Expected:
  - `ui/openapi.json` updated: `DefaultConfigSchema` now includes required `metric_keys`.
  - `ui/types/api.generated.ts` updated: `components['schemas']['DefaultConfigSchema']` now has `metric_keys: string[]`.

### 7) UI: remove unsafe type widening and consume generated field

- Update `[ui/lib/api/simulation.ts](ui/lib/api/simulation.ts)` `getDefaultConfig()`:
  - Remove `apiWithMetrics` cast.
  - Set `metricKeys: api.metric_keys`.
  - Confirm TypeScript now enforces the field’s presence via `ApiDefaultConfig`.

### 8) Capture **after** UI screenshots (required)

- Using the browser tooling, re-run the same happy flow and capture the updated UI state.
- Save screenshots to `docs/plans/2026-02-25_default_config_metric_keys_3f8c2a/images/after/`.

## Manual Verification

- **Backend unit test**:

```bash
uv run pytest tests/api/test_simulation_config.py
```

- **Backend quality gates (repo standard)**:

```bash
uv run ruff check .
uv run pyright .
```

- **UI contract drift guard**:

```bash
cd ui
npm run check:api
```

- **UI build/lint sanity**:

```bash
cd ui
npm run lint:all
npm run build
```

- **Manual UI check (happy path)**
  - Start API (local):

```bash
DISABLE_AUTH=1 PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload
```

- Start UI:

```bash
cd ui
NEXT_PUBLIC_DISABLE_AUTH=true npm run dev
```

- In the UI: open “Start New Simulation” (`ConfigForm`), confirm:
  - Metrics selector defaults are preselected from `defaultConfig.metricKeys` (not empty).
  - Submitting a run includes `metric_keys` only when selection is non-empty (existing behavior in `postRun`).

## Alternative approaches

- **UI-only runtime narrowing (Approach B)**: remove the cast and treat `metric_keys` as optional/unknown at runtime. We’re not choosing this because you want the field **always present** and contract-backed; Approach A makes the API explicit and type-safe end-to-end.

## Notes / constraints

- This change intentionally expands the response schema for `GET /v1/simulations/config/default`. Any clients that assume the response is *exactly* `{num_agents,num_turns}` should still work (extra fields are typically ignored), but tests and strict decoders may need adjustment.

