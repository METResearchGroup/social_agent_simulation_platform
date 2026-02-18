"""Prompt template for naive LLM comment prediction."""

COMMENT_PROMPT: str = (
    "Predict what comment this user would make on each post.\n\n"
    "Agent: {agent_handle}\n"
    "Posts:\n"
    "{posts_json}\n\n"
    "Return comments (post_id, text)."
)
