"""Tests for db.repositories.profile_repository module."""

from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from db.adapters.base import ProfileDatabaseAdapter
from db.repositories.profile_repository import SQLiteProfileRepository
from simulation.core.models.profiles import BlueskyProfile
from tests.db.repositories.conftest import make_mock_transaction_provider


class TestSQLiteProfileRepositoryCreateOrUpdateProfile:
    """Tests for SQLiteProfileRepository.create_or_update_profile method."""

    def test_creates_profile_with_correct_values(self):
        """Test that create_or_update_profile creates a profile with correct values."""
        # Arrange
        mock_adapter = Mock(spec=ProfileDatabaseAdapter)
        repo = SQLiteProfileRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        profile = BlueskyProfile(
            handle="test.bsky.social",
            did="did:plc:test123",
            display_name="Test User",
            bio="Test bio",
            followers_count=100,
            follows_count=50,
            posts_count=25,
        )

        # Act
        result = repo.create_or_update_profile(profile)

        # Assert
        assert result == profile
        mock_adapter.write_profile.assert_called_once()
        assert mock_adapter.write_profile.call_args[0][0] == profile
        assert mock_adapter.write_profile.call_args[1]["conn"] is not None

    def test_creates_profile_with_different_values(self):
        """Test that create_or_update_profile handles different profile values correctly."""
        # Arrange
        mock_adapter = Mock(spec=ProfileDatabaseAdapter)
        repo = SQLiteProfileRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        profile = BlueskyProfile(
            handle="another.bsky.social",
            did="did:plc:another456",
            display_name="Another User",
            bio="Another bio with more text",
            followers_count=5000,
            follows_count=200,
            posts_count=150,
        )

        # Act
        result = repo.create_or_update_profile(profile)

        # Assert
        assert result.handle == "another.bsky.social"
        assert result.followers_count == 5000
        assert result.posts_count == 150
        mock_adapter.write_profile.assert_called_once()
        assert mock_adapter.write_profile.call_args[0][0] == profile
        assert mock_adapter.write_profile.call_args[1]["conn"] is not None

    def test_persists_profile_to_database(self):
        """Test that create_or_update_profile persists the profile to the database via write_profile."""
        # Arrange
        mock_adapter = Mock(spec=ProfileDatabaseAdapter)
        repo = SQLiteProfileRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        profile = BlueskyProfile(
            handle="test.bsky.social",
            did="did:plc:test123",
            display_name="Test User",
            bio="Test bio",
            followers_count=100,
            follows_count=50,
            posts_count=25,
        )

        # Act
        result = repo.create_or_update_profile(profile)

        # Assert
        mock_adapter.write_profile.assert_called_once()
        assert mock_adapter.write_profile.call_args[1]["conn"] is not None
        call_args = mock_adapter.write_profile.call_args[0][0]
        assert isinstance(call_args, BlueskyProfile)
        assert call_args.handle == result.handle
        assert call_args.display_name == result.display_name
        assert call_args.bio == result.bio

    def test_raises_validation_error_when_handle_is_empty(self):
        """Test that creating BlueskyProfile with empty handle raises ValidationError from Pydantic."""
        # Arrange & Act & Assert
        # Pydantic validation happens at model creation time, not in repository
        with pytest.raises(ValidationError) as exc_info:
            BlueskyProfile(
                handle="",
                did="did:plc:test123",
                display_name="Test User",
                bio="Test bio",
                followers_count=100,
                follows_count=50,
                posts_count=25,
            )

        assert "handle cannot be empty" in str(exc_info.value)

    def test_raises_validation_error_when_handle_is_whitespace(self):
        """Test that creating BlueskyProfile with whitespace handle raises ValidationError from Pydantic."""
        # Arrange & Act & Assert
        # Pydantic validation happens at model creation time, not in repository
        with pytest.raises(ValidationError) as exc_info:
            BlueskyProfile(
                handle="   ",
                did="did:plc:test123",
                display_name="Test User",
                bio="Test bio",
                followers_count=100,
                follows_count=50,
                posts_count=25,
            )

        assert "handle cannot be empty" in str(exc_info.value)

    def test_propagates_adapter_exception_when_write_fails(self):
        """Test that create_or_update_profile propagates adapter exceptions when database write fails."""
        # Arrange
        mock_adapter = Mock(spec=ProfileDatabaseAdapter)
        mock_adapter.write_profile.side_effect = Exception("Database error")
        repo = SQLiteProfileRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        profile = BlueskyProfile(
            handle="test.bsky.social",
            did="did:plc:test123",
            display_name="Test User",
            bio="Test bio",
            followers_count=100,
            follows_count=50,
            posts_count=25,
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            repo.create_or_update_profile(profile)

        assert "Database error" in str(exc_info.value)
        assert exc_info.value is mock_adapter.write_profile.side_effect

    def test_propagates_adapter_exception_directly(self):
        """Test that create_or_update_profile propagates adapter exceptions directly."""
        # Arrange
        mock_adapter = Mock(spec=ProfileDatabaseAdapter)
        db_error = Exception("DB error")
        mock_adapter.write_profile.side_effect = db_error
        repo = SQLiteProfileRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        profile = BlueskyProfile(
            handle="specific.bsky.social",
            did="did:plc:test123",
            display_name="Test User",
            bio="Test bio",
            followers_count=100,
            follows_count=50,
            posts_count=25,
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            repo.create_or_update_profile(profile)

        assert exc_info.value is db_error
        assert "DB error" in str(exc_info.value)

    def test_propagates_original_exception_directly(self):
        """Test that create_or_update_profile propagates the original exception directly."""
        # Arrange
        mock_adapter = Mock(spec=ProfileDatabaseAdapter)
        original_error = ValueError("Invalid data")
        mock_adapter.write_profile.side_effect = original_error
        repo = SQLiteProfileRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        profile = BlueskyProfile(
            handle="test.bsky.social",
            did="did:plc:test123",
            display_name="Test User",
            bio="Test bio",
            followers_count=100,
            follows_count=50,
            posts_count=25,
        )

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            repo.create_or_update_profile(profile)

        assert exc_info.value is original_error
        assert "Invalid data" in str(exc_info.value)


class TestSQLiteProfileRepositoryGetProfile:
    """Tests for SQLiteProfileRepository.get_profile method."""

    def test_returns_profile_when_found(self):
        """Test that get_profile returns a profile when it exists in the database."""
        # Arrange
        mock_adapter = Mock(spec=ProfileDatabaseAdapter)
        repo = SQLiteProfileRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        handle = "test.bsky.social"
        expected = BlueskyProfile(
            handle=handle,
            did="did:plc:test123",
            display_name="Test User",
            bio="Test bio",
            followers_count=100,
            follows_count=50,
            posts_count=25,
        )
        mock_adapter.read_profile.return_value = expected

        # Act
        result = repo.get_profile(handle)

        # Assert
        assert result is not None
        assert result.handle == expected.handle
        assert result.did == expected.did
        assert result.display_name == expected.display_name
        assert result.bio == expected.bio
        assert result.followers_count == expected.followers_count
        assert result.follows_count == expected.follows_count
        assert result.posts_count == expected.posts_count
        mock_adapter.read_profile.assert_called_once()
        assert mock_adapter.read_profile.call_args[0][0] == handle
        assert mock_adapter.read_profile.call_args[1]["conn"] is not None

    def test_returns_none_when_profile_not_found(self):
        """Test that get_profile returns None when profile does not exist."""
        # Arrange
        mock_adapter = Mock(spec=ProfileDatabaseAdapter)
        repo = SQLiteProfileRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        handle = "nonexistent.bsky.social"
        mock_adapter.read_profile.return_value = None

        # Act
        result = repo.get_profile(handle)

        # Assert
        assert result is None
        mock_adapter.read_profile.assert_called_once()
        assert mock_adapter.read_profile.call_args[0][0] == handle
        assert mock_adapter.read_profile.call_args[1]["conn"] is not None

    def test_calls_read_profile_with_correct_handle(self):
        """Test that get_profile calls read_profile with the correct handle parameter."""
        # Arrange
        mock_adapter = Mock(spec=ProfileDatabaseAdapter)
        repo = SQLiteProfileRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        handle = "test.bsky.social"
        mock_adapter.read_profile.return_value = None

        # Act
        repo.get_profile(handle)

        # Assert
        mock_adapter.read_profile.assert_called_once()
        assert mock_adapter.read_profile.call_args[0][0] == handle
        assert mock_adapter.read_profile.call_args[1]["conn"] is not None

    def test_returns_profile_with_all_fields(self):
        """Test that get_profile returns a profile with all fields correctly populated."""
        # Arrange
        mock_adapter = Mock(spec=ProfileDatabaseAdapter)
        repo = SQLiteProfileRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        handle = "test.bsky.social"
        expected = BlueskyProfile(
            handle=handle,
            did="did:plc:test123",
            display_name="Test User With Long Name",
            bio="This is a longer bio that contains multiple sentences and more information about the user.",
            followers_count=12345,
            follows_count=678,
            posts_count=999,
        )
        mock_adapter.read_profile.return_value = expected

        # Act
        result = repo.get_profile(handle)

        # Assert
        assert result is not None
        assert result.handle == handle
        assert result.did == "did:plc:test123"
        assert result.display_name == "Test User With Long Name"
        assert (
            result.bio
            == "This is a longer bio that contains multiple sentences and more information about the user."
        )
        assert result.followers_count == 12345
        assert result.follows_count == 678
        assert result.posts_count == 999

    def test_raises_value_error_when_handle_is_empty(self):
        """Test that get_profile raises ValueError when handle is empty."""
        # Arrange
        mock_adapter = Mock(spec=ProfileDatabaseAdapter)
        repo = SQLiteProfileRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="handle cannot be empty"):
            repo.get_profile("")

        mock_adapter.read_profile.assert_not_called()

    def test_raises_value_error_when_handle_is_whitespace(self):
        """Test that get_profile raises ValueError when handle is whitespace."""
        # Arrange
        mock_adapter = Mock(spec=ProfileDatabaseAdapter)
        repo = SQLiteProfileRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="handle cannot be empty"):
            repo.get_profile("   ")

        mock_adapter.read_profile.assert_not_called()


class TestSQLiteProfileRepositoryListProfiles:
    """Tests for SQLiteProfileRepository.list_profiles method."""

    def test_returns_empty_list_when_no_profiles_exist(self):
        """Test that list_profiles returns an empty list when no profiles exist."""
        # Arrange
        mock_adapter = Mock(spec=ProfileDatabaseAdapter)
        repo = SQLiteProfileRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        expected = []
        mock_adapter.read_all_profiles.return_value = expected

        # Act
        result = repo.list_profiles()

        # Assert
        assert result == expected
        assert isinstance(result, list)
        assert len(result) == 0
        mock_adapter.read_all_profiles.assert_called_once()
        assert mock_adapter.read_all_profiles.call_args[1]["conn"] is not None

    def test_returns_all_profiles_when_profiles_exist(self):
        """Test that list_profiles returns all profiles from the database."""
        # Arrange
        mock_adapter = Mock(spec=ProfileDatabaseAdapter)
        repo = SQLiteProfileRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        expected = [
            BlueskyProfile(
                handle="user1.bsky.social",
                did="did:plc:user1",
                display_name="User 1",
                bio="Bio 1",
                followers_count=100,
                follows_count=50,
                posts_count=25,
            ),
            BlueskyProfile(
                handle="user2.bsky.social",
                did="did:plc:user2",
                display_name="User 2",
                bio="Bio 2",
                followers_count=200,
                follows_count=100,
                posts_count=50,
            ),
        ]
        mock_adapter.read_all_profiles.return_value = expected

        # Act
        result = repo.list_profiles()

        # Assert
        assert len(result) == 2
        assert result[0].handle == "user1.bsky.social"
        assert result[1].handle == "user2.bsky.social"
        assert result[0].display_name == "User 1"
        assert result[1].display_name == "User 2"

    def test_returns_profiles_in_correct_order(self):
        """Test that list_profiles returns profiles in the order provided by read_all_profiles."""
        # Arrange
        mock_adapter = Mock(spec=ProfileDatabaseAdapter)
        repo = SQLiteProfileRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        expected = [
            BlueskyProfile(
                handle="first.bsky.social",
                did="did:plc:first",
                display_name="First User",
                bio="First bio",
                followers_count=100,
                follows_count=50,
                posts_count=25,
            ),
            BlueskyProfile(
                handle="second.bsky.social",
                did="did:plc:second",
                display_name="Second User",
                bio="Second bio",
                followers_count=200,
                follows_count=100,
                posts_count=50,
            ),
        ]
        mock_adapter.read_all_profiles.return_value = expected

        # Act
        result = repo.list_profiles()

        # Assert
        assert result[0].handle == "first.bsky.social"
        assert result[1].handle == "second.bsky.social"

    def test_calls_read_all_profiles_once(self):
        """Test that list_profiles calls read_all_profiles exactly once."""
        # Arrange
        mock_adapter = Mock(spec=ProfileDatabaseAdapter)
        repo = SQLiteProfileRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        mock_adapter.read_all_profiles.return_value = []

        # Act
        repo.list_profiles()

        # Assert
        mock_adapter.read_all_profiles.assert_called_once()
        assert mock_adapter.read_all_profiles.call_args[1]["conn"] is not None

    def test_handles_large_number_of_profiles(self):
        """Test that list_profiles handles a large number of profiles correctly."""
        # Arrange
        mock_adapter = Mock(spec=ProfileDatabaseAdapter)
        repo = SQLiteProfileRepository(
            db_adapter=mock_adapter,
            transaction_provider=make_mock_transaction_provider(),
        )
        expected = [
            BlueskyProfile(
                handle=f"user{i}.bsky.social",
                did=f"did:plc:user{i}",
                display_name=f"User {i}",
                bio=f"Bio {i}",
                followers_count=100 + i,
                follows_count=50 + i,
                posts_count=25 + i,
            )
            for i in range(100)
        ]
        mock_adapter.read_all_profiles.return_value = expected

        # Act
        result = repo.list_profiles()

        # Assert
        assert len(result) == 100
        assert all(isinstance(profile, BlueskyProfile) for profile in result)
        assert result[0].handle == "user0.bsky.social"
        assert result[99].handle == "user99.bsky.social"
