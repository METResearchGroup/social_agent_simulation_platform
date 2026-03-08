# Changelog

## 2026-03-02 to 2026-03-08

### Backend/API

- High-level summary: Backend simulation APIs added agent deletion support and tightened validation usage across adapters and domain models. These changes primarily touched API routes, repositories, adapters, and model validators.
- PRs:
- [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/173](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/173): Add delete-agent endpoint and UI control. Adds a delete-agent API path and related repository/adapter support for deleting agent records and linked metadata.
- [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/193](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/193): Refine validate_non_empty_string usage. Normalizes validation utility usage across database adapters, schemas, and simulation core model types.

### UI/frontend

- High-level summary: Frontend updates added direct controls for agent deletion and run ID copying, with follow-up convention cleanup in core components. The week included both feature work and UI consistency adjustments.
- PRs:
- [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/173](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/173): Add delete-agent endpoint and UI control. Introduces the delete action in the agents UI and updates generated API types to support the new endpoint.
- [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/182](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/182): add copying button for runId. Adds a copy-to-clipboard control in the run summary view for faster run ID reuse.
- [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/197](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/197): Apply convention fixes from repo review automation. Applies targeted UI component convention fixes in `AgentsView` and `RunSummary`.

### ML

- High-level summary: No model, training, evaluation, or inference-specific pull requests were merged this week. ML behavior remained unchanged in this window.
- PRs:
 - _None this week._

### Platform

- High-level summary: No infrastructure or deployment-platform specific pull requests were identified in first-parent merge history this week. Runtime platform behavior did not have dedicated platform PRs in this window.
- PRs:
 - _None this week._

### Docs/Quality

- High-level summary: Quality work expanded validation tests and enforced Python test syntax conventions in CI and pre-commit. Validation cleanup work also updated test coverage and supporting runbook/plan artifacts.
- PRs:
- [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/181](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/181): Add unit tests for `validate_non_empty_iterable` and `validate_non_empty_string`. Adds focused unit tests for validation helpers in `tests/lib/test_validation_utils.py`.
- [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/193](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/193): Refine validate_non_empty_string usage. Updates validators and related tests to align string validation call patterns across the codebase.
- [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/196](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/196): Enforce python testing syntax conventions. Adds a lint script and CI/pre-commit enforcement while migrating affected test files to the required syntax pattern.
- [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/197](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/197): Apply convention fixes from repo review automation. Applies review-driven fixes in tests and UI components to align with repository conventions.

### Automation/CI

- High-level summary: Automation runs produced a weekly report at the start of the window, a feature-ideas report, and a refreshed weekly update at the end of the window. Reporting automation activity was concentrated in docs artifacts.
- PRs:
- [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/175](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/175): [2026-03-02] Codex repo automation - Weekly work update. Adds the weekly update artifact for the prior Monday-to-Sunday period in `docs/weekly_updates/`.
- [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/188](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/188): Add 2026-03-07 feature ideas automation report. Adds the dated feature-ideas automation output under `docs/feature_ideas/`.
- [https://github.com/METResearchGroup/social_agent_simulation_platform/pull/192](https://github.com/METResearchGroup/social_agent_simulation_platform/pull/192): [2026-03-08] Codex repo automation - Weekly work update. Adds the weekly update artifact for `2026-03-02` through `2026-03-08`.

### Bug Fixes

- High-level summary: No standalone bug-fix-only PRs were identified outside the feature and quality categories above. Fix-oriented changes are captured in those sections.
- PRs:
 - _None this week._
