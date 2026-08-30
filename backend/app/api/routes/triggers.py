"""Trigger listing, manual creation, deletion, and the geofence feed (§19-21)."""

from __future__ import annotations

import uuid
from datetime import timezone

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, SessionDep
from app.config import settings
from app.models import ResurfacingTrigger, TriggerStatus, TriggerType
from app.repositories import MemoryRepository, TriggerRepository
from app.schemas.common import Ack, Page
from app.schemas.trigger import GeofenceRead, TriggerCreate, TriggerRead
from app.utils.errors import MemoryNotFoundError, TriggerNotFoundError

router = APIRouter(tags=["triggers"])


@router.get("/triggers", response_model=Page[TriggerRead])
async def list_triggers(
    user: CurrentUser,
    session: SessionDep,
    status_filter: TriggerStatus | None = Query(None, alias="status"),
    trigger_type: TriggerType | None = Query(None, alias="type"),
    memory_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[TriggerRead]:
    items, total = await TriggerRepository(session).list(
        user_id=user.id,
        status=status_filter,
        trigger_type=trigger_type,
        memory_id=memory_id,
        limit=limit,
        offset=offset,
    )
    return Page(
        items=[TriggerRead.model_validate(t) for t in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/triggers/geofences", response_model=list[GeofenceRead])
async def geofences(user: CurrentUser, session: SessionDep) -> list[GeofenceRead]:
    triggers = await TriggerRepository(session).geofences(user_id=user.id)
    out: list[GeofenceRead] = []
    for trigger in triggers:
        memory = trigger.memory
        out.append(
            GeofenceRead(
                trigger_id=trigger.id,
                memory_id=trigger.memory_id,
                latitude=trigger.latitude,  # type: ignore[arg-type]
                longitude=trigger.longitude,  # type: ignore[arg-type]
                radius_meters=trigger.radius_meters
                or settings.geofence_default_radius_meters,
                place_label=trigger.place_label,
                title=memory.title if memory is not None else "Saved place",
                why=memory.why_saved if memory is not None else trigger.reason,
            )
        )
    return out


@router.post(
    "/triggers", response_model=TriggerRead, status_code=status.HTTP_201_CREATED
)
async def create_trigger(
    payload: TriggerCreate, user: CurrentUser, session: SessionDep
) -> TriggerRead:
    memory = await MemoryRepository(session).get(payload.memory_id, user_id=user.id)
    if memory is None:
        raise MemoryNotFoundError()

    fire_at = payload.fire_at
    if fire_at is not None and fire_at.tzinfo is None:
        fire_at = fire_at.replace(tzinfo=timezone.utc)

    radius = payload.radius_meters
    if payload.trigger_type == TriggerType.LOCATION and radius is None:
        radius = settings.geofence_default_radius_meters

    trigger = ResurfacingTrigger(
        memory_id=memory.id,
        user_id=user.id,
        trigger_type=payload.trigger_type,
        reason=payload.reason,
        fire_at=fire_at,
        latitude=payload.latitude,
        longitude=payload.longitude,
        radius_meters=radius,
        place_label=payload.place_label,
        payload=payload.payload,
        # User-created, so it is intentionally distinct from any derived trigger.
        dedupe_key=f"user:{payload.trigger_type.value.lower()}:{uuid.uuid4().hex[:12]}",
    )
    trigger = await TriggerRepository(session).create(trigger)
    await session.commit()
    await session.refresh(trigger)
    return TriggerRead.model_validate(trigger)


@router.delete("/triggers/{trigger_id}", response_model=Ack)
async def delete_trigger(
    trigger_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> Ack:
    repo = TriggerRepository(session)
    trigger = await repo.get(trigger_id, user_id=user.id)
    if trigger is None:
        raise TriggerNotFoundError()
    await repo.delete(trigger)
    await session.commit()
    return Ack(message="Reminder removed.")
