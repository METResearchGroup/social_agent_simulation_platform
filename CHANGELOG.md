# Changelog

## 2026-03-02 to 2026-03-08

### Backend/API (2026-03-02 to 2026-03-08)

- High-level summary: Backend simulation APIs added agent deletion support and tightened validation usage across adapters and domain models. These changes primarily touched API routes, repositories, adapters, and model validators.
- PRs:
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/173](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/173): Add delete-agent endpoint and UI control. Adds a delete-agent API path and related repository/adapter support for deleting agent records and linked metadata.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/193](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/193): Refine validate_non_empty_string usage. Normalizes validation utility usage across database adapters, schemas, and simulation core model types.

### UI/frontend (2026-03-02 to 2026-03-08)

- High-level summary: Frontend updates added direct controls for agent deletion and run ID copying, with follow-up convention cleanup in core components. The week included both feature work and UI consistency adjustments.
- PRs:
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/173](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/173): Add delete-agent endpoint and UI control. Introduces the delete action in the agents UI and updates generated API types to support the new endpoint.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/182](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/182): add copying button for runId. Adds a copy-to-clipboard control in the run summary view for faster run ID reuse.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/197](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/197): Apply convention fixes from repo review automation. Applies targeted UI component convention fixes in `AgentsView` and `RunSummary`.

### ML (2026-03-02 to 2026-03-08)

- High-level summary: No model, training, evaluation, or inference-specific pull requests were merged this week. ML behavior remained unchanged in this window.
- PRs:
  - _None this week._

### Platform (2026-03-02 to 2026-03-08)

- High-level summary: No infrastructure or deployment-platform specific pull requests were identified in first-parent merge history this week. Runtime platform behavior did not have dedicated platform PRs in this window.
- PRs:
  - _None this week._

### Docs/Quality (2026-03-02 to 2026-03-08)

- High-level summary: Quality work expanded validation tests and enforced Python test syntax conventions in CI and pre-commit. Validation cleanup work also updated test coverage and supporting runbook/plan artifacts.
- PRs:
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/181](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/181): Add unit tests for `validate_non_empty_iterable` and `validate_non_empty_string`. Adds focused unit tests for validation helpers in `tests/lib/test_validation_utils.py`.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/193](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/193): Refine validate_non_empty_string usage. Updates validators and related tests to align string validation call patterns across the codebase.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/196](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/196): Enforce python testing syntax conventions. Adds a lint script and CI/pre-commit enforcement while migrating affected test files to the required syntax pattern.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/197](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/197): Apply convention fixes from repo review automation. Applies review-driven fixes in tests and UI components to align with repository conventions.

### Automation/CI (2026-03-02 to 2026-03-08)

- High-level summary: Automation runs produced a weekly report at the start of the window, a feature-ideas report, and a refreshed weekly update at the end of the window. Reporting automation activity was concentrated in docs artifacts.
- PRs:
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/175](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/175): [2026-03-02] Codex repo automation - Weekly work update. Adds the weekly update artifact for the prior Monday-to-Sunday period in `docs/weekly_updates/`.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/188](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/188): Add 2026-03-07 feature ideas automation report. Adds the dated feature-ideas automation output under `docs/feature_ideas/`.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/192](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/192): [2026-03-08] Codex repo automation - Weekly work update. Adds the weekly update artifact for `2026-03-02` through `2026-03-08`.

### Bug Fixes (2026-03-02 to 2026-03-08)

- High-level summary: No standalone bug-fix-only PRs were identified outside the feature and quality categories above. Fix-oriented changes are captured in those sections.
- PRs:
  - _None this week._

## 2026-02-23 to 2026-02-28

### Backend/API (2026-02-23 to 2026-02-28)

- High-level summary: Stabilized backend data flows by extending schema docs, improving fault tolerance for run config fetches, and reshuffling connection management so auth and persistence layers stay reliable. Persisted run actions/metrics metadata, exposed feed config inputs, and added per-run metric selection so the UI can drive rich telemetry. Removed deprecated fields on agent creation submissions while keeping action guardrails and timeline attribution in sync with the new tables.
- PRs:
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/101](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/101): Add app_user table and run attribution (Phase 2 auth). Introduces the `app_user` table and associated attribution wiring to support Phase 2 authentication and map runs back to callers.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/165](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/165): Handle transient run config fetch failures. Adds safeguards so clients recover gracefully when run configuration lookups momentarily fail.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/142](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/142): Add versioned DB schema docs + drift checks. Documents schema versions and surfaces drift detection to prevent unmanaged database divergence.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/147](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/147): Migrate action guardrails into action history/policy. Moves guardrail logic into the action history/policy system so future decisions automatically honor historical constraints.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/135](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/135): Add permanent persistence for run actions (likes/comments/follows). Stores agent actions permanently so metrics and replay tooling can rely on a complete history.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/138](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/138): Display metrics as part of run parameters. Expands run metadata to include metric values so the UI can reflect them when configuring runs.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/127](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/127): Add per-run metric selection and persistence to the backend. Allows each run to capture which metrics were chosen and persist those selections for downstream reporting.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/124](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/124): Add metrics metadata to the API. Surfaces metadata (e.g., labels, descriptions) so the frontend can explain metric choices.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/122](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/122): Render feed algorithm config inputs. Delivers backend support for rendering feed ranking configuration so UI editors can adjust algorithm parameters.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/120](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/120): Move conn manager from adapter to repository layer. Relocates connection management to the repository layer to simplify dependency wiring for storage access.

### UI/frontend (2026-02-23 to 2026-02-28)

- High-level summary: Refined agent creation, pagination, and metric configuration experiences while tightly coupling the UI with backend APIs and typed contracts. Added validation for handwritten inputs, richer previews, and search filters so agent builders have immediate feedback, and generated OpenAPI-derived types to keep frontend/back-end contracts aligned.
- PRs:
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/161](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/161): Add validation for handwritten UI interfaces. Adds validation rules that surface errors when handwritten interface definitions fail schema checks.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/133](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/133): Create metrics selector component. Ships a reusable component so users can pick metrics from a consistent UI across forms.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/132](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/132): Add pagination for agent listing. Introduces pagination controls to keep large agent sets manageable in the UI.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/116](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/116): UI: Create a 'create-agents' view. Adds the dedicated agent creation screen and wires it into the main navigation.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/125](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/125): Add post previews for comment actions. Displays previews of comments within the UI so builders understand the context of comment actions.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/117](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/117): Connect Create agent form to backend and View agents to DB. Hooks UI forms up to backend persistence so created agents actually save to the database.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/152](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/152): Add agent search/filtering via q param. Enables quick filtering of agents via a query parameter.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/104](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/104): OpenAPI-generated UI API types + CI contract check. Adds generated API types and a CI check to keep UI contracts aligned with OpenAPI.

### ML (2026-02-23 to 2026-02-28)

- High-level summary: No ML-focused PRs were merged this week, so the pipeline work remains scheduled for future sprints.
- PRs:
  - _None this week._

### Platform (2026-02-23 to 2026-02-28)

- High-level summary: Improved the local development experience by allowing a deterministic dummy database and seed to be forced when DISABLE_AUTH is enabled. This keeps contributors productive while fuzzing auth gubs and preparing for future migrations.
- PRs:
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/136](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/136): Add LOCAL dev mode forced dummy DB + seed. Adds logic to create and seed a dummy database when local dev mode is enabled so devs can run scenarios without needing a real backend.

### Docs/Quality (2026-02-23 to 2026-02-28)

- High-level summary: Bolstered documentation linting, TypeScript/ Python guardrails, deterministic factories, and utility organization to keep the repo consistent and easier to scale. These changes also added metadata checks so CI can enforce the repository’s documentation and architecture conventions.
- PRs:
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/158](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/158): Add docs metadata linter. Ships the metadata linter that validates `description` and `tags` blocks in docs runbooks/plans.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/140](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/140): docs: suggest custom architecture linters. Documents new architecture linting ideas to guide future automation.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/153](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/153): Add TS custom ESLint linters (TS-1..TS-5). Adds tailor-made ESLint rules for the TypeScript codebase.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/154](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/154): Enforce PY-1 import contracts with import-linter. Enforces repository import layer contracts via import-linter.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/156](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/156): Add Python dependency injection guard. Adds checks to prevent instantiating concrete infrastructure inside business logic.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/155](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/155): Migrate simulation core utilities into utils package. Moves shared utilities into `utils/` to reduce coupling.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/148](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/148): Add deterministic test factories (Faker + Hypothesis). Adds deterministic Faker/Hypothesis factories so tests stay stable across runs.

### Automation/CI (2026-02-23 to 2026-02-28)

- High-level summary: Continued the Codex feature ideas scan automation across multiple dates to keep a steady stream of discovery for the backlog. The automation runs were documented so the daily scans remain visible in release notes.
- PRs:
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/144](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/144): [2026-02-25] Codex repo automation - Feature ideas scan. Captures the Feb 25 feature ideas scan automation results.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/131](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/131): [2026-02-24] Codex repo automation - Feature ideas scan. Captures the Feb 24 feature ideas scan automation results.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/106](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/106): [2026-02-21] Codex repo automation - Feature ideas scan. Captures the Feb 21 feature ideas scan automation results.

### Bug Fixes (2026-02-23 to 2026-02-28)

- High-level summary: Cleaned up failing tests by aligning the `expected_result` fixtures with the updated behavior so CI remains green. This also prevents regressions in suites that relied on those expectations.
- PRs:
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/143](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/143): Fix tests to use expected_result. Updates the affected tests to use the corrected `expected_result`.
  - [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/129](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/129): Fix tests to use expected_result. Aligns another batch of tests with the new `expected_result` semantics.
