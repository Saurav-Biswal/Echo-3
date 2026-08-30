"""Geofence evaluator: fire a LOCATION trigger when the user is within radius."""

from __future__ import annotations

import math

from app.models import ResurfacingTrigger, TriggerType
from app.services.trigger.evaluators.base import TriggerContext, TriggerEvaluator


class LocationEvaluator(TriggerEvaluator):
    trigger_type = TriggerType.LOCATION

    def matches(self, trigger: ResurfacingTrigger, context: TriggerContext) -> bool:
        if context.force:
            return True
        if context.latitude is None or context.longitude is None:
            return False
        if trigger.latitude is None or trigger.longitude is None:
            return False
        radius = trigger.radius_meters or 300
        distance = _haversine_meters(
            context.latitude, context.longitude, trigger.latitude, trigger.longitude
        )
        return distance <= radius


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres."""
    radius_earth = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return radius_earth * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
