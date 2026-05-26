"""Progress and opt-out helpers for simulation_v2 CLI runs."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Sized
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from typing import ParamSpec, TypeVar

from tqdm import tqdm

P = ParamSpec("P")
R = TypeVar("R")

BAR_FORMAT = "{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"

_progress_enabled: ContextVar[bool] = ContextVar(
    "simulation_v2_progress_enabled",
    default=True,
)


def progress_enabled() -> bool:
    return _progress_enabled.get()


def iteration_log_level() -> int:
    """Per-item logs use DEBUG when progress bars are shown, else INFO."""
    return logging.DEBUG if progress_enabled() else logging.INFO


def progress_items(
    items: Iterable[R],
    *,
    desc: str,
    unit: str = "it",
    leave: bool = True,
    total: int | None = None,
) -> Iterable[R]:
    if not progress_enabled():
        return items
    resolved_total = total
    if resolved_total is None and isinstance(items, Sized):
        resolved_total = len(items)
    if resolved_total == 0:
        return items
    return tqdm(
        items,
        desc=desc,
        unit=unit,
        total=resolved_total,
        leave=leave,
        bar_format=BAR_FORMAT,
    )


@contextmanager
def no_progress():
    token = _progress_enabled.set(False)
    try:
        yield
    finally:
        _progress_enabled.reset(token)


def no_progress_decorator(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        with no_progress():
            return func(*args, **kwargs)

    return wrapper
