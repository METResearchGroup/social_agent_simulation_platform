"""Unit tests for db.exceptions module."""

import pytest

from db.exceptions import DatabaseError


class TestDatabaseError:
    """Tests for DatabaseError exception class."""

    def test_creates_database_error_with_message(self):
        """Test that DatabaseError can be created with a message."""
        # Arrange
        message = "Database connection failed"

        # Act
        error = DatabaseError(message)

        # Assert
        assert str(error) == message
        assert isinstance(error, Exception)

    def test_creates_database_error_with_empty_message(self):
        """Test that DatabaseError can be created with an empty message."""
        # Act
        error = DatabaseError("")

        # Assert
        assert str(error) == ""
        assert isinstance(error, Exception)

    def test_database_error_can_be_raised(self):
        """Test that DatabaseError can be raised and caught."""
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            raise DatabaseError("Test error")

        assert "Test error" in str(exc_info.value)

    def test_database_error_can_be_caught_as_exception(self):
        """Test that DatabaseError can be caught as generic Exception."""
        # Arrange
        def raises_database_error():
            raise DatabaseError("Database error occurred")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            raises_database_error()

        assert isinstance(exc_info.value, DatabaseError)
        assert "Database error occurred" in str(exc_info.value)

    def test_database_error_preserves_message(self):
        """Test that DatabaseError preserves the error message."""
        # Arrange
        messages = [
            "Connection timeout",
            "Table not found",
            "UNIQUE constraint failed",
            "Disk I/O error",
        ]

        for message in messages:
            # Act
            error = DatabaseError(message)

            # Assert
            assert str(error) == message

    def test_database_error_with_format_string(self):
        """Test that DatabaseError works with formatted strings."""
        # Arrange
        table_name = "users"
        message = f"Table {table_name} does not exist"

        # Act
        error = DatabaseError(message)

        # Assert
        assert "users" in str(error)
        assert "Table" in str(error)

    def test_database_error_equality(self):
        """Test DatabaseError equality comparison."""
        # Arrange
        error1 = DatabaseError("Test error")
        error2 = DatabaseError("Test error")
        error3 = DatabaseError("Different error")

        # Act & Assert
        assert str(error1) == str(error2)
        assert str(error1) != str(error3)

    def test_database_error_with_special_characters(self):
        """Test that DatabaseError handles special characters."""
        # Arrange
        message = "Error: table 'user's_data' not found\nLine 42"

        # Act
        error = DatabaseError(message)

        # Assert
        assert "user's_data" in str(error)
        assert "Line 42" in str(error)

    def test_database_error_inheritance_chain(self):
        """Test that DatabaseError is properly inherited from Exception."""
        # Arrange
        error = DatabaseError("Test")

        # Act & Assert
        assert isinstance(error, DatabaseError)
        assert isinstance(error, Exception)
        assert isinstance(error, BaseException)