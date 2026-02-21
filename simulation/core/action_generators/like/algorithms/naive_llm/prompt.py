"""Prompt template for naive LLM like prediction."""

LIKE_PROMPT: str = (
    "Predict which posts this user would like.\n\n"
    "Agent: {agent_handle}\n"
    "Posts:\n"
    "{posts_json}\n\n"
    "Return the post IDs they would like."
)
