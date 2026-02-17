"""Shared validation helpers."""

from typing import Any, overload


@overload
def validate_nonnegative_value(
    v: int, field_name: str, *, ok_equals_zero: bool = True
) -> int: ...
@overload
def validate_nonnegative_value(
    v: float, field_name: str, *, ok_equals_zero: bool = True
) -> float: ...
def validate_nonnegative_value(
    v: int | float,
    field_name: str,
    *,
    ok_equals_zero: bool = True,
) -> int | float:
    """Validate that a numeric value is non-negative (and optionally strictly positive).

    Args:
        v: The value to validate.
        field_name: Name of the field (for error messages).
        ok_equals_zero: If True, allow zero (invalid only when v < 0).
            If False, require strictly positive (invalid when v <= 0).

    Returns:
        The value unchanged.

    Raises:
        ValueError: When v < 0 if ok_equals_zero else when v <= 0.
    """
    if ok_equals_zero:
        if v < 0:
            raise ValueError(f"{field_name} must be >= 0")
    else:
        if v <= 0:
            raise ValueError(f"{field_name} must be greater than 0")
    return v


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
