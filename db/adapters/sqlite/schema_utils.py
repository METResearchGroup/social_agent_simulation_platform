from __future__ import annotations

import sqlalchemy as sa


def ordered_column_names(table: sa.Table) -> list[str]:
    """Return column names in schema definition order."""
    return [col.name for col in table.columns]


def required_column_names(table: sa.Table) -> list[str]:
    """Return names of columns that are NOT NULL according to the schema."""
    return [col.name for col in table.columns if not col.nullable]
