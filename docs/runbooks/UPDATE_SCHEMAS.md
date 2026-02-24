# Updating API schemas (backend ↔ UI)

This project treats the FastAPI backend as the source of truth for API request/response
shapes (Pydantic models under `simulation/api/schemas/`). The UI consumes OpenAPI-
generated TypeScript types to prevent drift.

If you add a new field, rename a field, change nullability/optionality, change an enum,
or otherwise modify anything that affects the OpenAPI contract, you **must** regenerate
and commit the updated generated artifacts.

## When to regenerate

Run `generate:api` (and ensure `check:api` passes) after changes to:

- Any Pydantic schema used in API routes (add/remove/rename fields, defaults, `Optional`,
  validators, enums).
- Any FastAPI route signature (query params, path params, request body models, response
  models, status codes) that affects OpenAPI.
- Any change that would alter the OpenAPI output served at `/docs` when the API is
  running.

You typically do **not** need regeneration for UI-only refactors that do not touch the
API contract.

## Commands

From repo root:

```bash
cd ui
npm run generate:api
npm run check:api
```

What to commit after regeneration:

- `ui/openapi.json`
- `ui/types/api.generated.ts`

CI runs `npm run check:api` and will fail if these files are out of date.

## How generation works

`ui` has two scripts:

- `npm run generate:api`
  1) Runs `uv run python ../scripts/generate_openapi_json.py --out openapi.json`
     - Imports `simulation.api.main:app` and calls `app.openapi()` (no server required).
     - Writes the resulting OpenAPI JSON to `ui/openapi.json`.
  2) Runs `openapi-typescript openapi.json --output types/api.generated.ts`
     - Converts the OpenAPI schemas/paths into TypeScript types.

- `npm run check:api`
  - Runs `generate:api`, then asserts the repo is clean for the generated artifacts via
    `git diff --exit-code -- openapi.json types/api.generated.ts`.

The generated file exports types like:

- `components['schemas']['RunResponse']`
- `components['schemas']['TurnSchema']`
- `components['schemas']['PostSchema']`

Prefer using these in `ui/lib/api/*` instead of re-declaring API response interfaces.

## Typical workflow: adding a new field

1) Update backend schema / route
   - Example: add a field to `simulation/api/schemas/simulation.py` and ensure the
     route response includes it.
2) Regenerate contract artifacts
   - `cd ui && npm run generate:api`
3) Update UI usage
   - Update any mapping code (e.g., `ui/lib/api/simulation.ts`) and UI components to
     handle the new field (including `undefined`/`null` if applicable).
4) Verify locally
   - UI: `cd ui && npx tsc --noEmit` (or `npm run build`)
   - Backend: `uv run ruff check .`, `uv run pyright .`, `uv run pytest` (as appropriate)
5) Enforce drift-free state
   - `cd ui && npm run check:api` should pass
   - Ensure `ui/openapi.json` and `ui/types/api.generated.ts` are committed.

## Troubleshooting

- `openapi-typescript: command not found`
  - Run `cd ui && npm ci` (or `npm install`) to install UI devDependencies.
- Python import errors while generating OpenAPI
  - Run `uv sync` at repo root to install backend dependencies, then rerun
    `cd ui && npm run generate:api`.

