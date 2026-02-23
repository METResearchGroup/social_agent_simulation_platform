"""Centralized environment variable loading.

This module exists to avoid import-time side effects spread across the codebase.
It encapsulates:
- Loading .env from repo root via python-dotenv
- Type-safe retrieval with optional required-flag

Public API: EnvVarsContainer.get_env_var(name, required=False)
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

ENV_VAR_TYPES: Final[dict[str, type[str]]] = {
    "OPENAI_API_KEY": str,
    "BLUESKY_HANDLE": str,
    "BLUESKY_PASSWORD": str,
    "OPIK_WORKSPACE": str,
}


class EnvVarsContainer:
    """Thread-safe singleton container for environment variables."""

    _instance: EnvVarsContainer | None = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._initialized = False
        self._env_vars: dict[str, str | None] = {}
        self._env_var_types: dict[str, type[str]] = ENV_VAR_TYPES
        self._init_lock = threading.Lock()

    @classmethod
    def get_env_var(cls, name: str, required: bool = False) -> str:
        """Get an environment variable after container initialization.

        Args:
            name: Environment variable name.
            required: If True, raises ValueError when missing or empty.

        Returns:
            Value (cast per _env_var_types) or default ("" when missing).
        """
        instance: EnvVarsContainer = cls._get_instance()
        raw: str | None = instance._env_vars.get(name)

        if required:
            if raw is None:
                raise ValueError(
                    f"{name} is required but is missing. "
                    f"Please set the {name} environment variable."
                )
            if isinstance(raw, str) and not raw.strip():
                raise ValueError(
                    f"{name} is required but is empty. "
                    f"Please set the {name} environment variable to a non-empty value."
                )

        if raw is None:
            return ""
        return str(raw)

    @classmethod
    def _get_instance(cls) -> EnvVarsContainer:
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        cls._instance._ensure_initialized()
        return cls._instance

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            self._initialize_env_vars()
            self._initialized = True

    def _initialize_env_vars(self) -> None:
        env_path: Path = (Path(__file__).resolve().parent / ".." / ".env").resolve()
        load_dotenv(env_path)
        for key in self._env_var_types:
            self._env_vars[key] = os.getenv(key)
