"""Unit tests for ModelConfig and ModelConfigRegistry."""

# Mock providers.registry module before any imports to prevent actual provider registration
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Create mock registry module
mock_provider_registry_module = MagicMock()


class MockLLMProviderRegistry:
    """Mock LLMProviderRegistry for testing."""

    @staticmethod
    def get_provider(model_identifier: str):
        """Mock get_provider that returns a provider based on model identifier."""
        mock_provider = MagicMock()
        if model_identifier.startswith("gpt-4"):
            mock_provider.provider_name = "openai"
        elif model_identifier.startswith("gemini/"):
            mock_provider.provider_name = "gemini"
        elif model_identifier.startswith("groq/"):
            mock_provider.provider_name = "groq"
        elif model_identifier.startswith("huggingface/"):
            mock_provider.provider_name = "huggingface"
        else:
            raise ValueError(f"No provider found for model {model_identifier}")
        return mock_provider

    @staticmethod
    def list_providers():
        """Mock list_providers."""
        return ["openai", "gemini", "groq", "huggingface"]

    @staticmethod
    def clear():
        """Mock clear."""
        pass


mock_provider_registry_module.LLMProviderRegistry = MockLLMProviderRegistry

# Insert mock module before imports
sys.modules["ml_tooling.llm.providers.registry"] = mock_provider_registry_module

from ml_tooling.llm.config.model_registry import ModelConfig, ModelConfigRegistry  # noqa: E402,I001


@pytest.fixture
def actual_config_path():
    """Fixture that returns the path to the actual models.yaml file."""
    return Path(__file__).resolve().parents[4] / "ml_tooling/llm/config/models.yaml"


@pytest.fixture
def mock_provider_registry():
    """Fixture that mocks LLMProviderRegistry to avoid actual provider initialization."""
    # The registry is already mocked at module level, so this fixture just provides access
    # Return the mock registry module that was set up at module import time
    yield sys.modules["ml_tooling.llm.providers.registry"].LLMProviderRegistry


@pytest.fixture
def loaded_config(actual_config_path, mock_provider_registry):
    """Fixture that loads the actual models.yaml file for testing."""
    # Clear any cached config
    ModelConfigRegistry._config = None
    ModelConfigRegistry._config_path = None

    # Set the config path to the actual file
    ModelConfigRegistry.set_config_path(actual_config_path)

    yield ModelConfigRegistry._load_config()

    # Cleanup: reset the config after tests
    ModelConfigRegistry._config = None
    ModelConfigRegistry._config_path = None


class TestModelConfig:
    """Tests for ModelConfig class."""

    def test_init_raises_value_error_for_unsupported_model(self, loaded_config):
        """Test that __init__ raises ValueError when model is not supported by any provider."""
        # Arrange
        # Patch at source module since we use lazy imports
        with patch(
            "ml_tooling.llm.providers.registry.LLMProviderRegistry.get_provider"
        ) as mock_get_provider:
            mock_get_provider.side_effect = ValueError("No provider found")

            # Act & Assert
            with pytest.raises(ValueError, match="No provider found for model"):
                ModelConfig("unknown-model", loaded_config)

    def test_init_sets_provider_name_correctly(
        self, loaded_config, mock_provider_registry
    ):
        """Test that __init__ correctly identifies and sets the provider name."""
        # Arrange & Act
        model_config = ModelConfig("gpt-4o-mini", loaded_config)

        # Assert
        assert model_config.provider_name == "openai"
        assert model_config.model_identifier == "gpt-4o-mini"

    def test_init_sets_model_config_correctly(
        self, loaded_config, mock_provider_registry
    ):
        """Test that __init__ correctly loads model-specific configuration."""
        # Arrange & Act
        model_config = ModelConfig("huggingface/unsloth/llama-3-8b", loaded_config)

        # Assert
        assert model_config._model_config is not None
        assert "llm_inference_kwargs" in model_config._model_config

    def test_get_kwarg_value_resolves_from_model_specific_first(
        self, loaded_config, mock_provider_registry
    ):
        """Test that get_kwarg_value resolves from model-specific config first (highest precedence)."""
        # Arrange
        model_config = ModelConfig("huggingface/unsloth/llama-3-8b", loaded_config)

        # Act
        result = model_config.get_kwarg_value("api_base")

        # Assert
        expected = "https://api-inference.huggingface.co/models/unsloth/llama-3-8b"
        assert result == expected

    def test_get_kwarg_value_resolves_from_provider_when_not_in_model(
        self, loaded_config, mock_provider_registry
    ):
        """Test that get_kwarg_value falls back to provider-level config when not in model."""
        # Arrange
        model_config = ModelConfig("gpt-4o-mini", loaded_config)

        # Act
        result = model_config.get_kwarg_value("temperature")

        # Assert
        # Should come from provider (openai) llm_inference_kwargs, not model (which is empty)
        assert result == 0.0

    def test_get_kwarg_value_resolves_from_default_when_not_in_provider_or_model(
        self, loaded_config, mock_provider_registry
    ):
        """Test that get_kwarg_value falls back to default config when not in provider or model."""
        # Arrange
        # Use a model that has empty provider kwargs but default has temperature
        model_config = ModelConfig("gpt-4o-mini", loaded_config)

        # Act
        # Default has temperature: 0.0, provider has it too, so we should get it
        result = model_config.get_kwarg_value("temperature")

        # Assert
        assert result == 0.0

    def test_get_kwarg_value_returns_default_when_key_not_found(
        self, loaded_config, mock_provider_registry
    ):
        """Test that get_kwarg_value returns provided default when key is not found at any level."""
        # Arrange
        model_config = ModelConfig("gpt-4o-mini", loaded_config)

        # Act
        result = model_config.get_kwarg_value(
            "nonexistent_key", default="default_value"
        )

        # Assert
        assert result == "default_value"

    def test_get_kwarg_value_returns_none_when_key_not_found_and_no_default(
        self, loaded_config, mock_provider_registry
    ):
        """Test that get_kwarg_value returns None when key is not found and no default provided."""
        # Arrange
        model_config = ModelConfig("gpt-4o-mini", loaded_config)

        # Act
        result = model_config.get_kwarg_value("nonexistent_key")

        # Assert
        assert result is None

    def test_get_kwarg_value_resolves_complex_nested_values(
        self, loaded_config, mock_provider_registry
    ):
        """Test that get_kwarg_value correctly resolves complex nested values like safety_settings."""
        # Arrange
        model_config = ModelConfig("gemini/gemini-1.5-pro-latest", loaded_config)

        # Act
        result = model_config.get_kwarg_value("safety_settings")

        # Assert
        # Should come from provider (gemini) llm_inference_kwargs
        assert isinstance(result, list)
        assert len(result) == 4
        assert result[0]["category"] == "HARM_CATEGORY_HARASSMENT"
        assert result[0]["threshold"] == "BLOCK_NONE"

    def test_get_kwarg_value_model_overrides_provider_for_temperature(
        self, loaded_config, mock_provider_registry
    ):
        """Test that model-specific temperature overrides provider-level temperature."""
        # Arrange - this test uses a model that might have different temperature
        # For now, test with a model that has empty llm_inference_kwargs
        # The provider should provide the value
        model_config = ModelConfig("gpt-4o-mini", loaded_config)

        # Act
        result = model_config.get_kwarg_value("temperature")

        # Assert
        # Model has empty dict, so should come from provider
        assert result == 0.0

    def test_get_config_value_traverses_config_correctly(
        self, loaded_config, mock_provider_registry
    ):
        """Test that get_config_value correctly traverses the config dictionary."""
        # Arrange
        model_config = ModelConfig("gpt-4o-mini", loaded_config)

        # Act
        result = model_config.get_config_value(
            "models", "openai", "llm_inference_kwargs"
        )

        # Assert
        assert isinstance(result, dict)
        assert "temperature" in result
        assert result["temperature"] == 0.0

    def test_get_config_value_raises_key_error_for_nonexistent_path(
        self, loaded_config, mock_provider_registry
    ):
        """Test that get_config_value raises KeyError when path does not exist."""
        # Arrange
        model_config = ModelConfig("gpt-4o-mini", loaded_config)

        # Act & Assert
        with pytest.raises(KeyError, match="Configuration key not found"):
            model_config.get_config_value("models", "nonexistent", "key")

    def test_get_config_value_raises_value_error_when_parent_not_dict(
        self, loaded_config, mock_provider_registry
    ):
        """Test that get_config_value raises ValueError when trying to traverse non-dict parent."""
        # Arrange
        model_config = ModelConfig("gpt-4o-mini", loaded_config)

        # Act & Assert
        # First get temperature (which is a float, not a dict), then try to traverse further
        temperature = model_config.get_config_value(
            "models", "default", "llm_inference_kwargs", "temperature"
        )
        assert isinstance(temperature, (int, float))  # Verify it's not a dict

        # Now try to traverse through it - should raise ValueError
        with pytest.raises(ValueError, match="Cannot traverse key"):
            # Try to access something that's not a dict - temperature is a float, not a dict
            model_config.get_config_value(
                "models", "default", "llm_inference_kwargs", "temperature", "invalid"
            )

    def test_get_all_llm_inference_kwargs_merges_hierarchically(
        self, loaded_config, mock_provider_registry
    ):
        """Test that get_all_llm_inference_kwargs correctly merges all levels."""
        # Arrange
        model_config = ModelConfig("gpt-4o-mini", loaded_config)

        # Act
        result = model_config.get_all_llm_inference_kwargs()

        # Assert
        assert isinstance(result, dict)
        # Should include temperature from default/provider (model has empty dict)
        assert "temperature" in result
        assert result["temperature"] == 0.0

    def test_get_all_llm_inference_kwargs_model_overrides_provider(
        self, loaded_config, mock_provider_registry
    ):
        """Test that get_all_llm_inference_kwargs has model values override provider values."""
        # Arrange
        model_config = ModelConfig("huggingface/unsloth/llama-3-8b", loaded_config)

        # Act
        result = model_config.get_all_llm_inference_kwargs()

        # Assert
        # Model has api_base, provider has empty dict, default has temperature
        assert "api_base" in result
        assert (
            result["api_base"]
            == "https://api-inference.huggingface.co/models/unsloth/llama-3-8b"
        )

    def test_get_all_llm_inference_kwargs_includes_all_levels(
        self, loaded_config, mock_provider_registry
    ):
        """Test that get_all_llm_inference_kwargs includes values from all three levels."""
        # Arrange
        model_config = ModelConfig("gemini/gemini-1.5-pro-latest", loaded_config)

        # Act
        result = model_config.get_all_llm_inference_kwargs()

        # Assert
        # Should have temperature from default/provider, and safety_settings from provider
        assert "temperature" in result
        assert "safety_settings" in result
        assert result["temperature"] == 0.0
        assert isinstance(result["safety_settings"], list)


class TestModelConfigRegistry:
    """Tests for ModelConfigRegistry class."""

    def test_set_config_path_sets_path_and_clears_cache(self, actual_config_path):
        """Test that set_config_path correctly sets the path and clears the config cache."""
        # Arrange
        ModelConfigRegistry._config = {"cached": "data"}
        ModelConfigRegistry._config_path = None

        # Act
        ModelConfigRegistry.set_config_path(actual_config_path)

        # Assert
        assert ModelConfigRegistry._config_path == actual_config_path
        assert ModelConfigRegistry._config is None

        # Cleanup
        ModelConfigRegistry._config = None
        ModelConfigRegistry._config_path = None

    def test_get_model_config_returns_model_config_instance(
        self, actual_config_path, mock_provider_registry
    ):
        """Test that get_model_config returns a ModelConfig instance."""
        # Arrange
        ModelConfigRegistry.set_config_path(actual_config_path)

        # Act
        result = ModelConfigRegistry.get_model_config("gpt-4o-mini")

        # Assert
        assert isinstance(result, ModelConfig)
        assert result.model_identifier == "gpt-4o-mini"

        # Cleanup
        ModelConfigRegistry._config = None
        ModelConfigRegistry._config_path = None

    def test_get_model_config_raises_value_error_for_unsupported_model(
        self, actual_config_path, mock_provider_registry
    ):
        """Test that get_model_config raises ValueError for unsupported model."""
        # Arrange
        ModelConfigRegistry.set_config_path(actual_config_path)
        # Patch at source module since we use lazy imports
        with patch(
            "ml_tooling.llm.providers.registry.LLMProviderRegistry.get_provider"
        ) as mock_get_provider:
            mock_get_provider.side_effect = ValueError("No provider found")

            # Act & Assert
            with pytest.raises(
                ValueError, match="Model 'unsupported-model' is not supported"
            ):
                ModelConfigRegistry.get_model_config("unsupported-model")

        # Cleanup
        ModelConfigRegistry._config = None
        ModelConfigRegistry._config_path = None

    def test_list_providers_returns_all_providers_excluding_default(
        self, actual_config_path, mock_provider_registry
    ):
        """Test that list_providers returns all provider names excluding 'default'."""
        # Arrange
        ModelConfigRegistry.set_config_path(actual_config_path)

        # Act
        result = ModelConfigRegistry.list_providers()

        # Assert
        assert isinstance(result, list)
        assert "default" not in result
        assert "openai" in result
        assert "gemini" in result
        assert "groq" in result
        assert "huggingface" in result

        # Cleanup
        ModelConfigRegistry._config = None
        ModelConfigRegistry._config_path = None

    def test_list_models_for_provider_returns_model_identifiers(
        self, actual_config_path, mock_provider_registry
    ):
        """Test that list_models_for_provider returns all model identifiers for a provider."""
        # Arrange
        ModelConfigRegistry.set_config_path(actual_config_path)

        # Act
        result = ModelConfigRegistry.list_models_for_provider("openai")

        # Assert
        assert isinstance(result, list)
        assert "gpt-4o-mini" in result
        assert "gpt-4o-mini-2024-07-18" in result
        assert "gpt-4" in result

        # Cleanup
        ModelConfigRegistry._config = None
        ModelConfigRegistry._config_path = None

    def test_list_models_for_provider_returns_empty_list_for_nonexistent_provider(
        self, actual_config_path, mock_provider_registry
    ):
        """Test that list_models_for_provider returns empty list for nonexistent provider."""
        # Arrange
        ModelConfigRegistry.set_config_path(actual_config_path)

        # Act
        result = ModelConfigRegistry.list_models_for_provider("nonexistent")

        # Assert
        assert result == []

        # Cleanup
        ModelConfigRegistry._config = None
        ModelConfigRegistry._config_path = None

    def test_list_all_models_returns_all_model_identifiers(
        self, actual_config_path, mock_provider_registry
    ):
        """Test that list_all_models returns all model identifiers across all providers."""
        # Arrange
        ModelConfigRegistry.set_config_path(actual_config_path)

        # Act
        result = ModelConfigRegistry.list_all_models()

        # Assert
        assert isinstance(result, list)
        assert len(result) > 0
        # Check a few models from different providers
        assert "gpt-4o-mini" in result
        assert "gemini/gemini-1.5-pro-latest" in result
        assert "groq/llama3-8b-8192" in result
        assert "huggingface/unsloth/llama-3-8b" in result

        # Cleanup
        ModelConfigRegistry._config = None
        ModelConfigRegistry._config_path = None

    def test_load_config_raises_file_not_found_error_for_nonexistent_file(self):
        """Test that _load_config raises FileNotFoundError when config file doesn't exist."""
        # Arrange
        nonexistent_path = Path(__file__).parent / "nonexistent.yaml"
        ModelConfigRegistry.set_config_path(nonexistent_path)

        # Act & Assert
        with pytest.raises(
            FileNotFoundError, match="Model configuration file not found"
        ):
            ModelConfigRegistry._load_config()

        # Cleanup
        ModelConfigRegistry._config = None
        ModelConfigRegistry._config_path = None

    def test_load_config_is_thread_safe(
        self, actual_config_path, mock_provider_registry
    ):
        """Test that _load_config is thread-safe by checking it can be called concurrently."""
        import threading

        # Arrange
        ModelConfigRegistry.set_config_path(actual_config_path)
        ModelConfigRegistry._config = None  # Clear cache

        results = []
        errors = []

        def load_config():
            """Load config in a thread."""
            try:
                config = ModelConfigRegistry._load_config()
                results.append(config is not None)
            except Exception as e:
                # Ensure thread failures are detected: never append a truthy error string into results.
                results.append(False)
                errors.append(str(e))

        # Act - create multiple threads
        threads = [threading.Thread(target=load_config) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Assert - all threads should successfully load config
        assert len(results) == 5
        assert all(results) is True
        assert errors == []

        # Cleanup
        ModelConfigRegistry._config = None
        ModelConfigRegistry._config_path = None
