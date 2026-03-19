---
date: 2026-03-19
scope: python-backend
repo: agent-simulation-platform
---

## 5 immediate suggestions (next 1–3 PRs)

1. **Make simulation runs reproducible by default (seeded RNG)**
   - **Why**: today, “random_simple” policies use module-global `random.random()` without any run/turn seed control, so two runs with the same inputs can produce different outcomes.
   - **What to do**:
     - Introduce a `RunRng` (or `random.Random`) injected into action generators, seeded from a `run_seed` persisted on the `Run` record (and optionally a `turn_seed = hash(run_seed, turn_number)`).
     - Add a regression test that asserts two runs with the same seed produce the same actions for a fixed seed-state.
   - **Targets**: `simulation/core/action_generators/*/algorithms/random_simple.py`

2. **Normalize timestamps (UTC + ISO-8601) and centralize parsing**
   - **Why**: `Post.created_at` is an unconstrained string; action generators assume a custom format and treat parse failures as “0 recency”, which can silently change behavior depending on source.
   - **What to do**:
     - Add a single “parse timestamp” helper that accepts both current custom format and ISO-8601, returns an aware UTC `datetime`.
     - Over time, migrate persisted timestamps to ISO-8601 UTC and enforce it at the Pydantic model boundary.
   - **Targets**: `lib/timestamp_utils.py`, random-simple generators’ `CREATED_AT_FORMAT` parsing

3. **Fix action identifier semantics (agent_id vs agent_handle)**
   - **Why**: `Like.agent_id` / `Follow.agent_id` currently holds an agent handle, while the domain model has a distinct `Agent.agent_id`. This is a correctness and maintenance hazard when you add joins, analytics, or cross-entity constraints.
   - **What to do** (pick one and commit to it):
     - **Option A (recommended)**: rename action fields to `agent_handle` everywhere, keep handles as the primary identifier for actions.
     - **Option B**: store real `agent_id` in actions and include `agent_handle` as a separate field for display/debugging.
   - **Targets**: `simulation/core/models/actions.py`, action generators, DB adapters storing action rows

4. **Harden rate-limit client identity and proxy handling**
   - **Why**: `X-Forwarded-For` parsing is deployment-specific; without a trusted-proxy model, clients can spoof headers and evade or amplify rate limits.
   - **What to do**:
     - Decide on a single “source of truth” for client IP (e.g., `request.client.host` after trusted proxy headers are normalized).
     - Add an explicit configuration for trusted proxy hops / enable proxy header middleware at the ASGI layer if needed.
     - Add tests that validate rate-limit bucketing behavior under representative headers.
   - **Targets**: `lib/rate_limiting.py`, server/proxy deployment config

5. **Expand security headers to a modern baseline**
   - **Why**: current headers are a good start, but missing policies that reduce browser-side risk (even when an API is accessed by a web UI).
   - **What to do**:
     - Add at least: `Referrer-Policy`, `Permissions-Policy` (deny by default), and a minimal `Content-Security-Policy` if applicable to any HTML responses.
     - Make `Strict-Transport-Security` “on by default in prod” (guarded by env) and add tests to assert expected headers in prod-like mode.
   - **Targets**: `lib/security_headers.py`, `tests/api/test_security_headers.py`

## Linter + verification ideas to add (at least 10)

1. **Determinism lint (Semgrep): ban module-global randomness in `simulation/core/`**
   - **Gate**: fail if `random.random()`, `random.choice()`, etc. are used outside an injected RNG utility.
   - **Why**: prevents accidental non-reproducibility in core logic.

2. **Time-source lint (Semgrep): ban `datetime.now()` / `time.time()` in core (require `timestamp_utils`)**
   - **Gate**: in `simulation/` and `db/`, require using `lib/timestamp_utils` (or a new `Clock` interface) instead of raw wall-clock calls.
   - **Why**: enforces a single time source and makes time mocking + deterministic replay possible.

3. **UTC/ISO timestamp verifier (unit test + optional pre-commit)**
   - **Gate**: test that any persisted timestamp fields are parseable and normalized to UTC, and that mixed input formats normalize identically.
   - **Why**: catches “silent recency=0” style bugs early.

4. **Domain identifier semantics lint (Semgrep): forbid handles in `*_id` fields**
   - **Gate**: flag assignments where `agent_handle` is stored in a field named `agent_id` (and similar patterns).
   - **Why**: prevents long-term schema/data confusion and broken joins.

5. **SQL safety lint (Semgrep): forbid f-strings / `%` interpolation in SQL execution**
   - **Gate**: require parameterized SQL (placeholders + tuple args) for `conn.execute(...)`.
   - **Why**: even with SQLite, this prevents injection-style footguns and “quoting” bugs.

6. **Transaction boundary verifier (Semgrep): forbid `sqlite3.connect(...)` outside `db/adapters/sqlite/`**
   - **Gate**: enforce “DB access only through adapters/providers” so transactions and PRAGMA settings stay consistent.
   - **Why**: keeps persistence behavior consistent and makes future DB backends possible.

7. **Exception hygiene lint (Ruff + optional Semgrep): ban broad `except Exception` without re-raising typed errors**
   - **Gate**: allow `except Exception` only in the API boundary (where you translate to error envelopes) or in top-level orchestration; elsewhere require specific exceptions.
   - **Why**: improves debuggability and avoids swallowing invariant violations.

8. **Expand Ruff rule set gradually (CI-only first)**
   - **Gate**: enable additional Ruff families to act like “light formalism”:
     - bug risks (e.g., Bugbear-style checks), simplifications, error-prone patterns, and security checks.
   - **Why**: you’ll catch more correctness issues pre-review with minimal overhead.

9. **Repository contract tests (property-based where possible)**
   - **Gate**: for each repo method, assert invariants like “write then read yields same model”, “idempotent writes are idempotent”, “ordering guarantees hold”, and “transactions are atomic”.
   - **Why**: turns persistence semantics into executable contracts (a key step toward verification).

10. **Simulation invariants verifier (Hypothesis): action-history + rules are never violated**

    - **Gate**: generate random small runs (few agents, few turns) and assert global invariants:
      - no duplicate targets per agent per turn
      - no repeated likes/comments/follows across turns for same agent+target within run
      - persisted actions match action-history behavior when replayed

    - **Why**: raises confidence that “policy expansion” won’t break invariants.

11. **API schema stability gate**

    - **Gate**: snapshot or diff the OpenAPI schema and fail PRs that change it without an explicit version bump/approval.
    - **Why**: treats your API as a spec; prevents accidental breaking changes.

12. **Logging correctness lint**

    - **Gate**: require structured logs for key events to always include `{request_id, run_id, turn_number}` where applicable (Semgrep can enforce `extra={...}` keys or wrapper usage).
    - **Why**: makes invariant failures diagnosable and supports auditability.

## 5 recommendations to consider later (roadmap)

1. **Promote action/state invariants into an executable spec**
   - **Why**: you already have runtime invariants (no duplicate/previously-acted-on). An executable spec (Quint/TLA+-style) helps ensure *state transitions* remain valid as the system grows.
   - **What to do**: start with a minimal model of (run, turn, action history) and assert invariants; run bounded checking in CI nightly.

2. **Move long-running simulations off the request path**
   - **Why**: even though you offload to threads, the route is still synchronous “from the client’s POV” and holds resources; it will become a scaling bottleneck.
   - **What to do**: add an async job queue (or background worker) with an idempotency key; return `202 Accepted` + polling endpoints.

3. **Introduce “protocol-level” contracts for your engine/service interfaces**
   - **Why**: formal verification starts by making contracts explicit. You can approximate this with strict types, richer Pydantic invariants, and explicit pre/post conditions at boundaries.
   - **What to do**: add typed wrappers (`RunId`, `AgentHandle`, `TurnNumber`), tighten validators, and enforce monotonicity/invariants on write paths.

4. **Strengthen observability as a correctness tool**
   - **Why**: invariants fail fastest when you can correlate logs/traces/metrics by `request_id`, `run_id`, `turn_number`, and “policy”.
   - **What to do**: add structured fields to logs everywhere, add basic tracing spans, and persist per-turn duration + counts as first-class metrics.

5. **Plan for multi-backend persistence without leaking DB details**
   - **Why**: your adapter/repo abstractions are solid; the next step is ensuring SQLite-specific behaviors (e.g., replace semantics, connection quirks) don’t become accidental “spec”.
   - **What to do**: add repository-level “behavioral tests” (contract tests) and run them against SQLite now; later re-run against Postgres to preserve semantics.
