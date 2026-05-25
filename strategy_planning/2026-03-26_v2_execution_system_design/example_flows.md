# Example flows

In the new architecture, let's go through some example flows and scenarios to make it more clear what's happening per turn.

## User story 1: upload dataset

As a researcher, I want to upload my (1) agent graph *and* (2) a small set of seed posts in one step, so my simulation has real content in feeds and in storage.

Parameters for dataset upload step:

- Agents: 5
- Directed follow edges: hub: all non-Alice follow Alice; chain: Bob -> Cara, Cara -> Dev (Eden only follows Alice)
- dataset_id: ds_social_001

(note: this then means that turn 1 requires both agents *and* posts. This means one invariant is that on each turn, there *must* be posts.)

### User story 1 variant

As a researcher, I want to upload my (1) agent graph, and have an LLM model auto-generate seed posts for the network. For now, we can generate seed posts at random and then automatically link them to a random user in the network (to keep interactions in-network for now).

## User story 2: Execute turn 1 (feeds see real posts; agent DAG; metrics)

(TBD)
