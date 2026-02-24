"""Tests for db.adapters.sqlite.feed_post_adapter module."""

import sqlite3
from unittest.mock import Mock

import pytest

from db.adapters.sqlite.feed_post_adapter import SQLiteFeedPostAdapter
from simulation.core.models.posts import BlueskyFeedPost
from tests.db.adapters.sqlite.conftest import create_mock_row


@pytest.fixture
def adapter():
    """Create a SQLiteFeedPostAdapter instance."""
    return SQLiteFeedPostAdapter()


class TestSQLiteFeedPostAdapterReadFeedPostsByUris:
    """Tests for SQLiteFeedPostAdapter.read_feed_posts_by_uris method."""

    def test_returns_posts_when_found(self, adapter, mock_db_connection):
        """Test that read_feed_posts_by_uris returns list of posts when they exist."""
        # Arrange
        uris = ["uri1", "uri2", "uri3"]

        row_data_1 = {
            "uri": "uri1",
            "author_display_name": "Author 1",
            "author_handle": "author1.bsky.social",
            "text": "Post 1 text",
            "bookmark_count": 0,
            "like_count": 5,
            "quote_count": 0,
            "reply_count": 2,
            "repost_count": 1,
            "created_at": "2024_01_01-12:00:00",
        }
        row_data_2 = {
            "uri": "uri2",
            "author_display_name": "Author 2",
            "author_handle": "author2.bsky.social",
            "text": "Post 2 text",
            "bookmark_count": 1,
            "like_count": 10,
            "quote_count": 0,
            "reply_count": 3,
            "repost_count": 2,
            "created_at": "2024_01_01-12:01:00",
        }
        row_data_3 = {
            "uri": "uri3",
            "author_display_name": "Author 3",
            "author_handle": "author3.bsky.social",
            "text": "Post 3 text",
            "bookmark_count": 0,
            "like_count": 0,
            "quote_count": 0,
            "reply_count": 0,
            "repost_count": 0,
            "created_at": "2024_01_01-12:02:00",
        }
        mock_row_1 = create_mock_row(row_data_1)
        mock_row_2 = create_mock_row(row_data_2)
        mock_row_3 = create_mock_row(row_data_3)

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchall = Mock(
                return_value=[mock_row_1, mock_row_2, mock_row_3]
            )

            # Act
            result = adapter.read_feed_posts_by_uris(uris, conn=mock_conn)

            # Assert
            assert result is not None
            assert isinstance(result, list)
            assert len(result) == 3
            assert all(isinstance(post, BlueskyFeedPost) for post in result)
            assert result[0].uri == "uri1"
            assert result[0].text == "Post 1 text"
            assert result[1].uri == "uri2"
            assert result[2].uri == "uri3"

    def test_returns_empty_list_when_no_uris_provided(
        self, adapter, mock_db_connection
    ):
        """Test that read_feed_posts_by_uris returns empty list when no URIs provided."""
        # Arrange
        uris = []

        with mock_db_connection() as (mock_conn, mock_cursor):
            # Act
            result = adapter.read_feed_posts_by_uris(uris, conn=mock_conn)

            # Assert
            assert result is not None
            assert isinstance(result, list)
            assert len(result) == 0
            # Should not call database when empty list
            mock_conn.execute.assert_not_called()

    def test_returns_empty_list_when_no_posts_found(self, adapter, mock_db_connection):
        """Test that read_feed_posts_by_uris returns empty list when no posts exist."""
        # Arrange
        uris = ["nonexistent_uri1", "nonexistent_uri2"]

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchall = Mock(return_value=[])

            # Act
            result = adapter.read_feed_posts_by_uris(uris, conn=mock_conn)

            # Assert
            assert result is not None
            assert isinstance(result, list)
            assert len(result) == 0

    def test_returns_partial_results_when_some_uris_missing(
        self, adapter, mock_db_connection
    ):
        """Test that read_feed_posts_by_uris returns partial results when some URIs don't exist."""
        # Arrange
        uris = ["uri1", "nonexistent_uri", "uri2"]

        row_data_1 = {
            "uri": "uri1",
            "author_display_name": "Author 1",
            "author_handle": "author1.bsky.social",
            "text": "Post 1 text",
            "bookmark_count": 0,
            "like_count": 5,
            "quote_count": 0,
            "reply_count": 2,
            "repost_count": 1,
            "created_at": "2024_01_01-12:00:00",
        }
        row_data_2 = {
            "uri": "uri2",
            "author_display_name": "Author 2",
            "author_handle": "author2.bsky.social",
            "text": "Post 2 text",
            "bookmark_count": 0,
            "like_count": 10,
            "quote_count": 0,
            "reply_count": 3,
            "repost_count": 2,
            "created_at": "2024_01_01-12:01:00",
        }
        mock_row_1 = create_mock_row(row_data_1)
        mock_row_2 = create_mock_row(row_data_2)

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchall = Mock(return_value=[mock_row_1, mock_row_2])

            # Act
            result = adapter.read_feed_posts_by_uris(uris, conn=mock_conn)

            # Assert
            assert result is not None
            assert isinstance(result, list)
            assert len(result) == 2  # Only 2 posts found, 1 missing
            assert result[0].uri == "uri1"
            assert result[1].uri == "uri2"

    def test_preserves_input_order_when_database_returns_different_order(
        self, adapter, mock_db_connection
    ):
        """Test that read_feed_posts_by_uris preserves input URI order even if DB returns different order."""
        # Arrange
        # Input order: uri3, uri1, uri2
        uris = ["uri3", "uri1", "uri2"]

        row_data_1 = {
            "uri": "uri1",
            "author_display_name": "Author 1",
            "author_handle": "author1.bsky.social",
            "text": "Post 1 text",
            "bookmark_count": 0,
            "like_count": 5,
            "quote_count": 0,
            "reply_count": 2,
            "repost_count": 1,
            "created_at": "2024_01_01-12:00:00",
        }
        row_data_2 = {
            "uri": "uri2",
            "author_display_name": "Author 2",
            "author_handle": "author2.bsky.social",
            "text": "Post 2 text",
            "bookmark_count": 0,
            "like_count": 10,
            "quote_count": 0,
            "reply_count": 3,
            "repost_count": 2,
            "created_at": "2024_01_01-12:01:00",
        }
        row_data_3 = {
            "uri": "uri3",
            "author_display_name": "Author 3",
            "author_handle": "author3.bsky.social",
            "text": "Post 3 text",
            "bookmark_count": 0,
            "like_count": 0,
            "quote_count": 0,
            "reply_count": 0,
            "repost_count": 0,
            "created_at": "2024_01_01-12:02:00",
        }
        mock_row_1 = create_mock_row(row_data_1)
        mock_row_2 = create_mock_row(row_data_2)
        mock_row_3 = create_mock_row(row_data_3)

        with mock_db_connection() as (mock_conn, mock_cursor):
            # Database returns in different order: uri1, uri2, uri3
            mock_cursor.fetchall = Mock(
                return_value=[mock_row_1, mock_row_2, mock_row_3]
            )

            # Act
            result = adapter.read_feed_posts_by_uris(uris, conn=mock_conn)

            # Assert
            assert result is not None
            assert isinstance(result, list)
            assert len(result) == 3
            # Results should be in input order: uri3, uri1, uri2
            assert result[0].uri == "uri3"
            assert result[1].uri == "uri1"
            assert result[2].uri == "uri2"

    def test_raises_operational_error_on_database_error(
        self, adapter, mock_db_connection
    ):
        """Test that read_feed_posts_by_uris raises OperationalError on database error."""
        # Arrange
        uris = ["uri1", "uri2"]

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_conn.execute.side_effect = sqlite3.OperationalError("Database error")

            # Act & Assert
            with pytest.raises(sqlite3.OperationalError, match="Database error"):
                adapter.read_feed_posts_by_uris(uris, conn=mock_conn)

    def test_raises_keyerror_when_missing_required_column(
        self, adapter, mock_db_connection
    ):
        """Test that read_feed_posts_by_uris raises KeyError when required column is missing."""
        # Arrange
        uris = ["uri1"]

        # Missing "uri" column
        row_data = {
            "author_display_name": "Author 1",
            "author_handle": "author1.bsky.social",
            "text": "Post 1 text",
            "bookmark_count": 0,
            "like_count": 5,
            "quote_count": 0,
            "reply_count": 2,
            "repost_count": 1,
            "created_at": "2024_01_01-12:00:00",
        }
        mock_row = create_mock_row(row_data)

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchall = Mock(return_value=[mock_row])

            # Act & Assert
            with pytest.raises(KeyError):
                adapter.read_feed_posts_by_uris(uris, conn=mock_conn)

    def test_raises_valueerror_when_null_fields(self, adapter, mock_db_connection):
        """Test that read_feed_posts_by_uris raises ValueError when fields are NULL."""
        # Arrange
        uris = ["uri1"]

        # NULL uri
        row_data = {
            "uri": None,
            "author_display_name": "Author 1",
            "author_handle": "author1.bsky.social",
            "text": "Post 1 text",
            "bookmark_count": 0,
            "like_count": 5,
            "quote_count": 0,
            "reply_count": 2,
            "repost_count": 1,
            "created_at": "2024_01_01-12:00:00",
        }
        mock_row = create_mock_row(row_data)

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchall = Mock(return_value=[mock_row])

            # Act & Assert
            with pytest.raises(ValueError, match="uri cannot be NULL"):
                adapter.read_feed_posts_by_uris(uris, conn=mock_conn)

    def test_calls_database_with_correct_parameters_single_uri(
        self, adapter, mock_db_connection
    ):
        """Test that read_feed_posts_by_uris calls database with correct SQL for single URI."""
        # Arrange
        uris = ["uri1"]

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchall = Mock(return_value=[])

            # Act
            adapter.read_feed_posts_by_uris(uris, conn=mock_conn)

            # Assert
            mock_conn.execute.assert_called_once()
            call_args = mock_conn.execute.call_args
            # Should use parameterized IN clause
            assert "WHERE uri IN" in call_args[0][0]
            assert call_args[0][1] == tuple(uris)

    def test_calls_database_with_correct_parameters_multiple_uris(
        self, adapter, mock_db_connection
    ):
        """Test that read_feed_posts_by_uris calls database with correct SQL for multiple URIs."""
        # Arrange
        uris = ["uri1", "uri2", "uri3"]

        with mock_db_connection() as (mock_conn, mock_cursor):
            mock_cursor.fetchall = Mock(return_value=[])

            # Act
            adapter.read_feed_posts_by_uris(uris, conn=mock_conn)

            # Assert
            mock_conn.execute.assert_called_once()
            call_args = mock_conn.execute.call_args
            # Should use parameterized IN clause with correct number of placeholders
            assert "WHERE uri IN" in call_args[0][0]
            # Parameters should be tuple of URIs
            assert call_args[0][1] == tuple(uris)
