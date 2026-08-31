"""Wall-clock -> UTC anchoring (the timezone bug, §42).

The bug these lock in: a poster saying "7:30 pm" is wall-clock in the user's
zone, but the old code stamped it UTC and fired reminders 5.5 hours early in
Asia/Kolkata. Every path that turns an extracted date/time into an instant must
now interpret it in a real zone and store UTC.

Asia/Kolkata (UTC+5:30, no DST) is used as the concrete zone because its offset
is fixed year-round, so the expected UTC is unambiguous and stable.
"""

from __future__ import annotations

import uuid
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from app.models.enums import Category, IntentAction, TriggerType
from app.schemas.ai_output import IntentAnalysis, IntentDetails, IntentResurfacing
from app.services.trigger import build_triggers
from app.utils.timeparse import combine, parse_datetime, parse_time
from app.utils.timezones import (
    UTC,
    is_valid_zone,
    resolve_zone,
    to_utc,
)

IST = ZoneInfo("Asia/Kolkata")  # UTC+5:30, no DST


# --------------------------------------------------------------- resolve_zone


def test_resolve_zone_returns_named_zone():
    assert resolve_zone("Asia/Kolkata") == IST


def test_resolve_zone_falls_back_on_junk_never_raises():
    # A garbage client header must degrade to the configured default, not fail
    # a capture. It also must never fall through to None.
    zone = resolve_zone("Mars/Olympus_Mons")
    assert zone is not None
    # default_timezone is Asia/Kolkata in this build.
    assert zone == IST


def test_resolve_zone_none_uses_default():
    assert resolve_zone(None) == IST


def test_is_valid_zone():
    assert is_valid_zone("Asia/Kolkata") is True
    assert is_valid_zone("America/New_York") is True
    assert is_valid_zone("Not/AZone") is False
    assert is_valid_zone("") is False
    assert is_valid_zone(None) is False


# --------------------------------------------------------------------- to_utc


def test_to_utc_interprets_naive_in_zone():
    naive = datetime(2026, 9, 14, 19, 30)  # "7:30 pm" wall-clock
    result = to_utc(naive, IST)
    assert result == datetime(2026, 9, 14, 14, 0, tzinfo=UTC)  # 19:30 - 5:30
    assert result.tzinfo is not None


def test_to_utc_trusts_existing_offset():
    # An aware datetime already knows its offset; we do not second-guess it.
    aware = datetime(2026, 9, 14, 19, 30, tzinfo=timezone.utc)
    assert to_utc(aware, IST) == aware


# ---------------------------------------------------------------- parse_datetime


def test_parse_datetime_naive_string_is_wall_clock_in_zone():
    result = parse_datetime("2026-09-14T19:30:00", tz=IST)
    assert result == datetime(2026, 9, 14, 14, 0, tzinfo=UTC)


def test_parse_datetime_with_offset_is_trusted():
    result = parse_datetime("2026-09-14T19:30:00+00:00", tz=IST)
    assert result == datetime(2026, 9, 14, 19, 30, tzinfo=UTC)


def test_parse_datetime_trailing_z_is_utc():
    result = parse_datetime("2026-09-14T19:30:00Z", tz=IST)
    assert result == datetime(2026, 9, 14, 19, 30, tzinfo=UTC)


def test_parse_datetime_bare_iso_date_is_local_midnight():
    # "2026-09-14" is a valid ISO datetime (midnight); it is midnight *local*,
    # i.e. the previous evening in UTC for a positive offset like IST.
    result = parse_datetime("2026-09-14", tz=IST)
    assert result == datetime(2026, 9, 13, 18, 30, tzinfo=UTC)


def test_parse_datetime_non_iso_date_defaults_to_local_morning():
    # A non-ISO date string falls through to parse_date + the 09:00 local
    # default, i.e. 03:30 UTC.
    result = parse_datetime("September 14 2026", tz=IST)
    assert result == datetime(2026, 9, 14, 3, 30, tzinfo=UTC)


# --------------------------------------------------------------------- combine


def test_combine_anchors_wall_clock_to_zone():
    day = datetime(2026, 9, 14).date()
    result = combine(day, time(19, 30), tz=IST)
    assert result == datetime(2026, 9, 14, 14, 0, tzinfo=UTC)


def test_combine_default_hour_is_local_morning():
    day = datetime(2026, 9, 14).date()
    result = combine(day, None, tz=IST)  # defaults to 09:00 local
    assert result == datetime(2026, 9, 14, 3, 30, tzinfo=UTC)


def test_combine_none_day_returns_none():
    assert combine(None, time(19, 30), tz=IST) is None


# ----------------------------------------------------------- end-to-end trigger


def _analysis(fire_at: str | None) -> IntentAnalysis:
    return IntentAnalysis(
        category=Category.EVENT,
        title="Concert",
        summary="A short summary.",
        why_saved="You saved this to attend.",
        intent_action=IntentAction.OTHER,
        confidence=0.9,
        resurfacing=IntentResurfacing(
            type=TriggerType.DATE, reason="the right moment", fire_at=fire_at
        ),
        details=IntentDetails(),
    )


def test_build_triggers_anchors_event_at_to_user_zone():
    # The whole reason the bug mattered: the anchored event moment is the
    # wall-clock time the user's phone reported, not 5.5 hours early. (fire_at
    # itself is deliberately offset earlier by event_reminder_lead_hours, so we
    # assert on the anchored event_at the reminder is derived from.)
    analysis = _analysis("2027-01-01T19:30:00")
    triggers = build_triggers(
        analysis=analysis, entity=None, user_id=uuid.uuid4(), tz=IST
    )
    event_at = datetime.fromisoformat(triggers[0].payload["event_at"])
    assert event_at == datetime(2027, 1, 1, 14, 0, tzinfo=UTC)


def test_build_triggers_default_zone_when_tz_omitted():
    # Omitting tz uses settings.default_timezone (Asia/Kolkata), never naive UTC.
    analysis = _analysis("2027-01-01T19:30:00")
    triggers = build_triggers(analysis=analysis, entity=None, user_id=uuid.uuid4())
    event_at = datetime.fromisoformat(triggers[0].payload["event_at"])
    assert event_at == datetime(2027, 1, 1, 14, 0, tzinfo=UTC)
