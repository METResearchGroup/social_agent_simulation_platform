"""Validators for action generators."""

from lib.validation_utils import validate_value_in_set

LIKE_ALGORITHMS: tuple[str, ...] = ("random_simple",)
FOLLOW_ALGORITHMS: tuple[str, ...] = ("random_simple",)
COMMENT_ALGORITHMS: tuple[str, ...] = ("random_simple",)

_ALGORITHMS_BY_ACTION: dict[str, tuple[str, ...]] = {
    "like": LIKE_ALGORITHMS,
    "follow": FOLLOW_ALGORITHMS,
    "comment": COMMENT_ALGORITHMS,
}


def validate_algorithm(action_type: str, algorithm: str) -> str:
    """Validate that algorithm is allowed for the given action type.

    Args:
        action_type: One of 'like', 'follow', 'comment'.
        algorithm: The algorithm name to validate.

    Returns:
        The algorithm unchanged.

    Raises:
        ValueError: When action_type is unknown or algorithm is not in the allowed set.
    """
    allowed: tuple[str, ...] | None = _ALGORITHMS_BY_ACTION.get(action_type)
    if allowed is None:
        raise ValueError(
            f"Unknown action_type: {action_type}. "
            f"Must be one of {tuple(_ALGORITHMS_BY_ACTION.keys())}."
        )
    return validate_value_in_set(
        algorithm,
        f"{action_type}_algorithm",
        allowed,
        allowed_display_name=str(allowed),
    )
