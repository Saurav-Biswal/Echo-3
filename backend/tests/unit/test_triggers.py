"""Trigger derivation - turning an analysis into concrete triggers (§19)."""

from __future__ import annotations

import uuid

from app.models.enums import Category, IntentAction, TriggerType
from app.schemas.ai_output import IntentAnalysis, IntentDetails, IntentResurfacing
from app.services.trigger import build_triggers


def _analysis(
    category: Category,
    trigger_type: TriggerType,
    *,
    fire_at: str | None = None,
    title: str = "Some Thing",
    date: str | None = None,
) -> IntentAnalysis:
    return IntentAnalysis(
        category=category,
        title=title,
        summary="A short summary.",
        why_saved="You probably saved this because you want to act on it.",
        intent_action=IntentAction.OTHER,
        confidence=0.9,
        resurfacing=IntentResurfacing(
            type=trigger_type, reason="the right moment", fire_at=fire_at
        ),
        details=IntentDetails(date=date),
    )


def test_location_trigger_anchors_to_label_without_coords():
    analysis = _analysis(Category.PLACE, TriggerType.LOCATION, title="Cafe XYZ")
    triggers = build_triggers(analysis=analysis, entity=None, user_id=uuid.uuid4())
    assert len(triggers) == 1
    trigger = triggers[0]
    assert trigger.trigger_type == TriggerType.LOCATION
    assert trigger.place_label == "Cafe XYZ"
    assert trigger.dedupe_key.startswith("location:")


def test_date_trigger_with_explicit_moment():
    analysis = _analysis(
        Category.EVENT, TriggerType.DATE, fire_at="2027-01-01T09:00:00"
    )
    triggers = build_triggers(analysis=analysis, entity=None, user_id=uuid.uuid4())
    trigger = triggers[0]
    assert trigger.trigger_type == TriggerType.DATE
    assert trigger.fire_at is not None
    assert "event_at" in trigger.payload


def test_date_trigger_without_moment_falls_back_to_nudge():
    analysis = _analysis(Category.EVENT, TriggerType.DATE)
    triggers = build_triggers(analysis=analysis, entity=None, user_id=uuid.uuid4())
    trigger = triggers[0]
    assert trigger.trigger_type == TriggerType.DATE
    assert trigger.fire_at is not None
    assert trigger.payload.get("fallback_nudge") is True


def test_time_trigger_type_preserved():
    analysis = _analysis(Category.RECIPE, TriggerType.TIME)
    triggers = build_triggers(analysis=analysis, entity=None, user_id=uuid.uuid4())
    assert triggers[0].trigger_type == TriggerType.TIME


def test_manual_trigger():
    analysis = _analysis(Category.TOPIC, TriggerType.MANUAL)
    triggers = build_triggers(analysis=analysis, entity=None, user_id=uuid.uuid4())
    assert triggers[0].trigger_type == TriggerType.MANUAL
    assert triggers[0].dedupe_key == "manual"
