"""Service helpers for listing simulation metadata (algorithms, metrics)."""

from __future__ import annotations

from simulation.api.schemas.simulation import FeedAlgorithmSchema, MetricSchema


def list_feed_algorithms() -> list[FeedAlgorithmSchema]:
    """Return registered feed algorithms with metadata for the API."""
    from feeds.algorithms import get_registered_algorithms

    return [
        FeedAlgorithmSchema(id=alg_id, **meta.model_dump())
        for alg_id, meta in get_registered_algorithms()
    ]


def list_metrics() -> list[MetricSchema]:
    """Return registered metrics with metadata for the API."""
    from simulation.core.metrics.defaults import get_registered_metrics_metadata

    return [
        MetricSchema(
            key=key,
            display_name=display_name,
            description=description,
            scope=scope,
            author=author,
        )
        for key, display_name, description, scope, author in get_registered_metrics_metadata()
    ]
