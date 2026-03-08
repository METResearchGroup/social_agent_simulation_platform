"""Unit tests for scripts/lint_python_testing_syntax_conventions.py."""

from __future__ import annotations

from pathlib import Path

from scripts import lint_python_testing_syntax_conventions


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


class TestLintPythonTestingSyntaxConventions:
    def test_allows_class_based_tests(self, tmp_path: Path, capsys):
        root = tmp_path / "tests"
        root.mkdir()
        _write(
            root / "test_ok.py",
            "class TestOk:\n    def test_works(self):\n        assert True\n",
        )

        exit_code = lint_python_testing_syntax_conventions.main(["prog", str(root)])

        assert exit_code == 0
        out = capsys.readouterr().out
        assert "OK: no module-level test_* functions found" in out

    def test_allows_module_level_fixtures(self, tmp_path: Path, capsys):
        root = tmp_path / "tests"
        root.mkdir()
        _write(
            root / "test_fixture_ok.py",
            "import pytest\n\n"
            "@pytest.fixture\n"
            "def thing():\n"
            "    return 123\n\n"
            "class TestOk:\n"
            "    def test_uses_fixture(self, thing):\n"
            "        assert thing == 123\n",
        )

        exit_code = lint_python_testing_syntax_conventions.main(["prog", str(root)])

        assert exit_code == 0
        out = capsys.readouterr().out
        assert "OK: no module-level test_* functions found" in out

    def test_rejects_module_level_sync_tests(self, tmp_path: Path, capsys):
        root = tmp_path / "tests"
        root.mkdir()
        _write(
            root / "test_bad.py",
            "def test_bad():\n    assert True\n",
        )

        exit_code = lint_python_testing_syntax_conventions.main(["prog", str(root)])

        assert exit_code == 1
        out = capsys.readouterr().out
        assert "test function 'test_bad' is not allowed" in out

    def test_rejects_module_level_async_tests(self, tmp_path: Path, capsys):
        root = tmp_path / "tests"
        root.mkdir()
        _write(
            root / "test_bad_async.py",
            "async def test_bad_async():\n    assert True\n",
        )

        exit_code = lint_python_testing_syntax_conventions.main(["prog", str(root)])

        assert exit_code == 1
        out = capsys.readouterr().out
        assert "test function 'test_bad_async' is not allowed" in out

    def test_rejects_tests_inside_non_test_classes(self, tmp_path: Path, capsys):
        root = tmp_path / "tests"
        root.mkdir()
        _write(
            root / "test_bad_class.py",
            "class Helper:\n    def test_bad_in_helper(self):\n        assert True\n",
        )

        exit_code = lint_python_testing_syntax_conventions.main(["prog", str(root)])

        assert exit_code == 1
        out = capsys.readouterr().out
        assert "test function 'test_bad_in_helper' is not allowed" in out

    def test_allows_nested_test_named_helpers(self, tmp_path: Path, capsys):
        root = tmp_path / "tests"
        root.mkdir()
        _write(
            root / "test_nested_helper.py",
            "class TestOk:\n"
            "    def test_outer(self):\n"
            "        def test_inner():\n"
            "            return 123\n"
            "        assert test_inner() == 123\n",
        )

        exit_code = lint_python_testing_syntax_conventions.main(["prog", str(root)])

        assert exit_code == 0
        out = capsys.readouterr().out
        assert "OK: no module-level test_* functions found" in out
