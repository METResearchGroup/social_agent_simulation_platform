# Project Expectations — Feature Extraction API

## Overview

You’ll implement a sequence of NLP “feature extractors” as clean, testable Python modules with stable APIs. We’ll ship incrementally: each feature lands as a PR with tests + a runnable sanity script + brief perf notes.

## What you own vs what I own

- **You own**
  - Feature implementation modules (per-feature extractor)
  - Batch wrapper (`*_batch`) behavior
  - Deterministic output formatting + ordering
  - Example corpus + golden tests / invariants
  - A short write-up: “when it works / when it fails” + basic timings

- **I own / we pair closely**
  - FastAPI service wiring and request/response schemas
  - Orchestration (`POST /v1/extract`), timeouts/concurrency
  - Deployment (Railway), secrets, rate limits, auth integration
  - Observability + privacy policy enforcement (no raw text logging by default)
  - RAG retrieval (if/when we decide to do it)

We’ll adjust order based on what’s easiest to validate.

## Basic definition of "Done" (per feature PR)

A feature is “done” when the PR includes:

- **Stable public API** Something like the following, which we can discuss on a per-project basis.
  - `extract_<feature>(text: str, *, language: str = "en", **opts) -> FeatureOutput`
  - `extract_<feature>_batch(texts: list[str], ...) -> list[FeatureOutput]` (loop is fine)
- **Typed output**
  - Pydantic model or dataclass, JSON-serializable
- **Determinism rules**
  - Stable ordering (e.g., entities sorted by `(start, end, label)`; top_k sorted by score desc then label)
  - Fixed rounding policy if you round floats (or explicitly do not round)
- **Validation + limits**
  - Empty text handling is defined
  - Max length behavior is defined (truncate vs reject vs return error in module)
- **Tests**
  - 10–30 golden examples or invariant-based tests.
- **Sanity script**
  - `python -m ...` or a small script that prints outputs for 5–10 texts
- **Perf notes**
  - Rough timing for 10/100/1000 texts on CPU
  - Notes on memory/cold start if relevant
- **Known limitations**
  - Language, slang, long text, model bias, etc.

## Scope boundaries (important)

- You’re **not expected** to productionize the full microservice alone.
- If a feature requires significant taxonomy design (intent/stance), we’ll simplify the label set first.

## Quality bar

We prioritize: correctness + determinism + testability + clarity over “lots of features quickly.” One solid feature shipped is better than three half-working ones. Better to work on quality than quantity.
