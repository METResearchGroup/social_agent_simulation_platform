"""Unit tests for retry logic."""

import pytest
from pydantic import BaseModel, Field, ValidationError

from ml_tooling.llm.exceptions import (
    LLMAuthError,
    LLMInvalidRequestError,
    LLMPermissionDeniedError,
    LLMTransientError,
)
from ml_tooling.llm.retry import _should_retry, retry_llm_completion


class _TestModel(BaseModel):
    """Simple test model for ValidationError testing."""

    value: str = Field(description="A test value")


class TestShouldRetry:
    """Tests for _should_retry function."""

    @pytest.mark.parametrize(
        "exception",
        [
            LLMAuthError("Authentication failed"),
            LLMInvalidRequestError("Invalid request"),
            LLMPermissionDeniedError("Permission denied"),
        ],
    )
    def test_should_retry_returns_false_for_non_retryable_exceptions(self, exception):
        """Test that non-retryable exceptions (auth/invalid request) return False."""
        result = _should_retry(exception)
        assert result is False

    @pytest.mark.parametrize(
        "exception",
        [
            LLMTransientError("Rate limit exceeded"),
            LLMTransientError("Service unavailable"),
            ValueError("Test error"),
            AttributeError("Test error"),
            Exception("Test error"),
        ],
    )
    def test_should_retry_returns_true_for_retryable_exceptions(self, exception):
        """Test that retryable exceptions (transient errors, non-LLM exceptions) return True."""
        result = _should_retry(exception)
        assert result is True

    def test_should_retry_returns_true_for_validation_error(self):
        """Test that ValidationError is retryable (non-LLM exception)."""
        try:
            _TestModel.model_validate({})  # This will raise ValidationError
        except ValidationError as e:
            exception = e
        result = _should_retry(exception)
        assert result is True


class TestRetryLlmCompletion:
    """Tests for retry_llm_completion decorator."""

    def test_retry_llm_completion_succeeds_on_first_attempt(self):
        """Test that decorated function succeeds on first attempt without retrying."""
        call_count = 0

        @retry_llm_completion(max_retries=3, initial_delay=0.01, max_delay=0.1)
        def test_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = test_function()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.parametrize(
        "exception",
        [
            LLMTransientError("Rate limit exceeded"),
            LLMTransientError("Service unavailable"),
            ValueError("Test error"),
        ],
    )
    def test_retry_llm_completion_retries_then_succeeds(self, exception):
        """Test that decorated function retries on retryable errors and then succeeds."""
        call_count = 0

        @retry_llm_completion(max_retries=2, initial_delay=0.01, max_delay=0.1)
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # Fail twice, succeed on third attempt
                raise exception
            return "success"

        result = test_function()
        assert result == "success"
        assert call_count == 3

    def test_retry_llm_completion_retries_on_validation_error(self):
        """Test that ValidationError is retried (new behavior - retries on validation failures)."""
        call_count = 0

        @retry_llm_completion(max_retries=2, initial_delay=0.01, max_delay=0.1)
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                # Create a ValidationError by trying to validate invalid data
                try:
                    _TestModel.model_validate({})
                except ValidationError as e:
                    raise e
            return "success"

        result = test_function()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.parametrize(
        "exception",
        [
            LLMAuthError("Authentication failed"),
            LLMInvalidRequestError("Invalid request"),
            LLMPermissionDeniedError("Permission denied"),
        ],
    )
    def test_retry_llm_completion_does_not_retry_on_non_retryable_errors(self, exception):
        """Test that decorated function does not retry on non-retryable errors."""
        call_count = 0

        @retry_llm_completion(max_retries=3, initial_delay=0.01, max_delay=0.1)
        def test_function():
            nonlocal call_count
            call_count += 1
            raise exception

        with pytest.raises(type(exception)):
            test_function()
        assert call_count == 1  # Only initial attempt, no retries

    def test_retry_llm_completion_respects_max_retries(self):
        """Test that decorated function respects max_retries and eventually raises."""
        call_count = 0
        exception_instance = LLMTransientError("Rate limit exceeded")

        @retry_llm_completion(max_retries=1, initial_delay=0.01, max_delay=0.1)
        def test_function():
            nonlocal call_count
            call_count += 1
            raise exception_instance

        with pytest.raises(LLMTransientError):
            test_function()
        assert call_count == 2  # 1 initial + 1 retry

    def test_retry_llm_completion_retries_on_value_error(self):
        """Test that ValueError is retried (new behavior - retries on missing content, etc.)."""
        call_count = 0

        @retry_llm_completion(max_retries=2, initial_delay=0.01, max_delay=0.1)
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Response content is None")
            return "success"

        result = test_function()
        assert result == "success"
        assert call_count == 2
