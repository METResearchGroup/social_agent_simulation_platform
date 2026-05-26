"""Repository-layer exceptions for simulation_v2 SQLite."""

from __future__ import annotations


class RunNotFoundError(LookupError):
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        super().__init__(f"Run not found: {run_id}")


class TurnNotFoundError(LookupError):
    def __init__(self, turn_id: str) -> None:
        self.turn_id = turn_id
        super().__init__(f"Turn not found: {turn_id}")


class InvalidStatusTransitionError(ValueError):
    def __init__(self, current: str, target: str, entity_kind: str) -> None:
        self.current = current
        self.target = target
        self.entity_kind = entity_kind
        super().__init__(
            f"Invalid {entity_kind} status transition: {current!r} -> {target!r}"
        )
