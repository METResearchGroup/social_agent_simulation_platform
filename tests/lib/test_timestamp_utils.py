"""Tests for lib.timestamp_utils module.

Covers parse_timestamp_to_utc, recency_score_from_timestamp, and get_current_timestamp.
Ensures both legacy format and ISO-8601 inputs are supported with correct UTC normalization.
"""

from datetime import timezone

import pytest

from lib.timestamp_utils import (
    CREATED_AT_FORMAT,
    get_current_timestamp,
    parse_timestamp_to_utc,
    recency_score_from_timestamp,
)


class TestParseTimestampToUtc:
    """Tests for parse_timestamp_to_utc."""

    def test_parses_legacy_format(self):
        """Legacy format YYYY_MM_DD-HH:MM:SS parses and returns UTC-aware datetime."""
        ts = "2024_01_01-12:00:00"
        result = parse_timestamp_to_utc(ts)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 12
        assert result.minute == 0
        assert result.second == 0
        assert result.tzinfo == timezone.utc

    def test_parses_iso8601_with_z_suffix(self):
        """ISO-8601 with trailing Z parses as UTC."""
        ts = "2024-01-01T12:00:00Z"
        result = parse_timestamp_to_utc(ts)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 12
        assert result.minute == 0
        assert result.second == 0
        assert result.tzinfo == timezone.utc

    def test_parses_iso8601_with_explicit_utc_offset(self):
        """ISO-8601 with +00:00 offset parses and normalizes to UTC."""
        ts = "2024-06-15T18:30:45+00:00"
        result = parse_timestamp_to_utc(ts)
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15
        assert result.hour == 18
        assert result.minute == 30
        assert result.second == 45
        assert result.tzinfo == timezone.utc

    def test_parses_iso8601_naive_treated_as_utc(self):
        """Naive ISO-8601 (no timezone) is assumed UTC."""
        ts = "2024-01-01T12:00:00"
        result = parse_timestamp_to_utc(ts)
        assert result.year == 2024
        assert result.hour == 12
        assert result.tzinfo is not None

    def test_parses_iso8601_with_non_utc_offset_converts_to_utc(self):
        """Offset times are converted to UTC."""
        ts = "2024-01-01T12:00:00+05:00"  # UTC+5
        result = parse_timestamp_to_utc(ts)
        assert result.hour == 7  # 12 - 5 = 7 UTC
        assert result.tzinfo == timezone.utc

    def test_raises_on_empty_string(self):
        """Empty string raises ValueError."""
        with pytest.raises(ValueError, match="timestamp must be a non-empty string"):
            parse_timestamp_to_utc("")

    def test_raises_on_whitespace_only(self):
        """Whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="timestamp must be a non-empty string"):
            parse_timestamp_to_utc("   ")

    def test_raises_on_invalid_format(self):
        """Invalid format raises ValueError."""
        with pytest.raises(ValueError, match="cannot parse timestamp"):
            parse_timestamp_to_utc("not-a-date")


class TestRecencyScoreFromTimestamp:
    """Tests for recency_score_from_timestamp."""

    def test_legacy_format_produces_valid_score(self):
        """Legacy format produces a positive timestamp."""
        ts = "2024_01_01-12:00:00"
        score = recency_score_from_timestamp(ts)
        assert score > 0
        assert isinstance(score, float)

    def test_iso8601_format_produces_valid_score(self):
        """ISO-8601 format produces a positive timestamp."""
        ts = "2024-01-01T12:00:00Z"
        score = recency_score_from_timestamp(ts)
        assert score > 0
        assert isinstance(score, float)

    def test_same_moment_produces_same_score(self):
        """Legacy and ISO-8601 for same moment produce identical recency scores."""
        legacy = "2024_06_15-14:30:00"
        iso = "2024-06-15T14:30:00Z"
        score_legacy = recency_score_from_timestamp(legacy)
        score_iso = recency_score_from_timestamp(iso)
        assert score_legacy == score_iso

    def test_newer_timestamp_scores_higher(self):
        """Newer timestamp produces higher recency score."""
        old = recency_score_from_timestamp("2024_01_01-00:00:00")
        new = recency_score_from_timestamp("2024_12_31-23:59:59")
        assert new > old

    def test_raises_on_invalid_input(self):
        """Invalid timestamp raises ValueError."""
        with pytest.raises(ValueError):
            recency_score_from_timestamp("invalid")


class TestGetCurrentTimestamp:
    """Tests for get_current_timestamp."""

    def test_returns_legacy_format_string(self):
        """Returns string in YYYY_MM_DD-HH:MM:SS format."""
        result = get_current_timestamp()
        parsed = parse_timestamp_to_utc(result)
        assert parsed.tzinfo is not None
        # Reformat and compare: round-trip via our parser
        assert recency_score_from_timestamp(result) > 0

    def test_format_matches_expected_pattern(self):
        """Output can be parsed with CREATED_AT_FORMAT."""
        from datetime import datetime

        result = get_current_timestamp()
        parsed = datetime.strptime(result, CREATED_AT_FORMAT)
        assert parsed.year >= 2020
        assert parsed.month in range(1, 13)
        assert parsed.day in range(1, 32)
