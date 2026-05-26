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


def new_user_id() -> str:
    return str(uuid.uuid4())


def new_post_id() -> str:
    return str(uuid.uuid4())


def new_like_id() -> str:
    return str(uuid.uuid4())


def new_comment_id() -> str:
    return str(uuid.uuid4())


def new_follow_id() -> str:
    return str(uuid.uuid4())


def new_llm_proposed_action_id() -> str:
    return str(uuid.uuid4())


def new_eval_run_id() -> str:
    return str(uuid.uuid4())


def new_eval_metric_id() -> str:
    return str(uuid.uuid4())
