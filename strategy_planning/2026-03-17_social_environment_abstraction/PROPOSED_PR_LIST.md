---
description: Proposed PR-by-PR rollout for migrating simulation turn inputs to the SocialEnvironment architecture.
tags: [strategy, planning, architecture, simulation, social-environment]
---

## Remember

- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

## Overview

This migration should make the agent decision boundary explicit without turning `SimulationAgent` into a mutable bag of turn-scoped state. The target architecture is: `SimulationAgent` remains the durable actor, `SocialEnvironment` becomes the immutable per-agent/per-turn social read model, `SimulationCommandService` builds those environments in batch via a provider, and decision-oriented code consumes `agent + env` instead of reaching across multiple collaborators for feed/history inputs. The recommended stop point is to fully adopt `SocialEnvironment` and defer `AgentTurnContext` unless non-social execution inputs actually create noisy signatures afterward.

## Happy Flow

1. `SimulationCommandService._simulate_turn(...)` in `simulation/core/command_service.py` asks an injected `SocialEnvironmentProvider` to build environments for all participating agents for a single turn.
2. The provider assembles each `SocialEnvironment` from current turn-visible social facts:
   - feed posts from `feeds.interfaces.FeedGenerator`
   - prior seen post ids from `db.repositories.interfaces.GeneratedFeedRepository`
   - prior follow-memory from `simulation/core/action_history/interfaces.py`
3. Decision-oriented code consumes `SimulationAgent` plus `SocialEnvironment` instead of directly reloading those inputs from repositories or hiding them behind mutable agent fields.
4. `AgentActionRulesValidator` remains the place that enforces action invariants and rejects duplicates; persistence continues to live outside both the agent and the environment.
5. Architecture docs and lint rules prevent the main failure modes:
   - attaching `social_environment` or other turn-scoped fields to `SimulationAgent`
   - putting repositories/services inside `SocialEnvironment`
   - mutating `agent.social_environment = ...` in orchestration code

## Scope and non-goals

- In scope:
  - make per-turn social inputs explicit
  - centralize social read-model assembly
  - move decision APIs toward `agent + env`
  - add lint/docs guardrails so the boundary does not drift
- Out of scope:
  - inventing a richer social graph than the repo actually has today
  - moving persistence into `SocialEnvironment`
  - adding `AgentTurnContext` before multiple non-social inputs justify it
  - storing mutable environment state on `SimulationAgent`

## Proposed PR list

### PR 1: Architecture contract and anti-drift guardrails

#### PR 1 Goal

Lock the boundary in docs and linting before production code starts moving, so later PRs have a stable contract to build against.

#### PR 1 Primary Files

- New: `docs/architecture/agent-vs-social-environment.md`
- Update: `docs/RULES.md`
- Update: `docs/runbooks/PYTHON_DI_GUARD.md`
- Update: `scripts/lint_architecture.py`
- Update: `lint/semgrep/python-di.yml`
- Add/update tests under `tests/lint/`

#### PR 1 Changes

- Add a short architecture doc defining:
  - `SimulationAgent` = durable actor
  - `SocialEnvironment` = immutable per-turn social read model
  - `AgentTurnContext` = optional execution wrapper, deferred by default
- Add the first three guardrails recommended in `notes.md`:
  - `PY-ENV-1`: ban turn-scoped environment fields on `SimulationAgent`
  - `PY-ENV-2`: ban dependency/service-shaped fields inside `SocialEnvironment`
  - `PY-ENV-4`: ban `.social_environment = ...` assignment in production code
- Cross-link the new doc from `docs/RULES.md` and the DI guard runbook.

#### PR 1 Why This Should Be First

This is the lowest-risk PR, and it prevents the migration from accidentally converging on the wrong shape while several production files are changing in parallel.

#### PR 1 Merge Criteria

- `uv tool run semgrep --config lint/semgrep --error` reports `0 findings`
- `uv run --extra test python scripts/lint_architecture.py` reports `OK (...)`
- New lint fixtures/regression tests pass

### PR 2: Introduce the passive `SocialEnvironment` model and provider port

#### PR 2 Goal

Add the new model and provider abstraction with no orchestration rewiring yet.

#### PR 2 Primary Files

- New: `simulation/core/models/social_environment.py`
- New: `simulation/core/social_environment/__init__.py`
- New: `simulation/core/social_environment/interfaces.py`
- New: `tests/simulation/core/test_social_environment_model.py`
- New: `tests/simulation/core/test_social_environment_provider.py`

#### PR 2 Recommended Model Shape

```python
from dataclasses import dataclass

from simulation.core.models.posts import Post

@dataclass(frozen=True)
class SocialEnvironment:
    run_id: str
    turn_number: int
    agent_handle: str
    feed_posts: tuple[Post, ...]
    seen_post_ids: frozenset[str]
    already_followed_handles: frozenset[str]
```

#### PR 2 Changes

- Keep the model pure per `docs/RULES.md`: no imports from `db`, `feeds`, `simulation.api`, or service code.
- Add `SocialEnvironmentProvider` in `simulation/core/social_environment/interfaces.py`.
- Use a batch-oriented method signature that matches the real orchestration needs. Recommended shape:

```python
class SocialEnvironmentProvider(ABC):
    @abstractmethod
    def build_for_agents(
        self,
        *,
        agents: list[SimulationAgent],
        run_id: str,
        turn_number: int,
        feed_algorithm: str,
        action_history_store: ActionHistoryStore,
        feed_algorithm_config: Mapping[str, JsonValue] | None = None,
    ) -> dict[str, SocialEnvironment]:
        ...
```

- Keep `action_history_store` explicit on the provider call because `already_followed_handles` is run-scoped, in-memory state today, not durable repo state.

#### PR 2 Why This PR Stays Separate

It establishes the types and contracts without simultaneously changing orchestration, feed generation, and action policy code.

#### PR 2 Merge Criteria

- `uv run pytest tests/simulation/core/test_social_environment_model.py -q`
- `uv run pytest tests/simulation/core/test_social_environment_provider.py -q`
- `uv run pyright .`

### PR 3: Add the default provider and wire it into turn orchestration

#### PR 3 Goal

Make `SimulationCommandService` build explicit environments once per turn, in batch, before decision code runs.

#### PR 3 Primary Files

- New: `simulation/core/social_environment/provider.py`
- Update: `simulation/core/command_service.py`
- Update: `simulation/core/factories/command_service.py`
- Update: `simulation/core/factories/__init__.py`
- Update: `tests/simulation/core/test_command_service.py`
- Update: `tests/simulation/core/test_dependencies.py`

#### PR 3 Changes

- Implement a default provider that coordinates:
  - `FeedGenerator.generate_feeds(...)`
  - `GeneratedFeedRepository.get_post_ids_for_run(...)`
  - `ActionHistoryStore.has_followed(...)`
- Inject the provider into `SimulationCommandService` from `simulation/core/factories/command_service.py`.
- Change `SimulationCommandService._simulate_turn(...)` to build:
  - `agent_to_social_environments: dict[str, SocialEnvironment]`
  - then read `env.feed_posts` instead of storing turn inputs in local ad hoc variables
- Keep downstream action-policy code unchanged in this PR except for plumbing what is strictly necessary.
- Add validation for agents missing environments, analogous to the current missing-feed validation.

#### PR 3 Recommended Implementation Detail

Do not add `self.social_environment = ...` or `agent.social_environment = ...` anywhere. The provider output should stay local to the turn execution path and be passed explicitly.

#### PR 3 Why This PR Is Isolated

This is the main orchestration seam change. Keeping it separate makes regressions easier to localize.

#### PR 3 Merge Criteria

- `uv run pytest tests/simulation/core/test_command_service.py -q`
- `uv run pytest tests/simulation/core/test_dependencies.py -q`
- `uv run pytest tests/feeds/test_feed_generator.py -q`

### PR 4: Move action-policy code to env-first inputs

#### PR 4 Goal

Refactor decision-adjacent APIs so they consume `SocialEnvironment` explicitly instead of raw feed lists plus hidden social facts.

#### PR 4 Primary Files

- Update: `simulation/core/action_policy/interfaces.py`
- Update: `simulation/core/action_policy/candidate_filter.py`
- Update: `simulation/core/command_service.py`
- Update: `tests/simulation/core/test_agent_action_feed_filter.py`
- Update: `tests/simulation/core/test_command_service.py`

#### PR 4 Changes

- Update the candidate-filter API from:
  - `filter_candidates(run_id, agent_handle, feed, action_history_store)`
- Toward:
  - `filter_candidates(agent=agent, env=env, action_history_store=action_history_store)`
- Use:
  - `env.feed_posts` as the visible content surface
  - `env.already_followed_handles` for follow candidate exclusion
- Keep `action_history_store` in the signature for now for like/comment history checks unless a concrete need emerges to add liked/commented history to `SocialEnvironment`.
- Rename local variables in `SimulationCommandService` and tests so the main turn-time concept is `env`, not `feed`.

#### PR 4 Important Design Rule

Do not expand `SocialEnvironment` with speculative fields in this PR. Only add more history-derived fields if preserving current like/comment candidate behavior requires them and the need is demonstrated by failing tests.

#### PR 4 Why This PR Matters

This is the point where decision code actually starts "using `SocialEnvironment`" instead of merely having it available in orchestration.

#### PR 4 Merge Criteria

- `uv run pytest tests/simulation/core/test_agent_action_feed_filter.py -q`
- `uv run pytest tests/simulation/core/test_command_service.py -q`
- `uv run pyright .`

### PR 5: Consolidate turn-input assembly and remove legacy duplication

#### PR 5 Goal

Reduce duplicated turn-input assembly logic that remains split across `feeds/`, command orchestration, and history lookups after the initial env adoption.

#### PR 5 Primary Files

- Update: `feeds/candidate_generation.py`
- Update: `feeds/feed_generator.py`
- Update: `feeds/feed_generator_adapter.py`
- Update: `feeds/interfaces.py`
- Update: `simulation/core/social_environment/provider.py`
- Update: `simulation/core/action_history/interfaces.py`
- Update: `simulation/core/action_history/stores.py`
- Update: `tests/feeds/test_feed_generator.py`
- Update/add: `tests/simulation/core/test_social_environment_provider.py`

#### PR 5 Changes

- Decide which assembly layer is authoritative for these turn-time facts:
  - visible posts
  - seen post ids
  - already-followed handles
- Recommended end-state:
  - `FeedGenerator` remains responsible only for feed selection/ranking
  - `SocialEnvironmentProvider` is responsible for assembling the full read model used by decision code
- If needed for performance or clarity, add read-side history helpers to `ActionHistoryStore`, for example:
  - `list_followed_user_ids(run_id: str, agent_handle: str) -> frozenset[str]`
- If provider call counts become noisy, add bulk feed/history read methods rather than hiding per-agent I/O inside loops.

#### PR 5 Why This Needs Its Own PR

The first env wiring can tolerate some duplication. This PR is where we cleanly centralize ownership and avoid locking in accidental N+1 patterns.

#### PR 5 Merge Criteria

- `uv run pytest tests/feeds/test_feed_generator.py -q`
- `uv run pytest tests/simulation/core/test_social_environment_provider.py -q`
- `uv run pytest tests/simulation/core/test_command_service.py -q`

### PR 6: Rename misleading APIs and codify the end-state boundary

#### PR 6 Goal

Remove naming that still reflects the old feed-centric boundary and make the final architecture obvious to future readers.

#### PR 6 Primary Files

- Update: `simulation/core/action_policy/interfaces.py`
- Update: `simulation/core/action_policy/candidate_filter.py`
- Update: `simulation/core/command_service.py`
- Update: `simulation/core/factories/command_service.py`
- Update: `tests/simulation/core/`
- Update: `docs/architecture/agent-vs-social-environment.md`

#### PR 6 Changes

- Rename symbols that are now conceptually wrong after the migration. Most likely:
  - `AgentActionFeedFilter` -> `AgentActionEnvironmentFilter` or `ActionCandidateResolver`
  - `HistoryAwareActionFeedFilter` -> matching env-oriented name
- Rename orchestration locals:
  - `agent_to_hydrated_feeds` -> `agent_to_social_environments`
  - `feed` -> `env.feed_posts` or `social_environment.feed_posts`
- Remove any remaining direct decision-time repository access from modules that should now consume the assembled environment.
- Refresh docs and tests to use the new vocabulary consistently.

#### PR 6 Why This Is A Later PR

Doing renames after behavioral migration keeps earlier diffs smaller and makes the final cleanup easy to review.

#### PR 6 Merge Criteria

- `uv run pytest tests/simulation/core -q`
- `uv run ruff check .`
- `uv run pyright .`

### PR 7: Optional `AgentTurnContext` only if signatures are still noisy

#### PR 7 Goal

Introduce a higher-level execution wrapper only if concrete non-social inputs still sprawl across multiple APIs after PR 6.

#### PR 7 Primary Files

- New, only if justified: `simulation/core/models/agent_turn_context.py`
- Potential updates: `simulation/core/command_service.py`, `simulation/core/action_policy/`, `simulation/core/agent_actions.py`, related tests

#### PR 7 When To Do This

Only take this PR if, after PR 6, the code still repeatedly passes several non-social execution fields together, for example:

- `run_id`
- `turn_number`
- algorithm/config inputs
- deterministic RNG/seed
- tracing metadata

#### PR 7 When To Skip This

Skip it if `agent + env` already makes the public interfaces clear enough. The architecture notes explicitly recommend not introducing `AgentTurnContext` before it solves a real problem.

#### PR 7 Merge Criteria

- A concrete before/after signature diff in the PR description showing reduced public API noise
- No new "misc context bag" smell in the model or provider layer

## Recommended stopping point

Treat PR 6 as the default completion point for this migration. At that stage the codebase is genuinely using `SocialEnvironment` as the explicit social read model, while keeping `SimulationAgent` durable and small. PR 7 should be opt-in, not assumed.

## Cross-PR manual verification

- [ ] Run architecture lints after every PR:
  - `uv tool run semgrep --config lint/semgrep --error`
  - expected: `0 findings`
  - `uv run --extra test python scripts/lint_architecture.py`
  - expected: `OK (...)`
- [ ] Run targeted simulation-core tests after each PR touching core orchestration:
  - `uv run pytest tests/simulation/core -q`
  - expected: all pass
- [ ] Run feed tests after PRs 3-5:
  - `uv run pytest tests/feeds/test_feed_generator.py -q`
  - expected: all pass
- [ ] Run typechecking on the full migration path:
  - `uv run pyright .`
  - expected: `0 errors`
- [ ] Run Ruff checks on the full migration path:
  - `uv run ruff check .`
  - expected: exit code `0`
- [ ] Run a smoke simulation at least once after PR 3 and once after PR 6:
  - `PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload`
  - `POST http://localhost:8000/v1/simulations/run` with a small payload such as `{ "num_agents": 3, "num_turns": 1 }`
  - expected: run completes successfully and produced actions remain behaviorally consistent with pre-migration expectations

## Alternative approaches

- Big-bang rewrite in one PR:
  - Rejected because the migration touches orchestration, feed assembly, policy interfaces, tests, docs, and linting at once. Review risk is too high.
- Put `social_environment` directly on `SimulationAgent`:
  - Rejected because it hides turn-scoped dependencies behind mutable actor state and blurs the actor/read-model boundary.
- Introduce `AgentTurnContext` before `SocialEnvironment`:
  - Rejected because the current pain is specifically the missing social read model, not a generalized execution wrapper.
- Keep the old feed-centric names forever:
  - Rejected because it leaves the architecture conceptually wrong even if the code "works."

## Notes for whoever executes this plan

- The migration should preserve the current truth that the repo does not yet have a first-class adjacency graph. `SocialEnvironment` should describe only social facts the system can already compute honestly.
- `ActionHistoryStore` can continue to exist after the migration. The main change is that decision code should consume assembled turn inputs explicitly instead of directly depending on hidden assembly scattered across modules.
- No UI work is required for this migration, so no screenshot workflow is needed for this plan.
