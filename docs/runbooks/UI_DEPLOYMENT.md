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

From `ui/`:

```bash
vercel deploy --prod --yes
```

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

### Check runtime logs

```bash
vercel logs <deployment-url>
```

## Reproducibility notes

- `ui/package-lock.json` is committed and CI uses `npm ci` to ensure deterministic installs.
- Keep `next` on a patched version (Vercel blocks deployments of vulnerable Next.js releases).

