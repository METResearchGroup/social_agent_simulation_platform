from simulation_v2.models.turn import TurnInputsModel
from simulation_v2.simulate_turn import simulate_turn


def simulate_run(turn_inputs: TurnInputsModel) -> None:
    for i in range(turn_inputs.total_turns):
        simulate_turn(turn_inputs)
        print(f"Finished with turn {i + 1}/{turn_inputs.total_turns}")
