# PR 14 Golden Dataset Eval — Contract Freeze

| Symbol | Contract |
| --- | --- |
| `GoldenFixtureFile` | `schema_version: int` (must be `1`), `cases: list[GoldenCase]` |
| `GoldenCase` | Required: `case_id: str`, `user_id: str`. Optional: `expected_like_post_ids`, `expected_follow_user_ids`, `expected_write_topic` (each `list[str]` or `str` for topic). **Absent key = skip label**; **present empty list = negative label** (predicted must be empty). |
| `GoldenDatasetPlugin.name` | `"golden_dataset"` |
| `GoldenDatasetPlugin.scopes` | `frozenset({"turn"})` only |
| Default fixture path | `Path(__file__).resolve().parent.parent / "fixtures" / "golden_v1.json"` |
| Predicted sets | From `load_proposed_actions(context)` filtered to `record_kind == "validated"` and `user_id == case.user_id` |
| `metric_name` | `precision`, `recall`, `f1`, `tp`, `fp`, `fn`, plus informational `cases_evaluated`, `cases_skipped`, `labels_skipped` |
| `metadata_json` | At minimum `label_type`, `case_id`; macro rows use `label_type` only |
| `status` | `"passed"` for skeleton unless fixture file missing/invalid (then `"failed"` + warning) |
| Runner | **No edits** to `runner.py`; registry-only wiring |
| Config | **Do not** add to default `turn_plugins` / `run_plugins`; tests pass `LocalSimulationConfig` with `golden_dataset` in list |

## P/R/F1 helper

```python
def prf(predicted: set[str], expected: set[str]) -> tuple[float, float, float, int, int, int]:
    tp = len(predicted & expected)
    fp = len(predicted - expected)
    fn = len(expected - predicted)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1, tp, fp, fn
```

## Write topic (skeleton)

Case-insensitive equality: `predicted_topic.strip().lower() == expected_write_topic.strip().lower()` where `predicted_topic` is the first validated `write_post` action's `target_content` for that user in scope (empty string if none). Treat as set comparison with singleton sets for P/R/F1.

## Pass/fail

| Condition | `status` |
| --- | --- |
| Fixture loads and evaluates | `"passed"` |
| Fixture file missing or invalid JSON/schema | `"failed"` + warning |
