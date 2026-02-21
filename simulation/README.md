# Simulation

This directory contains the core simulation logic for the agent simulation platform.

## Available Scripts

### `main.py`

Runs the social media agent simulation:

- Creates initial agents from the database
- Runs 10 turns of simulation
- Each turn, agents:
  - Get their feed
  - Like posts
  - Comment on posts
  - Follow users
- Records all agent actions
- Prints summary statistics for each turn

## Running the Simulation

Run the simulation from the project root using `uv`:

```bash
uv run python simulation/main.py
```
