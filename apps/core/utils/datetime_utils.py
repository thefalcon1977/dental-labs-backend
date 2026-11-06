"""Datetime and timezone utility functions.

This module centralizes timezone handling for the application, with a focus on
conversions between UTC and the Asia/Tehran timezone.

The primary goals are:
- Provide a single source of truth for the Tehran timezone definition
- Ensure consistent handling of naive and timezone-aware datetimes
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TEHRAN_TZ = ZoneInfo("Asia/Tehran")
UTC_TZ = timezone.utc


def assume_tehran_timezone(value: datetime) -> datetime:
    """Attach or convert a datetime to the Asia/Tehran timezone.

    If the input datetime is naive (no tzinfo), it is assumed to be a local
    Asia/Tehran time and tzinfo is attached accordingly. If the input is
    already timezone-aware, it is converted to Asia/Tehran.

    Args:
        value: Input datetime value.

    Returns:
        Datetime object with Asia/Tehran tzinfo.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=TEHRAN_TZ)
    return value.astimezone(TEHRAN_TZ)


def tehran_to_utc(value: datetime) -> datetime:
    """Convert a Tehran-local datetime to UTC.

    Naive datetimes are first treated as Asia/Tehran local time, then converted
    to UTC. Timezone-aware values are converted via the Asia/Tehran timezone
    before the final UTC conversion.

    Args:
        value: Input datetime value representing Tehran local time.

    Returns:
        Datetime converted to UTC.
    """
    tehran_dt = assume_tehran_timezone(value)
    return tehran_dt.astimezone(UTC_TZ)


def utc_to_tehran(value: datetime) -> datetime:
    """Convert a UTC or timezone-aware datetime to Asia/Tehran.

    If the input datetime is naive, it is first assumed to be UTC. The value is
    then converted to Asia/Tehran timezone.

    Args:
        value: Input datetime value in UTC or with tzinfo.

    Returns:
        Datetime converted to Asia/Tehran timezone.
    """
    base = value
    if value.tzinfo is None:
        base = value.replace(tzinfo=UTC_TZ)
    else:
        base = value.astimezone(UTC_TZ)
    return base.astimezone(TEHRAN_TZ)
