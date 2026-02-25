"""Property-based tests for Hypothesis strategies under tests.factories.strategies."""

from hypothesis import given, settings

from tests.factories.strategies import bluesky_post_strategy, run_config_strategy


@given(post=bluesky_post_strategy())
@settings(max_examples=50, deadline=None)
def test_bluesky_post_strategy_produces_valid_post(post):
    assert post.uri
    assert post.id == post.uri
    assert post.author_handle
    assert post.author_display_name
    assert post.text
    assert post.like_count >= 0
    assert post.bookmark_count >= 0
    assert post.quote_count >= 0
    assert post.reply_count >= 0
    assert post.repost_count >= 0
    assert post.created_at


@given(config=run_config_strategy())
@settings(max_examples=25, deadline=None)
def test_run_config_strategy_produces_valid_config(config):
    assert config.num_agents >= 1
    assert config.num_turns >= 1
    assert config.feed_algorithm == "chronological"
