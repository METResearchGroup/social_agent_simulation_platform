"""LangChain LLM client for simulation v2 agents."""

from __future__ import annotations

import logging
import time
from typing import TypeVar

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, SecretStr

from lib.load_env_vars import EnvVarsContainer
from simulation_v2.models.telemetry import ActionType
from simulation_v2.telemetry.context import SimulationTraceContext
from simulation_v2.telemetry.llm_callback import LlmMetricsCallbackHandler
from simulation_v2.telemetry.llm_collector import LlmCallRecord
from simulation_v2.telemetry.opik import get_opik_tracer, is_opik_enabled

LOGGER = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-5-nano"
T = TypeVar("T", bound=BaseModel)


def get_chat_model(
    *, model: str = DEFAULT_MODEL, temperature: float = 0.7
) -> ChatOpenAI:
    """Return a configured ChatOpenAI instance."""
    api_key = SecretStr(EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True))
    return ChatOpenAI(model=model, temperature=temperature, api_key=api_key)


def _record_llm_call(
    *,
    trace_ctx: SimulationTraceContext,
    action_type: ActionType,
    user_id: str,
    write_attempt_index: int | None,
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
            user_id=user_id or "",
            action_type=action_type,
            latency_ms=latency_ms,
            cost_usd=metrics.get("cost_usd"),  # type: ignore[arg-type]
            prompt_tokens=metrics.get("prompt_tokens"),  # type: ignore[arg-type]
            completion_tokens=metrics.get("completion_tokens"),  # type: ignore[arg-type]
            success=success,
            error_type=error_type,
            write_attempt_index=write_attempt_index,
        )
    )


def invoke_structured(
    prompt: ChatPromptTemplate,
    output_model: type[T],
    *,
    trace_ctx: SimulationTraceContext | None = None,
    action_type: ActionType | None = None,
    user_id: str | None = None,
    write_attempt_index: int | None = None,
    **prompt_variables: object,
) -> T:
    """Invoke the LLM with structured output parsing."""
    llm = get_chat_model()
    structured_llm = llm.with_structured_output(output_model)
    chain = prompt | structured_llm

    telemetry_enabled = (
        trace_ctx is not None
        and trace_ctx.enabled
        and is_opik_enabled()
        and action_type is not None
    )

    callbacks: list[BaseCallbackHandler] = []
    metrics_handler: LlmMetricsCallbackHandler | None = None
    if telemetry_enabled and trace_ctx is not None and action_type is not None:
        try:
            callbacks.append(
                get_opik_tracer(
                    trace_ctx=trace_ctx,
                    action_type=action_type,
                    user_id=user_id or "",
                    write_attempt_index=write_attempt_index,
                )
            )
            metrics_handler = LlmMetricsCallbackHandler()
            callbacks.append(metrics_handler)
        except Exception:
            LOGGER.warning("Failed to initialize Opik telemetry", exc_info=True)
            telemetry_enabled = False
            callbacks = []
            metrics_handler = None

    start_time = time.perf_counter()
    try:
        if callbacks:
            invoke_config: RunnableConfig = {"callbacks": callbacks}
            result = chain.invoke(
                prompt_variables,
                config=invoke_config,
            )
        else:
            result = chain.invoke(prompt_variables)
    except Exception as exc:
        if telemetry_enabled and trace_ctx is not None and action_type is not None:
            try:
                _record_llm_call(
                    trace_ctx=trace_ctx,
                    action_type=action_type,
                    user_id=user_id or "",
                    write_attempt_index=write_attempt_index,
                    latency_ms=(time.perf_counter() - start_time) * 1000,
                    metrics_handler=metrics_handler,
                    success=False,
                    error_type=type(exc).__name__,
                )
            except Exception:
                LOGGER.warning(
                    "Failed to record failed LLM call metrics", exc_info=True
                )
        raise

    latency_ms = (time.perf_counter() - start_time) * 1000
    if telemetry_enabled and trace_ctx is not None and action_type is not None:
        try:
            _record_llm_call(
                trace_ctx=trace_ctx,
                action_type=action_type,
                user_id=user_id or "",
                write_attempt_index=write_attempt_index,
                latency_ms=latency_ms,
                metrics_handler=metrics_handler,
                success=True,
            )
        except Exception:
            LOGGER.warning("Failed to record LLM call metrics", exc_info=True)

    if not isinstance(result, output_model):
        raise TypeError(
            f"Expected {output_model.__name__}, got {type(result).__name__}"
        )
    return result
