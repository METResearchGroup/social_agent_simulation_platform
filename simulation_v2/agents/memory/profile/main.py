"""Manages personalization memory per-agent.

We maintain a durable per-agent “personalization card”:

- interests
- liked/disliked topics
- posting style
- favorite accounts
- political/technical/social tendencies
- recent mood.

RAG then retrieves supporting memories as evidence.

To consistently update this, we add a post-turn “memory consolidation” step
after run_agent_actions(). It updates the memory from new likes/posts/follows
plus retrieved prior evidence. Then prompts receive both profile_summary and retrieved_memories. This is probably the best product-quality version because it gives agents stable identity plus fresh recollection
"""


def fetch_memory(user) -> str:
    return ""
