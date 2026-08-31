"""Forgiving date/time parsing for AI-extracted strings.

Models emit dates in whatever shape the source used - "2026-09-15",
"September 15", "15 Sep 2026". Rather than reject those, parse what we can and
return ``None`` otherwise; a missing date is a normal outcome (§9), a wrong one
is a bug that fires a reminder on the wrong day.

Every extracted time is **wall-clock in the user's zone**, never UTC: a poster
saying "7:30 pm" says nothing about offsets. Functions that turn a date/time
into an instant therefore require a ``tz`` and return an aware UTC datetime -
storage is UTC, interpretation is local. Passing the zone is deliberately not
optional here, so no caller can silently reintroduce the naive-UTC bug.
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.utils.timezones import local_today, to_utc

_MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

_ISO_DATE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
# "September 15", "Sep 15 2026", "September 15, 2026"
_MONTH_FIRST = re.compile(
    r"^([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?$"
)
# "15 September", "15 Sep 2026"
_DAY_FIRST = re.compile(
    r"^(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\.?(?:,?\s+(\d{4}))?$"
)
_TIME = re.compile(r"^(\d{1,2})[:.](\d{2})\s*(am|pm)?$", re.IGNORECASE)
_TIME_HOUR_ONLY = re.compile(r"^(\d{1,2})\s*(am|pm)$", re.IGNORECASE)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_date(
    value: str | None,
    *,
    today: date | None = None,
    tz: ZoneInfo | timezone | None = None,
) -> date | None:
    """Parse a date string. A year-less date resolves to its next occurrence.

    "September 15" seen in August 2026 means 2026-09-15; seen in October 2026 it
    means 2027-09-15, because a saved event is always in the user's future.

    ``tz`` supplies the zone that decides what "today" is. It matters within a
    few hours of midnight: at 01:00 IST on 1 January the UTC date is still 31
    December, which would resolve a year-less date into the wrong year.
    """
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if today is not None:
        reference = today
    elif tz is not None:
        reference = local_today(tz)
    else:
        reference = utcnow().date()

    match = _ISO_DATE.match(text)
    if match:
        return _safe_date(int(match[1]), int(match[2]), int(match[3]))

    for pattern, month_group, day_group in (
        (_MONTH_FIRST, 1, 2),
        (_DAY_FIRST, 2, 1),
    ):
        match = pattern.match(text)
        if not match:
            continue
        month = _MONTHS.get(match[month_group].lower())
        if month is None:
            return None
        day = int(match[day_group])
        if match[3]:
            return _safe_date(int(match[3]), month, day)
        candidate = _safe_date(reference.year, month, day)
        if candidate is None:
            return None
        return candidate if candidate >= reference else _safe_date(
            reference.year + 1, month, day
        )

    return None


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_time(value: str | None) -> time | None:
    """Parse "19:30", "7:30 pm", "7pm"."""
    if not value:
        return None
    text = value.strip()

    match = _TIME.match(text)
    if match:
        hour, minute, meridiem = int(match[1]), int(match[2]), match[3]
        hour = _apply_meridiem(hour, meridiem)
        return time(hour, minute) if 0 <= hour <= 23 and 0 <= minute <= 59 else None

    match = _TIME_HOUR_ONLY.match(text)
    if match:
        hour = _apply_meridiem(int(match[1]), match[2])
        return time(hour, 0) if 0 <= hour <= 23 else None

    return None


def _apply_meridiem(hour: int, meridiem: str | None) -> int:
    if not meridiem:
        return hour
    lowered = meridiem.lower()
    if lowered == "pm" and hour < 12:
        return hour + 12
    if lowered == "am" and hour == 12:
        return 0
    return hour


def parse_datetime(
    value: str | None, *, tz: ZoneInfo | timezone
) -> datetime | None:
    """Parse an ISO-8601 datetime into an aware **UTC** instant.

    Tolerates a trailing ``Z`` and a bare date. A string carrying a real offset
    is trusted as-is; a naive string is wall-clock in ``tz``, because that is
    what a model transcribing "7:30 pm" actually saw.
    """
    if not value:
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        parsed_date = parse_date(value, tz=tz)
        if parsed_date is None:
            return None
        parsed = datetime.combine(parsed_date, time(9, 0))
    return to_utc(parsed, tz)


def combine(
    day: date | None,
    at: time | None,
    *,
    tz: ZoneInfo | timezone,
    default_hour: int = 9,
) -> datetime | None:
    """Turn a local date + wall-clock time into an aware UTC instant.

    ``tz`` is required: the whole point of this function is that "2026-09-14
    19:30" is not an instant until a zone says which 19:30 it is.
    """
    if day is None:
        return None
    naive = datetime.combine(day, at or time(default_hour, 0))
    return to_utc(naive, tz)


def humanise_until(target: datetime, *, now: datetime | None = None) -> str:
    """"tomorrow", "in 3 days", "in 2 hours" - used in notification copy."""
    reference = now or utcnow()
    if target.tzinfo is None:
        target = target.replace(tzinfo=timezone.utc)
    delta = target - reference

    if delta <= timedelta(0):
        return "now"
    if delta < timedelta(minutes=90):
        minutes = max(1, int(delta.total_seconds() // 60))
        return f"in {minutes} minute{'s' if minutes != 1 else ''}"
    if delta < timedelta(hours=24):
        hours = int(delta.total_seconds() // 3600)
        return f"in {hours} hour{'s' if hours != 1 else ''}"

    days = delta.days
    if days == 1:
        return "tomorrow"
    if days < 7:
        return f"in {days} days"
    if days < 14:
        return "next week"
    if days < 60:
        return f"in {days // 7} weeks"
    return f"in {days // 30} months"
