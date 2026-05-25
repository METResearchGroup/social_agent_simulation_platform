"""Turn simulation.

For this version, I'll decouple turn metrics generation and just generate it
after the fact. That extra complexity is obfuscating how this works.
"""

from simulation_v2.agent import get_agents_actions
from simulation_v2.feeds import generate_feeds
from simulation_v2.models.feeds import GeneratedFeedsModel
from simulation_v2.models.turn import TurnInputsModel


def load_turn_inputs() -> TurnInputsModel:
    raise NotImplementedError("load_turn_inputs is not implemented yet")


def run_agent_actions(turn_inputs: TurnInputsModel, feeds: GeneratedFeedsModel):
    return get_agents_actions(turn_inputs, feeds)


# no-op for now, intentionally.
def run_generate_turn_metrics():
    pass

# no-op for now, intentionally.
def mark_turn_as_done():
    pass


def simulate_turn(turn_inputs: TurnInputsModel):
    feeds: GeneratedFeedsModel = generate_feeds(turn_inputs)
    run_agent_actions(turn_inputs, feeds)
    run_generate_turn_metrics()
    mark_turn_as_done()
