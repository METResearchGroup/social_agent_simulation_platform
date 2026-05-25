"""Manages episodic memory for an agent.

Here, we store every meaningful experience as an append-only memory event:

- "saw post X,"
- "liked post Y,"
- "followed user Z,"
- "wrote post about topic T."

We take the top-k memories that are likely most relevant to the given decision.
"""

DEFAULT_TOP_K = 5


def fetch_memory(_user, _k: int = DEFAULT_TOP_K) -> str:
    return ""
