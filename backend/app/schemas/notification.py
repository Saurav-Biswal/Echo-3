"""Notification and demo-control schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.models.enums import Category, NotificationStatus, TriggerType
from app.schemas.common import ApiModel
from app.schemas.memory import ActionRead


class NotificationRead(ApiModel):
    id: uuid.UUID
    memory_id: uuid.UUID
    category: Category
    trigger_type: TriggerType

    title: str
    body: str
    why: str

    status: NotificationStatus
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    created_at: datetime

    # Snapshot of the actions offered at send time.
    actions: list[ActionRead] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)


class SimulateLocationRequest(ApiModel):
    """Demo control: pretend the user just walked somewhere (§45).

    Either name a memory directly, or give coordinates and let the real
    geofence evaluator decide - the latter exercises the production path.
    """

    memory_id: uuid.UUID | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class SimulateDateRequest(ApiModel):
    """Demo control: pretend it is ``as_of``, firing any due DATE/TIME trigger."""

    memory_id: uuid.UUID | None = None
    as_of: datetime | None = None


class ResurfaceRequest(ApiModel):
    """POST /api/test/resurface - force one memory to resurface now."""

    memory_id: uuid.UUID
    trigger_type: TriggerType | None = None


class ResurfaceResponse(ApiModel):
    fired: int
    notifications: list[NotificationRead] = Field(default_factory=list)
    message: str | None = None
