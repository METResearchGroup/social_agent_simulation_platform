"""UUID4 string helpers for simulation_v2 persistence identifiers."""

from __future__ import annotations

import uuid


def new_run_id() -> str:
    return str(uuid.uuid4())


def new_turn_id() -> str:
    return str(uuid.uuid4())


def new_action_id() -> str:
    return str(uuid.uuid4())


def new_feed_id() -> str:
    return str(uuid.uuid4())


def new_generation_id() -> str:
    return str(uuid.uuid4())


def new_memory_diff_id() -> str:
    return str(uuid.uuid4())
