# Proposed start simulation flow

In the Start Simulation:

- Instead of specifying number of agents, we can have an interface that's like:
  - "Select Agents"
  - Displays a paginated list of agents. Can make use of the same Viewer Component that's proposed in PROPOSED_AGENT_DETAIL_MIGRATION.md.
  - Show also the total number of available agents to choose from.
  - Two options: Random or Custom
    - For random, can specify a number of agents and then the Viewer Component is updated to show only that amount of agents. After seeing a result, can click a "Shuffle" button to randomly re-select agents. Can also manually click agents as well.
    - For custom, they have to click the agents.
    - A number updates that shows the number of selected agents.
- This all happens in a subsection like "> Select Agents".

We can imagine doing this in a series of PRs.

- PR 1: Introduce UI:
  - "Select Agents"

- PR 2: Display paginated list

  - Display the list.
  - Connect to backend.
  - Just show all the agents, in the paginated hydrated row format.
  - Out of scope: Selecting agents.

- PR 3: Add custom selection of agents

  - Users can select agents.
  - Add the agents choice to the export for "Start Simulation".
  - We can start a run and it has those agents. We should be able to look at a new run that's generated and then it has those agents chosen.

- PR 4: Add random selection

  - Add random selection of agents.
