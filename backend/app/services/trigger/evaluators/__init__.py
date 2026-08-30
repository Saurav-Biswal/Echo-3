"""Evaluator registry (§19).

Open for extension: register a new :class:`TriggerEvaluator` here and every
consumer that calls :func:`evaluate` picks it up. No other code branches on
trigger type.
"""

from __future__ import annotations

from app.models import ResurfacingTrigger, TriggerType
from app.services.trigger.evaluators.base import TriggerContext, TriggerEvaluator
from app.services.trigger.evaluators.location import LocationEvaluator
from app.services.trigger.evaluators.time import (
    DateEvaluator,
    ManualEvaluator,
    TimeEvaluator,
)

_REGISTRY: dict[TriggerType, TriggerEvaluator] = {
    evaluator.trigger_type: evaluator
    for evaluator in (
        LocationEvaluator(),
        DateEvaluator(),
        TimeEvaluator(),
        ManualEvaluator(),
    )
}


def get_evaluator(trigger_type: TriggerType) -> TriggerEvaluator:
    return _REGISTRY[trigger_type]


def evaluate(trigger: ResurfacingTrigger, context: TriggerContext) -> bool:
    """True when ``trigger`` should fire in ``context``."""
    return get_evaluator(trigger.trigger_type).matches(trigger, context)


__all__ = [
    "TriggerContext",
    "TriggerEvaluator",
    "evaluate",
    "get_evaluator",
]
