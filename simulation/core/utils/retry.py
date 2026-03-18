from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def retry_with_exponential_backoff(
    *,
    operation: Callable[[], T],
    retry_on: type[BaseException] | tuple[type[BaseException], ...],
    max_attempts: int,
    backoff_base: float,
    sleeper: Callable[[float], None],
) -> T:
    """
    Retry `operation` up to `max_attempts` using exponential backoff.

    The sleeper is injected so tests can run without real time delays.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    last_exc: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            return operation()
        except retry_on as e:
            last_exc = e
            if attempt >= max_attempts - 1:
                raise

            # Mirror existing behavior: sleep uses backoff_base**attempt.
            delay_s = backoff_base**attempt
            sleeper(delay_s)

    # Defensive: the loop always returns or raises.
    assert last_exc is not None
    raise last_exc
