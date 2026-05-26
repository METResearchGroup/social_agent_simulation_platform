"""Worker-specific errors."""

from __future__ import annotations


class RunNotRetryableError(Exception):
    """Raised when a run cannot be retried (e.g. failed status in PR 4)."""

    def __init__(self, run_id: str, status: str) -> None:
        self.run_id = run_id
        self.status = status
        super().__init__(f"Run {run_id!r} with status {status!r} is not retryable")
