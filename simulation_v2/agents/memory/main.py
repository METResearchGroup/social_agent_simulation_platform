from simulation_v2.agents.memory.episodic.main import (
    fetch_memory as fetch_episodic_memory,
)
from simulation_v2.agents.memory.profile.main import (
    fetch_memory as fetch_personalized_profile_memory,
)
from simulation_v2.agents.memory.social_relationship.main import (
    fetch_memory as fetch_social_relationship_memory,
)


def fetch_memory(user):

    episodic_memory = fetch_episodic_memory(user)
    personalized_profile_memory = fetch_personalized_profile_memory(user)
    social_relationship_memory = fetch_social_relationship_memory(user)

    return f"""

    Episodic memory: experiences you've had recently
    ```markdown
    {episodic_memory}
    ```

    Personalized profile memory: A list of the agent's interests, liked/disliked topics, posting style, favorite accounts, political/technical/social tendencies and recent mood.

    ```markdown
    {personalized_profile_memory}
    ```

    Social relationships memory: What the agent thinks about other users in the network.

    ```markdown
    {social_relationship_memory}
    ```
    """


def update_agent_memories():
    pass
