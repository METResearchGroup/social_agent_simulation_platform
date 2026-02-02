"""Load database configuration from db/config.yaml and expose via Config.get_config."""

from __future__ import annotations

import os
from pathlib import Path

import yaml


def _config_path() -> Path:
    """Path to db/config.yaml (next to this module)."""
    return Path(__file__).resolve().parent / "config.yaml"


def _load_raw() -> dict:
    """Load config.yaml; return empty dict if missing or invalid."""
    path = _config_path()
    if not path.is_file():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


class Config:
    """Database configuration from config.yaml with optional env override.

    Use get_config(name) to read a value. Environment variables override
    the YAML file when set (e.g. SIM_DB_PATH, SIM_DATABASE_URL).
    """

    _raw: dict

    def __init__(self) -> None:
        self._raw = _load_raw()

    def get_config(self, name: str) -> str | None:
        """Return the value for the given config name.

        If an environment variable with the same name is set, its value
        is returned. Otherwise the value from config.yaml is returned.
        Missing or unset values return None.

        Args:
            name: Config key, e.g. "SIM_DB_PATH", "SIM_DATABASE_URL".

        Returns:
            The configured value or None.
        """
        env_val = os.environ.get(name)
        if env_val is not None and env_val != "":
            return env_val
        val = self._raw.get(name)
        return str(val) if val is not None else None
