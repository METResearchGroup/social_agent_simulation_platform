#!/usr/bin/env python3
"""Concurrent load test for POST /v1/simulations/run.

Usage:
    PYTHONPATH=. python scripts/load_test_simulation.py [BASE_URL]
    # Default BASE_URL is http://localhost:8000

Example:
    PYTHONPATH=. python scripts/load_test_simulation.py
    # With server running: prints total time, success count, failure count, latencies.
"""

import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

DEFAULT_BASE_URL: str = "http://localhost:8000"
CONCURRENCY: int = 5
NUM_AGENTS: int = 2
NUM_TURNS: int = 2
TIMEOUT_SECONDS: float = 60.0


def _post_run(base_url: str) -> tuple[bool, float, str | None]:
    """Send one POST /v1/simulations/run; return (success, latency_s, run_id or None)."""
    url = f"{base_url.rstrip('/')}/v1/simulations/run"
    payload = json.dumps({"num_agents": NUM_AGENTS, "num_turns": NUM_TURNS}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            elapsed = time.perf_counter() - start
            data = json.loads(resp.read().decode())
            run_id = data.get("run_id")
            return resp.status == 200, elapsed, run_id
    except Exception as e:
        elapsed = time.perf_counter() - start
        return False, elapsed, str(e)


def main() -> int:
    base_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE_URL
    print(
        f"Load test: {CONCURRENCY} concurrent requests, {NUM_AGENTS} agents, {NUM_TURNS} turns"
    )
    print(f"Base URL: {base_url}\n")
    start = time.perf_counter()
    successes = 0
    failures = 0
    latencies: list[float] = []
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [executor.submit(_post_run, base_url) for _ in range(CONCURRENCY)]
        for f in as_completed(futures):
            ok, lat_s, run_id_or_err = f.result()
            latencies.append(lat_s)
            if ok:
                successes += 1
            else:
                failures += 1
    total_s = time.perf_counter() - start
    latencies.sort()
    p50 = latencies[len(latencies) // 2] * 1000 if latencies else 0
    p95 = (
        latencies[int(len(latencies) * 0.95)] * 1000
        if len(latencies) > 1
        else (latencies[0] * 1000 if latencies else 0)
    )
    print(f"Total time: {total_s:.2f}s")
    print(f"Successes: {successes}, Failures: {failures}")
    print(f"Latency p50: {p50:.0f}ms, p95: {p95:.0f}ms")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
