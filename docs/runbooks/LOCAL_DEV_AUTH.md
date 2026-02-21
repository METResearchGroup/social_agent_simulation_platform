# Local Development: Auth Bypass and Session Persistence

This runbook covers how to bypass auth during local development and how to persist a real OAuth session for testing.

---

## Option 1: Bypass auth (no sign-in)

Use this when you want to work on the app without configuring OAuth (e.g. for UI work, API integration).

### Backend

Set `DISABLE_AUTH=1` (or `true`) before starting the API:

```bash
DISABLE_AUTH=1 PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload --port 8000
```

Or add to `.env` in the project root (if your runner loads it):

```
DISABLE_AUTH=1
```

### Frontend

Add to `ui/.env.local`:

```
NEXT_PUBLIC_DISABLE_AUTH=true
```

Restart the Next.js dev server. The app will render without showing the Sign-In screen, and API requests will succeed without a Bearer token.

**Security:** Do not use these flags in production or committed config. They are for local development only.

---

## Option 2: Real OAuth with persistent session

Use this when you need to test the full auth flow or session persistence.

1. Configure OAuth per [OAUTH_SETUP.md](2026-02-20_auth_phase1_gate_app_382915/OAUTH_SETUP.md).
2. Ensure `ui/.env.local` has:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
3. Ensure the backend has `SUPABASE_JWT_SECRET` (from Supabase Project Settings → API → JWT Secret).
4. **Do not** set `DISABLE_AUTH` or `NEXT_PUBLIC_DISABLE_AUTH`.

### Signing in

1. Start backend: `PYTHONPATH=. uv run uvicorn simulation.api.main:app --reload --port 8000`
2. Start frontend: `cd ui && npm run dev`
3. Visit `http://localhost:3000`
4. Click **Sign in with Google** or **Sign in with GitHub**
5. Complete the OAuth flow; you will be redirected back to the app

### Session persistence

Supabase stores the session in `localStorage` by default. After signing in once:

- The session persists across page reloads
- The session persists across browser restarts (until it expires or you sign out)
- The API client automatically sends `Authorization: Bearer <token>` on each request

To clear the session: click **Sign out** in the sidebar, or clear `localStorage` for `localhost:3000` in DevTools.

---

## Enabling auth bypass for automated testing

For headless or automated UI tests (e.g. Playwright, browser MCP):

1. Start the backend with `DISABLE_AUTH=1`
2. Start the frontend with `NEXT_PUBLIC_DISABLE_AUTH=true` in `.env.local` or:

   ```bash
   NEXT_PUBLIC_DISABLE_AUTH=true npm run dev
   ```

3. The app will load directly to the simulation UI without a sign-in step
