"""Shared decorators for timing and observability."""

import asyncio
import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

logger = logging.getLogger(__name__)

# Scale factor for converting seconds to milliseconds (used for elapsed_ms).
SECONDS_TO_MS: float = 1000.0

P = ParamSpec("P")
R = TypeVar("R")


def timed(
    *,
    log_level: int | None = logging.DEBUG,
    attach_attr: str | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Record elapsed time for sync or async callables.

    Inputs: optional keyword-only log_level (default DEBUG; None to disable
    logging) and attach_attr (name of attribute to set with duration in ms
    on the first argument, or its .state if present). Output: a decorator that
    wraps the callable and runs timing/attach in a finally block after the
    call returns. Exceptions from the wrapped call are not caught. Attaching
    to the first argument is best-effort: attribute access/set errors are
    caught, logged, and suppressed so they never mask the wrapped call's
    exception.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                start = time.perf_counter()
                try:
                    return await func(*args, **kwargs)
                finally:
                    _after_call(
                        func=func,
                        start=start,
                        log_level=log_level,
                        attach_attr=attach_attr,
                        first_arg=args[0] if args else None,
                    )

            return async_wrapper  # type: ignore[return-value]

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                _after_call(
                    func=func,
                    start=start,
                    log_level=log_level,
                    attach_attr=attach_attr,
                    first_arg=args[0] if args else None,
                )

        return sync_wrapper  # type: ignore[return-value]

    return decorator


def _after_call(
    *,
    func: Callable[..., Any],
    start: float,
    log_level: int | None,
    attach_attr: str | None,
    first_arg: Any,
) -> None:
    """Log elapsed time and optionally attach duration to the first argument.

    Inputs: func (for qualname and log message), start time, optional
    log_level and attach_attr, and first_arg (the first positional argument
    of the wrapped call). Output: none. Logs at log_level when set; then, when
    attach_attr and first_arg are set, writes elapsed_ms onto first_arg.state
    (or first_arg if no .state). Attribute get/set is best-effort: any
    exception from getattr/hasattr/setattr is caught, logged with
    attach_attr and func.__qualname__, and suppressed so it never masks the
    wrapped function's exception.
    """
    elapsed_ms = int((time.perf_counter() - start) * SECONDS_TO_MS)
    if log_level is not None:
        logger.log(log_level, "%s completed in %dms", func.__qualname__, elapsed_ms)
    if attach_attr and first_arg is not None:
        try:
            target = getattr(first_arg, "state", first_arg)
            if hasattr(target, "__setattr__"):
                setattr(target, attach_attr, elapsed_ms)
        except Exception as e:
            logger.warning(
                "timed: failed to attach %s for %s: %s",
                attach_attr,
                func.__qualname__,
                e,
                exc_info=False,
            )
