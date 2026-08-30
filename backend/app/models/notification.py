"""Resurfacing notifications.

Persisted rather than fire-and-forget: the Android app polls/receives them, the
dashboard shows a resurfacing history, and persistence is what makes
"don't notify twice" enforceable.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UuidPrimaryKeyMixin
from app.models.enums import Category, NotificationStatus, TriggerType
from app.models.types import enum_column

if TYPE_CHECKING:
    from app.models.memory import EchoMemory


class Notification(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_status", "user_id", "status"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
    )

    memory_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("echo_memories.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    trigger_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("resurfacing_triggers.id", ondelete="SET NULL"),
        default=None,
    )

    category: Mapped[Category] = mapped_column(enum_column(Category))
    trigger_type: Mapped[TriggerType] = mapped_column(enum_column(TriggerType))

    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    # Why this came back now - shown under the body, never omitted (§22).
    why: Mapped[str] = mapped_column(Text)

    status: Mapped[NotificationStatus] = mapped_column(
        enum_column(NotificationStatus), default=NotificationStatus.SCHEDULED
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    acted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    dismissed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    # Snapshot of the actions offered, so history stays truthful even if the
    # memory is later edited.
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    memory: Mapped["EchoMemory"] = relationship(back_populates="notifications")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Notification {self.category} {self.status}>"
