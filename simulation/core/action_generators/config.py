"""Load action generator configuration from config.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml

_CONFIG_PATH: Path = Path(__file__).resolve().parent / "config.yaml"
_cached: dict | None = None

_FALLBACK_ALGORITHM_BY_ACTION: dict[str, str] = {
    "like": "deterministic",
    "comment": "random_simple",
    "follow": "random_simple",
}


def _load() -> dict:
    """Load config.yaml; return empty dict if missing or invalid. Caches result."""
    global _cached
    if _cached is not None:
        return _cached
    if not _CONFIG_PATH.is_file():
        _cached = {}
        return _cached
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    _cached = raw if isinstance(raw, dict) else {}
    return _cached


def resolve_algorithm(action_type: str, algorithm: str | None) -> str:
    """Return the effective algorithm: explicit override or configured default.

    Resolution order:
    1. If algorithm is provided and non-empty, return it.
    2. Else read config[action_type]["default_algorithm"] from config.yaml.
    3. Else return fallback for action_type.

    Args:
        action_type: One of 'like', 'comment', 'follow'.
        algorithm: Explicit algorithm from caller, or None to use config/default.

    Returns:
        The algorithm name to use.
    """
    if algorithm is not None and algorithm != "":
        return algorithm
    config: dict = _load()
    action_config: dict = config.get(action_type, {}) or {}
    default: str | None = action_config.get("default_algorithm")
    if default is not None and default != "":
        return default
    return _FALLBACK_ALGORITHM_BY_ACTION.get(action_type, "random_simple")
