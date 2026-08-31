"""IANA timezone resolution.

Extracted times are wall-clock: "7:30 pm" in a Mumbai listing means 19:30 in
``Asia/Kolkata``, and stamping it UTC fires the reminder 5.5 hours early. This
module is the single place a zone *name* becomes a usable ``tzinfo``.

Two rules it enforces:

* a zone name arriving from a client is untrusted input - an unknown or
  malformed name degrades to the configured default rather than raising, because
  a bad header should not fail a capture (§42);
* resolution never returns ``None``, so no caller can accidentally fall through
  to a naive datetime.

Windows ships no system tz database, which is why ``tzdata`` is a hard
dependency in ``requirements.txt`` and not an optional extra.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

UTC = timezone.utc

# Resolution is pure and the set of zones is tiny, so cache rather than rebuild
# a ZoneInfo per capture.
_cache: dict[str, ZoneInfo] = {}


def resolve_zone(name: str | None) -> ZoneInfo:
    """Return the zone for ``name``, falling back to the configured default.

    Never raises: an unknown zone is logged and replaced, because the caller is
    usually mid-capture and a reminder in the wrong zone beats no memory at all.
    """
    for candidate in (name, settings.default_timezone, "UTC"):
        if not candidate:
            continue
        cleaned = candidate.strip()
        if not cleaned:
            continue
        cached = _cache.get(cleaned)
        if cached is not None:
            return cached
        try:
            zone = ZoneInfo(cleaned)
        except (ZoneInfoNotFoundError, ValueError):
            logger.warning("timezone.unknown", requested=cleaned[:64])
            continue
        _cache[cleaned] = zone
        return zone
    # ZoneInfo("UTC") failing means tzdata is missing entirely; the stdlib
    # timezone.utc still gives correct (if less descriptive) behaviour.
    return UTC  # type: ignore[return-value]


def is_valid_zone(name: str | None) -> bool:
    """Whether ``name`` is a real IANA zone - used to validate client input."""
    if not name or not name.strip():
        return False
    cleaned = name.strip()
    if cleaned in _cache:
        return True
    try:
        _cache[cleaned] = ZoneInfo(cleaned)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True


def local_now(tz: ZoneInfo | timezone) -> datetime:
    """Current instant expressed in ``tz`` - the reference for "next occurrence"."""
    return datetime.now(UTC).astimezone(tz)


def local_today(tz: ZoneInfo | timezone) -> date:
    """Today's date *in the user's zone*.

    Near midnight this differs from the UTC date, which is exactly when a
    year-less "September 15" would otherwise resolve to the wrong year.
    """
    return local_now(tz).date()


def to_utc(moment: datetime, tz: ZoneInfo | timezone) -> datetime:
    """Interpret ``moment`` in ``tz`` if it is naive, then convert to UTC.

    An already-aware datetime keeps its own offset: if the model returned a real
    offset we trust it over our guess about the user.
    """
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=tz)
    return moment.astimezone(UTC)


__all__ = [
    "UTC",
    "is_valid_zone",
    "local_now",
    "local_today",
    "resolve_zone",
    "to_utc",
]
