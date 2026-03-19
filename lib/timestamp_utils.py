"""Canonical timestamp parsing and formatting.

Supports both the legacy format (YYYY_MM_DD-HH:MM:SS) and ISO-8601.
All timestamps are normalized to UTC-aware datetimes.
"""

from __future__ import annotations

from datetime import datetime, timezone

# Legacy format used in parts of the system (e.g. run_id, action metadata).
CREATED_AT_FORMAT: str = "%Y_%m_%d-%H:%M:%S"


def get_current_timestamp() -> str:
    """Get the current timestamp in the format YYYY_MM_DD-HH:MM:SS."""
    return datetime.now(tz=timezone.utc).strftime(CREATED_AT_FORMAT)


def parse_timestamp_to_utc(ts: str) -> datetime:
    """Parse a timestamp string to a UTC-aware datetime.

    Accepts:
        - Legacy format: YYYY_MM_DD-HH:MM:SS (e.g. 2024_01_01-12:00:00)
        - ISO-8601: any format parseable by datetime.fromisoformat or with Z suffix

    Returns:
        UTC-aware datetime. Naive inputs are assumed UTC.

    Raises:
        ValueError: If the string cannot be parsed as either format.
    """
    if not ts or not isinstance(ts, str):
        raise ValueError("timestamp must be a non-empty string")

    stripped = ts.strip()
    if not stripped:
        raise ValueError("timestamp must be a non-empty string")

    # Try legacy format first (deterministic, no ambiguity).
    try:
        dt = datetime.strptime(stripped, CREATED_AT_FORMAT)
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    # Try ISO-8601. Handle trailing Z as UTC.
    normalized = stripped.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError) as e:
        raise ValueError(f"cannot parse timestamp {ts!r} as legacy or ISO-8601") from e


def recency_score_from_timestamp(ts: str) -> float:
    """Convert a timestamp string to a numeric recency score (higher = newer).

    Uses the canonical parsing path. For use in recency-based scoring (e.g.
    like/comment/follow generators).

    Raises:
        ValueError: If the timestamp cannot be parsed.
    """
    dt = parse_timestamp_to_utc(ts)
    return float(dt.timestamp())
