"""Name-based registry for eval plugins."""

from __future__ import annotations

from simulation_v2.evals.interfaces import EvalPlugin

_PLUGINS: dict[str, EvalPlugin] = {}


def register_eval_plugin(plugin: EvalPlugin) -> None:
    _PLUGINS[plugin.name] = plugin


def get_eval_plugin(name: str) -> EvalPlugin | None:
    return _PLUGINS.get(name)
