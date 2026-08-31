"""User model.

The MVP ships a single demo user, but every downstream table carries
``user_id`` so real auth is an additive change, not a migration of logic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.db.base import Base, TimestampMixin, UuidPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.memory import EchoMemory


class User(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(120), default=None)
    is_demo: Mapped[bool] = mapped_column(default=False)

    # IANA zone name (e.g. "Asia/Kolkata"), reported by the client. Reminders are
    # computed from wall-clock times in this zone, so it is the difference
    # between a 7:30 pm reminder and a 2:00 am one. Stored as text, not an
    # offset: offsets change twice a year, zone names do not.
    timezone: Mapped[str] = mapped_column(
        String(64), default=lambda: settings.default_timezone
    )

    memories: Mapped[list["EchoMemory"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.email}>"
