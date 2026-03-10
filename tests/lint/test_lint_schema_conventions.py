"""Unit tests for scripts/lint_schema_conventions.py."""

from __future__ import annotations

import sqlalchemy as sa


class TestLintSchemaConventions:
    def test_accepts_repo_schema_metadata(self):
        # The linter must accept the current repo schema baseline.
        from db import schema as repo_schema
        from scripts import lint_schema_conventions

        violations = lint_schema_conventions.lint_metadata(repo_schema.metadata)

        assert violations == []

    def test_rejects_agent_tables_with_run_id(self):
        from scripts import lint_schema_conventions

        md = sa.MetaData()
        sa.Table(
            "agent_follow_edges",
            md,
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("run_id", sa.Text(), nullable=False),
        )

        violations = lint_schema_conventions.lint_metadata(md)

        assert any(v.rule == "SCHEMA-1" for v in violations)

    def test_rejects_run_tables_missing_run_id(self):
        from scripts import lint_schema_conventions

        md = sa.MetaData()
        sa.Table(
            "run_agents",
            md,
            sa.Column("agent_id", sa.Text(), nullable=False),
        )

        violations = lint_schema_conventions.lint_metadata(md)

        assert any(v.rule == "SCHEMA-2" for v in violations)

    def test_rejects_turn_tables_missing_turn_number(self):
        from scripts import lint_schema_conventions

        md = sa.MetaData()
        sa.Table(
            "turn_posts",
            md,
            sa.Column("run_id", sa.Text(), nullable=False),
            sa.Column("post_id", sa.Text(), nullable=False),
        )

        violations = lint_schema_conventions.lint_metadata(md)

        assert any(v.rule == "SCHEMA-3" for v in violations)
