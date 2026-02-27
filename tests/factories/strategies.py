from __future__ import annotations

from datetime import timezone

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from simulation.core.metrics.defaults import get_default_metric_keys
from simulation.core.models.posts import Post, PostSource
from simulation.core.models.runs import RunConfig


def bluesky_post_strategy() -> SearchStrategy[Post]:
    """Generate valid Post instances (Bluesky source).

    Keep constraints aligned with Pydantic validators (non-empty strings, non-negative counts).
    """
    uri = st.from_regex(
        r"at://did:plc:[a-z0-9]{5,20}/app\.bsky\.feed\.post/[a-z0-9]{5,20}",
        fullmatch=True,
    )
    handle = st.from_regex(
        r"[a-z][a-z0-9_]{2,20}\.bsky\.social",
        fullmatch=True,
    )
    printable = st.characters(whitelist_categories=("L", "N", "P", "Z"))
    display_name = st.text(alphabet=printable, min_size=1, max_size=40)
    text = st.text(alphabet=printable, min_size=1, max_size=240)
    count = st.integers(min_value=0, max_value=10_000)
    created_at = st.datetimes(timezones=st.just(timezone.utc)).map(
        lambda dt: dt.isoformat().replace("+00:00", "Z")
    )
    post_dict = st.fixed_dictionaries(
        {
            "source": st.just(PostSource.BLUESKY),
            "uri": uri,
            "author_handle": handle,
            "author_display_name": display_name,
            "text": text,
            "like_count": count,
            "bookmark_count": count,
            "quote_count": count,
            "reply_count": count,
            "repost_count": count,
            "created_at": created_at,
        }
    )
    post_dict_with_id = post_dict.map(lambda d: {**d, "post_id": f"bluesky:{d['uri']}"})
    return post_dict_with_id.map(Post.model_validate)


def run_config_strategy() -> SearchStrategy[RunConfig]:
    """Generate valid RunConfig instances.

    Use a known-good feed_algorithm to satisfy feeds.algorithms validators.
    """
    default_metric_keys = get_default_metric_keys()
    if default_metric_keys:
        metric_keys = st.one_of(
            st.none(),
            st.lists(
                st.sampled_from(default_metric_keys),
                min_size=1,
                unique=True,
            ),
        )
    else:
        metric_keys = st.none()
    return st.builds(
        RunConfig,
        num_agents=st.integers(min_value=1, max_value=50),
        num_turns=st.integers(min_value=1, max_value=200),
        feed_algorithm=st.just("chronological"),
        feed_algorithm_config=st.none(),
        metric_keys=metric_keys,
    )
