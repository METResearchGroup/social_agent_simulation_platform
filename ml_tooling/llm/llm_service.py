"""Service for interacting with LLM providers via LiteLLM."""

import threading
from typing import Any, TypeVar

import litellm
from litellm import ModelResponse, batch_completion
from pydantic import BaseModel

from ml_tooling.llm.config.model_registry import ModelConfigRegistry
from ml_tooling.llm.exceptions import (
    standardize_litellm_exception,
)
from ml_tooling.llm.providers.base import LLMProviderProtocol
from ml_tooling.llm.providers.registry import LLMProviderRegistry
from ml_tooling.llm.retry import retry_llm_completion

T = TypeVar("T", bound=BaseModel)


class LLMService:
    """LLM service for making API requests via LiteLLM."""

    def __init__(self, verbose: bool = False):
        """Initialize the LLM service.

        Args:
            verbose: If False (default), suppresses LiteLLM info and debug logs.
                    If True, does not suppress LiteLLM logs (uses LiteLLM defaults).

        Note: Providers are initialized lazily when first used to avoid
        requiring API keys for all providers when only one is needed.
        """
        if not verbose:
            self._suppress_litellm_logging()

    def _suppress_litellm_logging(self) -> None:
        """Configure logging to suppress LiteLLM info and debug logs.

        See https://github.com/BerriAI/litellm/issues/6813
        """
        import logging

        logging.getLogger("LiteLLM").setLevel(logging.WARNING)

    def _get_provider_for_model(self, model: str) -> LLMProviderProtocol:
        """Get the provider instance for a given model.

        Args:
            model: Model identifier (e.g., 'gpt-4o-mini', 'groq/llama3-8b-8192')

        Returns:
            Provider instance that supports the given model

        Raises:
            ValueError: If no provider supports the given model
        """
        provider = LLMProviderRegistry.get_provider(model)
        # Lazy initialization: only initialize the provider when it's actually used
        if not getattr(provider, "_initialized", False):
            provider.initialize()
        return provider

    def _prepare_completion_kwargs(
        self,
        model: str,
        provider: LLMProviderProtocol,
        response_format: type[BaseModel] | None = None,
        **kwargs,
    ) -> tuple[dict, dict[str, Any] | None]:
        """Extract shared logic for preparing completion kwargs.

        Used by both single and batch completion methods to avoid duplication.
        Handles model config resolution, response format formatting, and kwargs
        preparation via provider.

        Args:
            model: Model identifier to use
            provider: Provider instance for this model
            response_format: Pydantic model class for structured outputs
            **kwargs: Additional parameters to pass to the API (temperature, max_tokens, etc.)
                These override any default kwargs from the model configuration.

        Returns:
            Tuple of (completion_kwargs dict, response_format_dict or None)
        """
        # Get model configuration from registry
        try:
            model_config_obj = ModelConfigRegistry.get_model_config(model)
            # Convert ModelConfig to dict format expected by providers
            model_config_dict = {
                "kwargs": model_config_obj.get_all_llm_inference_kwargs()
            }
        except (ValueError, FileNotFoundError):
            # Model not in config - use empty config dict
            model_config_dict = {"kwargs": {}}

        # Format structured output if needed (delegates to provider)
        response_format_dict = None
        if response_format is not None:
            response_format_dict = provider.format_structured_output(
                response_format, model_config_dict
            )

        # Prepare completion kwargs using provider-specific logic
        # Note: messages is passed as placeholder empty list here, will be set by caller
        completion_kwargs = provider.prepare_completion_kwargs(
            model=model,
            messages=[],  # Placeholder, will be set by caller
            response_format=response_format_dict,
            model_config=model_config_dict,
            **kwargs,  # User kwargs override config kwargs
        )

        return completion_kwargs, response_format_dict

    def _chat_completion(
        self,
        messages: list[dict],
        model: str,
        provider: LLMProviderProtocol,
        response_format: type[BaseModel] | None = None,
        **kwargs,
    ) -> ModelResponse:
        """
        Create a chat completion request using the specified provider.

        This is an internal method that delegates provider-specific logic
        (structured output formatting, kwargs preparation) to the provider.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Model identifier to use
            provider: Provider instance for this model
            response_format: Pydantic model class for structured outputs
            **kwargs: Additional parameters to pass to the API (temperature, max_tokens, etc.)
                These override any default kwargs from the model configuration.

        Returns:
            The chat completion response from litellm

        Raises:
            LLMException: Standardized internal exception (LiteLLM exceptions are converted)
        """
        completion_kwargs, _ = self._prepare_completion_kwargs(
            model=model,
            provider=provider,
            response_format=response_format,
            **kwargs,
        )
        completion_kwargs["messages"] = messages
        # Avoid global LiteLLM state; use the provider instance's key per request.
        completion_kwargs["api_key"] = provider.api_key

        try:
            result = litellm.completion(**completion_kwargs)  # type: ignore
        except Exception as e:
            # Standardize LiteLLM exceptions to internal exception types at the boundary
            # This decouples retry logic from provider-specific exception types
            raise standardize_litellm_exception(e) from e

        # Coerce to ModelResponse for type safety
        # LiteLLM can return either ModelResponse or a CustomStreamWrapper;
        # our use case isn't stream-based. This is to satisfy pyright.
        return (
            result
            if isinstance(result, ModelResponse)
            else ModelResponse(**result.__dict__)  # type: ignore
        )

    def _batch_completion(
        self,
        messages_list: list[list[dict]],
        model: str,
        provider: LLMProviderProtocol,
        response_format: type[BaseModel] | None = None,
        **kwargs,
    ) -> list[ModelResponse]:
        """
        Create batch completion requests using the specified provider.

        This is an internal method that delegates provider-specific logic
        (structured output formatting, kwargs preparation) to the provider.

        Args:
            messages_list: List of message lists, where each inner list is one request
                with 'role' and 'content' keys
            model: Model identifier to use
            provider: Provider instance for this model
            response_format: Pydantic model class for structured outputs
            **kwargs: Additional parameters to pass to the API (temperature, max_tokens, etc.)
                These override any default kwargs from the model configuration.

        Returns:
            List of ModelResponse objects from litellm

        Raises:
            LLMException: Standardized internal exception (LiteLLM exceptions are converted)
            TODO: Consider supporting partial results for batch completions instead of
                all-or-nothing error handling.
        """
        completion_kwargs, _ = self._prepare_completion_kwargs(
            model=model,
            provider=provider,
            response_format=response_format,
            **kwargs,
        )

        # Remove placeholder messages from kwargs since batch_completion takes it separately
        completion_kwargs.pop("messages", None)
        completion_kwargs["messages"] = messages_list
        # Avoid global LiteLLM state; use the provider instance's key per request.
        completion_kwargs["api_key"] = provider.api_key

        try:
            results: list[ModelResponse] = batch_completion(**completion_kwargs)  # type: ignore
        except Exception as e:
            # Standardize LiteLLM exceptions to internal exception types at the boundary
            # This decouples retry logic from provider-specific exception types
            raise standardize_litellm_exception(e) from e

        # Coerce each result to ModelResponse for type safety
        # LiteLLM batch_completion may return dict-like objects
        coerced_results = []
        for result in results:
            coerced_result = (
                result
                if isinstance(result, ModelResponse)
                else ModelResponse(**result.__dict__)  # type: ignore
            )
            coerced_results.append(coerced_result)

        return coerced_results

    @retry_llm_completion(max_retries=3, initial_delay=1.0, max_delay=60.0)
    def _complete_and_validate_structured(
        self,
        messages: list[dict],
        model: str,
        provider: LLMProviderProtocol,
        response_format: type[T],
        **kwargs,
    ) -> T:
        """Execute chat completion and validate/parse the response.

        This method combines the HTTP call and response validation into a single
        retryable operation. Any failure (HTTP error, missing content, invalid schema)
        will trigger a retry, EXCEPT for non-retryable errors like authentication
        failures which fail hard immediately.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Model identifier to use
            provider: Provider instance for this model
            response_format: Pydantic model class for structured outputs (required)
            **kwargs: Additional parameters to pass to the API

        Returns:
            Validated Pydantic model instance

        Raises:
            LLMAuthError, LLMInvalidRequestError, LLMPermissionDeniedError:
                These exceptions are NOT retried and fail hard immediately.
            ValueError: If response content is None (will be retried)
            ValidationError: If schema validation fails (will be retried)
            LLMException: Any other LLM exception will trigger retry, then be re-raised
                after all retries are exhausted.
        """
        # Step 1: Make the HTTP call
        response = self._chat_completion(
            messages=messages,
            model=model,
            provider=provider,
            response_format=response_format,
            **kwargs,
        )

        # Step 2: Validate and parse the response
        return self.handle_completion_response(response, response_format)

    @retry_llm_completion(max_retries=3, initial_delay=1.0, max_delay=60.0)
    def _complete_and_validate_structured_batch(
        self,
        messages_list: list[list[dict]],
        model: str,
        provider: LLMProviderProtocol,
        response_format: type[T],
        **kwargs,
    ) -> list[T]:
        """Execute batch completion and validate/parse all responses.

        This method combines the batch HTTP call and response validation into a single
        retryable operation. Any failure (HTTP error, missing content, invalid schema)
        will trigger a retry, EXCEPT for non-retryable errors like authentication
        failures which fail hard immediately.

        Args:
            messages_list: List of message lists, where each inner list is one request
            model: Model identifier to use
            provider: Provider instance for this model
            response_format: Pydantic model class for structured outputs (required)
            **kwargs: Additional parameters to pass to the API

        Returns:
            List of validated Pydantic model instances

        Raises:
            LLMAuthError, LLMInvalidRequestError, LLMPermissionDeniedError:
                These exceptions are NOT retried and fail hard immediately.
            ValueError: If any response content is None (will be retried)
            ValidationError: If any schema validation fails (will be retried)
            LLMException: Any other LLM exception will trigger retry, then be re-raised
                after all retries are exhausted.
        """
        # Step 1: Make the batch HTTP call
        responses = self._batch_completion(
            messages_list=messages_list,
            model=model,
            provider=provider,
            response_format=response_format,
            **kwargs,
        )

        # Step 2: Validate and parse all responses
        return self.handle_batch_completion_responses(responses, response_format)

    def structured_completion(
        self,
        messages: list[dict],
        response_model: type[T],
        model: str | None = None,
        **kwargs,
    ) -> T:
        """
        Create a chat completion request and return the result as a Pydantic model.

        This is the main public API for structured completions. It orchestrates:
        1. Determining the correct provider for the model
        2. Executing completion with validation and retry logic

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            response_model: Pydantic model class to parse the response into
            model: Model to use (default: from config, falls back to gpt-4o-mini-2024-07-18)
            **kwargs: Additional parameters to pass to the API (temperature, max_tokens, etc.)
                These override any default kwargs from the model configuration.

        Returns:
            An instance of the specified Pydantic model parsed from the response

        Raises:
            ValueError: If the model is not supported by any provider, or if the response
                content is missing or invalid (after all retries)
            ValidationError: If the response cannot be parsed into the Pydantic model
                (after all retries)
        """
        # Step 1: Determine model (use default from config if not provided)
        if model is None:
            model = ModelConfigRegistry.get_default_model()

        # Step 2: Get provider for this model
        provider = self._get_provider_for_model(model)

        # Step 3: Execute with retry and validation
        return self._complete_and_validate_structured(
            messages=messages,
            model=model,
            provider=provider,
            response_format=response_model,
            **kwargs,
        )

    def handle_completion_response(
        self,
        response: ModelResponse,
        response_model: type[T],
    ) -> T:
        """Handles the completion response."""
        content: str | None = response.choices[0].message.content  # type: ignore
        if content is None:
            raise ValueError(
                "Response content is None. Expected structured output from LLM."
            )
        return response_model.model_validate_json(content)

    def handle_batch_completion_responses(
        self,
        responses: list[ModelResponse],
        response_model: type[T],
    ) -> list[T]:
        """Handles batch completion responses.

        Works the same as handle_completion_response but takes a list of responses.

        Args:
            responses: List of ModelResponse objects from batch completion
            response_model: Pydantic model class to parse responses into

        Returns:
            List of Pydantic model instances parsed from responses

        Raises:
            ValueError: If any response content is None
            ValidationError: If any response cannot be parsed into the Pydantic model
        """
        contents = []
        for response in responses:
            content: str | None = response.choices[0].message.content  # type: ignore
            if content is None:
                raise ValueError(
                    "Response content is None. Expected structured output from LLM."
                )
            contents.append(content)

        return [response_model.model_validate_json(content) for content in contents]

    def structured_batch_completion(
        self,
        prompts: list[str],
        response_model: type[T],
        model: str | None = None,
        role: str = "user",
        **kwargs,
    ) -> list[T]:
        """
        Create batch completion requests and return Pydantic models.

        This is the main public API for structured batch completions. It orchestrates:
        1. Determining the correct provider for the model
        2. Converting prompts to message lists
        3. Executing batch completion with validation and retry logic

        Args:
            prompts: List of prompt strings
            response_model: Pydantic model class to parse each response into
            model: Model to use (default: from config, falls back to gpt-4o-mini-2024-07-18)
            role: Message role for all prompts (default: 'user')
            **kwargs: Additional parameters to pass to the API (temperature, max_tokens, etc.)
                These override any default kwargs from the model configuration.

        Returns:
            List of Pydantic model instances parsed from responses

        Raises:
            ValueError: If the model is not supported by any provider, or if any response
                content is missing or invalid (after all retries)
            ValidationError: If any response cannot be parsed into the Pydantic model
        """
        # Step 1: Determine model
        if model is None:
            model = ModelConfigRegistry.get_default_model()

        # Step 2: Get provider for this model
        provider = self._get_provider_for_model(model)

        # Step 3: Convert prompts to message lists
        messages_list = [[{"role": role, "content": prompt}] for prompt in prompts]

        # Step 4: Execute with retry and validation
        return self._complete_and_validate_structured_batch(
            messages_list=messages_list,
            model=model,
            provider=provider,
            response_format=response_model,
            **kwargs,
        )


# Provider function for dependency injection
_llm_service_instance: LLMService | None = None
_llm_service_lock = threading.Lock()


def get_llm_service() -> LLMService:
    """Dependency provider for LLM service."""
    global _llm_service_instance
    if _llm_service_instance is None:
        with _llm_service_lock:
            if _llm_service_instance is None:
                _llm_service_instance = LLMService()
    return _llm_service_instance
