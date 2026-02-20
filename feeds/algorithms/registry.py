"""Central registry for feed generation algorithms."""

from feeds.algorithms.implementations.chronological import ChronologicalFeedAlgorithm
from feeds.algorithms.interfaces import FeedAlgorithm, FeedAlgorithmMetadata

_ALGORITHM_LOOKUP: dict[str, FeedAlgorithm] = {
    "chronological": ChronologicalFeedAlgorithm(),
}

FEED_ALGORITHMS: tuple[str, ...] = tuple(_ALGORITHM_LOOKUP.keys())


def get_registered_algorithms() -> list[tuple[str, FeedAlgorithmMetadata]]:
    """Return list of (algorithm_id, metadata) for all registered algorithms."""
    return [(alg_id, alg.metadata) for alg_id, alg in _ALGORITHM_LOOKUP.items()]


def get_feed_generator(algorithm: str) -> FeedAlgorithm:
    """Return the feed algorithm for the given algorithm ID.

    Raises:
        ValueError: When algorithm is not registered.
    """
    entry = _ALGORITHM_LOOKUP.get(algorithm)
    if entry is None:
        raise ValueError(f"feed_algorithm must be one of: {list(FEED_ALGORITHMS)}")
    return entry
