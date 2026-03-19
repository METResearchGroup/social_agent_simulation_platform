# Data snapshots

## Snapshots

A `Run*Snapshot` is an immutable, frozen copy of the state of things at the moment a run starts. We have a historical reference of what agents we used, what the state of the social network was, and what posts were available at the start of the simulation.

### The problem that snapshots solve

As the application grows and as we experiment, we may change the values that certain components have. For example, we may have an Agent A, and that agent follows Agents B and C. However, later on, we may change it so that Agent A also follows Agents D and E. If we were to "replay" the simulation, we want to know the exact state of the social network at the time of the simulation, and if we grab the latest state of Agent A, we would have incorrect information about their social network.

We can and we allow seed data to be updated/changed. However, this means that future runs can deviate from past runs, even if they in theory use the same seed data (same as determined by ID), because the data itself can change.

Run snapshots are like a run-level form of version control. We know exactly what the inputs were to a run, and what the state/values of those inputs were, at the time of the run.

### How does this affect how we interpret runs?

Having the `Run*Snapshot` allows us to know what was present at the start of a run. We can combine this with our `Turn*` data in order to replay/reconstruct what happens turn-by-turn for a given run.

#### Run snapshot = "state at the start of a run"

`Run*Snapshot` tables record what was true at the moment that a run started: which agents participants, their profile/follow/post state at the time, and likes/comments.

#### Turn data = "what happens during a turn"

Turn-scoped data records what the simulation did each turn. These are append-only, updated each turn.

#### How do we interpret a "run"?

To interpret or replay a run, we use both layers: we use `Run*Snapshot` to know what was true at the start of a run, and then the `Turn*` data for what happened each turn.

### What snapshots do we maintain?

#### `RunAgentSnapshot`

`RunAgentSnapshot` stores which agents were in the run and their identity/profile fields at run start (for example, handle/display name/bio and count fields as they existed at that moment). It answers: "Which agents were in this run, and what did each selected agent look like at start time?"

#### `RunFollowEdgeSnapshot`

`RunFollowEdgeSnapshot` stores the directed social graph between run participants at run start. It is scoped to the run and anchored to `RunAgentSnapshot`, so follow relationships are interpreted in the context of which agents were in the run.

#### `RunPostSnapshot`

`RunPostSnapshot` stores the initialized set of posts for the run.

#### `RunPostLikeSnapshot`

`RunPostLikeSnapshot` stores likes that already exist at run start, anchored to run-scoped posts. It captures who liked which run post at start time and preserves liker identity-at-start fields needed for stable historical interpretation.

#### `RunPostCommentSnapshot`

`RunPostCommentSnapshot` stores initialized comments that already exist at run start, anchored to run-scoped posts.

### Alternatives

Perhaps, depending on how this scales up, creating a run-level snapshot becomes too bulky. One alternative that I've considered is adding entity-level version control. We can track each change of an entity with a Git-like hash. That way, for example, instead of tracking all the details about a certain agent, we just need to track the agent's ID and their hash, and we can reconstruct the state of that agent on demand.
