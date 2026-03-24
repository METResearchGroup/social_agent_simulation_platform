---
name: release parity guardrails
description: "Implementation plan for release parity guardrails: coordinated same-ref Railway/Vercel deploys, auth-aware smoke tests aligned to the API contract, and live metadata-route verification."
tags: [plan, release, smoke-test, deployment]
overview: Plan the first implementation slice that stops production UI/API skew by tightening release coordination and adding contract-aware verification, without changing seeding, schema, or bootstrap behavior.
todos:
  - id: freeze-scope
    content: "Freeze the first slice to release-parity guardrails only: coordinated deploy docs, auth-aware smoke coverage, and explicit live-contract verification."
    status: pending
  - id: update-smoke-suite
    content: Revise the smoke suite to match the current API contract and cover the missing-route regression class with an explicit auth strategy.
    status: pending
  - id: update-runbooks
    content: Add a same-ref production release flow across the Railway and Vercel runbooks, including canonical API URL verification and post-deploy checks.
    status: pending
  - id: coordinator-verify
    content: Run the focused verification commands and confirm the docs/tests catch the exact skew failure mode from the diagnosis.
    status: pending
isProject: false
---

# Release Parity Guardrails

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- Maximum safely delegable parallelism
- Delegated tasks must be impossible to misread

## Overview

This slice addresses the outage class caused by deploying a newer UI against an older API. The work should stay narrowly focused on release coordination and verification guardrails: make the production deployment flow explicitly same-ref across Railway and Vercel, update the live smoke suite to match the current backend contract, and add operator checks that catch missing metadata routes or feed-shape skew before the UI is considered healthy.

## Happy Flow

1. An operator chooses one release ref and uses it for both the API and UI deploy flows documented in `[/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/RAILWAY_DEPLOYMENT.md](/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/RAILWAY_DEPLOYMENT.md)`, `[/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/UI_DEPLOYMENT.md](/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/UI_DEPLOYMENT.md)`, and `[/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/PRODUCTION_DEPLOYMENT.md](/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/PRODUCTION_DEPLOYMENT.md)`.
2. Railway serves the repo’s current backend contract, including the metadata endpoints implemented in `[/Users/mark/Documents/work/agent_simulation_platform/simulation/api/routes/metadata.py](/Users/mark/Documents/work/agent_simulation_platform/simulation/api/routes/metadata.py)` and mounted from `[/Users/mark/Documents/work/agent_simulation_platform/simulation/api/main.py](/Users/mark/Documents/work/agent_simulation_platform/simulation/api/main.py)`.
3. Vercel points `NEXT_PUBLIC_SIMULATION_API_URL` at the canonical Railway production URL used by the current UI client in `[/Users/mark/Documents/work/agent_simulation_platform/ui/lib/api/simulation.ts](/Users/mark/Documents/work/agent_simulation_platform/ui/lib/api/simulation.ts)`, so the UI requests the same contract that the backend actually serves.
4. The smoke suite in `[/Users/mark/Documents/work/agent_simulation_platform/tests/api/test_simulation_smoke.py](/Users/mark/Documents/work/agent_simulation_platform/tests/api/test_simulation_smoke.py)` verifies `/health`, verifies the current `POST /v1/simulations/run` response shape, and verifies the metadata endpoints with an explicit auth path rather than assuming they are public.
5. Manual post-deploy checks confirm the live API exposes the expected routes and the UI can open a seeded run without the `postIds` crash class described in `[/Users/mark/Documents/work/agent_simulation_platform/strategy_planning/2026-03-24_prod_bug_diagnosis/PROPOSED_FIXES.md](/Users/mark/Documents/work/agent_simulation_platform/strategy_planning/2026-03-24_prod_bug_diagnosis/PROPOSED_FIXES.md)`.

## Asset Storage

Store plan artifacts under `docs/plans/2026-03-24_release_parity_prod_contract_d2028c/`.

## Alternative Approaches

- We should not change seed loading, SQLite lifecycle, or startup bootstrap in this slice; those are separate concerns and would blur whether release skew was actually fixed.
- We should prefer auth-aware smoke verification over anonymous route checks because the metadata routes live behind the global simulation auth dependency in `[/Users/mark/Documents/work/agent_simulation_platform/simulation/api/routes/simulation.py](/Users/mark/Documents/work/agent_simulation_platform/simulation/api/routes/simulation.py)`.
- We should avoid changing UI components in this slice; the current repo already expects `post_ids`, so the main gap is release/process verification rather than UI implementation.

## Interface or Contract Freeze

- Do not change seeding behavior in `[/Users/mark/Documents/work/agent_simulation_platform/simulation/local_dev/seed_loader.py](/Users/mark/Documents/work/agent_simulation_platform/simulation/local_dev/seed_loader.py)`.
- Do not change SQLite schema, migrations, or deployment bootstrap files such as `[/Users/mark/Documents/work/agent_simulation_platform/Dockerfile](/Users/mark/Documents/work/agent_simulation_platform/Dockerfile)` or `[/Users/mark/Documents/work/agent_simulation_platform/railway.json](/Users/mark/Documents/work/agent_simulation_platform/railway.json)`.
- Treat the current backend contract as the source of truth for this slice: metadata routes exist, `FeedSchema.post_ids` is correct, and the smoke suite must be updated to that contract rather than restoring legacy `likes_per_turn` expectations.
- Keep local-dev auth semantics unchanged; if smoke coverage needs protected endpoints, use a bearer-token env var or documented local auth bypass rather than weakening route auth.
- Do not edit `ui/` source files unless a truly minimal doc-reference correction is unavoidable; this slice is verification-focused.

## Serial Coordination Spine

1. Confirm the exact verification target for protected routes: introduce one explicit smoke-suite input such as `SIMULATION_API_BEARER_TOKEN`, and document how operators provide it for deployed checks.
2. Update the smoke suite to reflect the current `RunResponse` contract and add protected-route verification for `/v1/simulations/metrics` and `/v1/simulations/feed-algorithms`.
3. Rewrite the deploy runbooks into one coordinated same-ref release flow with explicit checks for `NEXT_PUBLIC_SIMULATION_API_URL`, Railway domain, and post-deploy contract verification.
4. Run the focused verification commands locally and document any residual manual-only checks for the live environment.

## Parallel Task Packets

### Task Packet A: Smoke Suite Contract Guardrails

- Task ID: `smoke-contract-guardrails`
- Objective: Make `[/Users/mark/Documents/work/agent_simulation_platform/tests/api/test_simulation_smoke.py](/Users/mark/Documents/work/agent_simulation_platform/tests/api/test_simulation_smoke.py)` detect the exact contract-skew failure mode instead of validating stale response fields.
- Why parallelizable: This packet owns only test logic and its runbook references; it does not need to edit deployment docs at the same time.
- Exact files to inspect:
  - `[/Users/mark/Documents/work/agent_simulation_platform/tests/api/test_simulation_smoke.py](/Users/mark/Documents/work/agent_simulation_platform/tests/api/test_simulation_smoke.py)`
  - `[/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/SMOKE_TEST.md](/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/SMOKE_TEST.md)`
  - `[/Users/mark/Documents/work/agent_simulation_platform/simulation/api/main.py](/Users/mark/Documents/work/agent_simulation_platform/simulation/api/main.py)`
  - `[/Users/mark/Documents/work/agent_simulation_platform/simulation/api/routes/metadata.py](/Users/mark/Documents/work/agent_simulation_platform/simulation/api/routes/metadata.py)`
  - `[/Users/mark/Documents/work/agent_simulation_platform/simulation/api/routes/simulation.py](/Users/mark/Documents/work/agent_simulation_platform/simulation/api/routes/simulation.py)`
  - `[/Users/mark/Documents/work/agent_simulation_platform/simulation/api/schemas/simulation.py](/Users/mark/Documents/work/agent_simulation_platform/simulation/api/schemas/simulation.py)`
- Exact files allowed to change:
  - `[/Users/mark/Documents/work/agent_simulation_platform/tests/api/test_simulation_smoke.py](/Users/mark/Documents/work/agent_simulation_platform/tests/api/test_simulation_smoke.py)`
  - `[/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/SMOKE_TEST.md](/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/SMOKE_TEST.md)`
- Exact files forbidden to change:
  - `[/Users/mark/Documents/work/agent_simulation_platform/simulation/local_dev/seed_loader.py](/Users/mark/Documents/work/agent_simulation_platform/simulation/local_dev/seed_loader.py)`
  - `[/Users/mark/Documents/work/agent_simulation_platform/db/migrations](/Users/mark/Documents/work/agent_simulation_platform/db/migrations)`
  - `[/Users/mark/Documents/work/agent_simulation_platform/ui](/Users/mark/Documents/work/agent_simulation_platform/ui)`
  - `[/Users/mark/Documents/work/agent_simulation_platform/Dockerfile](/Users/mark/Documents/work/agent_simulation_platform/Dockerfile)`
- Preconditions:
  - The repo contract remains as currently implemented: metadata routes exist and require auth.
  - A valid deployed check can provide either `SIMULATION_API_BEARER_TOKEN` or a local bypass path such as `DISABLE_AUTH=1` for non-prod verification.
- Dependency tasks: none.
- Required contracts and invariants:
  - `GET /health` must remain anonymously accessible and continue returning `{"status": "ok"}`.
  - `POST /v1/simulations/run` assertions must match the current `RunResponse` shape in the repo, not legacy fields.
  - Metadata smoke checks must fail loudly on 404 and distinguish auth/setup failures from contract absence.
  - The smoke suite must still skip cleanly when `SIMULATION_API_URL` is unset.
- Step-by-step implementation instructions:
  1. Add one helper for optional bearer-token headers in `[/Users/mark/Documents/work/agent_simulation_platform/tests/api/test_simulation_smoke.py](/Users/mark/Documents/work/agent_simulation_platform/tests/api/test_simulation_smoke.py)`.
  2. Replace the legacy `likes_per_turn` and `total_likes` assertions with checks against the current `RunResponse` fields already returned by the repo.
  3. Add smoke tests for `GET /v1/simulations/metrics` and `GET /v1/simulations/feed-algorithms` that send `Authorization: Bearer <token>` when `SIMULATION_API_BEARER_TOKEN` is set.
  4. Make auth prerequisites explicit in `[/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/SMOKE_TEST.md](/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/SMOKE_TEST.md)`, including one deployed example and one local bypass example.
- Exact verification commands:
  - `uv run pytest tests/api/test_simulation_smoke.py -q`
  - `SIMULATION_API_URL=http://localhost:8000 uv run pytest -m smoke tests/api/test_simulation_smoke.py -q`
  - `SIMULATION_API_URL=https://agent-simulation-platform-production.up.railway.app SIMULATION_API_BEARER_TOKEN=<token> uv run pytest -m smoke tests/api/test_simulation_smoke.py -q`
- Expected outputs from verification:
  - First command: test module imports and local unit-style smoke file passes or skips without syntax/collection errors.
  - Second command: smoke tests pass against a locally running server with auth bypass enabled.
  - Third command: deployed smoke tests pass, including HTTP 200 responses from `/v1/simulations/metrics` and `/v1/simulations/feed-algorithms`.
- Done-when checklist:
  - Smoke assertions no longer reference legacy response fields.
  - Missing metadata routes would cause a deterministic smoke failure.
  - The runbook documents how to authenticate protected smoke checks.
- Coordinator review checklist:
  - Confirm the smoke suite never weakens production auth requirements.
  - Confirm the smoke suite surfaces 404 regressions, not just generic request failures.
  - Confirm examples in the runbook exactly match the env vars accepted by the test file.

### Task Packet B: Coordinated Release Runbooks

- Task ID: `release-runbook-parity`
- Objective: Turn the separate Railway and Vercel deployment docs into a coordinated production release flow that makes same-ref deployment and canonical API URL verification explicit.
- Why parallelizable: This packet owns docs and operator flow only; it does not need to change test implementation while Packet A proceeds.
- Exact files to inspect:
  - `[/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/RAILWAY_DEPLOYMENT.md](/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/RAILWAY_DEPLOYMENT.md)`
  - `[/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/UI_DEPLOYMENT.md](/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/UI_DEPLOYMENT.md)`
  - `[/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/PRODUCTION_DEPLOYMENT.md](/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/PRODUCTION_DEPLOYMENT.md)`
  - `[/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/SMOKE_TEST.md](/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/SMOKE_TEST.md)`
  - `[/Users/mark/Documents/work/agent_simulation_platform/ui/lib/api/simulation.ts](/Users/mark/Documents/work/agent_simulation_platform/ui/lib/api/simulation.ts)`
- Exact files allowed to change:
  - `[/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/RAILWAY_DEPLOYMENT.md](/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/RAILWAY_DEPLOYMENT.md)`
  - `[/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/UI_DEPLOYMENT.md](/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/UI_DEPLOYMENT.md)`
  - `[/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/PRODUCTION_DEPLOYMENT.md](/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/PRODUCTION_DEPLOYMENT.md)`
- Exact files forbidden to change:
  - `[/Users/mark/Documents/work/agent_simulation_platform/railway.json](/Users/mark/Documents/work/agent_simulation_platform/railway.json)`
  - `[/Users/mark/Documents/work/agent_simulation_platform/Dockerfile](/Users/mark/Documents/work/agent_simulation_platform/Dockerfile)`
  - `[/Users/mark/Documents/work/agent_simulation_platform/simulation/local_dev/seed_fixtures](/Users/mark/Documents/work/agent_simulation_platform/simulation/local_dev/seed_fixtures)`
  - `[/Users/mark/Documents/work/agent_simulation_platform/ui/components](/Users/mark/Documents/work/agent_simulation_platform/ui/components)`
- Preconditions:
  - Packet A defines the final smoke-test env vars and command examples before this packet is merged.
- Dependency tasks:
  - `smoke-contract-guardrails` for the exact smoke command shape.
- Required contracts and invariants:
  - The release process must require one chosen ref for both platforms.
  - The runbooks must explicitly verify `NEXT_PUBLIC_SIMULATION_API_URL` points at the canonical Railway production URL.
  - The runbooks must add post-deploy checks for `/health`, `/v1/simulations/metrics`, and `/v1/simulations/feed-algorithms`.
  - This packet must not introduce bootstrap, seeding, or infrastructure-behavior changes.
- Step-by-step implementation instructions:
  1. Add a short shared release section in `[/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/PRODUCTION_DEPLOYMENT.md](/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/PRODUCTION_DEPLOYMENT.md)` that defines the same-ref rule and recommended deploy order.
  2. Update `[/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/RAILWAY_DEPLOYMENT.md](/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/RAILWAY_DEPLOYMENT.md)` to include contract verification commands for the metadata endpoints and to remove stale references to `likes_per_turn` / `total_likes`.
  3. Update `[/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/UI_DEPLOYMENT.md](/Users/mark/Documents/work/agent_simulation_platform/docs/runbooks/UI_DEPLOYMENT.md)` to require checking the production API base URL and to point operators at the shared smoke/manual verification flow.
  4. Ensure the wording names the exact production URLs used in the diagnosis only as examples, while keeping the runbooks reusable for future releases.
- Exact verification commands:
  - `uv run python scripts/check_docs_metadata.py docs/runbooks/RAILWAY_DEPLOYMENT.md docs/runbooks/UI_DEPLOYMENT.md docs/runbooks/PRODUCTION_DEPLOYMENT.md docs/runbooks/SMOKE_TEST.md`
  - `rg "likes_per_turn|total_likes" /Users/mark/Documents/work/agent_simulation_platform/docs/runbooks`
- Expected outputs from verification:
  - Metadata check command exits successfully with no missing-front-matter errors.
  - `rg` returns no matches in the edited runbooks for stale legacy response fields.
- Done-when checklist:
  - Operators can follow one same-ref release flow without inferring hidden steps.
  - The Vercel runbook tells operators exactly what API URL to validate.
  - The Railway runbook includes route-level contract checks for the outage endpoints.
- Coordinator review checklist:
  - Confirm the runbooks do not imply anonymous access to protected endpoints.
  - Confirm every command in the docs is copy-pastable and uses the same env var names as Packet A.
  - Confirm no doc still describes legacy run-response fields.

## Integration Order

1. Complete `smoke-contract-guardrails` first so the final smoke command and auth inputs are stable.
2. Update the coordinated release runbooks against that finalized smoke command.
3. Run focused test and docs verification locally.
4. Use the updated runbooks for one live deploy verification pass against the production Railway and Vercel services.

## Manual Verification

- Start a local API with auth bypass for smoke validation: `DISABLE_AUTH=1 PYTHONPATH=. uv run uvicorn simulation.api.main:app --port 8000`
- Run the smoke suite locally: `SIMULATION_API_URL=http://localhost:8000 uv run pytest -m smoke tests/api/test_simulation_smoke.py -q`
- Expected local result: `/health`, `/v1/simulations/run`, `/v1/simulations/metrics`, and `/v1/simulations/feed-algorithms` all pass.
- Validate docs metadata after edits: `uv run python scripts/check_docs_metadata.py docs/runbooks/RAILWAY_DEPLOYMENT.md docs/runbooks/UI_DEPLOYMENT.md docs/runbooks/PRODUCTION_DEPLOYMENT.md docs/runbooks/SMOKE_TEST.md`
- Run the deployed smoke suite with auth: `SIMULATION_API_URL=https://agent-simulation-platform-production.up.railway.app SIMULATION_API_BEARER_TOKEN=<token> uv run pytest -m smoke tests/api/test_simulation_smoke.py -q`
- Manually check the live API routes:
  - `curl -sS https://agent-simulation-platform-production.up.railway.app/health`
  - `curl -sS -H "Authorization: Bearer <token>" https://agent-simulation-platform-production.up.railway.app/v1/simulations/metrics`
  - `curl -sS -H "Authorization: Bearer <token>" https://agent-simulation-platform-production.up.railway.app/v1/simulations/feed-algorithms`
- Manually check the UI deploy flow in the updated docs, confirm `NEXT_PUBLIC_SIMULATION_API_URL` points at the canonical Railway production URL, open the production UI, select a seeded run, and confirm the page loads without the `postIds` crash.

## Final Verification

- `uv run pytest tests/api/test_simulation_smoke.py -q`
  - Expected: no collection failures; smoke tests skip cleanly when `SIMULATION_API_URL` is unset.
- `DISABLE_AUTH=1 PYTHONPATH=. uv run uvicorn simulation.api.main:app --port 8000`
  - Expected: local server starts successfully for smoke validation.
- `SIMULATION_API_URL=http://localhost:8000 uv run pytest -m smoke tests/api/test_simulation_smoke.py -q`
  - Expected: local smoke pass covering `/health`, `/v1/simulations/run`, and both metadata endpoints.
- `uv run python scripts/check_docs_metadata.py docs/runbooks/RAILWAY_DEPLOYMENT.md docs/runbooks/UI_DEPLOYMENT.md docs/runbooks/PRODUCTION_DEPLOYMENT.md docs/runbooks/SMOKE_TEST.md`
  - Expected: success with no metadata errors.
- `SIMULATION_API_URL=https://agent-simulation-platform-production.up.railway.app SIMULATION_API_BEARER_TOKEN=<token> uv run pytest -m smoke tests/api/test_simulation_smoke.py -q`
  - Expected: deployed smoke pass that would fail immediately if the live backend were missing the metadata routes.

No UI screenshots are required for this slice because the planned code changes are limited to backend smoke tests and deployment/testing runbooks, not `ui/` implementation files.
