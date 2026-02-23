"""Prompt template for naive LLM follow prediction."""

FOLLOW_PROMPT: str = (
    "Predict who this user would follow from these authors.\n\n"
    "Agent: {agent_handle}\n"
    "Authors:\n"
    "{authors_json}\n\n"
    "Return user handles to follow."
)
