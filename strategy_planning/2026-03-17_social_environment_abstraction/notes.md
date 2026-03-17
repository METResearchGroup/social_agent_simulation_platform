# SocialEnvironment architecture notes

## Framing

The architectural goal here is not "put more things on the agent." The goal is:

- make agent decision inputs explicit
- make those inputs composable
- keep the decision boundary readable
- avoid hiding runtime dependencies behind mutable agent state

The cleanest shape is to keep `SimulationAgent` as the durable in-memory actor for the run, and introduce a separate turn-scoped read model that describes what social world the agent can perceive at decision time.

That suggests two possible abstractions:

1. `SocialEnvironment`
2. optionally later, `AgentTurnContext`

The recommendation is to introduce `SocialEnvironment` first, and only introduce `AgentTurnContext` if non-social turn inputs start spreading across multiple APIs.

## Current architecture observation

Today, the code already behaves like "inject decision inputs per turn", but it does so implicitly instead of through an explicit object.

The current turn flow is roughly:

1. load/generate feed per agent
2. filter feed into action-specific candidates
3. generate likes/comments/follows
4. validate against prior action history
5. persist turn outputs

In `SimulationCommandService`, the core flow is:

```275:311:simulation/core/command_service.py
        agent_to_hydrated_feeds: dict[str, list[Post]] = (
            self.feed_generator.generate_feeds(
                agents=agents,
                run_id=run_id,
                turn_number=turn_number,
                feed_algorithm=feed_algorithm,
                feed_algorithm_config=feed_algorithm_config,
            )
        )

        validate_agents_without_feeds(
            agent_handles=set(agent.handle for agent in agents),
            agents_with_feeds=set(agent_to_hydrated_feeds.keys()),
        )

        # ...

        for agent in agents:
            feed = agent_to_hydrated_feeds.get(agent.handle, [])

            if not feed:
                continue

            action_candidates = self.agent_action_feed_filter.filter_candidates(
                run_id=run_id,
                agent_handle=agent.handle,
                feed=feed,
                action_history_store=action_history_store,
            )
```

So the system already has turn-time decision inputs, but they are distributed across:

- `FeedGenerator`
- `GeneratedFeedRepository`
- `ActionHistoryStore`
- `AgentActionFeedFilter`
- seed-state metadata on `SimulationAgent`

That makes the system workable, but the domain boundary is blurry. There is no single object that answers:

"What social world is visible to this agent on this turn?"

## Recommended boundary

Use three layers:

1. `SimulationAgent` = the actor
2. `SocialEnvironment` = the observable social world for this turn
3. `AgentTurnContext` = optional full turn-time execution envelope

### `SimulationAgent`

This should remain the durable in-memory actor for the run. It is a good home for:

- identity: `agent_id`, `handle`, `display_name`
- persona/profile data: bio, generated bio
- durable run-local actor data

Today `SimulationAgent` is already roughly shaped that way, even though it still carries some social summary fields:

```20:32:simulation/core/models/agents.py
        self.handle: str = handle
        # Immutable seed identity fields (when hydrated from seed catalog).
        self.agent_id: str | None = agent_id
        self.display_name: str | None = display_name
        self.bio: str = ""
        self.generated_bio: str = ""
        self.followers: int = 0
        self.following: int = 0
        self.posts_count: int = 0
        self.posts: list[Post] = []
        self.likes: list[GeneratedLike] = []
        self.comments: list[GeneratedComment] = []
        self.follows: list[GeneratedFollow] = []
```

Important recommendation:

- do not attach a mutable `social_environment` field to `SimulationAgent`
- do not make the agent itself responsible for loading or caching turn inputs

The agent should not become a grab bag of "current turn stuff."

### `SocialEnvironment`

This should be:

- per-agent
- per-turn
- read-only
- social/content-oriented
- free of repositories and lazy loading

This object should answer:

- what content can the agent see?
- which authors are socially visible?
- what prior social exposure matters?
- what relationship constraints matter right now?

The best first version is intentionally small.

### Suggested v1 fields

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class SocialEnvironment:
    run_id: str
    turn_number: int
    agent_handle: str
    feed_posts: tuple[Post, ...]
    seen_post_ids: frozenset[str]
    already_followed_handles: frozenset[str]
```

Why these fields:

- `feed_posts`
  - the core social surface the agent sees
- `seen_post_ids`
  - already part of feed/candidate logic today and clearly part of the agent's social exposure state
- `already_followed_handles`
  - today implicit in action history / follow validation, but should be explicit if follow decisions are to be composable

This is enough to support:

- like decisions
- comment decisions
- follow decisions
- deterministic tests of turn-time decision logic

### Suggested v2 fields if needed

Only add these when a real policy needs them:

- `visible_author_handles: tuple[str, ...]`
- `incoming_follow_handles: frozenset[str]`
- `mutual_follow_handles: frozenset[str]`
- `author_features_by_handle: dict[str, VisibleAuthor]`

Possible helper model:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class VisibleAuthor:
    handle: str
    display_name: str | None = None
    follower_count: int | None = None
    following_count: int | None = None
    post_count: int | None = None
```

Only add author-level feature summaries if multiple policies would benefit from them. Otherwise the abstraction risks becoming a speculative feature bag.

### What should not go in `SocialEnvironment`

Do not put these inside it:

- repositories
- service objects
- lazy loaders
- persistence helpers
- methods that fetch additional state
- generated actions
- metric outputs
- LLM clients or model handles
- business logic that mutates simulation state

Good:

- `feed_posts`
- `already_followed_handles`
- `seen_post_ids`

Bad:

- `follow_repo`
- `load_feed()`
- `write_follow()`
- `rank_posts()`

The object should be a read model, not a service boundary.

## Optional `AgentTurnContext`

This abstraction is only useful if non-social decision inputs start spreading.

Use `AgentTurnContext` when the code begins needing a shared envelope for:

- `run_id`
- `turn_number`
- per-turn decision budgets
- algorithm/config inputs
- deterministic RNG or random seed
- tracing or execution metadata

That shape could be:

```python
from dataclasses import dataclass
from collections.abc import Mapping
from pydantic import JsonValue

@dataclass(frozen=True)
class AgentTurnContext:
    run_id: str
    turn_number: int
    social_environment: SocialEnvironment
    decision_config: Mapping[str, JsonValue] | None = None
    random_seed: int | None = None
```

For now, the recommendation is:

- start with `SocialEnvironment`
- skip `AgentTurnContext` unless multiple non-social turn parameters are causing noisy signatures

In other words, `AgentTurnContext` is useful, but it is not the first abstraction to add.

## Why `SocialEnvironment` is the right first move

The current system is feed-centric and history-aware, but not yet explicit about "social world."

Examples:

- feed candidate generation uses "already seen post ids"
- follow eligibility depends on whether an agent already followed a handle in the run
- follow generators infer candidate users from feed post authors

Those behaviors exist today, but they are split across multiple modules:

```15:27:simulation/core/action_history/interfaces.py
class ActionHistoryStore(ABC):
    """Run-scoped storage for previously accepted agent actions."""

    @abstractmethod
    def has_liked(self, run_id: str, agent_handle: str, post_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def has_commented(self, run_id: str, agent_handle: str, post_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def has_followed(self, run_id: str, agent_handle: str, user_id: str) -> bool:
        raise NotImplementedError
```

```15:27:feeds/candidate_generation.py
def load_seen_post_ids(
    *,
    agent: SimulationAgent,
    run_id: str,
    generated_feed_repo: GeneratedFeedRepository,
) -> set[str]:
    """Load the posts that the agent has already seen in the given run.

    Returns a set of post_ids.
    """
    return generated_feed_repo.get_post_ids_for_run(
        agent_handle=agent.handle, run_id=run_id
    )
```

Making those inputs explicit as a `SocialEnvironment` would improve:

- readability
- testability
- composability of policies
- future graph-aware decision logic

## Important non-goal

This abstraction should not pretend there is already a rich social graph if the codebase does not have one yet.

Right now the system has:

- follower/following counts from metadata
- run-local follow memory via `ActionHistoryStore`
- persisted follow events by run/turn

But it does not yet have a first-class adjacency model for the seed-state social graph.

That means `SocialEnvironment` should initially model only the social inputs that truly exist in the system, rather than overcommitting to concepts like:

- "friend graph"
- "neighborhood"
- "community cluster"
- "mutual trust network"

Those may become real later, but v1 should reflect the current simulation architecture honestly.

## Recommended provider boundary

The cleanest architecture is:

- `SimulationCommandService` orchestrates the turn
- `SocialEnvironmentProvider` builds explicit read models
- decision logic consumes `agent + social_environment`
- persistence stays outside both

Suggested interface:

```python
from abc import ABC, abstractmethod
from collections.abc import Mapping
from pydantic import JsonValue

class SocialEnvironmentProvider(ABC):
    @abstractmethod
    def build_for_agents(
        self,
        *,
        agents: list[SimulationAgent],
        run_id: str,
        turn_number: int,
        feed_algorithm: str,
        feed_algorithm_config: Mapping[str, JsonValue] | None = None,
    ) -> dict[str, SocialEnvironment]:
        ...
```

The provider should:

- batch-build environments for all agents in a turn
- avoid N+1 repository access patterns
- centralize turn-time social read assembly

This is preferable to storing turn state on the agent itself.

## How this changes the decision boundary

Today, decision-time inputs are passed around as multiple separate parameters, or hidden behind collaborators.

The target architecture should move toward APIs like:

```python
decisions = decision_policy.decide(agent=agent, env=env)
```

instead of:

```python
decisions = decision_policy.decide(
    agent=agent,
    run_id=run_id,
    turn_number=turn_number,
    feed=feed,
    action_history_store=action_history_store,
    config=config,
)
```

That is the composability win:

- smaller public interfaces
- easier testing
- clearer conceptual ownership of inputs

## Concrete rollout recommendation

### Phase 1: introduce `SocialEnvironment` as a passive model

Add a small immutable model with:

- `run_id`
- `turn_number`
- `agent_handle`
- `feed_posts`
- `seen_post_ids`
- `already_followed_handles`

Use it first in follow/like/comment candidate logic.

### Phase 2: add a `SocialEnvironmentProvider`

Create a provider that assembles these inputs in one place, in batch, per turn.

This should likely absorb or coordinate logic that is currently spread across:

- feed generation
- seen-post lookups
- follow-history lookups

### Phase 3: update policy / generator interfaces

Move APIs toward:

- `agent + env`
- optionally later `agent + turn_context`

This is the point where decision code becomes clearly composable.

### Phase 4: consider `AgentTurnContext` only if needed

If multiple non-social inputs become common, add `AgentTurnContext` as a wrapper around:

- social environment
- decision config
- random seed
- per-turn execution metadata

Do not add this wrapper before it solves a real interface problem.

## Naming guidance

`SocialEnvironment` is a good name if the abstraction remains focused on:

- observable feed content
- visible authors
- relationship state
- social exposure

If the object starts accumulating non-social execution data, a better top-level name may be:

- `AgentTurnContext`
- `DecisionContext`

Rule of thumb:

- if the field describes the social world, it belongs in `SocialEnvironment`
- if the field describes execution mechanics, it belongs in `AgentTurnContext`

## Proposed `docs/architecture` page

This topic is important enough that it should likely live in `docs/architecture/` once the abstraction is accepted. The purpose of that doc should be to make the boundary explicit for future refactors, reviews, and lint rules.

Suggested file name:

- `docs/architecture/agent-vs-social-environment.md`

Suggested sections:

- Purpose
- Definitions
- Boundary rules
- Allowed dependencies
- Examples
- Anti-patterns
- How to extend the model
- Lint enforcement

### Purpose

The document should explain that the repo intentionally separates:

- the actor (`SimulationAgent`)
- the actor's observable social world (`SocialEnvironment`)
- optional execution envelope (`AgentTurnContext`)

That distinction matters because the codebase wants explicit parameters and clear dependency boundaries, per `docs/RULES.md`.

### Definitions

The doc should define the abstractions in plain terms.

Suggested wording:

- `SimulationAgent`: the durable in-memory actor for a run. It represents identity, persona, and durable actor state.
- `SocialEnvironment`: the immutable per-turn social read model visible to one agent.
- `AgentTurnContext`: an optional wrapper for non-social execution metadata needed by decision logic.

### Boundary rules

This is the highest-value section. It should spell out exactly what belongs where.

Suggested rules:

- `SimulationAgent` answers: "who is the actor?"
- `SocialEnvironment` answers: "what social world can the actor observe right now?"
- `AgentTurnContext` answers: "what turn-time execution frame is this decision occurring within?"

More concretely:

`SimulationAgent` owns:

- identity fields
- persona/bio/profile data
- durable actor state that persists across turns within a run

`SocialEnvironment` owns:

- feed posts visible this turn
- visible authors or candidate social targets
- relationship/exposure facts relevant to this turn
- previously seen content or previously followed handles when used as decision inputs

`AgentTurnContext` owns:

- run/turn identifiers if a wrapper is needed
- decision budgets
- config for the decision step
- deterministic RNG / seed
- tracing or execution metadata

It should also explicitly ban the most likely blurring patterns:

- do not put turn-scoped environment on `SimulationAgent`
- do not let `SocialEnvironment` load data from repositories
- do not use `AgentTurnContext` as a generic bag for unrelated values

### Allowed dependencies

This section should connect to existing repo rules.

The architecture contract should say:

- domain models in `simulation/core/models/` remain pure per `docs/RULES.md`
- `SocialEnvironment` may contain domain objects like `Post`, strings, ids, and frozen collections
- the object must not depend on `db`, `feeds`, `ai`, or service objects
- construction of `SocialEnvironment` belongs in an application/service/provider boundary, not the model itself

This matters because the repo already has a strong "dependency injection over concrete instantiation" rule and a "domain purity" rule.

### Examples

The doc should include short examples of correct and incorrect modeling.

Good examples:

- `SimulationAgent(handle, bio, ...)`
- `SocialEnvironment(feed_posts, seen_post_ids, already_followed_handles)`
- `AgentTurnContext(social_environment=env, decision_config=config)`

Bad examples:

- `agent.social_environment = ...`
- `SocialEnvironment(follow_repo=follow_repo, feed_repo=feed_repo)`
- `AgentTurnContext(metrics_repo=..., llm_client=..., env=...)`

### Anti-patterns

This section should name the failure modes explicitly so code review becomes easier.

Key anti-patterns:

- mutable turn state attached directly to the agent
- repository-backed or lazy-loading environment objects
- context objects that become untyped "misc input" bags
- policy code that reaches back into repositories instead of consuming explicit inputs

### How to extend the model

This section should answer the future-maintainer question:

"I need one more field. Where should it go?"

Suggested rule:

- if it describes the agent's social perception for this turn, add it to `SocialEnvironment`
- if it describes execution mechanics, add it to `AgentTurnContext`
- if it is durable actor identity/persona/state, keep it on `SimulationAgent`
- if it requires I/O to compute, compute it in the provider layer and pass the result in

That one rubric would prevent a lot of drift.

### Lint enforcement section in the architecture doc

The doc should explicitly say that this boundary is not just a convention; it should be guarded by the existing architecture lint stack:

- Semgrep rules in `lint/semgrep/`
- AST rules in `scripts/lint_architecture.py`

That makes the architecture page operational rather than aspirational.

## Lint enforcement strategy

The repo already has the right enforcement shape:

- `lint/semgrep/python-di.yml`
- `scripts/lint_architecture.py`
- `docs/runbooks/PYTHON_DI_GUARD.md`

That is good news, because the `SimulationAgent` / `SocialEnvironment` boundary can be enforced by extending the existing DI/layering lint rules instead of introducing a separate linter framework.

The key principle should be:

- use Semgrep for simple syntactic bans
- use `scripts/lint_architecture.py` for AST-aware structural rules

### Existing enforcement base to build on

The existing DI guard already enforces important architecture constraints:

- concrete infra only in composition roots
- no optional infra dependencies outside factories
- no service-to-service injection in core
- no concrete infra type hints in business logic

That means the repo already accepts the pattern:

- architecture rule in `docs/RULES.md`
- mechanical enforcement in Semgrep and `lint_architecture.py`
- wired into pre-commit and CI

`SocialEnvironment` should follow that same pattern.

### Recommended lint rules for this boundary

The highest-value rules are simple and local.

#### Rule 1: no mutable environment field on `SimulationAgent`

Goal:

- prevent `SimulationAgent` from becoming a turn-state bag

What to enforce:

- in `simulation/core/models/agents.py`, disallow adding fields like:
  - `social_environment`
  - `turn_context`
  - `current_feed`
  - `current_environment`

Preferred implementation:

- AST rule in `scripts/lint_architecture.py`

Why AST:

- the rule is specific to one class and benefits from class/attribute awareness

Possible shape:

- inspect assignments inside `SimulationAgent.__init__`
- flag assignment to banned turn-scoped attribute names

Example violation message:

- `PY-ENV-1: SimulationAgent must not store turn-scoped environment fields; pass SocialEnvironment explicitly.`

#### Rule 2: no repositories or services inside `SocialEnvironment`

Goal:

- keep `SocialEnvironment` a passive read model

What to enforce:

- if a `SocialEnvironment` class exists, its fields/annotations must not reference:
  - `*Repository`
  - `*Service`
  - `*Adapter`
  - `*Provider`
  - concrete infra types

Preferred implementation:

- AST rule in `scripts/lint_architecture.py`

Why AST:

- the linter already resolves annotations and checks dependency-shaped types
- this rule is very similar in spirit to the existing `PY-8` and `PY-9` checks

Example violation message:

- `PY-ENV-2: SocialEnvironment must be a passive read model; dependency/service fields are not allowed.`

#### Rule 3: no repository imports in the `SocialEnvironment` model module

Goal:

- preserve domain purity and prevent leakage from construction layer into the model

What to enforce:

- if `simulation/core/models/social_environment.py` exists, ban imports from:
  - `db.`
  - `feeds.`
  - `simulation.api.`
  - `ml_tooling.`

Preferred implementation:

- AST rule in `scripts/lint_architecture.py`

Alternative:

- this could also be done with Semgrep, but AST is probably cleaner because the repo already has a "domain purity" concept in rules and architecture lint.

Example violation message:

- `PY-ENV-3: simulation/core/models/social_environment.py must remain a pure domain model module.`

#### Rule 4: no `.social_environment` mutation outside provider/composition code

Goal:

- prevent code from drifting into `agent.social_environment = env`

What to enforce:

- ban attribute assignment matching `.social_environment =`
- optionally also ban `.turn_context =`

Preferred implementation:

- Semgrep rule in `lint/semgrep/python-di.yml`

Why Semgrep:

- this is a straightforward syntactic pattern
- Semgrep is a good fit for assignment-shape bans

Scope:

- exclude tests if needed initially
- probably allow no production exceptions at all

Example violation message:

- `PY-ENV-4: Do not attach SocialEnvironment to SimulationAgent; pass it as an explicit input.`

#### Rule 5: no decision-policy repository injection if `SocialEnvironment` is meant to supply those facts

Goal:

- once the new architecture is adopted, prevent policy code from bypassing the explicit decision boundary

What to enforce:

- policy/generator classes under decision-oriented packages should not take repository dependencies that belong in environment construction

Candidates:

- `simulation/core/action_policy/**`
- `simulation/core/action_generators/**`

Preferred implementation:

- AST rule in `scripts/lint_architecture.py`

This should be phased in carefully, because it depends on the rollout. It is probably not a v1 lint rule, but it is a good target once `SocialEnvironmentProvider` exists.

Example violation message:

- `PY-ENV-5: Decision policies must consume explicit turn inputs, not repositories that belong in environment assembly.`

### Which rules should happen first

To avoid overengineering, the recommended order is:

1. add architecture docs first
2. add the narrowest lint rules
3. add stronger policy-layer enforcement only after the provider boundary exists

Concrete v1 lint set:

- `PY-ENV-1`: no mutable environment fields on `SimulationAgent`
- `PY-ENV-2`: no dependency/service fields in `SocialEnvironment`
- `PY-ENV-4`: no `agent.social_environment = ...` assignment

These three rules would enforce most of the intended shape with low complexity.

### Best implementation path using existing linters

Recommended split:

- add one or two simple Semgrep rules to `lint/semgrep/python-di.yml`
- extend `scripts/lint_architecture.py` with `PY-ENV-*` checks
- document them in `docs/runbooks/PYTHON_DI_GUARD.md`

That approach is consistent with the current repo pattern and avoids introducing:

- a brand-new linter
- a one-off script with overlapping scope
- an architecture rule that only exists in prose

### Why not rely on Ruff or Pyright alone

Ruff and Pyright are important, but they are not enough for this boundary.

- Ruff is best for syntax/style/code-quality patterns and some static correctness
- Pyright is best for typing
- neither is a great fit for repo-specific architecture constraints like:
  - "this one domain model must not store turn-scoped environment"
  - "this model class must not reference repositories"
  - "this assignment shape is architecturally banned"

So the recommended strategy is:

- keep Ruff and Pyright as general quality gates
- use the existing Semgrep + AST architecture linter for the boundary contract

That is still "building upon the existing linters," not inventing a new system.

## Final recommendation

Use this architecture:

1. keep `SimulationAgent` small and durable
2. introduce an immutable per-turn `SocialEnvironment`
3. build it via a provider, in batch, outside the agent
4. pass `agent + env` explicitly into decision logic
5. add `AgentTurnContext` only after non-social inputs justify it

This gives the main benefit sought here:

- agent decision inputs become explicit
- those inputs become composable
- the architecture becomes easier to reason about

without overengineering a general-purpose context framework too early.
