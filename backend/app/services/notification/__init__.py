"""Resurfacing notifications - the copy, and the fire-once orchestration.

§22: every resurfacing says *why it came back now*. The wording is
category-specific and server-authored so clients render it verbatim. The
:class:`ResurfacingService` runs the real evaluator path (§45): demo controls
only supply a simulated context, the firing logic is identical to production.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.models import (
    Category,
    EchoMemory,
    MemoryStatus,
    Notification,
    NotificationStatus,
    ResurfacingTrigger,
    TriggerStatus,
    TriggerType,
)
from app.repositories import (
    MemoryRepository,
    NotificationRepository,
    TriggerRepository,
)
from app.services.trigger import TriggerContext, evaluate
from app.utils.logging import get_logger
from app.utils.timeparse import humanise_until, utcnow

logger = get_logger(__name__)

_TITLE_TEMPLATES: dict[Category, str] = {
    Category.PLACE: "📍 You're near {title}",
    Category.EVENT: "🎟️ {title} is coming up",
    Category.RECIPE: "🍳 Feel like making {title}?",
    Category.TOOL: "🛠️ Still want to try {title}?",
    Category.TOPIC: "📖 Time to read: {title}",
}


def build_notification(
    memory: EchoMemory, trigger: ResurfacingTrigger
) -> Notification:
    """Compose the notification for ``memory`` resurfaced by ``trigger`` (§22)."""
    title = _TITLE_TEMPLATES.get(
        memory.category, "💭 Remember this?"
    ).format(title=memory.title)

    body = memory.why_saved
    why = _why_now(trigger)

    return Notification(
        memory_id=memory.id,
        user_id=memory.user_id,
        trigger_id=trigger.id,
        category=memory.category,
        trigger_type=trigger.trigger_type,
        title=title,
        body=body,
        why=why,
        status=NotificationStatus.SENT,
        sent_at=utcnow(),
        payload={"actions": [_action_snapshot(a) for a in memory.actions]},
    )


def _why_now(trigger: ResurfacingTrigger) -> str:
    if trigger.reason:
        return trigger.reason
    if trigger.trigger_type == TriggerType.LOCATION:
        return "You may want this when you are nearby."
    if trigger.fire_at is not None:
        return f"This is due {humanise_until(trigger.fire_at)}."
    return "You saved this to come back to."


def _action_snapshot(action: Any) -> dict[str, Any]:
    return {
        "id": str(action.id),
        "action_type": action.action_type.value,
        "label": action.label,
        "deep_link": action.deep_link,
        "web_link": action.web_link,
        "action_metadata": action.action_metadata or {},
        "is_primary": action.is_primary,
        "sort_order": action.sort_order,
    }


class ResurfacingService:
    """Evaluates pending triggers against a context and fires the matches."""

    def __init__(self, session: Any) -> None:
        self.session = session
        self.triggers = TriggerRepository(session)
        self.notifications = NotificationRepository(session)
        self.memories = MemoryRepository(session)

    async def resurface(
        self,
        *,
        user_id: uuid.UUID,
        context: TriggerContext,
        memory_id: uuid.UUID | None = None,
        trigger_type: TriggerType | None = None,
    ) -> list[Notification]:
        candidates = await self._candidates(
            user_id=user_id, memory_id=memory_id, trigger_type=trigger_type
        )
        fired: list[Notification] = []
        for trigger in candidates:
            if not evaluate(trigger, context):
                continue
            notification = await self._fire(trigger)
            if notification is not None:
                fired.append(notification)
        logger.info(
            "resurface.evaluated",
            candidates=len(candidates),
            fired=len(fired),
            forced=context.force,
        )
        return fired

    async def _candidates(
        self,
        *,
        user_id: uuid.UUID,
        memory_id: uuid.UUID | None,
        trigger_type: TriggerType | None,
    ) -> list[ResurfacingTrigger]:
        if memory_id is not None:
            memory = await self.memories.get(memory_id, user_id=user_id)
            if memory is None:
                return []
            pending = await self.triggers.pending_for_memory(memory_id)
        elif trigger_type is not None:
            pending = await self.triggers.pending_by_type(
                user_id=user_id, trigger_type=trigger_type
            )
        else:
            items, _ = await self.triggers.list(
                user_id=user_id, status=TriggerStatus.PENDING, limit=500
            )
            pending = items
        if trigger_type is not None:
            pending = [t for t in pending if t.trigger_type == trigger_type]
        return pending

    async def _fire(self, trigger: ResurfacingTrigger) -> Notification | None:
        memory = await self.session.get(EchoMemory, trigger.memory_id)
        if memory is None:
            return None

        trigger.status = TriggerStatus.FIRED
        trigger.fired_at = utcnow()
        trigger.fire_count += 1

        notification = build_notification(memory, trigger)
        await self.notifications.create(notification)

        if memory.status in (MemoryStatus.ACTIVE, MemoryStatus.NEEDS_REVIEW):
            memory.status = MemoryStatus.RESURFACED
        memory.resurfaced_at = utcnow()
        memory.resurface_count += 1
        return notification
