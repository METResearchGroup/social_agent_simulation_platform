"""Integration tests for db.repositories.generated_bio_repository module.

These tests use a real SQLite database to test end-to-end functionality.
"""

import os
import tempfile

import pytest

from db.adapters.sqlite.sqlite import DB_PATH, initialize_database
from db.repositories.generated_bio_repository import (
    create_sqlite_generated_bio_repository,
)
from lib.timestamp_utils import get_current_timestamp
from simulation.core.models.generated.base import GenerationMetadata
from simulation.core.models.generated.bio import GeneratedBio


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    # Save original DB path
    original_path = DB_PATH

    # Create temporary database
    fd, temp_path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)

    import db.adapters.sqlite.sqlite as sqlite_module

    sqlite_module.DB_PATH = temp_path

    # Initialize the database
    initialize_database()

    yield temp_path

    # Cleanup
    sqlite_module.DB_PATH = original_path
    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestSQLiteGeneratedBioRepositoryIntegration:
    """Integration tests using a real database."""

    def test_create_or_update_generated_bio_persists_to_database(self, temp_db):
        """Test that create_or_update_generated_bio persists a bio to the database."""
        repo = create_sqlite_generated_bio_repository()
        bio = GeneratedBio(
            handle="test.bsky.social",
            generated_bio="This is a test bio for the profile.",
            metadata=GenerationMetadata(
                model_used=None,
                generation_metadata=None,
                created_at=get_current_timestamp(),
            ),
        )

        # Create bio
        created_bio = repo.create_or_update_generated_bio(bio)
        assert created_bio.handle == "test.bsky.social"
        assert created_bio.generated_bio == "This is a test bio for the profile."

        # Read it back
        retrieved_bio = repo.get_generated_bio("test.bsky.social")
        assert retrieved_bio is not None
        assert retrieved_bio.handle == created_bio.handle
        assert retrieved_bio.generated_bio == created_bio.generated_bio
        assert retrieved_bio.metadata.created_at == created_bio.metadata.created_at

    def test_get_generated_bio_retrieves_from_database(self, temp_db):
        """Test that get_generated_bio retrieves a bio from the database."""
        repo = create_sqlite_generated_bio_repository()
        bio = GeneratedBio(
            handle="retrieve.bsky.social",
            generated_bio="This bio should be retrievable.",
            metadata=GenerationMetadata(
                model_used=None,
                generation_metadata=None,
                created_at=get_current_timestamp(),
            ),
        )

        # Create the bio first
        repo.create_or_update_generated_bio(bio)

        # Retrieve it
        retrieved_bio = repo.get_generated_bio("retrieve.bsky.social")
        assert retrieved_bio is not None
        assert retrieved_bio.handle == "retrieve.bsky.social"
        assert retrieved_bio.generated_bio == "This bio should be retrievable."

    def test_list_all_generated_bios_retrieves_all_bios(self, temp_db):
        """Test that list_all_generated_bios retrieves all bios from the database."""
        repo = create_sqlite_generated_bio_repository()

        # Create multiple bios
        bio1 = GeneratedBio(
            handle="user1.bsky.social",
            generated_bio="Bio 1",
            metadata=GenerationMetadata(
                model_used=None,
                generation_metadata=None,
                created_at=get_current_timestamp(),
            ),
        )
        bio2 = GeneratedBio(
            handle="user2.bsky.social",
            generated_bio="Bio 2",
            metadata=GenerationMetadata(
                model_used=None,
                generation_metadata=None,
                created_at=get_current_timestamp(),
            ),
        )
        bio3 = GeneratedBio(
            handle="user3.bsky.social",
            generated_bio="Bio 3",
            metadata=GenerationMetadata(
                model_used=None,
                generation_metadata=None,
                created_at=get_current_timestamp(),
            ),
        )

        repo.create_or_update_generated_bio(bio1)
        repo.create_or_update_generated_bio(bio2)
        repo.create_or_update_generated_bio(bio3)

        # List all bios
        bios = repo.list_all_generated_bios()

        # Assert
        assert len(bios) == 3
        handles = {b.handle for b in bios}
        assert handles == {
            "user1.bsky.social",
            "user2.bsky.social",
            "user3.bsky.social",
        }

        # Verify all fields are correct
        bio_dict = {b.handle: b for b in bios}
        assert bio_dict["user1.bsky.social"].generated_bio == "Bio 1"
        assert bio_dict["user2.bsky.social"].generated_bio == "Bio 2"
        assert bio_dict["user3.bsky.social"].generated_bio == "Bio 3"

    def test_create_or_update_generated_bio_updates_existing_bio(self, temp_db):
        """Test that create_or_update_generated_bio updates an existing bio."""
        repo = create_sqlite_generated_bio_repository()

        # Create initial bio
        initial_bio = GeneratedBio(
            handle="update.bsky.social",
            generated_bio="Initial bio text",
            metadata=GenerationMetadata(
                model_used=None,
                generation_metadata=None,
                created_at=get_current_timestamp(),
            ),
        )
        repo.create_or_update_generated_bio(initial_bio)

        # Update the bio (same handle, different content)
        updated_bio = GeneratedBio(
            handle="update.bsky.social",
            generated_bio="Updated bio text with more information",
            metadata=GenerationMetadata(
                model_used=None,
                generation_metadata=None,
                created_at=get_current_timestamp(),
            ),
        )
        repo.create_or_update_generated_bio(updated_bio)

        # Verify update
        retrieved_bio = repo.get_generated_bio("update.bsky.social")
        assert retrieved_bio is not None
        assert retrieved_bio.handle == "update.bsky.social"
        assert retrieved_bio.generated_bio == "Updated bio text with more information"
        # Note: created_at will be the updated timestamp since we use INSERT OR REPLACE

    def test_get_generated_bio_returns_none_for_nonexistent_handle(self, temp_db):
        """Test that get_generated_bio returns None for a non-existent handle."""
        repo = create_sqlite_generated_bio_repository()

        result = repo.get_generated_bio("nonexistent.bsky.social")
        assert result is None

    def test_generated_bio_with_long_text_content(self, temp_db):
        """Test that generated bios with long text content are handled correctly."""
        repo = create_sqlite_generated_bio_repository()

        long_bio_text = "This is a very long bio. " * 100  # 2500 characters
        bio = GeneratedBio(
            handle="longbio.bsky.social",
            generated_bio=long_bio_text,
            metadata=GenerationMetadata(
                model_used=None,
                generation_metadata=None,
                created_at=get_current_timestamp(),
            ),
        )

        repo.create_or_update_generated_bio(bio)
        retrieved = repo.get_generated_bio("longbio.bsky.social")

        assert retrieved is not None
        expected_bio = long_bio_text.strip()
        assert retrieved.generated_bio == expected_bio
        assert len(retrieved.generated_bio) >= 2299

    def test_multiple_bios_with_different_handles(self, temp_db):
        """Test that multiple bios with different handles can coexist."""
        repo = create_sqlite_generated_bio_repository()

        bio1 = GeneratedBio(
            handle="alice.bsky.social",
            generated_bio="Alice's bio",
            metadata=GenerationMetadata(
                model_used=None,
                generation_metadata=None,
                created_at=get_current_timestamp(),
            ),
        )
        bio2 = GeneratedBio(
            handle="bob.bsky.social",
            generated_bio="Bob's bio",
            metadata=GenerationMetadata(
                model_used=None,
                generation_metadata=None,
                created_at=get_current_timestamp(),
            ),
        )

        repo.create_or_update_generated_bio(bio1)
        repo.create_or_update_generated_bio(bio2)

        # Retrieve each bio
        alice_bio = repo.get_generated_bio("alice.bsky.social")
        bob_bio = repo.get_generated_bio("bob.bsky.social")

        assert alice_bio is not None
        assert bob_bio is not None
        assert alice_bio.handle == "alice.bsky.social"
        assert bob_bio.handle == "bob.bsky.social"
        assert alice_bio.generated_bio == "Alice's bio"
        assert bob_bio.generated_bio == "Bob's bio"

    def test_list_all_generated_bios_returns_empty_list_when_no_bios(self, temp_db):
        """Test that list_all_generated_bios returns an empty list when no bios exist."""
        repo = create_sqlite_generated_bio_repository()

        bios = repo.list_all_generated_bios()
        assert bios == []
        assert isinstance(bios, list)

    def test_get_generated_bio_with_empty_handle_raises_error(self, temp_db):
        """Test that get_generated_bio raises ValueError when handle is empty."""
        repo = create_sqlite_generated_bio_repository()

        with pytest.raises(ValueError, match="handle cannot be empty"):
            repo.get_generated_bio("")

    def test_generated_bio_with_special_characters(self, temp_db):
        """Test that generated bios with special characters work correctly."""
        repo = create_sqlite_generated_bio_repository()

        bio_text = "Bio with special chars: !@#$%^&*() and unicode: 🚀✨"
        bio = GeneratedBio(
            handle="special.bsky.social",
            generated_bio=bio_text,
            metadata=GenerationMetadata(
                model_used=None,
                generation_metadata=None,
                created_at=get_current_timestamp(),
            ),
        )

        repo.create_or_update_generated_bio(bio)
        retrieved = repo.get_generated_bio("special.bsky.social")

        assert retrieved is not None
        assert retrieved.generated_bio == bio_text
