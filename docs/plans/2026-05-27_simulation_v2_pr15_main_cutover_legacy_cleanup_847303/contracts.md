# PR 15 Contract Freeze

| Symbol | Location | Contract |
| --- | --- | --- |
| Public entrypoint | `simulation_v2/main.py` | Only runtime entry; calls `start_run` + `get_run_summary`; no imports from deleted modules |
| Default config | `LocalSimulationConfig.default()` | 10 users, 5 posts/user, 3 turns (from `config.py`) |
| Seed in-memory models | `simulation_v2/seed/models.py` | Hosts `UserModel`, `PostModel`, `LikeModel`, `FollowModel`, `SeedDataModel`, `LoadedUserModel`, `LoadedPostModel`, `LoadedSeedDataModel`, `SeedDataset`, `SeedImportSummary` |
| Telemetry in-memory models | `simulation_v2/telemetry/models.py` | Hosts `ActionType`, `LatencyPercentiles`, `ActionLlmMetricsSummary`, `TurnLlmMetricsSummary`, `RunLlmMetricsSummary` |
| `count_run_entity_totals` | `simulation_v2/db/repositories.py` | Returns dict with keys: `user_count`, `post_count`, `like_count`, `follow_count`, `comment_count`, `memory_count`, `generation_count`, `proposed_action_count`, `generated_feed_count`, `eval_run_count`, `eval_metric_count`, `turn_count` |
| Run summary initial counts | `RunRecord.seed_metadata_json` | Use `post_count`, `like_count`, `follow_count` as baseline; `comment_count` baseline = 0 |
| Seed parquet CLI | `simulation_v2/seed/generator.py` | `if __name__ == "__main__"` block replaces deleted `seed_data.py` CLI |
| Deleted paths (must not exist post-PR) | — | `simulate_run.py`, `simulate_turn.py`, `legacy_feeds.py`, `load_seed_data.py`, `seed_data.py`, `agents/`, `models/` (entire package) |
