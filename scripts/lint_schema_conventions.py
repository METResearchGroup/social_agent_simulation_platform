"""Schema convention linter for persistence-scope contracts.

This linter enforces the mechanically-checkable subset of the persistence-scope
contract documented in:
- docs/RULES.md (Persistence scopes)
- docs/architecture/seed-state-run-snapshot-turn-events.md

It is intentionally narrow: it validates only table naming + the presence or
absence of `run_id`/`turn_number` columns for new tables.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import sqlalchemy as sa

# TODO: Delete when legacy seed-state tables are migrated to agent_* naming.
LEGACY_SEED_STATE_TABLES: frozenset[str] = frozenset(
    {
        # Seed-state tables that predate the `agent_*` prefix.
        "agent",
        "agent_persona_bios",
        "user_agent_profile_metadata",
    }
)

# TODO: Delete when legacy turn-event tables are migrated to turn_* naming.
LEGACY_TURN_EVENT_TABLES: frozenset[str] = frozenset(
    {
        # Legacy-named turn event tables (treated like `turn_*`).
        "generated_feeds",
        "likes",
        "comments",
        "follows",
        # Already-prefixed turn-event tables.
        "turn_metadata",
        "turn_metrics",
    }
)


@dataclass(frozen=True)
class Violation:
    rule: str
    table_name: str
    message: str

    def format(self) -> str:
        return f"db/schema.py [{self.rule}] {self.table_name}: {self.message}"


def _has_column(table: sa.Table, name: str) -> bool:
    return name in table.c


def _has_nonnull_column(table: sa.Table, name: str) -> bool:
    col = table.c.get(name)
    if col is None:
        return False
    return col.nullable is False


def _lint_agent_table(table: sa.Table) -> Iterable[Violation]:
    name = table.name
    if _has_column(table, "run_id"):
        yield Violation(
            rule="SCHEMA-1",
            table_name=name,
            message="agent_* tables must not declare run_id (seed state must not mix run scope).",
        )
    if _has_column(table, "turn_number"):
        yield Violation(
            rule="SCHEMA-1",
            table_name=name,
            message=(
                "agent_* tables must not declare turn_number "
                "(seed state must not mix turn events)."
            ),
        )


def _lint_run_table(table: sa.Table) -> Iterable[Violation]:
    name = table.name
    if not _has_nonnull_column(table, "run_id"):
        yield Violation(
            rule="SCHEMA-2",
            table_name=name,
            message="run_* tables must declare a non-null run_id column.",
        )


def _lint_turn_event_table(table: sa.Table) -> Iterable[Violation]:
    name = table.name
    if not _has_nonnull_column(table, "run_id"):
        yield Violation(
            rule="SCHEMA-3",
            table_name=name,
            message="turn-event tables must declare a non-null run_id column.",
        )
    if not _has_nonnull_column(table, "turn_number"):
        yield Violation(
            rule="SCHEMA-3",
            table_name=name,
            message="turn-event tables must declare a non-null turn_number column.",
        )


def lint_metadata(metadata: sa.MetaData) -> list[Violation]:
    """Return violations for the provided SQLAlchemy MetaData."""

    violations: list[Violation] = []
    for table in metadata.tables.values():
        name = table.name

        if name.startswith("agent_") or name in LEGACY_SEED_STATE_TABLES:
            violations.extend(_lint_agent_table(table))
            continue

        if name.startswith("run_"):
            violations.extend(_lint_run_table(table))
            continue

        if name.startswith("turn_") or name in LEGACY_TURN_EVENT_TABLES:
            violations.extend(_lint_turn_event_table(table))
            continue

        # Current-state legacy tables and non-governed tables are not linted here.

    return sorted(violations, key=lambda v: (v.rule, v.table_name, v.message))


def main() -> int:
    from db import schema as repo_schema

    violations = lint_metadata(repo_schema.metadata)
    if violations:
        for v in violations:
            print(v.format())
        return 1

    table_count = len(repo_schema.metadata.tables)
    print(f"OK ({table_count} tables checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
