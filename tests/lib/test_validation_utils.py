import pytest

from lib.validation_utils import validate_non_empty_iterable
from lib.validation_utils import validate_non_empty_iterable


class TestValidateNonEmptyIterable:
    """Test validate_non_empty_iterable function.

    (1) if iterable is None
    (2) if iterable is NOT None
    (3) if not iterable
    """

    def test_if_iterable_is_none(self):
        """Test if iterable is None."""
        iterable = None
        with pytest.raises(ValueError):
            validate_non_empty_iterable(iterable, "iterable")  # type: ignore

    def test_if_iterable_is_not_none(self):
        """Test if iterable is not None."""
        iterable = [1, 2, 3]
        result = validate_non_empty_iterable(iterable, "iterable")
        assert result == iterable

    def test_if_iterable_is_empty(self):
        """Test if iterable is empty."""
        iterable = []
        with pytest.raises(ValueError):
            validate_non_empty_iterable(iterable, "iterable")  # type: ignore


class TestValidateNonEmptyString:
    def test_if_input_is_none(self):
        input = "string"
        assert validate_non_empty_string(input, "field_name") == None

    
    
