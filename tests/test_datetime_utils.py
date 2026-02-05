"""
Unit tests for datetime utility functions.

These tests verify pure Python logic without external API calls.
They ensure time parsing and UTC conversion work correctly.
"""
from datetime import datetime, timezone

import pytest

from app.datetime_utils import parse_iso_datetime, ensure_utc, utc_now


class TestParseIsoDatetime:
    """
    Tests for ISO 8601 string parsing.

    Verifies that time strings returned from Supabase are
    correctly converted to Python datetime objects.
    """

    def test_parse_none_returns_none(self):
        """Verify None input returns None."""
        result = parse_iso_datetime(None)
        assert result is None

    def test_parse_z_suffix(self):
        """
        Verify parsing of UTC time with 'Z' suffix.

        Example: "2024-01-15T10:30:00Z"
        'Z' stands for Zulu time (UTC).
        """
        result = parse_iso_datetime("2024-01-15T10:30:00Z")

        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30
        assert result.tzinfo == timezone.utc

    def test_parse_with_offset(self):
        """
        Verify parsing of timezone offset format.

        Example: "2024-01-15T10:30:00+00:00"
        """
        result = parse_iso_datetime("2024-01-15T10:30:00+00:00")

        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_parse_converts_to_utc(self):
        """
        Verify non-UTC timezone is converted to UTC.

        Input: "2024-01-15T19:30:00+09:00" (Korea time 19:30)
        Output: UTC 10:30 (subtract 9 hours)
        """
        result = parse_iso_datetime("2024-01-15T19:30:00+09:00")

        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result.hour == 10  # 19:30 +09:00 = 10:30 UTC


class TestEnsureUtc:
    """
    Tests for UTC conversion function.

    Verifies that only timezone-aware datetimes are accepted,
    and naive datetimes raise an error.
    """

    def test_none_returns_none(self):
        """Verify None input returns None."""
        result = ensure_utc(None)
        assert result is None

    def test_naive_datetime_raises_error(self):
        """
        Verify naive datetime (without timezone) raises ValueError.

        Naive datetimes are dangerous because we can't know which timezone they represent.
        Example: datetime(2024, 1, 15, 10, 30) - is this UTC? Local time? Unknown.
        """
        naive_dt = datetime(2024, 1, 15, 10, 30)  # No tzinfo

        with pytest.raises(ValueError, match="Naive datetime not allowed"):
            ensure_utc(naive_dt)

    def test_utc_datetime_unchanged(self):
        """Verify UTC datetime is returned unchanged."""
        utc_dt = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        result = ensure_utc(utc_dt)

        assert result == utc_dt
        assert result.tzinfo == timezone.utc


class TestUtcNow:
    """
    Tests for current UTC time function.

    Using utc_now() instead of datetime.now() ensures
    we always get a timezone-aware UTC datetime.
    """

    def test_returns_datetime(self):
        """Verify return type is datetime."""
        result = utc_now()
        assert isinstance(result, datetime)

    def test_returns_utc_timezone(self):
        """Verify returned datetime has UTC timezone."""
        result = utc_now()
        assert result.tzinfo == timezone.utc

    def test_returns_current_time(self):
        """
        Verify returned time is approximately current time.

        Result should be between before and after timestamps.
        """
        before = datetime.now(timezone.utc)
        result = utc_now()
        after = datetime.now(timezone.utc)

        assert before <= result <= after
