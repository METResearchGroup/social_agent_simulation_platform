"""Shared validation helpers for Pydantic models."""

from typing import Any


def validate_turn_number(turn_number: int) -> None:
    """Validate that turn_number is a non-negative integer.

    Raises:
        ValueError: If turn_number is None or negative.
    """
    if turn_number is None or turn_number < 0:
        raise ValueError("turn_number is invalid")


def validate_non_empty_string(v: Any, field_name: str) -> str:
    """Validate that a string field is non-empty after stripping.

    This function is intended to be called from Pydantic field_validators
    after type coercion has occurred, so v should already be a str.
    However, we include defensive None and type checking for robustness.

    Args:
        v: The value to validate (expected to be str after Pydantic coercion,
           but defensively handles None and non-str types)
        field_name: The name of the field being validated (for error messages)

    Returns:
        The stripped string value

    Raises:
        ValueError: If the value is None, not a string, or empty after stripping
    """
    if v is None:
        raise ValueError(f"{field_name} cannot be None")
    if not isinstance(v, str):
        raise ValueError(f"{field_name} must be a string")
    v = v.strip()
    if not v:
        raise ValueError(f"{field_name} cannot be empty")
    return v
