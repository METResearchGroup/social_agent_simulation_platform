# Authentication Migration Plan

OAuth + JWT-based authentication for the Agent Simulation Platform. User metadata stored in Supabase (Auth + DB in one place). No per-user views or configurations initially; focus on gating access and attributing activity to users.

---

## Goals

1. **Gate the app**: Only authenticated users can access the API.
2. **Create and track user accounts**: On first login, create a user record; link activity (runs, etc.) to that user.
3. **Future-ready**: Lay groundwork for per-user views, rate limits, and stricter authorization later.

---

## Technology Choices

| Choice | Decision | Rationale |
|--------|----------|-----------|
| Auth mechanism | **JWT (Bearer tokens)** | Works well with SPA + API; stateless; easy to verify in FastAPI middleware. |
| User metadata | **Supabase** | Auth + DB in one place; `auth.users` for identity; sync to app tables as needed. |
| Provider | **Supabase Auth** | Single backend, RLS-ready, easy OAuth (Google, GitHub, etc.) and magic links. |

---

## Create and Track User Accounts

**Create**:

- On first successful login (JWT verified), ensure a user record exists.
- Upsert from IdP profile: `auth_provider_id`, `email`, `display_name`, `created_at`, `last_seen_at`.
- Schema now enforces that `app_users.email` and `app_users.display_name` are NOT NULL. The new migration
  `db/migrations/versions/f0e1d2c3b4a5_enforce_app_user_identity_not_null.py` will fail early if there are
  existing rows with missing values, so confirm the Supabase JWT claims you rely on always include those fields.

**Track**:

- Store `user_id` on all relevant entities (e.g. `runs.created_by`).
- Update `last_seen_at` on each authenticated request (optional but useful for analytics).
- Enables future queries: "who started this run?" and "what did user X do?"

---

## Multi-Step Implementation

### Phase 1: Gate the App (OAuth + JWT verification)

- Integrate Supabase Auth with OAuth (e.g. Google, GitHub).
- Frontend: "Sign in with X" flow → receive access token.
- Backend: Middleware or dependency that validates JWT and returns 401 if missing or invalid.
- No user rows in app tables yet; only "authenticated or not."

**Deliverables**:

- Supabase project with Auth enabled and OAuth providers configured.
- FastAPI dependency/middleware to verify Supabase JWTs.
- Protected routes require valid `Authorization: Bearer <token>`.

---

### Phase 2: User Table + Activity Attribution

- Add `users` table (or equivalent) in Supabase/Postgres:
  - `id` (UUID, PK)
  - `auth_provider_id` (e.g. `auth.users.id` from Supabase)
  - `email`, `display_name`
  - `created_at`, `last_seen_at`
- On first authenticated request: resolve `auth_provider_id` → create/update user row.
- Add nullable `user_id` (or `created_by`) to `runs`.
- When creating a run: set `user_id` from the current user.
- No enforcement of "only your runs" yet; just store the link.

**Deliverables**:

- `users` table and migration.
- `runs.user_id` column and migration.
- Upsert logic on authenticated request (create/update user, update `last_seen_at`).
- Run creation writes `user_id`.

---

### Phase 3: Per-User Views (later)

- Use `user_id` in queries for "my runs" when that view is added.
- Enforce "can only view your own runs" where appropriate.
- Consider per-user rate limits (in addition to existing global limits).

---

## Auth Provider Alternatives (if Supabase changes)

| Provider | Notes |
|----------|-------|
| **Clerk** | Minimal backend code; managed user store; optional sync to Supabase. |
| **Auth0 (Okta)** | Enterprise-ready; SAML/OIDC; 7k MAU free tier. |
| **WorkOS** | B2B / org SSO. |
| **Cognito (AWS)** | AWS-native; pay-per-MAU. |

Supabase Auth is preferred for "Auth + DB in one place" and native Postgres integration.

---

## Open Questions / Assumptions

1. Will the UI and API share the same origin, or run separately (CORS implications for tokens)?
2. Refresh token handling: store in `httpOnly` cookie vs. memory (affects XSS/CSRF posture).
3. Which OAuth providers to enable initially (Google, GitHub, etc.)?

---

## Suggested Next Actions

1. **Phase 1**: Configure Supabase Auth, add JWT verification to the FastAPI API, protect routes.
2. **Phase 2**: Add `users` table, `runs.user_id`, and upsert/tracking logic.
3. **Phase 3**: Defer until per-user views or stricter authorization are needed.
