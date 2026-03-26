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

### What tables are in a turn?

The turn-specific tables:

```python
class TurnPost:
    """Posts written during a turn.
    
    PK: (post_id, run_id, turn_id)
    """
    run_id: str
    turn_id: str
    post_id: str
    user_id: str # ID of the user who wrote the post.
    text: str
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

## Task Execution Platform

We have a generic task platform that does all task execution. The model would be something like:

```python
class TaskCreationPlatform:
    def __init__(self):
        pass

    async def create_tasks(self):
        pass

class TaskExecutionEngine:
    """Manages how different tasks are scheduled in parallel, using
    a semaphore model."""
    def __init__(self):
        self.tasks = []

    async def submit_tasks(self):
        """Submits tasks for execution. Awaits until all tasks are done.

        "Done" can happen in two ways:
            1. Success: writes to temp output. Updates status (TODO: need
            to figure out how job statuses are updated).
            2. Failure: either (1) fails on retries (in which case, can push
            to deadletter queue) or (2) fails on timeouts (also can push to
            deadletter queue).
        """
        pass


class TaskOutputPersistenceManager:
    """Manages how task outputs are persisted to permanent storage"""
    def __init__(self):
        pass

    def persist_results(self):
        pass


class TaskPlatform:
    def __init__(self):
        self.task_creation_platform = TaskCreationPlatform()
        self.task_execution_engine =

    async def create_tasks(self):
        self.task_creation_platform.create_tasks()

    async def submit_tasks(self):
        pass

    def persist_results(self):
        pass

# how these are called in the DAG

task_platform = TaskPlatform()
tasks = await task_platform.create_tasks()
await task_platform.submit_tasks(tasks) # need to see, does this need to be async?
task_platform.persist_results()
```

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
