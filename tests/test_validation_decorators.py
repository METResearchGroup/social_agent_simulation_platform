import inspect

import pytest

from lib.validation_decorators import validate_inputs
from simulation.core.utils.validators import validate_run_id, validate_turn_number


def test_validate_inputs_rebinds_normalized_values() -> None:
    @validate_inputs((validate_run_id, "run_id"))
    def echo_run_id(*, run_id: str) -> str:
        return run_id

    assert echo_run_id(run_id="  run_123  ") == "run_123"


def test_validate_inputs_raises_on_invalid_values() -> None:
    @validate_inputs((validate_turn_number, "turn_number"))
    def echo_turn_number(*, turn_number: int) -> int:
        return turn_number

    with pytest.raises(ValueError, match="turn_number must be >= 0"):
        echo_turn_number(turn_number=-1)


def test_validate_inputs_supports_cross_field_validation() -> None:
    def validate_turn_in_bounds(turn_number: int, max_turns: int) -> None:
        if turn_number >= max_turns:
            raise ValueError("turn_number out of bounds")

    @validate_inputs((validate_turn_in_bounds, ("turn_number", "max_turns")))
    def f(*, turn_number: int, max_turns: int) -> tuple[int, int]:
        return (turn_number, max_turns)

    with pytest.raises(ValueError, match="out of bounds"):
        f(turn_number=3, max_turns=3)


def test_validate_inputs_preserves_signature() -> None:
    def original(*, run_id: str, turn_number: int = 0) -> tuple[str, int]:
        return (run_id, turn_number)

    wrapped = validate_inputs(
        (validate_run_id, "run_id"),
        (validate_turn_number, "turn_number"),
    )(original)

    assert inspect.signature(wrapped) == inspect.signature(original)
