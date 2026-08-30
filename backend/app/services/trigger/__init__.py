"""Trigger derivation - turning an analysis into the "WAIT" of the loop.

Given the AI's chosen resurfacing type and the extracted entity, produce the
concrete :class:`ResurfacingTrigger` rows. Feasibility is checked here: a
LOCATION trigger with no place to anchor to, or a DATE trigger with no derivable
moment, degrades to something that can actually fire rather than a dead row.

Evaluation lives in :mod:`app.services.trigger.evaluators`; this module only
*builds* triggers. Both halves share the registry, so trigger types stay open
for extension (§19).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from app.config import settings
from app.models import Entity, ResurfacingTrigger, TriggerType
from app.schemas.ai_output import IntentAnalysis
from app.services.trigger.evaluators import TriggerContext, evaluate, get_evaluator
from app.utils.timeparse import combine, parse_date, parse_datetime, parse_time, utcnow

__all__ = [
    "TriggerContext",
    "build_triggers",
    "evaluate",
    "get_evaluator",
]


def build_triggers(
    *,
    analysis: IntentAnalysis,
    entity: Entity | None,
    user_id: uuid.UUID,
    now: datetime | None = None,
) -> list[ResurfacingTrigger]:
    """Build the resurfacing trigger(s) for a memory. Usually exactly one."""
    reference = now or utcnow()
    desired = analysis.resurfacing.type
    reason = analysis.resurfacing.reason.strip() or "Echo saved this for later."

    if desired == TriggerType.LOCATION:
        trigger = _location_trigger(analysis, entity, user_id, reason)
        if trigger is not None:
            return [trigger]
        return [_manual_trigger(user_id, reason)]

    if desired in (TriggerType.DATE, TriggerType.TIME):
        trigger = _time_trigger(analysis, entity, user_id, reason, reference, desired)
        return [trigger]

    return [_manual_trigger(user_id, reason)]


def _location_trigger(
    analysis: IntentAnalysis,
    entity: Entity | None,
    user_id: uuid.UUID,
    reason: str,
) -> ResurfacingTrigger | None:
    lat = lng = None
    label = analysis.title
    if entity is not None:
        if entity.has_coordinates:
            lat, lng = entity.latitude, entity.longitude
        label = entity.name or entity.location or analysis.title

    if lat is not None and lng is not None:
        dedupe_key = f"location:{lat:.4f},{lng:.4f}"
    elif label:
        dedupe_key = f"location:{label.strip().lower()}"[:200]
    else:
        return None  # nothing to anchor a geofence to

    return ResurfacingTrigger(
        user_id=user_id,
        trigger_type=TriggerType.LOCATION,
        reason=reason,
        latitude=lat,
        longitude=lng,
        radius_meters=settings.geofence_default_radius_meters,
        place_label=(label.strip()[:255] if label else None),
        dedupe_key=dedupe_key,
        payload={"anchored": lat is not None},
    )


def _time_trigger(
    analysis: IntentAnalysis,
    entity: Entity | None,
    user_id: uuid.UUID,
    reason: str,
    reference: datetime,
    desired: TriggerType,
) -> ResurfacingTrigger:
    event_at = _resolve_moment(analysis, entity)
    payload: dict[str, object] = {}

    if event_at is not None:
        payload["event_at"] = event_at.isoformat()
        # Remind ahead of the event, but never in the past.
        lead = timedelta(hours=settings.event_reminder_lead_hours)
        fire_at = event_at - lead
        if fire_at <= reference:
            fire_at = max(event_at, reference + timedelta(minutes=1))
    else:
        # No concrete moment: a gentle nudge later keeps the memory from going
        # silent forever (§ default_time_trigger_delay_hours).
        fire_at = reference + timedelta(hours=settings.default_time_trigger_delay_hours)
        payload["fallback_nudge"] = True

    return ResurfacingTrigger(
        user_id=user_id,
        trigger_type=desired,
        reason=reason,
        fire_at=fire_at,
        dedupe_key=f"{desired.value.lower()}:{fire_at.isoformat()}",
        payload=payload,
    )


def _resolve_moment(analysis: IntentAnalysis, entity: Entity | None) -> datetime | None:
    explicit = parse_datetime(analysis.resurfacing.fire_at)
    if explicit is not None:
        return explicit
    if entity is not None and entity.starts_at is not None:
        return entity.starts_at
    if entity is not None and entity.event_date is not None:
        return combine(entity.event_date, parse_time(entity.event_time))
    day = parse_date(analysis.details.date)
    if day is not None:
        return combine(day, parse_time(analysis.details.time))
    return None


def _manual_trigger(user_id: uuid.UUID, reason: str) -> ResurfacingTrigger:
    return ResurfacingTrigger(
        user_id=user_id,
        trigger_type=TriggerType.MANUAL,
        reason=reason,
        dedupe_key="manual",
        payload={},
    )
