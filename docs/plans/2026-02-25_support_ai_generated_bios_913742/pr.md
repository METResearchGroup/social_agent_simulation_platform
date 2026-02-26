## Overview
Move the agent-generated-bio endpoints into the service layer so the routes no longer reach directly into `db` or `simulation.core`, and refresh the schema + docs that describe the new `agent_generated_bios` table.

## Problem / motivation
Routes for generating and listing AI bios were importing `db` repositories and `simulation.core` models directly, which breaks the import contracts (and left pyright/pre-commit failing) whenever those handlers ran; the new generated-bio flow also depends on metadata that was being fetched manually in the route instead of through reusable services.

## Solution
Add a dedicated `list_agent_generated_bios_for_agent` helper, normalize handles + repository access in the service, convert prompt messages to JSON before handing them to the LLM, and let the routes call that service (so they only touch schemas and not the persistence layers). Update the repository exports and schema documentation so everything aligns with the new migration.

## Happy Flow
1. **Request handling** – `POST /simulations/agents/{handle}/generated-bios` now calls `create_generated_bio_for_agent`, logs metrics, and transforms the resulting `AgentGeneratedBio` into `AgentGeneratedBioSchema`.
2. **Listing history** – `GET /simulations/agents/{handle}/generated-bios` delegates to `list_agent_generated_bios_for_agent`, which validates the handle, loads repositories, and maps each `AgentGeneratedBio` into the schema.
3. **Service orchestration** – `simulation/api/services/agent_generated_bio_service.py` continues to build the LLM prompt, now serializes `ChatPromptTemplate` output into dicts, invokes `structured_completion`, and persists the generated bio through the adapter + repository stack.

## Data Flow
1. The service normalizes the handle, loads the SQLite adapter/repository, fetches the freshest persona + metadata, formats the prompt (as JSON dicts), calls the LLM, then writes the generated bio via `AgentGeneratedBioRepository`.
2. Listing uses the same normalization flow but simply reads the stored `agent_generated_bios` rows from the repository and returns them as schema objects.
3. The routes call those services via `asyncio.to_thread`, convert the service results to `AgentGeneratedBioSchema`, and surface the same `/simulations/agents/{handle}/generated-bios` endpoints with rate limits and structured HTTP errors.

## Changes
- `simulation/api/routes/simulation.py`: remove direct `db`/`simulation.core` imports, wire the new listing helper, and keep error handling focused on HTTP responses.
- `simulation/api/services/agent_generated_bio_service.py`: serialize prompt messages before calling the LLM, add `list_agent_generated_bios_for_agent`, and keep normalization + repo wiring inside the service.
- `db/repositories/__init__.py` & `db/repositories/interfaces.py`: export `AgentGeneratedBioRepository` so callers can reference the interface alongside the new SQLite implementation.
- `db/adapters/sqlite/agent_generated_bio_adapter.py` & `db/repositories/agent_generated_bio_repository.py`: persist/list bios through the new SQLite repository/adapter pair.
- `db/schema.py`, `docs/db/LATEST.txt`, and `docs/db/2026_02_26-083707-support-ai-generated-bios/*`: capture the updated schema metadata and docs for the `agent_generated_bios` migration.
- `tests/db/adapters/sqlite/test_agent_generated_bio_adapter.py` & `tests/db/repositories/test_agent_generated_bio_repository.py`: tighten expectations around optional metadata and list behavior, matching the service.

## Manual Verification
- `uv run ruff check .`
- `PYTHONPATH=. uv run --extra test pyright .`
- `pre-commit run pyright --all-files`
- `uv run python scripts/generate_db_schema_docs.py --update`
- `uv run python scripts/check_db_schema_drift.py`

## State (Before)
![Agents metadata before](docs/plans/2026-02-25_support_ai_generated_bios_913742/images/before/agents-metadata-before.png)

## State (After)
![Agents metadata after](docs/plans/2026-02-25_support_ai_generated_bios_913742/images/after/agents-metadata-after.png)
