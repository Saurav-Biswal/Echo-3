"""Structured actions - the "ACT" half of the loop.

Actions are typed rows with resolved deep links, never free text (§36), so the
Android app and the dashboard can render and execute them without parsing
anything.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UuidPrimaryKeyMixin
from app.models.enums import ActionType
from app.models.types import enum_column

if TYPE_CHECKING:
    from app.models.memory import EchoMemory


class MemoryAction(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "actions"

    memory_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("echo_memories.id", ondelete="CASCADE"), index=True
    )
    action_type: Mapped[ActionType] = mapped_column(enum_column(ActionType))
    label: Mapped[str] = mapped_column(String(80))

    # Android-native intent URI, e.g. "geo:19.07,72.87?q=Cafe+XYZ".
    deep_link: Mapped[str | None] = mapped_column(Text, default=None)
    # Browser-openable equivalent for the dashboard.
    web_link: Mapped[str | None] = mapped_column(Text, default=None)

    action_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    sort_order: Mapped[int] = mapped_column(default=0)
    is_primary: Mapped[bool] = mapped_column(default=False)

    memory: Mapped["EchoMemory"] = relationship(back_populates="actions")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<MemoryAction {self.action_type}>"
