"""Turn simulation.

For this version, I'll decouple turn metrics generation and just generate it
after the fact. That extra complexity is obfuscating how this works.
"""

from pydantic import BaseModel

class TurnInputsModel(BaseModel):
    pass


class GeneratedFeedsModel(BaseModel):
    pass

def load_turn_inputs() -> TurnInputsModel:
    return TurnInputsModel()

def generate_feeds() -> GeneratedFeedsModel:
    return GeneratedFeedsModel()

def run_agent_actions(turn_inputs: TurnInputsModel, feeds: GeneratedFeedsModel):
    pass

def run_generate_turn_metrics():
    pass

def mark_turn_as_done():
    pass

def simulate_turn():
    turn_inputs: TurnInputsModel = load_turn_inputs()
    feeds: GeneratedFeedsModel = generate_feeds()
    run_agent_actions(turn_inputs, feeds)
    run_generate_turn_metrics()
    mark_turn_as_done()
