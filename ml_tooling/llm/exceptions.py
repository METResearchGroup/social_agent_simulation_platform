"""Internal exception abstraction for LLM operations.

This module provides an abstraction layer over provider-specific exceptions
(e.g., LiteLLM) to decouple retry logic and tests from provider internals.
"""

from enum import Enum

# Import LiteLLM exceptions only when needed for standardization
# This keeps the coupling localized to this function
try:
    import litellm.exceptions as litellm_exceptions  # type: ignore[import-untyped]
except ImportError:
    litellm_exceptions = None  # type: ignore[assignment]


class ExceptionCategory(Enum):
    """Categorization of exceptions for retry decision logic."""

    AUTH_ERROR = "auth_error"
    INVALID_REQUEST = "invalid_request"
    TRANSIENT = "transient"
    UNRECOVERABLE = "unrecoverable"


class LLMException(Exception):
    """Base exception for all LLM-related errors.

    All LLM exceptions have a category that determines retry behavior,
    and preserve the original exception for debugging via exception chaining.
    """

    category: ExceptionCategory
    original_exception: Exception | None = None

    def __init__(
        self, message: str, original_exception: Exception | None = None
    ) -> None:
        """Initialize LLM exception.

        Args:
            message: Human-readable error message
            original_exception: The original exception from the provider (e.g., LiteLLM)
                This will be chained via __cause__ for debugging
        """
        super().__init__(message)
        self.original_exception = original_exception
        if original_exception is not None:
            self.__cause__ = original_exception


class LLMAuthError(LLMException):
    """Authentication/authorization error - should not be retried."""

    category = ExceptionCategory.AUTH_ERROR


class LLMInvalidRequestError(LLMException):
    """Invalid request error (bad parameters, schema violations) - should not be retried."""

    category = ExceptionCategory.INVALID_REQUEST


class LLMPermissionDeniedError(LLMException):
    """Permission denied error - should not be retried."""

    category = (
        ExceptionCategory.AUTH_ERROR
    )  # Treated same as auth error for retry logic


class LLMTransientError(LLMException):
    """Transient error (rate limits, timeouts, service unavailable) - should be retried."""

    category = ExceptionCategory.TRANSIENT


class LLMUnrecoverableError(LLMException):
    """Unrecoverable error - should not be retried."""

    category = ExceptionCategory.UNRECOVERABLE


def standardize_litellm_exception(exception: Exception) -> LLMException:
    """Standardize LiteLLM exceptions to internal exception types.

    This function serves as the boundary between provider-specific exceptions
    (LiteLLM) and our internal exception abstraction, allowing retry logic
    to be decoupled from provider internals.

    Args:
        exception: The LiteLLM exception that was raised

    Returns:
        Internal LLMException with appropriate category

    Note:
        The original exception is preserved via exception chaining (__cause__)
        for debugging purposes while maintaining clean retry logic.
    """
    if litellm_exceptions is None:
        # Fallback if LiteLLM is not available - treat as transient
        return LLMTransientError(
            f"LiteLLM exception (LiteLLM not available): {exception}",
            original_exception=exception,
        )

    # Extract error message from exception
    message = getattr(exception, "message", str(exception))
    if not message:
        message = f"{type(exception).__name__}: {exception}"

    # Standardize LiteLLM exception types to internal types
    # Non-retryable exceptions (auth/validation errors)
    if isinstance(exception, litellm_exceptions.AuthenticationError):  # type: ignore[attr-defined]
        return LLMAuthError(message, original_exception=exception)
    elif isinstance(exception, litellm_exceptions.PermissionDeniedError):  # type: ignore[attr-defined]
        return LLMPermissionDeniedError(message, original_exception=exception)
    elif isinstance(exception, litellm_exceptions.InvalidRequestError):  # type: ignore[attr-defined]
        # InvalidRequestError is deprecated in favor of BadRequestError, but we handle both
        return LLMInvalidRequestError(message, original_exception=exception)
    elif hasattr(litellm_exceptions, "BadRequestError") and isinstance(
        exception,
        litellm_exceptions.BadRequestError,  # type: ignore[attr-defined]
    ):
        # Handle BadRequestError (replacement for InvalidRequestError in newer LiteLLM versions)
        return LLMInvalidRequestError(message, original_exception=exception)
    # Retryable exceptions (transient errors)
    elif isinstance(
        exception,
        (
            litellm_exceptions.RateLimitError,  # type: ignore[attr-defined]
            litellm_exceptions.Timeout,  # type: ignore[attr-defined]
            litellm_exceptions.ServiceUnavailableError,  # type: ignore[attr-defined]
        ),
    ):
        return LLMTransientError(message, original_exception=exception)
    # APIError - check status code to determine if transient
    elif isinstance(exception, litellm_exceptions.APIError):  # type: ignore[attr-defined]
        status_code = getattr(exception, "status_code", None)
        # 4xx errors (except auth which is handled above) are usually not retryable
        # 5xx errors are transient
        if status_code and 500 <= status_code < 600:
            return LLMTransientError(message, original_exception=exception)
        else:
            # Treat unknown API errors as invalid requests (non-retryable)
            return LLMInvalidRequestError(message, original_exception=exception)
    else:
        # Unknown LiteLLM exception - treat as transient to allow retry
        # This is safer than failing hard on unknown errors
        return LLMTransientError(
            f"Unknown LiteLLM error: {message}", original_exception=exception
        )
