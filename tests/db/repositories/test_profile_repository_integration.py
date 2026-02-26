"""Integration tests for db.repositories.profile_repository module.

These tests use a real SQLite database to test end-to-end functionality.
"""

import pytest
from pydantic import ValidationError

from tests.factories import BlueskyProfileFactory


class TestSQLiteProfileRepositoryIntegration:
    """Integration tests using a real database."""

    def test_create_and_read_profile(self, profile_repo):
        """Test creating a profile and reading it back from the database."""
        repo = profile_repo
        profile = BlueskyProfileFactory.create(
            handle="test.bsky.social",
            did="did:plc:test123",
            display_name="Test User",
            bio="Test bio",
            followers_count=100,
            follows_count=50,
            posts_count=25,
        )

        # Create profile
        created_profile = repo.create_or_update_profile(profile)
        assert created_profile.handle == "test.bsky.social"
        assert created_profile.display_name == "Test User"
        assert created_profile.followers_count == 100

        # Read it back
        retrieved_profile = repo.get_profile("test.bsky.social")
        assert retrieved_profile is not None
        assert retrieved_profile.handle == created_profile.handle
        assert retrieved_profile.did == created_profile.did
        assert retrieved_profile.display_name == created_profile.display_name
        assert retrieved_profile.bio == created_profile.bio
        assert retrieved_profile.followers_count == created_profile.followers_count
        assert retrieved_profile.follows_count == created_profile.follows_count
        assert retrieved_profile.posts_count == created_profile.posts_count

    def test_create_or_update_profile_updates_existing_profile(self, profile_repo):
        """Test that create_or_update_profile updates an existing profile."""
        repo = profile_repo

        # Create initial profile
        initial_profile = BlueskyProfileFactory.create(
            handle="test.bsky.social",
            did="did:plc:test123",
            display_name="Initial Name",
            bio="Initial bio",
            followers_count=100,
            follows_count=50,
            posts_count=25,
        )
        repo.create_or_update_profile(initial_profile)

        # Update the profile
        updated_profile = BlueskyProfileFactory.create(
            handle="test.bsky.social",
            did="did:plc:test123",
            display_name="Updated Name",
            bio="Updated bio with more text",
            followers_count=5000,
            follows_count=200,
            posts_count=150,
        )
        repo.create_or_update_profile(updated_profile)

        # Verify update
        retrieved_profile = repo.get_profile("test.bsky.social")
        assert retrieved_profile is not None
        assert retrieved_profile.handle == "test.bsky.social"
        assert retrieved_profile.display_name == "Updated Name"
        assert retrieved_profile.bio == "Updated bio with more text"
        assert retrieved_profile.followers_count == 5000
        assert retrieved_profile.follows_count == 200
        assert retrieved_profile.posts_count == 150

    def test_get_profile_returns_none_for_nonexistent_handle(self, profile_repo):
        """Test that get_profile returns None for a non-existent handle."""
        repo = profile_repo

        result = repo.get_profile("nonexistent.bsky.social")
        assert result is None

    def test_list_profiles_returns_empty_list_when_no_profiles(self, profile_repo):
        """Test that list_profiles returns an empty list when no profiles exist."""
        repo = profile_repo

        profiles = repo.list_profiles()
        assert profiles == []
        assert isinstance(profiles, list)

    def test_list_profiles_returns_all_profiles(self, profile_repo):
        """Test that list_profiles returns all profiles from the database."""
        repo = profile_repo

        # Create multiple profiles
        profile1 = BlueskyProfileFactory.create(
            handle="user1.bsky.social",
            did="did:plc:user1",
            display_name="User 1",
            bio="Bio 1",
            followers_count=100,
            follows_count=50,
            posts_count=25,
        )
        profile2 = BlueskyProfileFactory.create(
            handle="user2.bsky.social",
            did="did:plc:user2",
            display_name="User 2",
            bio="Bio 2",
            followers_count=200,
            follows_count=100,
            posts_count=50,
        )
        profile3 = BlueskyProfileFactory.create(
            handle="user3.bsky.social",
            did="did:plc:user3",
            display_name="User 3",
            bio="Bio 3",
            followers_count=300,
            follows_count=150,
            posts_count=75,
        )

        repo.create_or_update_profile(profile1)
        repo.create_or_update_profile(profile2)
        repo.create_or_update_profile(profile3)

        # List all profiles
        profiles = repo.list_profiles()

        # Assert
        assert len(profiles) == 3
        handles = {p.handle for p in profiles}
        assert handles == {
            "user1.bsky.social",
            "user2.bsky.social",
            "user3.bsky.social",
        }

        # Verify all fields are correct
        profile_dict = {p.handle: p for p in profiles}
        assert profile_dict["user1.bsky.social"].display_name == "User 1"
        assert profile_dict["user2.bsky.social"].followers_count == 200
        assert profile_dict["user3.bsky.social"].posts_count == 75

    def test_create_or_update_profile_with_empty_handle_raises_error(
        self, profile_repo
    ):
        """Test that creating BlueskyProfile with empty handle raises ValidationError from Pydantic."""
        # Pydantic validation happens at model creation time, not in repository
        with pytest.raises(ValidationError) as exc_info:
            BlueskyProfileFactory.create(
                handle="",
                did="did:plc:test123",
                display_name="Test User",
                bio="Test bio",
                followers_count=100,
                follows_count=50,
                posts_count=25,
            )

        assert "handle cannot be empty" in str(exc_info.value)

    def test_get_profile_with_empty_handle_raises_error(self, profile_repo):
        """Test that get_profile raises ValueError when handle is empty."""
        repo = profile_repo

        with pytest.raises(ValueError, match="handle cannot be empty"):
            repo.get_profile("")

    def test_multiple_profiles_with_different_handles(self, profile_repo):
        """Test that multiple profiles with different handles can coexist."""
        repo = profile_repo

        profile1 = BlueskyProfileFactory.create(
            handle="alice.bsky.social",
            did="did:plc:alice",
            display_name="Alice",
            bio="Alice's bio",
            followers_count=1000,
            follows_count=500,
            posts_count=100,
        )
        profile2 = BlueskyProfileFactory.create(
            handle="bob.bsky.social",
            did="did:plc:bob",
            display_name="Bob",
            bio="Bob's bio",
            followers_count=2000,
            follows_count=600,
            posts_count=200,
        )

        repo.create_or_update_profile(profile1)
        repo.create_or_update_profile(profile2)

        # Retrieve each profile
        alice = repo.get_profile("alice.bsky.social")
        bob = repo.get_profile("bob.bsky.social")

        assert alice is not None
        assert bob is not None
        assert alice.handle == "alice.bsky.social"
        assert bob.handle == "bob.bsky.social"
        assert alice.display_name == "Alice"
        assert bob.display_name == "Bob"
        assert alice.followers_count == 1000
        assert bob.followers_count == 2000

    def test_profile_with_long_bio(self, profile_repo):
        """Test that profiles with long bios are handled correctly."""
        repo = profile_repo

        long_bio = "This is a very long bio. " * 50  # 1000+ characters
        profile = BlueskyProfileFactory.create(
            handle="longbio.bsky.social",
            did="did:plc:longbio",
            display_name="Long Bio User",
            bio=long_bio,
            followers_count=5000,
            follows_count=1000,
            posts_count=500,
        )

        repo.create_or_update_profile(profile)
        retrieved = repo.get_profile("longbio.bsky.social")

        assert retrieved is not None
        assert retrieved.bio == long_bio
        assert len(retrieved.bio) > 1000

    def test_profile_with_special_characters_in_handle(self, profile_repo):
        """Test that profiles with special characters in handle work correctly."""
        repo = profile_repo

        # Note: Bluesky handles typically don't have special chars, but test edge cases
        profile = BlueskyProfileFactory.create(
            handle="user-name.bsky.social",
            did="did:plc:username",
            display_name="User Name",
            bio="Bio with special chars: !@#$%",
            followers_count=100,
            follows_count=50,
            posts_count=25,
        )

        repo.create_or_update_profile(profile)
        retrieved = repo.get_profile("user-name.bsky.social")

        assert retrieved is not None
        assert retrieved.handle == "user-name.bsky.social"
        assert retrieved.bio == "Bio with special chars: !@#$%"
