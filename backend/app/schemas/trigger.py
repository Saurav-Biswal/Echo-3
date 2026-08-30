"""Trigger schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from app.models.enums import TriggerStatus, TriggerType
from app.schemas.common import ApiModel


class TriggerRead(ApiModel):
    id: uuid.UUID
    memory_id: uuid.UUID
    trigger_type: TriggerType
    status: TriggerStatus
    reason: str

    fire_at: datetime | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius_meters: int | None = None
    place_label: str | None = None

    fired_at: datetime | None = None
    fire_count: int = 0
    created_at: datetime

    @property
    def is_geofence(self) -> bool:
        return self.trigger_type == TriggerType.LOCATION


class TriggerCreate(ApiModel):
    memory_id: uuid.UUID
    trigger_type: TriggerType
    reason: str = Field(min_length=1, max_length=400)

    fire_at: datetime | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_meters: int | None = Field(default=None, ge=50, le=50_000)
    place_label: str | None = Field(default=None, max_length=255)
    payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_required_fields(self) -> "TriggerCreate":
        if self.trigger_type in (TriggerType.DATE, TriggerType.TIME) and self.fire_at is None:
            raise ValueError(f"{self.trigger_type.value} triggers require fire_at")
        if self.trigger_type == TriggerType.LOCATION and (
            self.latitude is None or self.longitude is None
        ):
            raise ValueError("LOCATION triggers require latitude and longitude")
        return self


class GeofenceRead(ApiModel):
    """Flat shape the Android geofence registrar consumes."""

    trigger_id: uuid.UUID
    memory_id: uuid.UUID
    latitude: float
    longitude: float
    radius_meters: int
    place_label: str | None = None
    title: str
    why: str
