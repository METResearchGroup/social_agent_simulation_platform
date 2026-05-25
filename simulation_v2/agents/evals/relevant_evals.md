# Relevant LLM evals for simulation_v2

Proposed evals for agent quality and simulation realism in `simulation_v2`. Mix of traditional (deterministic / code-based) and LLM-as-judge evals. Instrumentation surfaces include `agents/actions.py`, `agents/prompts.py`, `agents/validators.py`, `telemetry/llm_collector.py`, and `telemetry/simulation_metrics.py`.

| Type | Eval | Motivating question |
|---|---|---|
| Traditional | Structured output reliability | Do the `like`, `follow`, and `write` prompts reliably produce parseable, schema-conformant outputs across many users and feeds? |
| Traditional | Invalid action proposal rate | How often does the model propose illegal actions that the validators later discard, such as self-likes, self-follows, or IDs not present in the feed/candidate set? |
| Traditional | Memory ablation lift | Does injecting episodic/profile/relationship memory materially improve agent decisions, or is it mostly adding token cost without measurable benefit? |
| Traditional | Behavioral diversity / anti-collapse | Are different agents actually behaving differently, or are they collapsing into the same generic taste, follow choices, and writing style? |
| Traditional | Proposal-to-kept calibration | Given the stochastic filters after LLM proposal, are the final kept actions consistent with configured probabilities, or are you masking a poor proposal model behind random acceptance/rejection? |
| Traditional | Cost and latency regression | For each action type, are token cost, request count, and p50/p90 latency staying within budget as prompts, models, or memory payloads change? |
| LLM-as-judge | Like relevance judge | Given the user profile, memory, and visible feed, are the selected likes genuinely relevant to this agent’s interests and not just popularity chasing? |
| LLM-as-judge | Follow plausibility judge | Given the candidate authors in the feed and the agent’s memory, are chosen follows socially plausible and well-motivated for that specific user? |
| LLM-as-judge | Post groundedness judge | Is the generated post plausibly grounded in the feed and the agent’s memory, rather than being generic, off-topic, or hallucinated? |
| LLM-as-judge | Persona consistency judge | Across several turns, does the same agent sound like the same person in tone, interests, and posting style? |
| LLM-as-judge | Relationship consistency judge | When relationship memory exists, do likes, follows, and posts remain consistent with what the agent supposedly thinks about other users? |
| LLM-as-judge | Multi-turn simulation realism judge | If you inspect a short trajectory of feeds and actions, does the simulated ecosystem look like a plausible social network, or like disconnected one-shot LLM calls stitched together? |

## Regression evals (labeled dataset, run on every change)

Assume a versioned labeled eval set where each case includes: `user`, `feed`, optional `memory` snapshot, and ground-truth labels such as `expected_like_post_ids`, `expected_follow_user_ids`, `expected_write_content` (or `expected_write_topic`), and `expected_no_action` flags per action type. Run this suite on every PR/commit that touches prompts, models, validators, memory, or agent orchestration.

| Type | Eval | Motivating question |
|---|---|---|
| Traditional | Like F1 vs labels | On labeled cases, does the model’s proposed like set match the annotated relevant posts (precision/recall/F1), not just parse correctly? |
| Traditional | Follow F1 vs labels | On labeled cases, does the proposed follow set match the annotated users this agent should follow? |
| Traditional | Negative-action accuracy | When labels say “like none”, “follow none”, or “do not write”, does the model respect empty outputs instead of hallucinating actions? |
| Traditional | Golden fixture parity | On frozen labeled fixtures (fixed user, feed, memory, model config), do outputs match stored golden responses within tolerance, catching silent behavior drift? |
| Traditional | Validator-clean final actions | After validators and stochastic filters, are 100% of kept likes/follows valid IDs from the feed/candidate set (zero self-actions, zero OOD IDs)? |
| Traditional | Write semantic similarity | For labeled write cases, does generated post content stay above a cosine-similarity (or ROUGE-L) threshold vs the reference post text? |
| Traditional | Write topic/category match | When labels specify topic or category (not exact wording), does the post classify to the same topic as the reference (classifier or embedding cluster)? |
| Traditional | Composite regression score | Does a weighted score (like F1, follow F1, write similarity, negative-action accuracy) stay at or above the baseline from the last approved eval run? |
| Traditional | Cost/latency envelope | On the labeled regression corpus, do p50 latency, total cost, and request count per action type stay within an agreed envelope vs the baseline run? |
| LLM-as-judge | Human-label agreement rate | On a labeled human-quality subset, does an LLM judge agree with human pass/fail labels at ≥80%, so judge-based nightly evals remain trustworthy after prompt/model changes? |

### Label fields assumed per case

| Field | Used by |
|---|---|
| `expected_like_post_ids` | Like F1, negative-action (empty like) |
| `expected_follow_user_ids` | Follow F1, negative-action (empty follow) |
| `expected_write_content` or `expected_write_topic` | Write semantic similarity, write topic match |
| `expected_no_write` | Negative-action accuracy |
| `golden_snapshot_hash` (optional) | Golden fixture parity |
| `human_quality_pass` (subset) | Human-label agreement rate |

## Suite split (suggested)

- **Regression (every PR):** full labeled regression table above; block merge if composite score or golden parity drops below threshold.
- **Core (every PR):** structured output reliability, invalid action proposal rate, cost/latency regression (from quality table).
- **Nightly:** memory ablation, behavioral diversity, proposal-to-kept calibration, sampled LLM-as-judge evals from the quality table.
- **Note:** multi-turn memory and relationship evals gain value once `update_agent_memories()` is implemented in `agents/memory/main.py`.
