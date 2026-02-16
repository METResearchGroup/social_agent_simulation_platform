"""Unit tests for LLMService."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pydantic import BaseModel, Field

from ml_tooling.llm.llm_service import LLMService
from ml_tooling.llm.providers.base import LLMProviderProtocol


class SamplePydanticModel(BaseModel):
    value: str = Field(description="A test value")
    number: int = Field(description="A test number")


class _DummyProvider(LLMProviderProtocol):
    """Minimal provider stub to satisfy LLMService internals in unit tests."""

    _initialized = True
    _api_key = "dummy-test-key"

    @property
    def provider_name(self) -> str:
        return "dummy"

    @property
    def supported_models(self) -> list[str]:
        return ["dummy-model"]

    @property
    def api_key(self) -> str:
        return self._api_key

    def initialize(self, api_key=None) -> None:  # noqa: ANN001
        return None

    def supports_model(self, model_name: str) -> bool:  # noqa: ARG002
        return True

    def format_structured_output(self, response_model, model_config):  # noqa: ANN001,ARG002
        return {"type": "json_schema", "json_schema": {"schema": {}}}

    def prepare_completion_kwargs(
        self,
        model: str,
        messages: list[dict],
        response_format,
        model_config,
        **kwargs,  # noqa: ANN001,ARG002
    ) -> dict:
        return {"model": model, "messages": messages, **kwargs}


class TestLLMService:
    @patch("ml_tooling.llm.llm_service.litellm.completion")
    def test__chat_completion_reraises_exceptions(self, mock_litellm_completion):
        """_chat_completion should re-raise exceptions from litellm.completion."""
        service = LLMService()
        provider = _DummyProvider()
        messages = [{"role": "user", "content": "test prompt"}]
        mock_litellm_completion.side_effect = Exception("API error")

        # Avoid depending on provider/model registry logic here.
        with patch.object(
            service, "_prepare_completion_kwargs", return_value=({}, None)
        ):
            with pytest.raises(Exception, match="API error"):
                service._chat_completion(
                    messages=messages, model="gpt-4o-mini", provider=provider
                )

    @patch("ml_tooling.llm.llm_service.litellm.completion")
    def test__chat_completion_returns_model_response(self, mock_litellm_completion):
        """_chat_completion should return a ModelResponse from litellm.completion."""
        from litellm import Choices, Message, ModelResponse

        service = LLMService()
        provider = _DummyProvider()
        messages = [{"role": "user", "content": "test prompt"}]

        mock_response = ModelResponse(
            id="test-id",
            choices=[
                Choices(message=Message(role="assistant", content="test response"))
            ],
        )
        mock_litellm_completion.return_value = mock_response

        with patch.object(
            service, "_prepare_completion_kwargs", return_value=({}, None)
        ):
            result = service._chat_completion(
                messages=messages, model="gpt-4o-mini", provider=provider
            )

        assert isinstance(result, ModelResponse)
        assert result.id == "test-id"
        mock_litellm_completion.assert_called_once()

    def test_structured_completion_returns_parsed_model(self):
        """structured_completion should parse the response content into the response_model."""
        service = LLMService()
        messages = [{"role": "user", "content": "test prompt"}]
        dummy_provider = _DummyProvider()

        parsed_model = SamplePydanticModel(value="test", number=42)

        with patch.object(
            service, "_get_provider_for_model", return_value=dummy_provider
        ):
            with patch.object(
                service, "_complete_and_validate_structured", return_value=parsed_model
            ) as mock_complete:
                result = service.structured_completion(
                    messages=messages,
                    response_model=SamplePydanticModel,
                    model="gpt-4o-mini",
                    max_tokens=100,
                    temperature=0.7,
                )

        assert isinstance(result, SamplePydanticModel)
        assert result.value == "test"
        assert result.number == 42
        mock_complete.assert_called_once()

    def test_structured_completion_raises_value_error_when_content_is_none(self):
        """Verify structured_completion raises ValueError when response content is None."""
        service = LLMService()
        dummy_provider = _DummyProvider()
        messages = [{"role": "user", "content": "test prompt"}]

        with patch.object(
            service, "_get_provider_for_model", return_value=dummy_provider
        ):
            # Mock _complete_and_validate_structured to raise ValueError (simulating handle_completion_response)
            with patch.object(
                service,
                "_complete_and_validate_structured",
                side_effect=ValueError(
                    "Response content is None. Expected structured output from LLM."
                ),
            ):
                with pytest.raises(ValueError, match="Response content is None"):
                    service.structured_completion(
                        messages=messages,
                        response_model=SamplePydanticModel,
                        model="gpt-4o-mini",
                    )

    def test_structured_completion_raises_validation_error_for_invalid_json(self):
        """Verify structured_completion raises ValidationError for invalid JSON response."""
        from pydantic import ValidationError

        service = LLMService()
        dummy_provider = _DummyProvider()
        messages = [{"role": "user", "content": "test prompt"}]

        # Create a ValidationError by trying to parse invalid data
        # This will definitely raise a ValidationError since required fields are missing
        validation_error: ValidationError
        try:
            SamplePydanticModel.model_validate({})  # Empty dict will fail validation
            # This should never happen, but satisfy type checker
            raise AssertionError("Expected ValidationError was not raised")
        except ValidationError as e:
            validation_error = e

        with patch.object(
            service, "_get_provider_for_model", return_value=dummy_provider
        ):
            # Mock _complete_and_validate_structured to raise ValidationError
            with patch.object(
                service,
                "_complete_and_validate_structured",
                side_effect=validation_error,
            ):
                with pytest.raises(ValidationError):
                    service.structured_completion(
                        messages=messages,
                        response_model=SamplePydanticModel,
                        model="gpt-4o-mini",
                    )

    def test_structured_completion_passes_kwargs_to_complete_and_validate(self):
        """Verify structured_completion passes kwargs through to _complete_and_validate_structured."""
        service = LLMService()
        dummy_provider = _DummyProvider()
        messages = [{"role": "user", "content": "test prompt"}]

        parsed_model = SamplePydanticModel(value="test", number=42)

        with patch.object(
            service, "_get_provider_for_model", return_value=dummy_provider
        ):
            with patch.object(
                service, "_complete_and_validate_structured", return_value=parsed_model
            ) as mock_complete:
                service.structured_completion(
                    messages=messages,
                    response_model=SamplePydanticModel,
                    model="gpt-4o-mini",
                    max_tokens=200,
                    temperature=0.5,
                    top_p=0.9,
                )

        call_kwargs = mock_complete.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o-mini"
        assert call_kwargs["response_format"] == SamplePydanticModel
        assert call_kwargs["max_tokens"] == 200
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["top_p"] == 0.9
