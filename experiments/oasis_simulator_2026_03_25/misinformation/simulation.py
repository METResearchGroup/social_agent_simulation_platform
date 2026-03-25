"""Source: https://github.com/camel-ai/oasis/blob/25e0fc26/docs/cookbooks/misinformation_spreading.mdx?plain=1#L61-L87

Updated to use gpt-5-nano.

Run from root directory with:

uv run --env-file .env python experiments/oasis_simulator_2026_03_25/misinformation/simulation.py
"""

import asyncio
import os
import random
from pathlib import Path
from typing import TypeAlias

import oasis
import pandas as pd
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from oasis import ActionType, LLMAction, ManualAction
from oasis.social_agent.agent import SocialAgent
from oasis.social_agent.agents_generator import generate_twitter_agent_graph

ActionValue: TypeAlias = ManualAction | LLMAction | list[ManualAction | LLMAction]

current_dir = Path(__file__).parent
db_path = current_dir / "data" / "simulation.db"
agent_profile_path = current_dir / "random_network.csv"
sampled_profile_path = current_dir / "data" / "random_network_sample_10.csv"
SAMPLED_USER_COUNT = 10


async def main():
    db_path.parent.mkdir(parents=True, exist_ok=True)
    sampled_df = pd.read_csv(agent_profile_path)
    sampled_df = sampled_df.sample(
        n=min(SAMPLED_USER_COUNT, len(sampled_df)),
        random_state=42,
    )
    sampled_df.to_csv(sampled_profile_path, index=False)

    openai_model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_5_NANO,
        model_config_dict={"temperature": 1},
    )

    # Define the available actions for the agents
    available_actions = [
        ActionType.CREATE_POST,
        ActionType.LIKE_POST,
        ActionType.REPOST,
        ActionType.FOLLOW,
        ActionType.DO_NOTHING,
        ActionType.QUOTE_POST,
    ]

    # Delete the old database
    if os.path.exists(db_path):
        os.remove(db_path)

    # Build agent graph from profile CSV (required by oasis>=0.2.5).
    agent_graph = await generate_twitter_agent_graph(
        profile_path=str(sampled_profile_path),
        model=openai_model,
        available_actions=available_actions,
    )

    # Make the environment
    env = oasis.make(
        agent_graph=agent_graph,
        platform=oasis.DefaultPlatformType.TWITTER,
        database_path=db_path,
    )

    # Run the environment
    await env.reset()

    # Inject truth and misinformation via manual actions from agent 0.
    seed_actions: list[ManualAction | LLMAction] = [
        ManualAction(
            action_type=ActionType.CREATE_POST,
            action_args={
                "content": "Amazon is expanding its delivery drone program to deliver packages within 30 minutes in select cities. This initiative aims to improve efficiency and reduce delivery times."
            },
        ),
        ManualAction(
            action_type=ActionType.CREATE_POST,
            action_args={
                "content": "Amazon plans to completely eliminate its delivery drivers within two years due to the new drone program. #Automation #Future"
            },
        ),
        ManualAction(
            action_type=ActionType.CREATE_POST,
            action_args={
                "content": "Harvard University has announced a new scholarship program that will cover full tuition for all undergraduate students from families earning less than $75,000 per year."
            },
        ),
        ManualAction(
            action_type=ActionType.CREATE_POST,
            action_args={
                "content": "Harvard is raising tuition fees for all students despite the new scholarship program, making it harder for families to afford education. #EducationCrisis"
            },
        ),
        ManualAction(
            action_type=ActionType.CREATE_POST,
            action_args={
                "content": "The latest Marvel movie, Avengers: Forever, has officially broken box office records, earning over $1 billion in its opening weekend."
            },
        ),
        ManualAction(
            action_type=ActionType.CREATE_POST,
            action_args={
                "content": "Marvel is planning to retire the Avengers franchise after this film, saying it will not produce any more superhero movies. #EndOfAnEra"
            },
        ),
        ManualAction(
            action_type=ActionType.CREATE_POST,
            action_args={
                "content": "A recent study shows that regular exercise can significantly reduce the risk of chronic diseases such as diabetes and heart disease."
            },
        ),
        ManualAction(
            action_type=ActionType.CREATE_POST,
            action_args={
                "content": "Health experts claim that exercise will be deemed unnecessary in five years as new treatments will eliminate chronic diseases entirely. #HealthRevolution"
            },
        ),
    ]

    agent_zero = env.agent_graph.get_agent(0)
    initial_step_actions: dict[SocialAgent, ActionValue] = {agent_zero: seed_actions}
    await env.step(initial_step_actions)

    # Simulate 3 timesteps by activating 1% of agents with LLM actions.
    all_agents = [agent for _, agent in env.agent_graph.get_agents()]
    for _ in range(3):
        print(f"Step {_ + 1}/{3}")  # noqa
        num_agents_to_activate = max(1, int(len(all_agents) * 0.01))
        activated_agents = random.sample(all_agents, num_agents_to_activate)
        step_actions: dict[SocialAgent, ActionValue] = {
            agent: LLMAction() for agent in activated_agents
        }
        print(f"Step actions: {step_actions}")  # noqa
        await env.step(step_actions)
        print("Step actions completed")  # noqa

    # Close the environment
    await env.close()


if __name__ == "__main__":
    asyncio.run(main())
