---
description: Deploy the Next.js UI to Vercel using the Vercel CLI (link, preview, production, verify).
tags: [ui, deployment, vercel, nextjs]
---

# UI Deployment Guide (Vercel)

This runbook deploys the Next.js UI in `ui/` to Vercel using the Vercel CLI (no dashboard required).

## Prerequisites

- Vercel account
- Vercel CLI installed: `npm i -g vercel`
- Logged in: `vercel whoami` (or `vercel login`)

## One-time: link the project

From `ui/`:

```bash
vercel link
```

Notes:

- This creates `ui/.vercel/` (already gitignored).
- Node version is controlled by `ui/package.json` via `engines.node` (we pin to `20.x` for parity with CI).

## Deploy a preview

From `ui/`:

```bash
vercel deploy --yes
```

The CLI prints a deployment URL.

## Deploy to production

Deploy from the **same git ref** as the API for that release (see [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md)). From `ui/`:

```bash
vercel deploy --prod --yes
```

## Production API URL (`NEXT_PUBLIC_SIMULATION_API_URL`)

The browser must call the same backend contract the UI was built against.

- In the Vercel project, set **`NEXT_PUBLIC_SIMULATION_API_URL`** to the **canonical production API base** the app should use (including `/v1` if your client expects it under that path—the value must match how `ui/lib/api/simulation.ts` joins paths; typically the full API root the UI uses, e.g. `https://<your-railway-service>.up.railway.app/v1`).
- After deploy, confirm it points at the Railway production service you verified, not a stale preview or wrong project.

Wrong or outdated values are a common cause of missing-route errors in the browser (for example metadata endpoints returning 404 while the UI assumes they exist).

## Verify the deployment

### Find the stable public URL (aliases)

The random-suffix deployment URL may be protected, but production deployments get stable aliases.

Inspect the latest production deployment and use one of the alias URLs:

```bash
vercel inspect <deployment-url>
```

Then verify with:

```bash
curl -sS -o /dev/null -w "%{http_code}\n" <ALIAS_URL>
```

Expected: HTTP `200`.

### API contract and smoke tests

After production deploy, validate that the live API behind `NEXT_PUBLIC_SIMULATION_API_URL` exposes the expected routes. Use the same checks as the Railway runbook and the automated suite in [SMOKE_TEST.md](./SMOKE_TEST.md) (`SIMULATION_API_URL` + `SIMULATION_API_BEARER_TOKEN` for `/v1` routes).

### Check runtime logs

```bash
vercel logs <deployment-url>
```

## Reproducibility notes

- `ui/package-lock.json` is committed and CI uses `npm ci` to ensure deterministic installs.
- Keep `next` on a patched version (Vercel blocks deployments of vulnerable Next.js releases).
