"""Notification feed and acknowledgement (§22)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, SessionDep
from app.models import NotificationStatus
from app.repositories import NotificationRepository
from app.schemas.common import Ack, Page
from app.schemas.memory import ActionRead
from app.schemas.notification import NotificationRead
from app.utils.errors import NotificationNotFoundError
from app.utils.timeparse import utcnow

router = APIRouter(tags=["notifications"])

_DISMISS_WORDS = {"dismiss", "dismissed", "ignore", "snooze"}


def _to_read(notification) -> NotificationRead:
    read = NotificationRead.model_validate(notification)
    # The truthful action set is the snapshot taken at send time (§22).
    actions = (notification.payload or {}).get("actions", [])
    read.actions = [ActionRead.model_validate(a) for a in actions]
    return read


@router.get("/notifications", response_model=Page[NotificationRead])
async def list_notifications(
    user: CurrentUser,
    session: SessionDep,
    status_filter: NotificationStatus | None = Query(None, alias="status"),
    latitude: float | None = Query(None, ge=-90, le=90),
    longitude: float | None = Query(None, ge=-180, le=180),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[NotificationRead]:
    if latitude is not None and longitude is not None:
        from app.models import TriggerType
        from app.services.notification import ResurfacingService
        from app.services.trigger import TriggerContext

        service = ResurfacingService(session)
        context = TriggerContext(
            now=utcnow(), latitude=latitude, longitude=longitude, force=False
        )
        await service.resurface(
            user_id=user.id,
            context=context,
            trigger_type=TriggerType.LOCATION,
        )
        await session.commit()

    items, total = await NotificationRepository(session).list(
        user_id=user.id, status=status_filter, limit=limit, offset=offset
    )
    return Page(
        items=[_to_read(n) for n in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/notifications/{notification_id}/ack", response_model=Ack)
async def ack_notification(
    notification_id: uuid.UUID,
    body: dict,
    user: CurrentUser,
    session: SessionDep,
) -> Ack:
    repo = NotificationRepository(session)
    notification = await repo.get(notification_id, user_id=user.id)
    if notification is None:
        raise NotificationNotFoundError()

    action = str(body.get("action", "")).strip().lower()
    now = utcnow()
    if action in _DISMISS_WORDS:
        notification.status = NotificationStatus.DISMISSED
        notification.dismissed_at = now
        message = "Dismissed."
    else:
        notification.status = NotificationStatus.ACTED
        notification.acted_at = now
        message = "Nice - marked as acted on."

    await session.commit()
    return Ack(message=message)
