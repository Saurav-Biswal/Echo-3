"""Resurfacing triggers - the "WAIT" half of the Echo loop.

A trigger is a row, not a code path: evaluation is delegated to a registered
evaluator per :class:`TriggerType`, so CALENDAR/WEATHER/ROUTINE can be added
later without touching this table's consumers (§19).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UuidPrimaryKeyMixin
from app.models.enums import TriggerStatus, TriggerType
from app.models.types import enum_column

if TYPE_CHECKING:
    from app.models.memory import EchoMemory


class ResurfacingTrigger(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "resurfacing_triggers"
    __table_args__ = (
        # §21: never create the same reminder twice.
        UniqueConstraint("memory_id", "dedupe_key", name="uq_trigger_memory_dedupe"),
        Index("ix_triggers_status_fire_at", "status", "fire_at"),
        Index("ix_triggers_user_status", "user_id", "status"),
    )

    memory_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("echo_memories.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    trigger_type: Mapped[TriggerType] = mapped_column(enum_column(TriggerType))
    status: Mapped[TriggerStatus] = mapped_column(
        enum_column(TriggerStatus), default=TriggerStatus.PENDING
    )
    # Human-readable: "User may want this when they are nearby".
    reason: Mapped[str] = mapped_column(Text)

    # --- DATE / TIME ------------------------------------------------------
    fire_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    # --- LOCATION ---------------------------------------------------------
    latitude: Mapped[float | None] = mapped_column(Float, default=None)
    longitude: Mapped[float | None] = mapped_column(Float, default=None)
    radius_meters: Mapped[int | None] = mapped_column(Integer, default=None)
    place_label: Mapped[str | None] = mapped_column(String(255), default=None)

    # Stable identity for the trigger's intent, e.g. "date:2026-09-14T09:00"
    # or "location:19.0760,72.8777". Combined with memory_id it is unique.
    dedupe_key: Mapped[str] = mapped_column(String(200))

    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    fired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    fire_count: Mapped[int] = mapped_column(default=0)

    memory: Mapped["EchoMemory"] = relationship(back_populates="triggers")

    @property
    def is_pending(self) -> bool:
        return self.status == TriggerStatus.PENDING

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ResurfacingTrigger {self.trigger_type} {self.status}>"
