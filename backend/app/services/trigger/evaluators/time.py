"""Time-based evaluators: a DATE/TIME trigger fires once its moment has arrived."""

from __future__ import annotations

from app.models import ResurfacingTrigger, TriggerType
from app.services.trigger.evaluators.base import TriggerContext, TriggerEvaluator


class _DueAtEvaluator(TriggerEvaluator):
    def matches(self, trigger: ResurfacingTrigger, context: TriggerContext) -> bool:
        if context.force:
            return True
        if trigger.fire_at is None:
            return False
        fire_at = trigger.fire_at
        if fire_at.tzinfo is None:
            from datetime import timezone

            fire_at = fire_at.replace(tzinfo=timezone.utc)
        return fire_at <= context.now


class DateEvaluator(_DueAtEvaluator):
    trigger_type = TriggerType.DATE


class TimeEvaluator(_DueAtEvaluator):
    trigger_type = TriggerType.TIME


class ManualEvaluator(TriggerEvaluator):
    """MANUAL triggers never fire on their own - only when explicitly forced."""

    trigger_type = TriggerType.MANUAL

    def matches(self, trigger: ResurfacingTrigger, context: TriggerContext) -> bool:
        return context.force
