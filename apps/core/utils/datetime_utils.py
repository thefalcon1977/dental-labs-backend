"""Timezone-aware datetime utility helpers."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

UTC_TZ = timezone.utc
TEHRAN_TZ = ZoneInfo("Asia/Tehran")


def assume_tehran_timezone(value: datetime) -> datetime:
    """Return a datetime with Asia/Tehran timezone when it is naive.

    Args:
        value: Datetime value to normalize.

    Returns:
        Timezone-aware datetime. Naive values are treated as Tehran local time.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=TEHRAN_TZ)
    return value


def tehran_to_utc(value: datetime) -> datetime:
    """Convert a Tehran-local datetime to UTC.

    Args:
        value: Datetime value to convert. Naive values are treated as Tehran
            local time.

    Returns:
        UTC-aware datetime.
    """
    return assume_tehran_timezone(value).astimezone(UTC_TZ)


def utc_to_tehran(value: datetime) -> datetime:
    """Convert a UTC datetime to Tehran local time.

    Args:
        value: Datetime value to convert. Naive values are treated as UTC.

    Returns:
        Asia/Tehran-aware datetime.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC_TZ)
    return value.astimezone(TEHRAN_TZ)


__all__ = [
    "TEHRAN_TZ",
    "UTC_TZ",
    "assume_tehran_timezone",
    "tehran_to_utc",
    "utc_to_tehran",
]
