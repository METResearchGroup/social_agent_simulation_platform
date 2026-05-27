"""Unit tests for actions.llm structured generation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.prompts import ChatPromptTemplate
from pydantic import ValidationError

from simulation_v2.actions.llm import invoke_structured_generation
from simulation_v2.actions.models import (
    ActionType,
    LlmGenerationResult,
    LlmLikePostOutput,
    LlmWritePostOutput,
)
from simulation_v2.actions.prompts import LIKE_POSTS_PROMPT, WRITE_POST_PROMPT
from simulation_v2.config import LlmConfig
from simulation_v2.telemetry.context import SimulationTraceContext


@pytest.fixture
def llm_config() -> LlmConfig:
    return LlmConfig(model="gpt-5-nano", temperature=0.0)


@pytest.fixture
def trace_ctx() -> SimulationTraceContext:
    return SimulationTraceContext(run_id="run-1", turn_number=1)


def _invoke_with_mock_chain(
    *,
    prompt: ChatPromptTemplate,
    output_model: type,
    llm_config: LlmConfig,
    side_effect: object,
    action_type: ActionType = "like_post",
    trace_ctx: SimulationTraceContext | None = None,
) -> LlmGenerationResult:
    mock_llm = MagicMock()
    mock_chain = MagicMock()
    mock_chain.invoke = MagicMock(side_effect=side_effect)

    with (
        patch("simulation_v2.actions.llm.get_chat_model", return_value=mock_llm),
        patch.object(ChatPromptTemplate, "__or__", return_value=mock_chain),
    ):
        return invoke_structured_generation(
            prompt,
            output_model,
            llm_config=llm_config,
            prompt_variables={"name": "Alice"},
            action_type=action_type,
            user_id="u1",
            trace_ctx=trace_ctx,
        )


class TestInvokeStructuredGeneration:
    def test_success_returns_completed_result(self, llm_config: LlmConfig) -> None:
        parsed = LlmLikePostOutput(post_ids=["p1"])
        result = _invoke_with_mock_chain(
            prompt=LIKE_POSTS_PROMPT,
            output_model=LlmLikePostOutput,
            llm_config=llm_config,
            side_effect=[parsed],
        )

        assert result.status == "completed"
        assert isinstance(result.parsed, LlmLikePostOutput)
        assert result.parsed.post_ids == ["p1"]
        assert result.latency_ms is not None
        assert result.error is None

    def test_retryable_failure_then_succeeds(self, llm_config: LlmConfig) -> None:
        parsed = LlmWritePostOutput(content="hello")
        mock_llm = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(
            side_effect=[TimeoutError("timeout"), TimeoutError("timeout"), parsed]
        )

        with (
            patch("simulation_v2.actions.llm.get_chat_model", return_value=mock_llm),
            patch.object(ChatPromptTemplate, "__or__", return_value=mock_chain),
        ):
            result = invoke_structured_generation(
                WRITE_POST_PROMPT,
                LlmWritePostOutput,
                llm_config=llm_config,
                prompt_variables={"name": "Alice"},
                action_type="write_post",
                user_id="u1",
            )

        assert result.status == "completed"
        assert mock_chain.invoke.call_count == 3

    def test_retryable_failure_exhausted(self, llm_config: LlmConfig) -> None:
        mock_llm = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(side_effect=TimeoutError("timeout"))

        with (
            patch("simulation_v2.actions.llm.get_chat_model", return_value=mock_llm),
            patch.object(ChatPromptTemplate, "__or__", return_value=mock_chain),
        ):
            result = invoke_structured_generation(
                WRITE_POST_PROMPT,
                LlmWritePostOutput,
                llm_config=llm_config,
                prompt_variables={"name": "Alice"},
                action_type="write_post",
                user_id="u1",
            )

        assert result.status == "failed"
        assert result.error is not None
        assert mock_chain.invoke.call_count == 4

    def test_schema_failure_wrong_shape(self, llm_config: LlmConfig) -> None:
        result = _invoke_with_mock_chain(
            prompt=LIKE_POSTS_PROMPT,
            output_model=LlmLikePostOutput,
            llm_config=llm_config,
            side_effect=[{"unexpected": "shape"}],
        )

        assert result.status == "schema_failed"
        assert result.parsed is None
        assert result.error is not None

    def test_schema_failure_validation_error(self, llm_config: LlmConfig) -> None:
        validation_error = ValidationError.from_exception_data(
            "LlmLikePostOutput",
            [{"type": "missing", "loc": ("post_ids",), "input": {}}],
        )
        result = _invoke_with_mock_chain(
            prompt=LIKE_POSTS_PROMPT,
            output_model=LlmLikePostOutput,
            llm_config=llm_config,
            side_effect=[validation_error],
        )

        assert result.status == "schema_failed"

    @patch("simulation_v2.actions.llm.is_opik_enabled", return_value=False)
    @patch("simulation_v2.actions.llm.get_opik_tracer")
    def test_opik_disabled_skips_callbacks(
        self,
        mock_get_opik_tracer: MagicMock,
        mock_is_opik_enabled: MagicMock,
        llm_config: LlmConfig,
        trace_ctx: SimulationTraceContext,
    ) -> None:
        assert mock_is_opik_enabled.return_value is False
        parsed = LlmLikePostOutput(post_ids=["p1"])
        mock_llm = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value=parsed)

        with (
            patch("simulation_v2.actions.llm.get_chat_model", return_value=mock_llm),
            patch.object(ChatPromptTemplate, "__or__", return_value=mock_chain),
        ):
            result = invoke_structured_generation(
                LIKE_POSTS_PROMPT,
                LlmLikePostOutput,
                llm_config=llm_config,
                prompt_variables={"name": "Alice"},
                action_type="like_post",
                user_id="u1",
                trace_ctx=trace_ctx,
            )

        assert result.status == "completed"
        mock_get_opik_tracer.assert_not_called()
        assert mock_chain.invoke.call_args.kwargs.get("config") is None
