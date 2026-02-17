"""Validators for action generators."""

BEHAVIOR_MODE_DETERMINISTIC: str = "deterministic"
BEHAVIOR_MODES: tuple[str, ...] = (BEHAVIOR_MODE_DETERMINISTIC,)
DEFAULT_BEHAVIOR_MODE: str = BEHAVIOR_MODE_DETERMINISTIC


def validate_behavior_mode(mode: str) -> str:
    """Validate that mode is a known behavior mode."""
    if mode not in BEHAVIOR_MODES:
        raise ValueError(
            f"Unknown behavior mode: {mode}. Expected one of {BEHAVIOR_MODES}"
        )
    return mode
