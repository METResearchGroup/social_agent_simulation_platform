"""Validators for action generators."""

from lib.validation_utils import validate_value_in_set

BEHAVIOR_MODE_DETERMINISTIC: str = "deterministic"
BEHAVIOR_MODES: tuple[str, ...] = (BEHAVIOR_MODE_DETERMINISTIC,)
DEFAULT_BEHAVIOR_MODE: str = BEHAVIOR_MODE_DETERMINISTIC


def validate_behavior_mode(mode: str) -> str:
    """Validate that mode is a known behavior mode."""
    return validate_value_in_set(
        mode,
        "behavior_mode",
        BEHAVIOR_MODES,
        allowed_display_name=str(BEHAVIOR_MODES),
    )
