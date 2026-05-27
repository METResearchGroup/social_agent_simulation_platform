"""LangChain LLM wrapper with retry, Opik telemetry, and structured output."""

from __future__ import annotations

import logging
import time
from typing import Any, TypeVar

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from openai import AuthenticationError, PermissionDeniedError
from pydantic import BaseModel, SecretStr, ValidationError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from lib.load_env_vars import EnvVarsContainer
from simulation_v2.actions.models import ActionType, LlmGenerationResult
from simulation_v2.config import LlmConfig
from simulation_v2.models.telemetry import ActionType as TelemetryActionType
from simulation_v2.telemetry.context import SimulationTraceContext
from simulation_v2.telemetry.llm_callback import LlmMetricsCallbackHandler
from simulation_v2.telemetry.llm_collector import LlmCallRecord
from simulation_v2.telemetry.opik import get_opik_tracer, is_opik_enabled

LOGGER = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_NON_RETRYABLE_EXCEPTIONS = (
    AuthenticationError,
    PermissionDeniedError,
    ValueError,
    TypeError,
    ValidationError,
)


def _should_retry(exception: BaseException) -> bool:
    return not isinstance(exception, _NON_RETRYABLE_EXCEPTIONS)


def _telemetry_action_type(action_type: ActionType) -> TelemetryActionType:
    mapping: dict[ActionType, TelemetryActionType] = {
        "like_post": "like_posts",
        "write_post": "write_post",
        "follow_user": "follow_users",
        "comment_on_post": "comment_on_post",
    }
    return mapping[action_type]


def get_chat_model(llm_config: LlmConfig) -> ChatOpenAI:
    api_key = SecretStr(EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True))
    return ChatOpenAI(
        model=llm_config.model,
        temperature=llm_config.temperature,
        api_key=api_key,
    )


def _record_llm_call(
    *,
    trace_ctx: SimulationTraceContext,
    action_type: ActionType,
    user_id: str,
    latency_ms: float,
    metrics_handler: LlmMetricsCallbackHandler | None,
    success: bool,
    error_type: str | None = None,
) -> None:
    metrics = metrics_handler.get_metrics() if metrics_handler else {}
    trace_ctx.turn_llm_collector.add(
        LlmCallRecord(
            run_id=trace_ctx.run_id,
            turn_number=trace_ctx.turn_number,
            user_id=user_id,
            action_type=_telemetry_action_type(action_type),
            latency_ms=latency_ms,
            cost_usd=metrics.get("cost_usd"),  # type: ignore[arg-type]
            prompt_tokens=metrics.get("prompt_tokens"),  # type: ignore[arg-type]
            completion_tokens=metrics.get("completion_tokens"),  # type: ignore[arg-type]
            success=success,
            error_type=error_type,
        )
    )


def _build_callbacks(
    *,
    trace_ctx: SimulationTraceContext | None,
    action_type: ActionType,
    user_id: str,
) -> tuple[list[BaseCallbackHandler], LlmMetricsCallbackHandler | None, bool]:
    telemetry_enabled = (
        trace_ctx is not None and trace_ctx.enabled and is_opik_enabled()
    )
    callbacks: list[BaseCallbackHandler] = []
    metrics_handler: LlmMetricsCallbackHandler | None = None
    if not telemetry_enabled or trace_ctx is None:
        return callbacks, metrics_handler, False

    try:
        callbacks.append(
            get_opik_tracer(
                trace_ctx=trace_ctx,
                action_type=_telemetry_action_type(action_type),
                user_id=user_id,
            )
        )
        metrics_handler = LlmMetricsCallbackHandler()
        callbacks.append(metrics_handler)
    except Exception:
        LOGGER.warning("Failed to initialize Opik telemetry", exc_info=True)
        return [], None, False

    return callbacks, metrics_handler, True


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential_jitter(initial=1, max=60),
    retry=retry_if_exception(_should_retry),
    before_sleep=before_sleep_log(LOGGER, logging.WARNING),
    reraise=True,
)
def _invoke_chain(
    chain: Any,
    prompt_variables: dict[str, object],
    invoke_config: RunnableConfig | None,
) -> BaseModel:
    if invoke_config:
        return chain.invoke(prompt_variables, config=invoke_config)
    return chain.invoke(prompt_variables)


def invoke_structured_generation(
    prompt: ChatPromptTemplate,
    output_model: type[T],
    *,
    llm_config: LlmConfig,
    prompt_variables: dict[str, object],
    action_type: ActionType,
    user_id: str,
    trace_ctx: SimulationTraceContext | None = None,
) -> LlmGenerationResult:
    """Invoke structured LLM generation with retries and optional Opik telemetry."""
    llm = get_chat_model(llm_config)
    structured_llm = llm.with_structured_output(output_model)
    chain = prompt | structured_llm

    callbacks, metrics_handler, telemetry_enabled = _build_callbacks(
        trace_ctx=trace_ctx,
        action_type=action_type,
        user_id=user_id,
    )
    invoke_config: RunnableConfig | None = (
        {"callbacks": callbacks} if callbacks else None
    )

    start_time = time.perf_counter()
    try:
        result = _invoke_chain(chain, prompt_variables, invoke_config)
    except ValidationError as exc:
        latency_ms = (time.perf_counter() - start_time) * 1000
        return LlmGenerationResult(
            status="schema_failed",
            latency_ms=latency_ms,
            error=str(exc),
        )
    except Exception as exc:
        latency_ms = (time.perf_counter() - start_time) * 1000
        if telemetry_enabled and trace_ctx is not None:
            try:
                _record_llm_call(
                    trace_ctx=trace_ctx,
                    action_type=action_type,
                    user_id=user_id,
                    latency_ms=latency_ms,
                    metrics_handler=metrics_handler,
                    success=False,
                    error_type=type(exc).__name__,
                )
            except Exception:
                LOGGER.warning(
                    "Failed to record failed LLM call metrics", exc_info=True
                )
        return LlmGenerationResult(
            status="failed",
            latency_ms=latency_ms,
            error=str(exc),
        )

    latency_ms = (time.perf_counter() - start_time) * 1000
    if not isinstance(result, output_model):
        return LlmGenerationResult(
            status="schema_failed",
            latency_ms=latency_ms,
            error=(f"Expected {output_model.__name__}, got {type(result).__name__}"),
            raw_response_json=_serialize_raw(result),
        )

    metrics = metrics_handler.get_metrics() if metrics_handler else {}
    if telemetry_enabled and trace_ctx is not None:
        try:
            _record_llm_call(
                trace_ctx=trace_ctx,
                action_type=action_type,
                user_id=user_id,
                latency_ms=latency_ms,
                metrics_handler=metrics_handler,
                success=True,
            )
        except Exception:
            LOGGER.warning("Failed to record LLM call metrics", exc_info=True)

    return LlmGenerationResult(
        status="completed",
        parsed=result,
        latency_ms=metrics.get("latency_ms", latency_ms),  # type: ignore[arg-type]
        prompt_tokens=metrics.get("prompt_tokens"),  # type: ignore[arg-type]
        completion_tokens=metrics.get("completion_tokens"),  # type: ignore[arg-type]
        cost_usd=metrics.get("cost_usd"),  # type: ignore[arg-type]
        raw_response_json=result.model_dump(),
    )


def _serialize_raw(result: object) -> dict[str, Any] | None:
    if isinstance(result, BaseModel):
        return result.model_dump()
    if isinstance(result, dict):
        return result
    return None
