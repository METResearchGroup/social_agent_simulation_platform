"""Validators for feed algorithms."""

from feeds.algorithms.registry import FEED_ALGORITHMS
from lib.validation_utils import validate_value_in_set


def validate_feed_algorithm(feed_algorithm: str | None) -> str | None:
    """Validate that feed_algorithm, when provided, is a registered algorithm."""
    if feed_algorithm is None:
        return None
    return validate_value_in_set(
        feed_algorithm,
        "feed_algorithm",
        FEED_ALGORITHMS,
        allowed_display_name="registered feed algorithms",
    )
