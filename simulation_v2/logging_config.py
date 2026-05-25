"""Logging defaults for simulation v2 CLI entrypoints."""

from __future__ import annotations

import logging

_QUIET_LOGGERS = (
    "httpx",
    "httpcore",
    "opik",
    "opik.api_objects",
    "opik.message_processing",
    "opik.decorator",
    "opik.integrations",
)


def configure_simulation_logging(*, level: int = logging.INFO) -> None:
    """Configure console logging with reduced third-party noise."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )
    for logger_name in _QUIET_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
