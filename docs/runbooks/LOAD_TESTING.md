---
description: How to run the concurrent load test for POST /v1/simulations/run against local or deployed servers.
tags: [load-testing, performance, simulation, api]
---

# Load Testing Runbook

This runbook describes how to run the concurrent load test for `POST /v1/simulations/run`.

## Prerequisites

- The simulation API server must be running (local or deployed).
- From repo root, ensure `PYTHONPATH` is set when invoking the script.

## Running the Load Test

```bash
PYTHONPATH=. python scripts/load_test_simulation.py [BASE_URL]
```

Default `BASE_URL` is `http://localhost:8000` if omitted.

Example against local server:

```bash
PYTHONPATH=. python scripts/load_test_simulation.py
```

Example against deployed URL:

```bash
PYTHONPATH=. python scripts/load_test_simulation.py https://your-app.railway.app
```

The script prints total time, success count, failure count, and latency metrics.
