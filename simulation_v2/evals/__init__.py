"""Eval plugin framework for simulation_v2."""

from simulation_v2.evals.interfaces import (
    EvalContext,
    EvalMetricDraft,
    EvalPlugin,
    EvalResult,
)
from simulation_v2.evals.registry import register_builtin_eval_plugins

register_builtin_eval_plugins()

__all__ = [
    "EvalContext",
    "EvalMetricDraft",
    "EvalPlugin",
    "EvalResult",
]
