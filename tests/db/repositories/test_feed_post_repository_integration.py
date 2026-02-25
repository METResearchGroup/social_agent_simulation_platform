"""Integration tests for db.repositories.feed_post_repository module.

These tests use a real SQLite database to test end-to-end functionality.
"""

import pytest

from simulation.core.models.posts import BlueskyFeedPost
from tests.factories import PostFactory


class TestSQLiteFeedPostRepositoryIntegration:
    """Integration tests using a real database."""

    def test_create_and_read_feed_post(self, feed_post_repo):
        """Test creating a feed post and reading it back from the database."""
        repo = feed_post_repo
        post = PostFactory.create(
            id="at://did:plc:test123/app.bsky.feed.post/test",
            uri="at://did:plc:test123/app.bsky.feed.post/test",
            author_display_name="Test User",
            author_handle="test.bsky.social",
            text="Test post content",
            bookmark_count=5,
            like_count=10,
            quote_count=2,
            reply_count=3,
            repost_count=1,
            created_at="2024-01-01T00:00:00Z",
        )

        # Create post
        created_post = repo.create_or_update_feed_post(post)
        assert created_post.uri == "at://did:plc:test123/app.bsky.feed.post/test"
        assert created_post.text == "Test post content"
        assert created_post.like_count == 10

        # Read it back
        retrieved_post = repo.get_feed_post(
            "at://did:plc:test123/app.bsky.feed.post/test"
        )
        assert retrieved_post is not None
        assert retrieved_post.uri == created_post.uri
        assert retrieved_post.author_display_name == created_post.author_display_name
        assert retrieved_post.author_handle == created_post.author_handle
        assert retrieved_post.text == created_post.text
        assert retrieved_post.bookmark_count == created_post.bookmark_count
        assert retrieved_post.like_count == created_post.like_count
        assert retrieved_post.quote_count == created_post.quote_count
        assert retrieved_post.reply_count == created_post.reply_count
        assert retrieved_post.repost_count == created_post.repost_count
        assert retrieved_post.created_at == created_post.created_at

    def test_create_or_update_feed_posts_batch_persists_to_database(
        self, feed_post_repo
    ):
        """Test that create_or_update_feed_posts (batch) persists multiple posts to the database."""
        repo = feed_post_repo
        posts = [
            PostFactory.create(
                id=f"at://did:plc:test{i}/app.bsky.feed.post/test{i}",
                uri=f"at://did:plc:test{i}/app.bsky.feed.post/test{i}",
                author_display_name=f"User {i}",
                author_handle=f"user{i}.bsky.social",
                text=f"Post {i} content",
                bookmark_count=i,
                like_count=i * 10,
                quote_count=i * 2,
                reply_count=i * 3,
                repost_count=i,
                created_at=f"2024-01-0{i}T00:00:00Z",
            )
            for i in range(1, 4)
        ]

        # Create posts in batch
        created_posts = repo.create_or_update_feed_posts(posts)
        assert len(created_posts) == 3

        # Read them back individually
        for i, post in enumerate(posts, 1):
            retrieved = repo.get_feed_post(post.uri)
            assert retrieved is not None
            assert retrieved.uri == post.uri
            assert retrieved.text == post.text
            assert retrieved.like_count == post.like_count

    def test_create_or_update_feed_post_updates_existing_post(self, feed_post_repo):
        """Test that create_or_update_feed_post updates an existing post."""
        repo = feed_post_repo

        # Create initial post
        initial_post = PostFactory.create(
            id="at://did:plc:test123/app.bsky.feed.post/test",
            uri="at://did:plc:test123/app.bsky.feed.post/test",
            author_display_name="Initial Name",
            author_handle="test.bsky.social",
            text="Initial content",
            bookmark_count=5,
            like_count=10,
            quote_count=2,
            reply_count=3,
            repost_count=1,
            created_at="2024-01-01T00:00:00Z",
        )
        repo.create_or_update_feed_post(initial_post)

        # Update the post
        updated_post = PostFactory.create(
            id="at://did:plc:test123/app.bsky.feed.post/test",
            uri="at://did:plc:test123/app.bsky.feed.post/test",
            author_display_name="Updated Name",
            author_handle="test.bsky.social",
            text="Updated content with more text",
            bookmark_count=50,
            like_count=200,
            quote_count=10,
            reply_count=25,
            repost_count=15,
            created_at="2024-01-01T00:00:00Z",
        )
        repo.create_or_update_feed_post(updated_post)

        # Verify update
        retrieved_post = repo.get_feed_post(
            "at://did:plc:test123/app.bsky.feed.post/test"
        )
        assert retrieved_post is not None
        assert retrieved_post.uri == "at://did:plc:test123/app.bsky.feed.post/test"
        assert retrieved_post.text == "Updated content with more text"
        assert retrieved_post.like_count == 200
        assert retrieved_post.reply_count == 25
        assert retrieved_post.repost_count == 15

    def test_get_feed_post_raises_value_error_for_nonexistent_uri(self, feed_post_repo):
        """Test that get_feed_post raises ValueError for a non-existent URI."""
        repo = feed_post_repo

        with pytest.raises(ValueError, match="No feed post found for uri"):
            repo.get_feed_post("at://did:plc:nonexistent/app.bsky.feed.post/test")

    def test_list_feed_posts_by_author_retrieves_correct_posts(self, feed_post_repo):
        """Test that list_feed_posts_by_author filters correctly by author."""
        repo = feed_post_repo

        # Create posts by different authors
        post1 = PostFactory.create(
            id="at://did:plc:alice/app.bsky.feed.post/post1",
            uri="at://did:plc:alice/app.bsky.feed.post/post1",
            author_display_name="Alice",
            author_handle="alice.bsky.social",
            text="Alice's post 1",
            bookmark_count=1,
            like_count=10,
            quote_count=2,
            reply_count=3,
            repost_count=1,
            created_at="2024-01-01T00:00:00Z",
        )
        post2 = PostFactory.create(
            id="at://did:plc:alice/app.bsky.feed.post/post2",
            uri="at://did:plc:alice/app.bsky.feed.post/post2",
            author_display_name="Alice",
            author_handle="alice.bsky.social",
            text="Alice's post 2",
            bookmark_count=2,
            like_count=20,
            quote_count=4,
            reply_count=6,
            repost_count=2,
            created_at="2024-01-02T00:00:00Z",
        )
        post3 = PostFactory.create(
            id="at://did:plc:bob/app.bsky.feed.post/post1",
            uri="at://did:plc:bob/app.bsky.feed.post/post1",
            author_display_name="Bob",
            author_handle="bob.bsky.social",
            text="Bob's post",
            bookmark_count=3,
            like_count=30,
            quote_count=6,
            reply_count=9,
            repost_count=3,
            created_at="2024-01-03T00:00:00Z",
        )

        repo.create_or_update_feed_post(post1)
        repo.create_or_update_feed_post(post2)
        repo.create_or_update_feed_post(post3)

        # List posts by Alice
        alice_posts = repo.list_feed_posts_by_author("alice.bsky.social")
        assert len(alice_posts) == 2
        uris = {p.uri for p in alice_posts}
        assert uris == {
            "at://did:plc:alice/app.bsky.feed.post/post1",
            "at://did:plc:alice/app.bsky.feed.post/post2",
        }

        # List posts by Bob
        bob_posts = repo.list_feed_posts_by_author("bob.bsky.social")
        assert len(bob_posts) == 1
        assert bob_posts[0].uri == "at://did:plc:bob/app.bsky.feed.post/post1"

    def test_list_all_feed_posts_retrieves_all_posts(self, feed_post_repo):
        """Test that list_all_feed_posts retrieves all posts from the database."""
        repo = feed_post_repo

        # Create multiple posts
        posts = [
            PostFactory.create(
                id=f"at://did:plc:test{i}/app.bsky.feed.post/test{i}",
                uri=f"at://did:plc:test{i}/app.bsky.feed.post/test{i}",
                author_display_name=f"User {i}",
                author_handle=f"user{i}.bsky.social",
                text=f"Post {i} content",
                bookmark_count=i,
                like_count=i * 10,
                quote_count=i * 2,
                reply_count=i * 3,
                repost_count=i,
                created_at=f"2024-01-0{i}T00:00:00Z",
            )
            for i in range(1, 4)
        ]

        for post in posts:
            repo.create_or_update_feed_post(post)

        # List all posts
        all_posts = repo.list_all_feed_posts()

        # Assert
        assert len(all_posts) == 3
        uris = {p.uri for p in all_posts}
        assert uris == {
            "at://did:plc:test1/app.bsky.feed.post/test1",
            "at://did:plc:test2/app.bsky.feed.post/test2",
            "at://did:plc:test3/app.bsky.feed.post/test3",
        }

        # Verify all fields are correct
        post_dict = {p.uri: p for p in all_posts}
        assert (
            post_dict["at://did:plc:test1/app.bsky.feed.post/test1"].text
            == "Post 1 content"
        )
        assert post_dict["at://did:plc:test2/app.bsky.feed.post/test2"].like_count == 20
        assert post_dict["at://did:plc:test3/app.bsky.feed.post/test3"].reply_count == 9

    def test_list_all_feed_posts_returns_empty_list_when_no_posts(self, feed_post_repo):
        """Test that list_all_feed_posts returns an empty list when no posts exist."""
        repo = feed_post_repo

        posts = repo.list_all_feed_posts()
        assert posts == []
        assert isinstance(posts, list)

    def test_list_feed_posts_by_author_returns_empty_list_when_not_found(
        self, feed_post_repo
    ):
        """Test that list_feed_posts_by_author returns empty list when no posts found."""
        repo = feed_post_repo

        posts = repo.list_feed_posts_by_author("nonexistent.bsky.social")
        assert posts == []
        assert isinstance(posts, list)

    def test_create_or_update_feed_post_with_empty_uri_raises_error(
        self, feed_post_repo
    ):
        """Test that creating BlueskyFeedPost with empty uri raises ValidationError from Pydantic."""
        # Pydantic validation happens at model creation time, not in repository
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            BlueskyFeedPost(
                id="",
                uri="",
                author_display_name="Test User",
                author_handle="test.bsky.social",
                text="Test post content",
                bookmark_count=5,
                like_count=10,
                quote_count=2,
                reply_count=3,
                repost_count=1,
                created_at="2024-01-01T00:00:00Z",
            )

        assert "uri cannot be empty" in str(exc_info.value)

    def test_get_feed_post_with_empty_uri_raises_error(self, feed_post_repo):
        """Test that get_feed_post raises ValueError when uri is empty."""
        repo = feed_post_repo

        with pytest.raises(ValueError, match="uri cannot be empty"):
            repo.get_feed_post("")

    def test_list_feed_posts_by_author_with_empty_handle_raises_error(
        self, feed_post_repo
    ):
        """Test that list_feed_posts_by_author raises ValueError when author_handle is empty."""
        repo = feed_post_repo

        with pytest.raises(ValueError, match="handle cannot be empty"):
            repo.list_feed_posts_by_author("")

    def test_feed_post_with_long_text(self, feed_post_repo):
        """Test that feed posts with long text are handled correctly."""
        repo = feed_post_repo

        long_text = "This is a very long post. " * 100  # 2500+ characters
        post = PostFactory.create(
            id="at://did:plc:longpost/app.bsky.feed.post/test",
            uri="at://did:plc:longpost/app.bsky.feed.post/test",
            author_display_name="Long Post User",
            author_handle="longpost.bsky.social",
            text=long_text,
            bookmark_count=5,
            like_count=10,
            quote_count=2,
            reply_count=3,
            repost_count=1,
            created_at="2024-01-01T00:00:00Z",
        )

        repo.create_or_update_feed_post(post)
        retrieved = repo.get_feed_post("at://did:plc:longpost/app.bsky.feed.post/test")

        assert retrieved is not None
        assert retrieved.text == long_text
        assert len(retrieved.text) > 2000

    def test_read_feed_posts_by_uris_returns_posts_for_existing_uris(
        self, feed_post_repo
    ):
        """Test that read_feed_posts_by_uris returns posts for existing URIs."""
        repo = feed_post_repo

        # Create multiple posts
        posts = [
            PostFactory.create(
                id=f"at://did:plc:test{i}/app.bsky.feed.post/test{i}",
                uri=f"at://did:plc:test{i}/app.bsky.feed.post/test{i}",
                author_display_name=f"User {i}",
                author_handle=f"user{i}.bsky.social",
                text=f"Post {i} content",
                bookmark_count=i,
                like_count=i * 10,
                quote_count=i * 2,
                reply_count=i * 3,
                repost_count=i,
                created_at=f"2024-01-0{i}T00:00:00Z",
            )
            for i in range(1, 4)
        ]

        for post in posts:
            repo.create_or_update_feed_post(post)

        # Read posts by URIs
        uris = [post.uri for post in posts]
        retrieved_posts = repo.read_feed_posts_by_uris(uris)

        # Assert
        assert len(retrieved_posts) == 3
        retrieved_uris = {p.uri for p in retrieved_posts}
        assert retrieved_uris == set(uris)

        # Verify all fields are correct
        post_dict = {p.uri: p for p in retrieved_posts}
        assert post_dict[uris[0]].text == "Post 1 content"
        assert post_dict[uris[1]].like_count == 20
        assert post_dict[uris[2]].reply_count == 9

    def test_read_feed_posts_by_uris_returns_empty_list_when_no_uris(
        self, feed_post_repo
    ):
        """Test that read_feed_posts_by_uris returns empty list when no URIs provided."""
        repo = feed_post_repo

        posts = repo.read_feed_posts_by_uris([])
        assert posts == []
        assert isinstance(posts, list)

    def test_read_feed_posts_by_uris_returns_empty_list_when_no_posts_found(
        self, feed_post_repo
    ):
        """Test that read_feed_posts_by_uris returns empty list when no posts exist for URIs."""
        repo = feed_post_repo

        uris = [
            "at://did:plc:nonexistent1/app.bsky.feed.post/test1",
            "at://did:plc:nonexistent2/app.bsky.feed.post/test2",
        ]
        posts = repo.read_feed_posts_by_uris(uris)
        assert posts == []
        assert isinstance(posts, list)

    def test_read_feed_posts_by_uris_returns_partial_results_when_some_missing(
        self, feed_post_repo
    ):
        """Test that read_feed_posts_by_uris returns partial results when some URIs don't exist."""
        repo = feed_post_repo

        # Create some posts
        post1 = PostFactory.create(
            id="at://did:plc:test1/app.bsky.feed.post/test1",
            uri="at://did:plc:test1/app.bsky.feed.post/test1",
            author_display_name="User 1",
            author_handle="user1.bsky.social",
            text="Post 1 content",
            bookmark_count=1,
            like_count=10,
            quote_count=2,
            reply_count=3,
            repost_count=1,
            created_at="2024-01-01T00:00:00Z",
        )
        post2 = PostFactory.create(
            id="at://did:plc:test2/app.bsky.feed.post/test2",
            uri="at://did:plc:test2/app.bsky.feed.post/test2",
            author_display_name="User 2",
            author_handle="user2.bsky.social",
            text="Post 2 content",
            bookmark_count=2,
            like_count=20,
            quote_count=4,
            reply_count=6,
            repost_count=2,
            created_at="2024-01-02T00:00:00Z",
        )

        repo.create_or_update_feed_post(post1)
        repo.create_or_update_feed_post(post2)

        # Query with mix of existing and non-existing URIs
        uris = [
            "at://did:plc:test1/app.bsky.feed.post/test1",  # exists
            "at://did:plc:nonexistent/app.bsky.feed.post/test",  # doesn't exist
            "at://did:plc:test2/app.bsky.feed.post/test2",  # exists
        ]

        retrieved_posts = repo.read_feed_posts_by_uris(uris)

        # Should return only the 2 existing posts
        assert len(retrieved_posts) == 2
        retrieved_uris = {p.uri for p in retrieved_posts}
        assert retrieved_uris == {
            "at://did:plc:test1/app.bsky.feed.post/test1",
            "at://did:plc:test2/app.bsky.feed.post/test2",
        }
