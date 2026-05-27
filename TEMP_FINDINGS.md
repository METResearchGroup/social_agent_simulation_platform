# Simulation V2 Architecture Review Findings

## Evaluation Criteria

1. **Local-First Architecture Fit**
   Good: cloud concepts map cleanly to in-process control plane, dispatch, worker, and SQLite. Bad: local code either mimics cloud infra unnecessarily or bypasses the intended service split.

2. **Single Runtime Path**
   Good: `main.py` enters one clear SQLite-backed flow. Bad: old simulation paths, duplicate models, or compatibility shims remain active or confusing.

3. **State Durability Across Turns**
   Good: turn N+1 reads durable SQLite outputs from turn N. Bad: actions are only returned in memory, rolled back too broadly, or invisible to later turns.

4. **Run/Turn Lifecycle Semantics**
   Good: run and turn statuses transition predictably and persist on success/failure/retry. Bad: failures leave runs stuck, completed turns duplicate work, or transitions are owned by the wrong layer.

5. **SQLite Data Model Completeness**
   Good: all core entities, generations, actions, feeds, memories, and eval metrics have typed records and constraints. Bad: rows are missing, weakly typed, or not protected by uniqueness/FK constraints.

6. **Turn Pipeline Completeness**
   Good: snapshot -> feed generation -> LLM actions -> validation -> execution -> memory -> evals happens in order. Bad: stages are skipped, conflated, or write outside their ownership boundary.

7. **Action Provenance and Validation**
   Good: every LLM call, raw proposed action, accepted action, and rejected action is persisted with reasons. Bad: schema failures, invalid actions, or execution diffs disappear into logs.

8. **Memory as First-Class State**
   Good: memories are loaded before acting, updated deterministically, and visible in later turns. Bad: memory is prompt-only, stale, or not persisted append-only.

9. **Eval Plugin Architecture**
   Good: evals are plugin-style, scoped to turn/run, persisted, and usable as deterministic regression signals. Bad: evals are ad hoc scripts, non-persistent, or coupled directly to worker internals.

10. **Testability and Operational Inspectability**
    Good: focused tests cover repositories, orchestration, actions, memory, feeds, evals, and the main smoke path. Bad: the system only works manually, lacks DB assertions, or cannot explain what happened after a run.

## Findings

### High: Failure Persistence Is Structurally Fragile

`worker.service.run_job()` wraps seed import, all turns, evals, and final completion in one transaction. If any turn fails, the transaction rolls back the earlier `running` status and all intermediate records, then the failure handler only marks failed if the persisted run is still `running`, so a failed run can remain `queued` with no diagnostic state in SQLite. This conflicts with the architecture's durable status/progress model.

```python
try:
    with transaction(db_path) as conn:
        run = repos.get_run(job.run_id, conn)
        # ...
        if run.status == "queued":
            repos.update_run_status(job.run_id, "running", conn)

        config = LocalSimulationConfig.model_validate(run.config_json)
        import_seed_if_needed(job.run_id, config, repos, conn)
        execute_run(job.run_id, config, conn, repos)
        repos.update_run_status(job.run_id, "completed", conn)
except (RunNotRetryableError, RunNotFoundError):
    raise
except Exception as exc:
    with transaction(db_path) as conn:
        run = repos.get_run(job.run_id, conn)
        if run is not None and run.status == "running":
            repos.update_run_status(job.run_id, "failed", conn, error=str(exc))
```

### Resolved: PR15 Legacy Cleanup Complete

`simulation_v2/agents/` and `simulation_v2/models/` were deleted in PR15 (#327). This follow-up removed orphaned stochastic telemetry (`simulation_metrics.py`, `record_stochastic_filter`) and the PR15 guard test (`test_legacy_paths_removed.py`) that only enforced the cutover. Stochastic downsampling via `actions/noise.py` remains intentionally deferred.

### Medium: Transaction Boundaries Do Not Match Intended Turn-Level Persistence

The proposal wanted turn execution writes through explicit transactions so partial turns fail cleanly. Current execution persists feeds, generations, actions, diffs, turn completion, and evals on the same long-lived connection passed from the worker, so the code shape is right but the durability boundary is too broad.

### Medium: Feed Generation Is Plugin-Style But Still Stochastic By Default

`most_liked` uses `random.random()` without a seeded RNG from config, so local smoke runs are not reproducible even though the architecture leans toward inspectable local regression. That is acceptable for exploratory simulation, but weaker for CI/golden comparisons.

### Medium: Local-First Scope Is Mostly Respected

The implementation has `config`, `control_plane`, `worker`, `db`, `seed`, `feeds`, `actions`, `memory`, and `evals`, and `main.py` goes through `start_run()`. External repo-local imports are minimal, though `simulation_v2/time.py` no longer wraps `lib.timestamp_utils` as proposed.

## Overall Assessment

The build is much further along than a scaffold: it implements most of the intended local-first architecture and covers the major entities, plugins, and service boundaries. Against `PROPOSAL.md`, it is roughly 75-85% architecturally aligned, with the main gaps being failure/retry durability.

Tests were not run during this review.
