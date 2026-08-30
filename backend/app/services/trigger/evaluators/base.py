"""Trigger evaluation context and the evaluator interface (§19).

A trigger is data; *whether it fires now* is delegated to an evaluator keyed by
:class:`TriggerType`. Adding CALENDAR/WEATHER/ROUTINE later means adding an
evaluator and registering it - no consumer of triggers changes.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import datetime

from app.models import ResurfacingTrigger, TriggerType
from app.utils.timeparse import utcnow


@dataclass(slots=True)
class TriggerContext:
    """The simulated or real world state a trigger is evaluated against."""

    now: datetime
    latitude: float | None = None
    longitude: float | None = None
    # Demo/test override: fire regardless of whether the condition is met.
    force: bool = False

    @classmethod
    def now_context(cls, **kwargs: object) -> "TriggerContext":
        return cls(now=utcnow(), **kwargs)  # type: ignore[arg-type]


class TriggerEvaluator(abc.ABC):
    trigger_type: TriggerType

    @abc.abstractmethod
    def matches(self, trigger: ResurfacingTrigger, context: TriggerContext) -> bool:
        """True when ``trigger`` should fire given ``context``."""
        raise NotImplementedError
