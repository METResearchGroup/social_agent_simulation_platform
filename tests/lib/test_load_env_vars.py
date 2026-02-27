"""Tests for lib.load_env_vars module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from lib.load_env_vars import EnvVarsContainer


@pytest.fixture(autouse=True)
def reset_env_container():
    """Reset the EnvVarsContainer singleton before each test for isolation."""
    EnvVarsContainer._instance = None
    yield


def test_get_env_var_returns_value_when_set():
    """get_env_var returns the value when the env var is set."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-key"}, clear=False):
        expected_result = "sk-test-key"
        actual = EnvVarsContainer.get_env_var("OPENAI_API_KEY")
        assert actual == expected_result


def test_get_env_var_required_raises_when_missing():
    """get_env_var with required=True raises ValueError when var is missing."""
    with patch("lib.load_env_vars.load_dotenv", return_value=False):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)
            expected_message = "OPENAI_API_KEY is required but is missing"
            assert expected_message in str(exc_info.value)


def test_get_env_var_required_raises_when_empty_string():
    """get_env_var with required=True raises ValueError when var is empty string."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
        with pytest.raises(ValueError) as exc_info:
            EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)
        expected_message = "OPENAI_API_KEY is required but is empty"
        assert expected_message in str(exc_info.value)


def test_get_env_var_returns_empty_string_for_optional_missing():
    """get_env_var returns empty string for optional missing str var."""
    with patch("lib.load_env_vars.load_dotenv", return_value=False):
        with patch.dict("os.environ", {}, clear=True):
            expected_result = ""
            actual = EnvVarsContainer.get_env_var("OPIK_WORKSPACE")
            assert actual == expected_result


def test_load_dotenv_called_from_repo_root():
    """load_dotenv is invoked with path resolving to repo root .env."""
    with patch("lib.load_env_vars.load_dotenv") as mock_load_dotenv:
        EnvVarsContainer._instance = None
        with patch.dict("os.environ", {"OPENAI_API_KEY": "x"}, clear=False):
            EnvVarsContainer.get_env_var("OPENAI_API_KEY")

        mock_load_dotenv.assert_called_once()
        call_arg = mock_load_dotenv.call_args[0][0]
        resolved = Path(call_arg).resolve()
        expected_name = ".env"
        assert resolved.name == expected_name
        assert resolved.parent.name != "lib"
