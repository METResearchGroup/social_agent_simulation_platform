# Feature Extraction API — PRD (Draft)

## Summary

We will build a standalone “Feature Extraction” microservice that accepts text (and optional metadata) and returns a set of deterministic, versioned NLP/ML features. These features will be used by other services in the simulation platform (e.g., feed ranking, agent policies, analytics) and will provide a practical path for implementing and deploying model-backed inference behind an API with production-grade observability.

This PRD focuses on **five initial features**, the **API contract**, and an **implementation + rollout plan**.

## Goals

- Provide a single, stable HTTP API to extract a **set of versioned features** from text.
- Make feature extraction **composable** (request N features in one call) and **cost-transparent** (timings, model ids).
- Support **batch inputs** for throughput and experimentation.
- Ship with **production-grade logging, metrics, and tracing** so behavior is measurable and debuggable.
- Keep route handlers thin; enforce dependency injection and clear boundaries between:
  - API layer (FastAPI routes + validation)
  - service layer (orchestration + policies)
  - extractor implementations (model loading + inference)

## Non-goals (initially)

- Streaming token-by-token inference.
- Online model training or continuous learning.
- Multi-modal features (images, audio, video).
- Exactly-once processing semantics.
- Feature store persistence (we return features; storing them can be a separate component later).

## Primary Users / Consumers

- Backend services needing consistent text features:
  - simulation services (agent behavior, event processing)
  - feed ranking / recommendation components
  - analytics pipelines
- Researchers/operators who need quick, reliable inference results with reproducible versions.

## Glossary / Terms

- **Feature**: a named output derived from text (e.g., `sentiment.v1`).
- **Extractor**: the implementation that produces one feature (or feature group).
- **Extractor ID**: stable id for the code/model bundle, e.g. `sentiment.v1:distilroberta-base@sha256:...`.
- **Feature key**: stable API name for a feature, e.g. `ner.v1`.
- **Model version**: underlying model artifact identity (hash/commit/tag).

## Feature Set (Initial 5)

Each feature below is intended to be:

1) useful on its own, 2) broadly applicable, 3) testable, 4) observable in production.

### 1) Named Entities (`ner.v1`)

**What**: Detect spans and labels (e.g., PERSON, ORG, GPE) and optionally normalize some entity strings.

**Inputs**:

- `text` (required)
- `language` (optional, default `en`)

**Outputs**:

- entities: list of `{start, end, text, label, score}`
- optional normalization hints: `{canonical_text?}`

**Notes**:

- Can start with spaCy or a transformer NER model; keep the interface stable either way.
- Must define how offsets are computed (byte vs codepoint); standardize on Unicode codepoint offsets.

### 2) Sentiment + Emotion (`sentiment.v1`)

**What**: Provide polarity (negative/neutral/positive) and a small emotion distribution (e.g., joy/anger/sadness/fear).

**Inputs**:

- `text`
- `language` (optional)

**Outputs**:

- `polarity_label` + `polarity_score`
- `emotion_scores`: map of emotion → score (sums to 1.0)

**Notes**:

- Useful for agent behavior, moderation, and feed features.

### 3) Toxicity / Safety Signals (`toxicity.v1`)

**What**: Return a small set of safety-related scores (toxicity, insult, threat) with a conservative default threshold.

**Inputs**:

- `text`
- optional `context` (e.g. “comment”, “dm”) to support future policy tuning

**Outputs**:

- `scores`: map of signal → score
- `flags`: map of signal → boolean (thresholded)

**Notes**:

- This is not “moderation enforcement”; it is a feature supplier.
- Must log aggregate metrics; do not log raw text by default (see Observability).

### 4) Topic Classification (`topic.v1`)

**What**: Classify text into a constrained taxonomy (e.g., politics, sports, entertainment, tech, health).

**Inputs**:

- `text`
- optional `taxonomy_id` (default `default.v1`)

**Outputs**:

- `top_k`: list of `{label, score}` (k configurable, default 5)

**Notes**:

- Start with a simple taxonomy that is stable; later allow multiple taxonomies.
- Decide whether to return “other/unknown” explicitly; initial default: always return top_k.

### 5) Embeddings (`embeddings.v1`)

**What**: Generate a fixed-length vector embedding for semantic similarity, clustering, retrieval, etc.

**Inputs**:

- `text`
- optional `embedding_model` (default configured server-side)

**Outputs**:

- `vector`: list[float]
- `dim`: int
- `norm`: optional float (if normalized)

**Notes**:

- Prefer normalizing embeddings server-side for consistent cosine similarity usage.
- Consider payload sizes (vectors can be large); support gzip and/or an optional base64-encoded float16 representation later.

## API Design

### High-level principles

- **Versioned endpoints and versioned features**:
  - Endpoint version: `/v1/...`
  - Feature keys include versions: `ner.v1`, `sentiment.v1`, etc.
- **One call can request multiple features** to avoid redundant tokenization/model loading overhead.
- **Batch-first**: accept a list of inputs and return a list of results.
- **Deterministic by default**: no sampling; same input → same output given the same extractor id.

### Endpoints (proposed)

- `GET /health`
  - returns service health and basic readiness (model load status, etc.)

- `GET /v1/features`
  - returns available feature keys, their schemas, and extractor ids

- `POST /v1/extract`
  - extracts one or more feature keys for one or more inputs

- `POST /v1/extract/{feature_key}`
  - convenience endpoint for a single feature

- `GET /metrics`
  - Prometheus metrics scrape endpoint (or OpenTelemetry collector export; exact setup depends on deployment)

### Request: `POST /v1/extract`

```json
{
  "inputs": [
    {
      "id": "optional-client-id-1",
      "text": "Text to analyze.",
      "language": "en",
      "metadata": {
        "source": "comment",
        "thread_id": "123"
      }
    }
  ],
  "feature_keys": ["ner.v1", "sentiment.v1", "toxicity.v1"],
  "options": {
    "include_debug": false,
    "fail_on_unknown_feature": true
  }
}
```

### Response: `POST /v1/extract`

```json
{
  "results": [
    {
      "id": "optional-client-id-1",
      "features": {
        "ner.v1": {
          "extractor_id": "ner.v1:spacy_en_core_web_trf@<hash>",
          "entities": [{ "start": 0, "end": 4, "text": "Text", "label": "MISC", "score": 0.51 }]
        },
        "sentiment.v1": {
          "extractor_id": "sentiment.v1:distilroberta@<hash>",
          "polarity_label": "neutral",
          "polarity_score": 0.62,
          "emotion_scores": { "joy": 0.12, "anger": 0.04, "sadness": 0.05, "fear": 0.03, "neutral": 0.76 }
        }
      },
      "timing_ms": {
        "total": 18.3,
        "by_feature": { "ner.v1": 8.1, "sentiment.v1": 4.2, "toxicity.v1": 3.9 }
      }
    }
  ],
  "request_id": "server-generated-request-id",
  "warnings": []
}
```

### Errors (proposed)

- `400` invalid input (empty text when disallowed, invalid feature key format, etc.)
- `404` unknown feature key (if `fail_on_unknown_feature=true`)
- `413` payload too large (batch too big or text too long)
- `429` rate limited
- `500` internal error
- `503` model not loaded / temporarily unavailable

All error responses should be structured and include `request_id`.

### Limits (initial defaults; configurable)

- Max input text length: 10k characters (reject larger to avoid pathological compute/memory)
- Max batch size: 32 inputs
- Max number of requested feature keys per call: 10
- Request timeout: 2–10 seconds depending on deployment constraints

### Authentication / Authorization

Default expectation: service is internal-only, but still:

- Support standard bearer token auth (or shared service auth mechanism used in the platform).
- Include request identity (user/service) in logs and traces.

### Idempotency / Traceability

- If client sends `X-Request-Id`, echo it back; otherwise generate `request_id`.
- Include per-input `id` to make batch requests debuggable.

## Observability Requirements (Production-grade)

### Logging (structured)

Log events should be JSON with at least:

- `request_id`, `route`, `status_code`
- `feature_keys`, `batch_size`
- per-feature timings and total timing
- extractor ids (model/version)
- error category and exception type

**PII policy** (initial stance):

- Do not log raw `text` by default.
- Allow opt-in debug mode behind an explicit config and request header for trusted environments only.

### Metrics

At minimum:

- request count / latency histograms by route and status code
- per-feature latency histograms
- model load time + model cache hit/miss (if applicable)
- request/response payload sizes
- error counts by category

### Tracing

- OpenTelemetry tracing with spans:
  - `extract_request`
  - one nested span per feature extractor
- Propagate trace context headers if present.

## Implementation Plan (Engineering Steps)

This section is intended to be directly reusable as part of the PRD’s delivery plan.

### Phase 0 — Align on contracts (1–2 days)

- Define the canonical feature keys, schemas, and error handling rules.
- Decide offset semantics for NER (`start`, `end`).
- Write an API contract doc for `/v1/extract` and `/v1/features` (inputs, outputs, errors, limits).

Deliverable:

- A stable OpenAPI spec draft (even if implementation is not done yet).

### Phase 1 — Core extractor framework (2–4 days)

- Create a `FeatureExtractor` interface (e.g., `extract(text, *, language, metadata, options) -> FeatureResult`).
- Create a registry that maps `feature_key -> extractor`.
- Add a model/artifact loader abstraction so extractors don’t do ad-hoc global loads.
- Implement consistent timing + error capture wrappers so each extractor reports:
  - duration
  - extractor_id
  - structured errors (without swallowing exceptions at the wrong layer)

Deliverables:

- Unit tests for registry behavior and error normalization.
- A reference “toy” extractor (e.g., `length.v1`) to validate wiring.

### Phase 2 — Implement the five extractors (5–10 days)

For each of: `ner.v1`, `sentiment.v1`, `toxicity.v1`, `topic.v1`, `embeddings.v1`:

- Choose an initial model/library that is:
  - fast enough for a microservice
  - easy to package reproducibly
  - licensed acceptably for the project
- Implement extractor with clear configuration and an explicit `extractor_id`.
- Add golden tests (fixed inputs → fixed outputs within tolerances).
- Add load-time caching so repeated calls do not reload models per request.

Deliverables:

- One PR per extractor (or grouped if small) with tests + docs.

### Phase 3 — Microservice API (2–5 days)

- Build a dedicated FastAPI app (separate process/service) exposing:
  - `/health`, `/v1/features`, `/v1/extract`, `/metrics`
- Keep routes thin:
  - validate request (Pydantic)
  - resolve dependencies (registry, config, logger, tracer)
  - call a single service function (orchestrator)
- Add batch orchestration with:
  - per-input error isolation (one bad input shouldn’t drop the batch unless configured)
  - predictable ordering
- Add request limits (text length, batch size, feature key count).

Deliverables:

- OpenAPI served at `/docs`
- Smoke test that calls the running service and asserts basic correctness.

### Phase 4 — Observability hardening (2–4 days)

- Add structured logging and correlation id propagation.
- Add OpenTelemetry tracing and Prometheus metrics.
- Add dashboards/queries runbook notes (where to find key metrics and logs).

Deliverables:

- “Operational readiness checklist” for on-call debugging.

### Phase 5 — Deployment (2–5 days)

- Create Docker image for the service with pinned model artifacts.
- Add environment-based config:
  - default models per extractor
  - concurrency settings
  - debug logging gates
- Decide deployment target (e.g., Railway, Kubernetes, or internal VM) and document:
  - required env vars
  - health checks
  - scaling knobs

Deliverables:

- A deployable service in the target environment with `/health` and `/v1/extract` working.

### Phase 6 — Integration + adoption (ongoing)

- Add a small client library in the main platform that calls the service.
- Integrate one feature into one downstream path (e.g., feed ranking) behind a feature flag.
- Monitor latency, error rate, and compute cost; iterate on defaults.

## Testing Strategy

- Unit tests:
  - extractor registry
  - each extractor’s deterministic outputs on a small corpus
  - error normalization (timeouts, invalid model config, unsupported language)
- Integration tests:
  - spin up service locally, hit `/v1/extract` for 2–3 feature keys
- Smoke tests:
  - run against deployed environment using a minimal set of requests

## Performance and Scaling Considerations

- Prefer process-level model caching (load once per worker).
- Consider multi-process workers rather than per-request threads for CPU-heavy workloads.
- If using GPU later:
  - expose `FEATURE_EXTRACTION_DEVICE=cuda|cpu`
  - explicitly document throughput/latency differences

## Security and Privacy

- Treat raw input text as potentially sensitive.
- Default: do not persist or log text.
- Add request size limits and timeouts to reduce abuse risk.
- Rate limit by client/service identity.

## Open Questions

- What is the initial deployment target (Railway vs other)?
- Do we need multi-language support immediately, or only English?
- Do we want a strict schema registry for features (JSON Schema) returned by `/v1/features`?
- Should embeddings be returned as float32 arrays (easy) or compressed (smaller)?
