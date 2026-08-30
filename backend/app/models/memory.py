"""The Echo Memory: an intention, not a bookmark.

``why_saved`` + ``intent_action`` + the memory's trigger are the product; the
``summary`` is supporting information (§3).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UuidPrimaryKeyMixin
from app.models.enums import Category, ConfidenceBand, IntentAction, MemoryStatus
from app.models.types import enum_column

if TYPE_CHECKING:
    from app.models.action import MemoryAction
    from app.models.entity import Entity
    from app.models.media_source import MediaSource
    from app.models.notification import Notification
    from app.models.trigger import ResurfacingTrigger
    from app.models.user import User


class EchoMemory(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "echo_memories"
    __table_args__ = (
        Index("ix_echo_memories_user_status", "user_id", "status"),
        Index("ix_echo_memories_user_category", "user_id", "category"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("media_sources.id", ondelete="SET NULL"),
        default=None,
        index=True,
    )

    # --- what -------------------------------------------------------------
    category: Mapped[Category] = mapped_column(enum_column(Category))
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str | None] = mapped_column(Text, default=None)

    # --- why (the product) ------------------------------------------------
    why_saved: Mapped[str] = mapped_column(Text)
    intent_action: Mapped[IntentAction] = mapped_column(enum_column(IntentAction))
    intent_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_band: Mapped[ConfidenceBand] = mapped_column(
        enum_column(ConfidenceBand), default=ConfidenceBand.LOW
    )

    # --- lifecycle --------------------------------------------------------
    status: Mapped[MemoryStatus] = mapped_column(
        enum_column(MemoryStatus), default=MemoryStatus.ACTIVE, index=True
    )
    needs_review_reason: Mapped[str | None] = mapped_column(Text, default=None)
    resurfaced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    resurface_count: Mapped[int] = mapped_column(default=0)

    # --- provenance / correction -----------------------------------------
    ai_model: Mapped[str | None] = mapped_column(String(120), default=None)
    # The validated AI payload, kept for re-analysis and debugging - not a
    # dumping ground for application state.
    ai_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    user_confirmed: Mapped[bool] = mapped_column(default=False)
    user_corrected: Mapped[bool] = mapped_column(default=False)

    # --- relationships ----------------------------------------------------
    user: Mapped["User"] = relationship(back_populates="memories")
    source: Mapped["MediaSource | None"] = relationship(
        back_populates="memory", lazy="selectin"
    )
    entities: Mapped[list["Entity"]] = relationship(
        back_populates="memory",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Entity.created_at",
    )
    triggers: Mapped[list["ResurfacingTrigger"]] = relationship(
        back_populates="memory", cascade="all, delete-orphan", lazy="selectin"
    )
    actions: Mapped[list["MemoryAction"]] = relationship(
        back_populates="memory",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="MemoryAction.sort_order",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="memory", cascade="all, delete-orphan"
    )

    @property
    def primary_entity(self) -> "Entity | None":
        for entity in self.entities:
            if entity.is_primary:
                return entity
        return self.entities[0] if self.entities else None

    @property
    def primary_trigger(self) -> "ResurfacingTrigger | None":
        return self.triggers[0] if self.triggers else None

    def __repr__(self) -> str:  # pragma: no cover
        return f"<EchoMemory {self.category} {self.title!r}>"
