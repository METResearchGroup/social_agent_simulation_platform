---
name: UI schema-first contracts
description: Generate UI-friendly camelCase aliases straight from the backend OpenAPI spec so the UI types stay in sync without handwritten definitions or a dedicated validator.
tags:
  - ui
  - schema
  - docs
---

## Remember
- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

## Overview
Treat the previously handwritten interfaces as generated aliases: run `scripts/generate_openapi_json.py`, compile to `ui/types/api.generated.ts`, then automatically emit `ui/types/generated.ts` that camelizes schema properties and re-exports `Run`, `Agent`, `Post`, `Feed`, `AgentAction`, `Turn`, `FeedAlgorithm`, `Metric`, and `RunConfig`. This removes duplication, keeps the backend OpenAPI spec as the source of truth, and eliminates the need for the validator script that was guarding against drift.

## Happy Flow
1. **Spec regeneration** – `scripts/generate_openapi_json.py --out ui/openapi.json` followed by `openapi-typescript` updates `ui/types/api.generated.ts` with the latest backend schemas.
2. **Generate aliases** – `ui/scripts/generate-ui-contracts.mts` consumes `components['schemas']`, applies `Camelize` helpers, and writes `ui/types/generated.ts` with UI-facing aliases.
3. **UI imports** – UI code continues to `import { Run, Agent, Post, ... } from '@/types';`, but `ui/types/index.ts` now re-exports the generated aliases instead of hand-rolled interfaces.
4. **CI guard** – `ui/package.json`’s `generate:api` pipeline runs both generation steps and `check:api` still regenerates the contracts before diffing `openapi.json`/`types/api.generated.ts`, making drift impossible.

## Manual Verification
- `cd ui && npm run generate:api` — confirm `types/api.generated.ts` and `types/generated.ts` regenerate without diffs.
- `cd ui && npm run check:api` — ensures the new generator runs and the git diff check passes (this is the CI step now).
- (Optional drift proof) edit `ui/types/generated.ts` (manually, then revert) to simulate drift, rerun `npm run check:api`, and verify git diff catches it.

## Alternative approaches
1. **Keep handwritten interfaces + validator:** Already implemented; requires manual maintenance and an extra script that quickly became redundant once we re-export generated aliases.
2. **Consume generated schemas directly everywhere:** Possible but would force snake_case properties into UI code; generating camelCased aliases keeps ergonomics while still reading from the spec.
3. **Runtime schema validation (zod, etc.):** Would add runtime cost and dependencies for minimal benefit since we now rely on compile-time aliases.

## Specific implementation steps
1. Add `ui/scripts/generate-ui-contracts.mts` that builds `ui/types/generated.ts` with camelCase aliases plus a `RunConfig` helper that exposes `metricKeys?`.
2. Change `ui/types/index.ts` to re-export `Run`, `Agent`, etc., from `./generated` and keep `ApiError` defined locally.
3. Update `ui/package.json` so `generate:api` runs the new generator, keeping `check:api` as `npm run generate:api && git diff --exit-code -- openapi.json types/api.generated.ts`.
4. Remove `ui/scripts/validate-handwritten-interfaces.mts`; CI no longer needs it because the UI types are now derived.
5. Document the workflow in `docs/plans/2026-02-27_ui_schema_source_478301/plan.md` and `README.md`.

## Assumptions / defaults
- Node 20+ for `npm run generate:api` and `tsx` before removal (no longer needed). 
- Backend OpenAPI spec generation remains upstream of all UI contracts. 
- No UI screenshot work required for this plan.
