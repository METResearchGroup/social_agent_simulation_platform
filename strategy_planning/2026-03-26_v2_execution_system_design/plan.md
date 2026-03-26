# Proposed plan

[Diagram link](https://app.diagrams.net/#G1q_eINXHkikiOEuy1pc7PsSmXQbtnJtdp#%7B%22pageId%22%3A%22kubc4wDPqAbCVnN0LSeD%22%7D)

## What is a run?

A run is a single unit of full end-to-end execution.

### What is the input/output of a run?

The inputs to a run are:

- A `Dataset` (see below).
- Basic configuration:
  - Choice of algorithm.

#### What does the input .csv of data look like?

We want the following fields in the .csv file:

- user_id (str): ID of the user
- user_handle (str): handle of the user.
- username (str): username of the user.
- bio (Optional[str]): the bio of the user.
- follow_ids (Optional[list[str]]): IDs of the users who they follow.
- follower_ids (Optional[list[str]]): IDs of the users who follow them.

**Out-of-scope**: What's out of scope of the V1 is a list of the user's posts.

- We can eventually support this by passing in an additional .csv file that
has a list of posts, with something like:
  - post_id (str): ID the post
  - user_id (str): ID of the author
  - text (str): text of the post.

#### What does the configuration look like?

For now, we can keep a lightweight configuration object, something like:

```python
class RunConfig:
    feed_algorithm: str # likely should validate against some enum
```

### Datasets: determining what data goes into a run

Before a run starts, we want to "save" data into a dataset, and then runs/turns can use that as the singular representation of the "start" state of a run.

All runs/turns reference a dataset. This dataset is the "starting point" of a given run/turn.

We save a single representation here because this lets us represent the starting agents/network state one time, and have all runs/turns reference it. The alternative is to save this at the run/turn level (i.e., the existing "snapshot" representation), which in practice leads to a lot of duplication.

The input would be the above .csv.

The UI would be something like a "add a new dataset" tab. The users would add a new .csv file, give it a name, we would parse it, ask for user approval (and report simple statistics like number of agents), and then have a popup that says "dataset successfully saved".

On starting a new run, they toggle a dropdown menu that selects one of the datasets that they have. They can only choose a previously submitted dataset. If the users have not submitted a datset, we prompt them to go to the "add a new dataset" tab to add a dataset.

#### Tables

```python
class Dataset:
    dataset_id: str # PK
    user_id (str): ID of the user
    user_handle (str): handle of the user.
    username (str): username of the user.
    bio (Optional[str]): the bio of the user.
    follow_ids (Optional[list[str]]): IDs of the users who they follow.
    follower_ids (Optional[list[str]]): IDs of the users who follow them.

class DatasetMetadata:
    dataset_id: str # PK
    user: str # user who uploaded the dataset. Can clarify later how this should be done. Might just be determined by who is logged in. Can also use whatever identifier I already have for checking "who is logged in".
    created_at: str # timestamp when the dataset was created.
```

For now, these datasets should be immutable and insert-only (no upsert).

#### API routes

For the API routes, we would have a write and a read route.

#### Usage

During a run, we would reference the dataset, so we would have something like:

```python
class Run:
    run_id: str
    dataset_id: str # the dataset used for the run
    ...
```

### What is the high-level flow of a run?

The high-level flow of a run is:

#### 1. Start the run

Here, we (1) collect the inputs from the user, and (2) write the run record in the DB.

Tables:

```python
class Run:
    run_id: str
    dataset_id: str
    run_progress: str # some enum, probably "started" in the beginning
    timestamp: str # using standardized timestamp utils
```

The `Run` record can be upserted, and we expect it to be upserted. This is how we track and update run status.

We then read the dataset and write records for turn=0.

Related tables for the start of a run:

- `turn_follows`: we add the user's follows/followers.

Out-of-scope:

- `turn_likes`: currently out-of-scope for the start (we currently don't accept likes from users at the start).
- `turn_posts`/`turn_comments`: currently out-of-scope for the start (we currently don't accept posts from users at the start).

#### 2. Trigger the turns

#### 3. Do the run completion module

Once the turns are done, we want to do the remainder of the tasks needed to mark a run as completed.

##### Task 1: Calculate run-based metrics (if any)

We calculate the run-based metrics, if any, using the same primitives for metrics calculation used in the turn-based logic.

The sources of data can vary based on the metrics used.

See the `What is the "generate metrics" DAG?` section to review the actual implementation.

##### Task 2: Update run status

We then mark the run as "completed":

```python
class Run:
    run_id: str
    dataset_id: str
    run_progress: str = "completed" # some enum, probably "started" in the beginning
    timestamp: str # using standardized timestamp utils
```

## What is a turn?

A turn is a single discrete timestep in the simulation, where the agents perform actions and the state of the platform changes.

### What is the high-level flow of a turn?

A turn generally takes the following steps:

1. Get the inputs to a turn.
2. Run the feed algorithms to get the feeds per user.
3. Execute the "run agent actions" DAG.
4. Execute the "generate metrics" DAG.

#### 1. Get the inputs to a turn

Inputs here are:

- (list inputs)

Completion here looks like:

- (list conditions for completion)

#### 2. Run the feed algorithms to get the feeds per user

Inputs here are:

- (list inputs)

Completion here looks like:

- (list conditions for completion)

#### 3. Execute the "run agent actions" DAG

Inputs here are:

- (list inputs)

Completion here looks like:

- (list conditions for completion)

See the `What is the "run agent actions" DAG?` section for more information.

#### 4. Execute the "generate metrics" DAG

Inputs here are:

- (list inputs)

Completion here looks like:

- (list conditions for completion)

See the `What is the "generate metrics" DAG?` section for more information.

### What is the "run agent actions" DAG?

Our "run agent actions" DAG has three components:

1. Create the jobs.
2. Execute the jobs (and write results to temp storage).
3. Persist the results to permanent storage.

Concretely, it would be executed as something like this:

```python
class RunAgentActionsPlatform:
    def __init__(self, num_turns: int):
        self.task_platform = TaskPlatform()
        self.num_turns: int = num_turns

    def execute(self):
        """Performs single turn.

        Additional things to add:
        - For each of these steps, probably want logging + metadata tracked.
        - Also probably want to add task details/metadata for each task.
        """
        tasks = self._create_tasks()
        self.task_platform.submit_tasks(tasks)
        self.task_platform.persist_results()

    def _create_tasks(self) -> list:
        """Creates the tasks to execute.
        
        Has two parts:
        1. Defining the custom state needed for creating the tasks.
        2. Creating the tasks.
        """
        task_params = {} # extra steps, definiing how we perform tasks here
        tasks = self.task_platform.create_tasks(task_params)
        return tasks
```

### What is the "generate metrics" DAG?

Our "generate metrics" DAG has three components:

1. Create the metrics tasks.
2. Execute the tasks (and write results to temp storage).
3. Persist the results to permanent storage.

```python
class GenerateMetricsPlatform:
    def __init__(self, num_turns: int):
        self.task_platform = TaskPlatform()

    def execute(self):
        """Performs single turn.

        Additional things to add:
        - For each of these steps, probably want logging + metadata tracked.
        - Also probably want to add task details/metadata for each task.
        """
        tasks = self._create_tasks()
        self.task_platform.submit_tasks(tasks)
        self.task_platform.persist_results()

    def _create_tasks(self) -> list:
        """Creates the tasks to execute.
        
        Has two parts:
        1. Defining the custom state needed for creating the tasks.
        2. Creating the tasks.

        Of note: can probably use the same base `GenerateMetricsPlatform`
        and define child classes, `TurnGenerateMetricsPlatform` and
        `RunGenerateMetricsPlatform`, if needed, and the only thing that
        would change is what tasks are created.
        """
        task_params = {} # extra steps, definiing how we perform tasks here
        tasks = self.task_platform.create_tasks(task_params)
        return tasks
```

### What is a "task"?

(more info)

Se the "Task Execution Platform" below for more details on how the tasks are actually run.

### What tables are in a turn?

The turn-specific tables:

```python
class TurnPost:
    """Posts written during a turn.
    
    PK: (post_id, run_id, turn_id)
    FK:
    - run_id is a foreign key to the Run table (run_id).
    - (run_id, turn_id) together form a foreign key to the Turn table (composite key).
    - generation_id (if not None) is a foreign key to the Generation table (generation_id).
    """
    run_id: str
    turn_id: str
    post_id: str
    user_id: str # ID of the user who wrote the post.
    text: str
    generation_id: str | None # the ID of the generation that resulted in this post, if any.

class TurnLike:
    """Like records during a turn.
    
    FK:
    - run_id is a foreign key to the Run table (run_id).
    - (run_id, turn_id) together form a foreign key to the Turn table (composite key).
    - (post_id, run_id, turn_id) is a post that must exist (an agent can only like a post that already exists, and the PK for posts is (post_id, run_id, turn_id)).
    - generation_id (if not None) is a foreign key to the Generation table (generation_id).
    """
    run_id: str
    turn_id: str
    like_id: str
    post_id: str # ID of the user who wrote the post
    generation_id: str | None # the ID of the generation that resulted in this post, if any.

class TurnComment(TurnPost):
    """Comment written during a turn."""
    super().__init__()
    parent_post_id: str # ID of the post commented on.
    parent_post_user_id: str # ID of the user who posted the comment.

class TurnFollow:
    """Table representing follow information. Each row corresponds to a single user. We intentionally choose to make each row unique on user_id rather than some combination of (user_id, follow_id/follower_id) for deduplication's sake and to reduce the number of write ops.
    """
    run_id: str
    turn_id: str
    user_id (str): ID of the user # PK
    follow_ids (Optional[list[str]]): IDs of the users who they follow.
    follower_ids (Optional[list[str]]): IDs of the users who follow them.
    generation_id: str | None # the ID of the generation that resulted in any change in follows/followers this turn, if any.
```

## Job Execution Platform

We have a generic job platform that does all job execution. The model would be something like:

```python
class JobExecutionEngine:
    """Manages how different jobs are scheduled in parallel, using
    a semaphore model. Creates tasks given the different jobs.
    
    We intentionally create all tasks upfront, as opposed to doing it in batches.

    With large scales, this may be memory-intensive and we may want to move
    to a queue-based or event-driven model, but we're nowhere near there yet.

    This simple "create all tasks upfront" is the simplest abstraction we
    can have for now.
    """
    def __init__(self, max_concurrent: int):
        self._tasks = []
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def submit_jobs(
        self,
        jobs: Iterable[tuple[Callable[..., Awaitable[Any]], dict[str, Any]]]

    ):
        """Submits tasks for execution. Awaits until all tasks are done.

        "Done" can happen in two ways:
            1. Success: writes to temp output. Updates status (TODO: need
            to figure out how job statuses are updated).
            2. Failure: either (1) fails on retries (in which case, can push
            to deadletter queue) or (2) fails on timeouts (also can push to
            deadletter queue).
        """
        for coro_func, kwargs in jobs:
            self._submit_job(coro_func, kwargs)

        return await self.wait()

    async def _run_with_limit(
        self,
        coro_func: Callable[..., Awaitable[Any]],
        **kwargs: Any,
    ) -> Any:
        """Run a task (bounded by the semaphore concurrency limit).
        
        TODO: will also likely want retry logic as well. Probably
        can just re-append to tasks queue if retry is needed.
        """
        async with self._semaphore:
            # assumed that each coroutine function will manage persisting
            # its own results to permanent storage. We want to leave that
            # work to the coro_func rather than checking here if it exists.
            # A coro_func should have (1) unit of work and (2) writing to
            # temp output (or deadletter, if needed).
            return await coro_func(**kwargs)

    def _submit_job(
        self,
        coro_func: Callable[..., Awaitable[Any]],
        kwargs: dict[str, Any],
    ) -> asyncio.Task[Any]:
        """Submit a task to the execution engine."""
        task = asyncio.create_task(self._run_with_limit(coro_func, **kwargs))
        self._tasks.append(task)
        return task


    async def wait(self) -> list[Any]:
        if not self._tasks:
            return []

        results = await asyncio.gather(*self._tasks, return_exceptions=False)
        self._tasks.clear()
        return results

    def done(self) -> bool:
        return all(task.done() for task in self._tasks)


class JobOutputPersistenceManager:
    """Manages how job outputs are persisted to permanent storage"""
    def __init__(self):
        pass

    def persist_results(self):
        pass


class JobPlatform:
    """Platform for executing a series of jobs."""
    def __init__(self):
        self.job_execution_engine = JobExecutionEngine()
        self.job_output_persistence_manager = JobOutputPersistenceManager()

    async def submit_jobs(self, jobs):
        await self.job_execution_engine.submit_jobs(jobs)

    def persist_results(self):
        pass

# how these are called in the DAG
job_platform = JobPlatform()
jobs = [] # each caller is required to create jobs themselves.
await job_platform.submit_jobs(jobs)
job_platform.persist_results()
```

The platform is intended to be used within the context of a DAG, rather than directly called.

### Design considerations

#### Tracking jobs

We track a job through job metadata:

(TODO: write fields)

```python
class JobMetadata:
    job_id: str # PK
    job_metadata: Optional[str] # Optional. The job execution platform should be independent of any specific use case. However, we can have metadata like `{"run_id": <id>, "turn_id": <turn>}` for our own tracking.
    status: str # probably an enum, with values pending/running/temp_written/persisted/failed
```

#### When is a job finished?

A job is considered finished when (1) a job finishes, (2) it is persisted to temp output, and (3) returns a success message to the caller. A job would stall out if it finished but didn't write to temp output. We would have timeouts for a given job and if it doesn't return a success message.

#### Choosing write model (temp -> permanent storage)

Right now, we intentionally choose an architecture where we write the job outputs to a temp output storage and then have the persistence manager pick up the temp files and write to permanent storage. This was chosen for the following reasons:

- Crash tolerance: if the job finishes but the writer fails, then we can retry. We'll probably want to build towards making jobs "resumable" or "retryable", especially as we scale up and don't want to merely lose work.
- Decouples engine from persistence manager: this means that both can be run on seperate processes/servers. Also means that they can be run on different schedules.
- Max memory requirements are lowered: as the tasks complete, we don't have to accumulate the results in memory. This keeps the execution engine relatively lightweight, as opposed to the model where we have to accumulate all the results in memory and then passing it to the persistence manager. An intermediate approach, of accumulating a batch of results, then passing that batch to the persistence manager, requires extra work to manage batches, which is complicated for a V1. We want *all tasks* to be run, and then *all tasks* to be persisted.
- Natural audit trail. Temp files give you inspectable artifacts for debugging.

Some tradeoffs though in doing this:

- More I/O: we write to temp storage and then we read the temp storage output and then write to permanent storage. We could just pass the results from memory to the persistence manager directly.
- Slower end-to-end latency than direct return for small jobs.
- Possible need for deduplication: on retry, we'd have to make sure that we don't duplicate work that's in the temp storage. Can ameliorate by "flushing" the temp path, if it exists, before running the engine.

Alternatives considered:

- Direct in-memory transfer
- Batching: requires batching semantics, which incorporate more complications.
- Keeping both in-memory and temp output: probably the most complicated of the two, as there's a lot of edge casing to be considered (e.g., how can you tell that the in-memory one is incomplete and thus you need the temp output?). Also creates two possible sources of truth, which causes its own problems.

#### Single-node model

We plan on using a single-node model for the application. We want to keep the current V1 implementation as lightweight on the infra requirements as possible.

(tradeoffs).

#### Multi-threaded engine, single-threaded writer

We want to use a multi-threaded engine, but a single-threaded writer.

We will use a multi-threaded engine capped by a semaphore. We'll do some load testing to see what our semaphore count should be. Since the application is heavily LLM-driven, we expect the application to be I/O bound but relatively light on memory requirements. We'll probably be rate-limited client-side by any LLM provider limitations on parallelism (e.g., past ad-hoc experimentations found that ~40 parallel task submissions to OpenAI's API, while using `gpt-5-nano`, was the max for performance; above that and we saw rate limit caps), so this will likely be what determines the semaphore cap.

We will use a single-threaded writer model. We don't expect our writes to be computationally expensive and we would rather writes take slightly longer if it guarantees correctness and idempotency semantics. This avoids race conditions from multiple writers (see the `What if persistence writes to DB successfully but crashes before deleting the temp file?` discussion).

#### What is the unit of idempotency?

(TODO)

#### Known failure modes

##### What if the process dies halfway through writing the temp file?

If the process dies halfway through writing the temp file, then we count that as incomplete and the job will timeout (and thus be counted as failed).

##### What if persistence writes to DB successfully but crashes before deleting the temp file?

Before writes to the DB, we first load records from the DB with `job_id` values equal to the ones we're attempting to write. We don't write records whose `job_id` already exists in the DB.

This model assumes a single-threaded DB writer model; otherwise if we have two DB writers that attempt to grab a temp output, we can have a TOCTOU race condition, where they both check if the temp output exists yet in the DB, see that it doesn't, and then they both try to write.

##### What if the persistence manager processes half the temp files and then dies?

This is OK and we just retry the persistence manager. This should be managed at the orchestrator level, which can do heartbeat checks on the persistence manager process to verify completion. The persistence manager process will either return a success message, crash and return an error message, or timeout, and all of these modes can be managed at the orchestration level.

##### What if one bad temp file blocks the whole persistence pass?

If one bad temp file blocks the persistence pass, we can skip it.

For reads, we can have two approaches:

- Read all the files in a temp output path all at once (via `pandas`). This assumes that they're all supposed to be read together (i.e., they're from the same set of jobs). This can be specified in the temp output (e.g., for `turn_likes`, the temp path can be something like `<base path>/temp/run_id={run_id}/turn_id={turn_id}/record=turn_likes/`), so that all records in a given temp path are assumed to belong together. We can then have strong schema validation on the outputs. We have Pydantic models for each output type, so we can validate schemas on-read. We can also explore validation via Parquet (e.g., collect all temp files, write to parquet, then read).
- If that fails, we can read each one individually, and then delete files that fail to be read. This is assuming a transient file error (e.g., corrupted file) rather than systemic error (e.g., incorrect syntax) that is casuing reads to fail (i.e., it's a one-off bad file). We are OK with our simulations being lossy on rare occassions. For example, if the record was "Agent A wanted to like this post", we're OK if it's lossy 0.001% of the time (or a lossiness of that scale), and one source of lossiness is "temp file wasn't able to be read for some reason". We should also have logging for how often this happens, to verify if it is indeed transient. We can tentatively say that an error rate of 0.01% (1/10,000) is the reporting threshold for something like this, as this should remain a transient error.
  - Errors that we're OK with: network errors, retryable errors (errors resolved if we, say, rerun the persistence pass).
  - Errors that we're NOT OK with, at all: corrupted files. We can set a threshold of 0.01% (1/10,000)
  - Errors that we'll have to monitor: Pydantic model shape validation: the individual tasks should check the model output shape and verify it against a Pydantic model. To verify shape, we also, on read, enforce a specific Pydantic model output (we can do something like `.model_validate()` on read). This should always pass, since we do validate schemas on write. However, we want to monitor this. Let's log whenever this breaks, as downstream users of the data will assume a specific contract shape and we want to validate that before persisting to storage. Model validation should be handled on write, but we verify it on reads as well so that we can guarantee data formats for downstream callers.

## LLM Platform

### How do we manage LLM generations?

We separate the telemetry and tables for the LLM generations and decouple those from the turn tables.

```python
class Generation:
    """LLM-based generations.
    
    PK: generation_id.
    """
    generation_id: str
    prompt: str
    model_name: str
    model_configs: dict
    model_response_object: object # the Pydantic model used for the response
    response: str # the actual model's response
    created_at: str # timestamp
```

#### Linking generations to their Turn records

We intentionally add `generation_id` to each of the relevant tables (e.g., `turn_posts`), to create a relationship between the record and the LLM generation that motivated it. We expect most records to have the `generation_id` populated in practice, so we add it directly as a column. The alternative is to keep the ID only in the `Generation` table and create a FK linking it to the correct table + ID. But this requires additional logic to map the table + ID to the correct table AND it also requires an O(n) lookup each time we want to, say, know what LLM generation led to a given result. This is a search pattern we'll likely often want (I can envision a feature where we can "inspect" the LLM call that led to a given generation), so we don't want this to be an O(n) lookup. Reverse lookup (find all records a generation “caused”) is possible, though less common. Adding a table/tag ref to `Generation` is really only justifiable if you expect frequent reverse lookups or complex many-to-1/1-to-many mappings. Doing it here adds schema and integrity overhead and creates more room for error. For example, you'd have to validate that the table name + PK actually exists in the records table, whereas if for some reason we have a generation whose `generation_id` doesn't exist in a Turn* record, this is OK, and we just disregard/cleanup that record.

## Orchestration

We'll run the application as a series of DAGs using Prefect in Railway.

## Connecting to the API

(TODO: still WIP)

Proposed model:

- Press "submit" or similar button in the UI.
- DAG is run.
- Get results
- Update the frontend.

The user can manually trigger each turn (would be easier to orchestrate than "leave it and forget" for runs, plus it would give more immediate results to the user.)

Should get the DAG working first in Prefect and prove that that can even work. Let's get the task execution and the Prefect orchestration logic working first, I think, and do it on a small dummy example pipeline. Then we can come back and implement the data models and whatnot.

- TODO: figure out a simple pipeline experimental implementation that I can do. A basic dummy one.

Request model would be something like:

The best fit here is:

- POST /jobs creates a Prefect flow run and returns immediately with a job_id / flow_run_id
- the UI switches to pending
- the UI either polls GET /jobs/{id} every few seconds, or subscribes to a live update channel
- when the run reaches a terminal Prefect state, the UI fetches the final result.

Polling is the easiest implementation here. Connecting websockets would be a bit heavier and would require more setup (e.g., managing the connection lifecycle, reconnect handling, etc).
