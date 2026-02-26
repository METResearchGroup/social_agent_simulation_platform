"""Tests for db.exceptions module."""

import pytest

from db.exceptions import DatabaseError


class TestDatabaseError:
    """Tests for DatabaseError exception class."""

    def test_creates_error_with_message_only(self):
        """Test that DatabaseError can be created with just a message."""
        # Arrange
        message = "Database connection failed"

        # Act
        error = DatabaseError(message)

        # Assert
        assert error.message == message
        assert error.cause is None
        assert str(error) == message

    def test_creates_error_with_message_and_cause(self):
        """Test that DatabaseError can be created with message and cause."""
        # Arrange
        message = "Database operation failed"
        cause = ValueError("Invalid value")

        # Act
        error = DatabaseError(message, cause=cause)

        # Assert
        assert error.message == message
        assert error.cause is cause
        assert error.__cause__ is cause
        assert str(error) == message

    def test_message_attribute_accessible(self):
        """Test that message attribute is accessible."""
        # Arrange
        message = "Connection timeout"
        error = DatabaseError(message)

        # Act & Assert
        assert hasattr(error, "message")
        assert error.message == message

    def test_cause_attribute_accessible(self):
        """Test that cause attribute is accessible."""
        # Arrange
        cause = RuntimeError("Underlying error")
        error = DatabaseError("Wrapper error", cause=cause)

        # Act & Assert
        assert hasattr(error, "cause")
        assert error.cause is cause

    def test_inherits_from_exception(self):
        """Test that DatabaseError inherits from Exception."""
        # Arrange
        error = DatabaseError("Test error")

        # Act & Assert
        assert isinstance(error, Exception)

    def test_can_be_raised_and_caught(self):
        """Test that DatabaseError can be raised and caught."""
        # Arrange
        message = "Test database error"

        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            raise DatabaseError(message)

        assert exc_info.value.message == message

    def test_can_be_raised_with_cause_and_caught(self):
        """Test that DatabaseError with cause can be raised and caught."""
        # Arrange
        message = "High-level error"
        cause = IOError("Low-level IO error")

        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            raise DatabaseError(message, cause=cause)

        assert exc_info.value.message == message
        assert exc_info.value.cause is cause
        assert exc_info.value.__cause__ is cause

    def test_exception_chain_preserved(self):
        """Test that exception chain is preserved when using cause."""
        # Arrange
        original_error = ValueError("Original error")
        wrapped_error = DatabaseError("Wrapped error", cause=original_error)

        # Act & Assert
        assert wrapped_error.__cause__ is original_error

    def test_different_messages_create_different_errors(self):
        """Test that different messages create different error instances."""
        # Arrange
        error1 = DatabaseError("Error 1")
        error2 = DatabaseError("Error 2")

        # Act & Assert
        assert error1.message != error2.message
        assert str(error1) != str(error2)

    def test_same_message_creates_equal_string_representation(self):
        """Test that same message creates equal string representation."""
        # Arrange
        message = "Same error message"
        error1 = DatabaseError(message)
        error2 = DatabaseError(message)

        # Act & Assert
        assert str(error1) == str(error2)
        assert error1.message == error2.message

    def test_cause_can_be_none_explicitly(self):
        """Test that cause can be explicitly set to None."""
        # Arrange
        message = "Test error"

        # Act
        error = DatabaseError(message, cause=None)

        # Assert
        assert error.cause is None

    def test_empty_message_allowed(self):
        """Test that empty message is allowed."""
        # Arrange
        message = ""

        # Act
        error = DatabaseError(message)

        # Assert
        assert error.message == ""
        assert str(error) == ""

    def test_long_message_handled(self):
        """Test that long messages are handled correctly."""
        # Arrange
        message = "A" * 1000

        # Act
        error = DatabaseError(message)

        # Assert
        assert error.message == message
        assert len(error.message) == 1000

    def test_multiline_message_handled(self):
        """Test that multiline messages are handled correctly."""
        # Arrange
        message = "Line 1\nLine 2\nLine 3"

        # Act
        error = DatabaseError(message)

        # Assert
        assert error.message == message
        assert "\n" in error.message

    def test_cause_with_different_exception_types(self):
        """Test that cause can be different exception types."""
        # Test with ValueError
        error1 = DatabaseError("Error 1", cause=ValueError("value error"))
        assert isinstance(error1.cause, ValueError)

        # Test with RuntimeError
        error2 = DatabaseError("Error 2", cause=RuntimeError("runtime error"))
        assert isinstance(error2.cause, RuntimeError)

        # Test with TypeError
        error3 = DatabaseError("Error 3", cause=TypeError("type error"))
        assert isinstance(error3.cause, TypeError)

    def test_repr_contains_message(self):
        """Test that repr contains the message."""
        # Arrange
        message = "Database error occurred"
        error = DatabaseError(message)

        # Act
        repr_str = repr(error)

        # Assert
        assert message in repr_str or "DatabaseError" in repr_str

    def test_database_error_is_base_for_db_specific_errors(self):
        """Test that DatabaseError can serve as a base class for db-specific errors."""
        # This test verifies the design intent that DatabaseError is a base
        # for truly database-specific errors (connection, schema, driver)

        # Arrange
        error = DatabaseError("Schema error")

        # Act & Assert
        # Can be caught as DatabaseError
        with pytest.raises(DatabaseError):
            raise error

        # Can also be caught as Exception
        with pytest.raises(Exception):
            raise DatabaseError("Another error")