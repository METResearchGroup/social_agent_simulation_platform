import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


def record_runtime(func: Callable) -> Callable:
    """Log runtime in milliseconds for the wrapped function."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.debug("%s completed in %dms", func.__qualname__, elapsed_ms)

    return wrapper
