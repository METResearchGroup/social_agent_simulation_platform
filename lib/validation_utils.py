"""Shared validation helpers."""

from typing import Any, Iterable, TypeVar, overload

T = TypeVar("T")


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


def validate_not_none(obj: T | None, field_name: str) -> T:
    """Validate that a value is not None.

    Args:
        obj: The value to validate.
        field_name: Name of the field (for error messages).

    Returns:
        The value unchanged.

    Raises:
        ValueError: When obj is None.
    """
    if obj is None:
        raise ValueError(f"{field_name} cannot be None")
    return obj


def validate_non_empty_mapping(mapping: Any, field_name: str) -> Any:
    """Validate that a mapping (e.g. dict) is not None and not empty.

    Args:
        mapping: The mapping to validate (must support truthiness / len).
        field_name: Name of the field (for error messages).

    Returns:
        The value unchanged.

    Raises:
        ValueError: When mapping is None or empty.
    """
    if mapping is None:
        raise ValueError(f"{field_name} cannot be None")
    if not mapping:
        raise ValueError(f"{field_name} cannot be empty")
    return mapping


def validate_non_empty_iterable(iterable: Iterable[T], field_name: str) -> Iterable[T]:
    """Validate that an iterable is not None and not empty.

    Prefer passing a Collection (list, set, etc.) so the check does not consume
    iterators. For iterators, the check uses truthiness (empty iterator is falsy).

    Args:
        iterable: The iterable to validate.
        field_name: Name of the field (for error messages).

    Returns:
        The value unchanged.

    Raises:
        ValueError: When iterable is None or empty.
    """
    if iterable is None:
        raise ValueError(f"{field_name} cannot be None")
    if not iterable:
        raise ValueError(f"{field_name} cannot be empty")
    return iterable


def validate_value_in_set(
    value: T,
    field_name: str,
    allowed: Iterable[T],
    *,
    allowed_display_name: str | None = None,
) -> T:
    """Validate that a value is in an allowed set.

    Args:
        value: The value to validate.
        field_name: Name of the field (for error messages).
        allowed: Allowed values (e.g. set, list, or dict keys for membership).
        allowed_display_name: Optional description for allowed (e.g. 'allowed algorithms').

    Returns:
        The value unchanged.

    Raises:
        ValueError: When value not in allowed.
    """
    if value not in allowed:
        hint = (
            allowed_display_name if allowed_display_name is not None else list(allowed)
        )
        raise ValueError(f"{field_name} must be one of: {hint}")
    return value


def validate_turn_number(turn_number: int | None) -> None:
    """Validate that turn_number is a non-negative integer.

    Raises:
        ValueError: If turn_number is None or negative.
    """
    if turn_number is None:
        raise ValueError("turn_number is invalid")
    validate_nonnegative_value(turn_number, "turn_number")


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
