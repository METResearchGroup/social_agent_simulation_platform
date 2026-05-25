"""Turn simulation.

For this version, I'll decouple turn metrics generation and just generate it
after the fact. That extra complexity is obfuscating how this works.
"""

from pydantic import BaseModel

from simulation_v2.models.turn import TurnInputsModel


class GeneratedFeedsModel(BaseModel):
    pass


def load_turn_inputs() -> TurnInputsModel:
    raise NotImplementedError("load_turn_inputs is not implemented yet")


def generate_feeds() -> GeneratedFeedsModel:
    return GeneratedFeedsModel()


def run_agent_actions(turn_inputs: TurnInputsModel, feeds: GeneratedFeedsModel):
    pass


def run_generate_turn_metrics():
    pass


def mark_turn_as_done():
    pass


def simulate_turn(turn_inputs: TurnInputsModel):
    feeds: GeneratedFeedsModel = generate_feeds()
    run_agent_actions(turn_inputs, feeds)
    run_generate_turn_metrics()
    mark_turn_as_done()

