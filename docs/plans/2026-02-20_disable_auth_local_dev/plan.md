# Disable auth during local dev

## Problem

After PR #96 (OAuth with Supabase), every simulation API call requires a valid JWT and the app gates on sign-in. Local development and automated testing (e.g. browser MCP) require OAuth setup and a persisted session, slowing iteration.

## Solution

Add opt-in auth bypass via env vars:

- **Backend** `DISABLE_AUTH=1`: `require_auth` returns a mock payload; no JWT validation.
- **Frontend** `NEXT_PUBLIC_DISABLE_AUTH=true`: AuthContext treats user as authenticated; app loads without sign-in.

## Verification

1. Without bypass: app shows Sign-In screen; API returns 401 without token.
2. With bypass: app loads simulation UI directly; API accepts requests without Authorization header.

### Screenshots

- **Before** (auth required): [`images/before/sign-in-required.png`](images/before/sign-in-required.png)
- **After** (auth bypass): [`images/after/simulation-ui-with-bypass.png`](images/after/simulation-ui-with-bypass.png)

See `docs/runbooks/LOCAL_DEV_AUTH.md` for usage.
