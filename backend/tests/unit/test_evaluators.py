"""Trigger evaluation: the WAIT->RESURFACE decision, per trigger type (§19)."""

from __future__ import annotations

from datetime import timedelta

from app.models import ResurfacingTrigger
from app.models.enums import TriggerType
from app.services.trigger import TriggerContext, evaluate
from app.utils.timeparse import utcnow


def _location_trigger(lat: float, lng: float, radius: int = 300) -> ResurfacingTrigger:
    return ResurfacingTrigger(
        trigger_type=TriggerType.LOCATION,
        reason="nearby",
        latitude=lat,
        longitude=lng,
        radius_meters=radius,
        dedupe_key="location:test",
    )


def test_location_fires_when_inside_radius():
    trigger = _location_trigger(12.9716, 77.5946, radius=500)
    # ~100m away, well inside 500m.
    context = TriggerContext(now=utcnow(), latitude=12.9720, longitude=77.5950)
    assert evaluate(trigger, context) is True


def test_location_does_not_fire_when_far():
    trigger = _location_trigger(12.9716, 77.5946, radius=300)
    # Different city entirely.
    context = TriggerContext(now=utcnow(), latitude=19.0760, longitude=72.8777)
    assert evaluate(trigger, context) is False


def test_location_needs_context_coords():
    trigger = _location_trigger(12.9716, 77.5946)
    context = TriggerContext(now=utcnow(), latitude=None, longitude=None)
    assert evaluate(trigger, context) is False


def test_force_fires_any_trigger():
    trigger = _location_trigger(12.9716, 77.5946)
    context = TriggerContext(now=utcnow(), force=True)
    assert evaluate(trigger, context) is True


def test_date_fires_once_due():
    now = utcnow()
    due = ResurfacingTrigger(
        trigger_type=TriggerType.DATE,
        reason="time",
        fire_at=now - timedelta(hours=1),
        dedupe_key="date:past",
    )
    not_due = ResurfacingTrigger(
        trigger_type=TriggerType.DATE,
        reason="time",
        fire_at=now + timedelta(hours=1),
        dedupe_key="date:future",
    )
    context = TriggerContext(now=now)
    assert evaluate(due, context) is True
    assert evaluate(not_due, context) is False


def test_manual_never_fires_without_force():
    trigger = ResurfacingTrigger(
        trigger_type=TriggerType.MANUAL, reason="held", dedupe_key="manual"
    )
    assert evaluate(trigger, TriggerContext(now=utcnow())) is False
    assert evaluate(trigger, TriggerContext(now=utcnow(), force=True)) is True
