"""Name-based registry for eval plugins."""

from __future__ import annotations

from simulation_v2.evals.interfaces import EvalPlugin

_PLUGINS: dict[str, EvalPlugin] = {}


def register_eval_plugin(plugin: EvalPlugin) -> None:
    _PLUGINS[plugin.name] = plugin


def get_eval_plugin(name: str) -> EvalPlugin | None:
    return _PLUGINS.get(name)


def register_builtin_eval_plugins() -> None:
    from simulation_v2.evals.plugins.action_counts import ActionCountsPlugin
    from simulation_v2.evals.plugins.feed_coverage import FeedCoveragePlugin
    from simulation_v2.evals.plugins.golden_dataset import GoldenDatasetPlugin
    from simulation_v2.evals.plugins.invalid_action_rate import (
        InvalidActionRatePlugin,
    )
    from simulation_v2.evals.plugins.llm_structured_output import (
        LlmStructuredOutputPlugin,
    )

    register_eval_plugin(ActionCountsPlugin())
    register_eval_plugin(InvalidActionRatePlugin())
    register_eval_plugin(FeedCoveragePlugin())
    register_eval_plugin(GoldenDatasetPlugin())
    register_eval_plugin(LlmStructuredOutputPlugin())
