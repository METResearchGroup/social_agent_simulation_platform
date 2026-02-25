# Suggested custom linters (Python + TypeScript)

Goal: maximally enforce dependency injection (DI), clean architecture boundaries, and repo conventions, in a way that is **mechanically checkable** and can be wired into CI/pre-commit.

## Notes from scanning this repo

- Python currently uses `ruff` (limited to `E/F/I`), `pyright` (basic), and `complexipy` via pre-commit (`.pre-commit-config.yaml`).
- UI has `eslint.config.mjs` and `npm run lint`, but pre-commit currently runs `oxlint` + `react-doctor` for `ui/`.
- Two referenced docs are not present in this worktree:
  - `ai_tools/agents/task_instructions/rules/CLEAN_CODE_PRINCIPLES.md`
  - `ai_tools/agents/task_instructions/rules/CODING_REPO_CONVENTIONS.md`
  This document is therefore anchored primarily in `docs/RULES.md` plus observed code patterns.

Concrete boundary/DI issues observed (useful as initial targets / “known failing examples”):

- **Domain models import non-model core code**:
  - `simulation/core/models/agents.py` imports `simulation.core.action_generators` (inside methods).
- **Concrete infra is constructed in API services (not just factories)**, weakening DI boundaries:
  - `simulation/api/services/agent_query_service.py` constructs `SqliteTransactionProvider()` and `create_sqlite_*` repos
  - `simulation/api/services/agent_command_service.py` similarly constructs SQLite dependencies

These are good candidates for linting because they are:

1) architecture-relevant, 2) detectable by static analysis, and 3) costly to catch only in review.

## Updated architecture expectations (per your guidance)

- `lib/` is a repo-wide utilities package:
  - Anything may import from `lib`.
  - `lib` must not import from other first-party packages (i.e., `lib` is a leaf for intra-repo imports).
- `ml_tooling/` is an allowed dependency for most code:
  - Anything **except `lib`** may import from `ml_tooling`.
  - `ml_tooling` may import from `lib` (and stdlib/third-party), but may not import from other first-party packages.

---

## Python: 5 linter ideas (including custom linters)

### PY-1: Import contracts / layered architecture (import-linter)

#### Enforces (PY-1)

- “Domain purity”: `simulation.core.models` may import only:
  - stdlib
  - `pydantic` (and possibly `typing_extensions`)
  - `lib.*` (utilities)
  - `simulation.core.models.*` (same-layer models)
- `lib` is a leaf for first-party imports:
  - `lib/**` must not import from `simulation`, `db`, `feeds`, `ai`, `jobs`, `ml_tooling`, or `ui`.
- `ml_tooling` is also constrained:
  - `ml_tooling/**` may import `lib.*` but must not import from `simulation`, `db`, `feeds`, `ai`, `jobs`, or `ui`.
- API boundaries: `simulation.api.routes` may import only:
  - `fastapi` / `starlette` (framework types)
  - `simulation.api.schemas.*`, `simulation.api.services.*`, `simulation.api.dependencies.*`
  - `lib.*` (cross-cutting helpers), but **not** `db.*` or `simulation.core.factories.*`

#### Why (PY-1)

- Import contracts are the most direct way to enforce clean boundaries; violations are objective and “diff-stable”.

#### How (implementation) (PY-1)

- Add `import-linter` (or `grimp`-based checks) and a `contracts` file (e.g. `lint/import_contracts.ini`).
- Wire into pre-commit + CI (`uv run import-linter`).

#### Known failing examples in this repo (PY-1)

- `simulation/core/models/agents.py` importing `simulation.core.action_generators` (even if inside methods) is a strong “domain depends on services/registries” smell if the intent is “models are pure”.

#### Design detail (PY-1)

- Start with “warn-only” in CI, then ratchet (block new violations first, then backfill).

---

### PY-2: “No concrete infra instantiation” outside factories (Semgrep rule pack)

#### Enforces (PY-2)

- Disallow `SqliteTransactionProvider()` and `create_sqlite_*` calls in non-factory modules.
- Allowlist locations where concrete wiring is permitted:
  - `simulation/core/factories/**`
  - `db/**` (implementation)
  - `jobs/**` (scripts are allowed to be imperative wiring)
  - possibly `simulation/api/main.py` (app startup wiring)

#### Why (PY-2)

- This directly enforces DI (“no concrete instantiation in business logic”), and stops architecture drift early.

#### How (implementation) (PY-2)

- Use Semgrep (fast, easy custom rules, language-aware patterns).
- Add a repo-owned ruleset, e.g. `lint/semgrep/python-di.yml`.
- Pre-commit hook: `semgrep --config lint/semgrep --error`.

#### Example rule sketch (Semgrep) (PY-2)

```yaml
rules:
  - id: no-sqlite-transaction-provider-outside-factories
    languages: [python]
    message: "Do not instantiate SqliteTransactionProvider() outside factories/jobs; inject TransactionProvider."
    severity: ERROR
    patterns:
      - pattern: SqliteTransactionProvider(...)
      - pattern-not-inside: |
          # ok: factories
          ...
    paths:
      exclude:
        - simulation/core/factories/
        - db/
        - jobs/
```

#### Known failing examples in this repo (PY-2)

- `simulation/api/services/agent_query_service.py`
- `simulation/api/services/agent_command_service.py`

---

### PY-3: “Factory-only defaults” (AST-based custom linter)

#### Enforces (PY-3)

- Outside a factory module, forbid patterns like:
  - `dep = dep or ConcreteDep()`
  - `if dep is None: dep = ConcreteDep()`
  - `dep = dep or create_sqlite_*()`
- Outside a *designated composition root*, code must accept dependencies as required parameters and assume they’re present (per `docs/RULES.md`).

#### Why (PY-3)

- This is the core mechanism to make DI real: constructors/services can’t secretly “self-wire”.

#### How (implementation) (PY-3)

- Implement a small AST linter (Python `ast` module) as `scripts/lint_architecture.py` (or `lint/python_arch_lint/`).
- Configure allowlists by path (factories/jobs ok; everything else error).
- Run in CI + pre-commit.

#### Detection notes (PY-3)

- Regex-based linters will miss many cases; AST is reliable.
- Start with a minimal set of forbidden idioms and grow over time.

---

### PY-4: FastAPI route thinness + dependency wiring contract (Semgrep + AST hybrid)

#### Enforces (PY-4)

- In `simulation/api/routes/**`:
  - Forbid importing `db.*` directly.
  - Forbid calling `create_engine`, `create_sqlite_*`, or instantiating repos/providers.
  - Encourage the pattern: route → service call (optionally `asyncio.to_thread`) → response mapping.
- (Optional) cap cyclomatic complexity per route handler (or require helpers `_execute_*` live below route declarations).

#### Why (PY-4)

- Keeps HTTP boundary “dumb” and prevents slow creep of orchestration/infra inside routes.

#### How (implementation) (PY-4)

- Semgrep for import/path restrictions + obvious constructors.
- AST linter for higher-signal checks (e.g. “route handler contains `with transaction_provider.run_transaction()`”).

#### Repo fit (PY-4)

- Current `simulation/api/routes/simulation.py` already tends to delegate to service functions; this linter keeps it that way.

---

### PY-5: “Domain models must be pure Pydantic/stdlib” (import + symbol usage lints)

#### Enforces (PY-5)

- In `simulation/core/models/**`:
  - No imports from `db`, `feeds`, `ai`, `jobs`, `ml_tooling`.
  - Imports from `lib` are allowed (per your repo rule).
  - No access to time/I/O directly (e.g., `datetime.now()` in model constructors) unless explicitly allowlisted.
- Encourages moving validation helpers either:
  - into the models themselves (pure functions local to the models layer), or
  - into a `simulation.core.models.validation` module (still within the domain layer), when the helper is truly domain-specific.

#### Why (PY-5)

- “Domain purity” is one of the strongest levers for long-term maintainability.

#### How (implementation) (PY-5)

- Start with import-linter contracts (PY-1).
- Add Semgrep “banned import” rules for clarity and quick feedback in reviews.

---

## TypeScript: 5 custom linters (ESLint rules)

Implementation recommendation: add a local ESLint plugin (e.g. `ui/eslint-rules/`) and wire rules into `ui/eslint.config.mjs`. Keep `oxlint` for speed, but run ESLint for the custom rules (either in `lint:all` or only in CI if performance is a concern).

### TS-1: No `fetch()` outside the API client layer

#### Enforces (TS-1)

- Only `ui/lib/api/**` may call `fetch`.
- All network calls must flow through a single “API client” boundary.

#### Why (TS-1)

- Centralizes auth headers, error handling, retries, telemetry, and URL construction.

#### Repo status (TS-1)

- Already true today: `fetch(` occurs only in `ui/lib/api/simulation.ts`.

#### Implementation (ESLint custom rule) (TS-1)

- Report any `CallExpression` where callee is `fetch` unless filename matches allowlist glob.

---

### TS-2: No `process.env.*` outside approved modules

#### Enforces (TS-2)

- Only allow `process.env.*` access in:
  - `ui/next.config.ts`
  - `ui/lib/**` “environment boundary” modules (e.g. `ui/lib/supabase.ts`, `ui/lib/api/simulation.ts`)
  - `ui/scripts/**` (build/dev scripts)
- Components/hooks must not read env directly.

#### Why (TS-2)

- Makes configuration flow explicit and testable, and prevents accidental runtime env coupling in UI code.

#### Repo status (TS-2)

- Env reads are already concentrated in a few files; this linter keeps it that way.

---

### TS-3: Supabase boundary linter (“only AuthContext may use supabase auth”)

#### Enforces (TS-3)

- Forbid importing `{ supabase }` in UI components/hooks except:
  - `ui/contexts/AuthContext.tsx`
  - `ui/lib/supabase.ts` (creation)
- Force all auth/session access to go through `useAuth()` (DI via React context).

#### Why (TS-3)

- Prevents “global singleton usage everywhere” and keeps auth concerns centralized.

#### Implementation (TS-3)

- ESLint rule that inspects `ImportDeclaration` from `@/lib/supabase` and checks imported specifiers + filename allowlist.

---

### TS-4: `useEffect` async race-condition guard (request-id pattern)

#### Enforces (TS-4)

- If a `useEffect` contains:
  - an async function that `await`s and then calls `setState`, **and**
  - the effect can re-run (has dependencies other than `[]`)
  then it must include a request-id guard (per `docs/RULES.md`) or an explicit AbortController pattern.

#### Why (TS-4)

- These bugs are subtle and very common; enforcing a single approved pattern makes the UI more deterministic.

#### Repo status (TS-4)

- `ui/hooks/useSimulationPageState.ts` already uses request-id guards in some effects; this rule ensures consistency.

#### Implementation approach (TS-4)

- This is non-trivial but feasible with ESLint AST:
  - detect `useEffect(() => { ... }, deps)`
  - detect inner async function invoked (or IIFE)
  - detect `await` + `setState` usage
  - require a guard check comparing a captured id to a ref/current value before any `setState` after an await

---

### TS-5: Enforce UI layering via import boundaries (components/hooks/lib/types)

#### Enforces (TS-5)

- A simple layering model, e.g.:
  - `ui/types/**` is leaf-only (no imports from components/hooks/app)
  - `ui/lib/**` may import `ui/types/**` but not `ui/components/**`
  - `ui/hooks/**` may import `ui/lib/**` + `ui/types/**` but not `ui/components/**`
  - `ui/components/**` may import hooks/lib/types
  - `ui/app/**` should be mostly composition and may import components/hooks/lib/types

#### Why (TS-5)

- This prevents “spaghetti imports”, keeps core logic testable, and ensures a stable direction of dependency flow.

#### Implementation (TS-5)

- Either:
  - a custom ESLint rule that checks import specifiers against filename-based allowlists, or
  - use `eslint-plugin-boundaries` for the heavy lifting and keep a thin wrapper rule to enforce the exact architecture you want.

---

## Recommended rollout plan (practical and strict)

1. Add the linters in **warn-only** mode, but block *new* violations (baseline snapshot).
2. Convert the highest-signal rules to **error** once the baseline is paid down:
   - Python: DI instantiation + import contracts
   - TS: fetch/env/supabase boundaries + layering
3. Ratchet: lower allowlists over time; keep the composition root(s) explicit and small.
