"""Structured entities extracted from a save.

Columns exist for every field a trigger needs to evaluate (coordinates, dates)
- those are never buried in JSON. ``details`` holds supplemental,
category-specific data such as recipe ingredients (§38).
"""

from __future__ import annotations

import uuid
from datetime import date as date_type
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UuidPrimaryKeyMixin
from app.models.enums import EntityType
from app.models.types import enum_column

if TYPE_CHECKING:
    from app.models.memory import EchoMemory


class Entity(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "entities"
    __table_args__ = (Index("ix_entities_memory_type", "memory_id", "entity_type"),)

    memory_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("echo_memories.id", ondelete="CASCADE"), index=True
    )
    entity_type: Mapped[EntityType] = mapped_column(enum_column(EntityType))

    name: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text, default=None)

    # --- place ------------------------------------------------------------
    location: Mapped[str | None] = mapped_column(String(255), default=None)
    address: Mapped[str | None] = mapped_column(Text, default=None)
    latitude: Mapped[float | None] = mapped_column(Float, default=None)
    longitude: Mapped[float | None] = mapped_column(Float, default=None)

    # --- event ------------------------------------------------------------
    event_date: Mapped[date_type | None] = mapped_column(Date, default=None, index=True)
    # "19:30" - kept as text because sources are often imprecise about zones.
    event_time: Mapped[str | None] = mapped_column(String(16), default=None)
    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    venue: Mapped[str | None] = mapped_column(String(255), default=None)

    # --- shared -----------------------------------------------------------
    url: Mapped[str | None] = mapped_column(Text, default=None)
    price: Mapped[str | None] = mapped_column(String(120), default=None)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, default=None)

    # Recipe ingredients/steps, tool features, topic key ideas.
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    is_primary: Mapped[bool] = mapped_column(default=False)

    memory: Mapped["EchoMemory"] = relationship(back_populates="entities")

    @property
    def has_coordinates(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Entity {self.entity_type} {self.name!r}>"
