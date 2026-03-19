from __future__ import annotations

import textwrap

from scripts import lint_architecture


def _lint(path: str, source: str):
    exit_code, violations = lint_architecture.lint_file(path, textwrap.dedent(source))
    assert exit_code == 0
    return violations


def _rules(violations: list[lint_architecture.Violation]) -> list[str]:
    return [v.rule for v in violations]


class TestLintArchitecturePY13RepoConnContract:
    def test_accepts_conn_optional_with_if_and_transaction_fallback(self):
        violations = _lint(
            "db/repositories/test_agent_posts_repository.py",
            """
            class SQLiteTestAgentPostsRepository(AgentPostRepository):
                def __init__(self):
                    pass

                def list_posts_for_agent_ids(self, agent_ids: list[str], conn: object | None = None):
                    if not agent_ids:
                        return []
                    if conn is not None:
                        return self._db_adapter.read_posts_for_agent_ids(agent_ids, conn=conn)
                    with self._transaction_provider.run_transaction() as c:
                        return self._db_adapter.read_posts_for_agent_ids(agent_ids, conn=c)
            """,
        )
        assert "PY-13" not in _rules(violations)

    def test_rejects_missing_conn_param(self):
        violations = _lint(
            "db/repositories/test_agent_posts_repository.py",
            """
            class SQLiteTestAgentPostsRepository(AgentPostRepository):
                def __init__(self):
                    pass

                def list_posts_for_agent_ids(self, agent_ids: list[str]):
                    if not agent_ids:
                        return []
                    if conn is not None:
                        return self._db_adapter.read_posts_for_agent_ids(agent_ids, conn=conn)
                    with self._transaction_provider.run_transaction() as c:
                        return self._db_adapter.read_posts_for_agent_ids(agent_ids, conn=c)
            """,
        )
        assert "PY-13" in _rules(violations)

    def test_rejects_missing_if_conn_is_not_none_branch(self):
        violations = _lint(
            "db/repositories/test_agent_posts_repository.py",
            """
            class SQLiteTestAgentPostsRepository(AgentPostRepository):
                def __init__(self):
                    pass

                def list_posts_for_agent_ids(self, agent_ids: list[str], conn: object | None = None):
                    if not agent_ids:
                        return []
                    with self._transaction_provider.run_transaction() as c:
                        return self._db_adapter.read_posts_for_agent_ids(agent_ids, conn=c)
            """,
        )
        assert "PY-13" in _rules(violations)

    def test_rejects_missing_transaction_fallback_with_as_c(self):
        violations = _lint(
            "db/repositories/test_agent_posts_repository.py",
            """
            class SQLiteTestAgentPostsRepository(AgentPostRepository):
                def __init__(self):
                    pass

                def list_posts_for_agent_ids(self, agent_ids: list[str], conn: object | None = None):
                    if not agent_ids:
                        return []
                    if conn is not None:
                        return self._db_adapter.read_posts_for_agent_ids(agent_ids, conn=conn)
                    return []
            """,
        )
        assert "PY-13" in _rules(violations)

    def test_accepts_async_transaction_fallback_with_as_c(self):
        violations = _lint(
            "db/repositories/test_agent_posts_repository.py",
            """
            class SQLiteTestAgentPostsRepository(AgentPostRepository):
                def __init__(self):
                    pass

                async def list_posts_for_agent_ids(self, agent_ids: list[str], conn: object | None = None):
                    if not agent_ids:
                        return []
                    if conn is not None:
                        return self._db_adapter.read_posts_for_agent_ids(agent_ids, conn=conn)
                    async with self._transaction_provider.run_transaction() as c:
                        return self._db_adapter.read_posts_for_agent_ids(agent_ids, conn=c)
            """,
        )
        assert "PY-13" not in _rules(violations)

    def test_ignores_public_methods_without_db_adapter_call(self):
        violations = _lint(
            "db/repositories/test_agent_posts_repository.py",
            """
            class SQLiteTestAgentPostsRepository(AgentPostRepository):
                def __init__(self):
                    pass

                def count_posts_for_agent_ids(self, agent_ids: list[str], conn: object | None = None) -> dict[str, int]:
                    # No `_db_adapter.*` call => should not trigger PY-13.
                    return {a: 0 for a in agent_ids}
            """,
        )
        assert "PY-13" not in _rules(violations)


class TestLintArchitecturePY14AdapterConnSignature:
    def test_accepts_conn_parameter_in_adapter_method_signature(self):
        violations = _lint(
            "db/adapters/test_adapter.py",
            """
            class AgentPostDatabaseAdapter:
                pass

            class SQLiteTestAgentPostAdapter(AgentPostDatabaseAdapter):
                def read_posts_for_agent_ids(self, agent_ids, *, conn):
                    return []
            """,
        )
        assert "PY-14" not in _rules(violations)

    def test_rejects_missing_conn_parameter_in_adapter_method_signature(self):
        violations = _lint(
            "db/adapters/test_adapter.py",
            """
            class AgentPostDatabaseAdapter:
                pass

            class SQLiteTestAgentPostAdapter(AgentPostDatabaseAdapter):
                def read_posts_for_agent_ids(self, agent_ids):
                    return []
            """,
        )
        assert "PY-14" in _rules(violations)

    def test_ignores_classes_not_subclassing_known_adapter_abc(self):
        violations = _lint(
            "db/adapters/test_adapter.py",
            """
            class NotAnAdapter:
                pass

            class ConcreteNotAdapter(NotAnAdapter):
                def read_posts_for_agent_ids(self, agent_ids):
                    return []
            """,
        )
        assert "PY-14" not in _rules(violations)
