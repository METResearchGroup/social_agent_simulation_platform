import pytest

from lib.validation_utils import validate_non_empty_iterable, validate_non_empty_string


class TestValidateNonEmptyIterable:
    """Test validate_non_empty_iterable function.

    (1) if iterable is None
    (2) if iterable is NOT None
    (3) if not iterable
    """

    def test_if_iterable_is_none(self):
        """Test if iterable is None."""
        iterable = None
        with pytest.raises(ValueError, match="iterable cannot be None"):
            validate_non_empty_iterable(iterable, "iterable")  # type: ignore

    def test_if_iterable_is_not_none(self):
        """Test if iterable is not None."""
        iterable = [1, 2, 3]
        result = validate_non_empty_iterable(iterable, "iterable")
        expected_result = iterable
        assert result == expected_result

    def test_if_iterable_is_empty(self):
        """Test if iterable is empty."""
        iterable = []
        with pytest.raises(ValueError, match="iterable cannot be empty"):
            validate_non_empty_iterable(iterable, "iterable")


class TestValidateNonEmptyString:
    @pytest.mark.parametrize(
        "string, expected_error",
        [
            (None, "field_name cannot be None"),
            (5, "field_name must be a string"),
            ("", "field_name cannot be empty"),
            ("   ", "field_name cannot be empty"),
        ],
    )
    def test_validation_errors(self, string, expected_error):
        with pytest.raises(ValueError, match=expected_error):
            validate_non_empty_string(string, "field_name")

    @pytest.mark.parametrize(
        "string, expected",
        [
            ("string", "string"),
            ("  string with spaces  ", "string with spaces"),
        ],
    )
    def test_strips_surrounding_whitespace(self, string, expected):
        result = validate_non_empty_string(string, "field_name")
        expected_result = expected
        assert expected_result == result
