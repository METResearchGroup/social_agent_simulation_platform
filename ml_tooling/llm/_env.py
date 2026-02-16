"""Environment variable helpers for ml_tooling.llm."""

import os


def get_env_var(name: str, required: bool = False) -> str | None:
    """Return an environment variable value.

    Args:
        name: Environment variable name.
        required: If True, raise when the variable is missing or empty.
    """
    value = os.getenv(name)
    if required and not value:
        raise RuntimeError(f"Required environment variable '{name}' is not set.")
    return value
