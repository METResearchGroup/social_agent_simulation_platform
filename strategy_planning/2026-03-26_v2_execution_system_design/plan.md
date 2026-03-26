# Proposed plan

[Diagram link](https://app.diagrams.net/#G1q_eINXHkikiOEuy1pc7PsSmXQbtnJtdp#%7B%22pageId%22%3A%22kubc4wDPqAbCVnN0LSeD%22%7D)

## What is a run?

A run is a single unit of full end-to-end execution.

### What is the input/output of a run?

The inputs to a run are:

- A .csv file of data to use in the run.
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

The table structure would be something like:

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

For the API routes, we would have a write and a read route.

Then, during a run, we would reference the dataset, so we would have something like:

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

Completion here is we've:

1. written the run record in the DB, stating that we've started the run.
2. Saved the inputs to a normalized format in the DB. We save this as the turn=0 data for the given run.

Tables:

```python
class Run:
    run_progress: str # some enum
    timestamp: str # using standardized timestamp utils

class RunAgents:
    """For a given run, all the agents who participated in the run at
    any point.

    This is added only at the start of a run.
    """
    run_id: str
    user_id: str
    user_handle (str): handle of the user.
    username (str): username of the user.
    bio (Optional[str]): the bio of the user.
    follow_ids (Optional[list[str]]): IDs of the users who they follow.
    follower_ids (Optional[list[str]]): IDs of the users who follow them.
```

#### 2. Transform the inputs to a run

## What is a turn?

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
