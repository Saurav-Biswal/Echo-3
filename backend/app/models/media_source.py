"""What the user shared, normalised.

Created during the FETCHING stage, before the AI runs, so it doubles as the
dedupe index (§33) and survives an analysis failure for retry. Raw media is
intentionally not stored here - only a URI plus the cheap derived fields (§43).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UuidPrimaryKeyMixin
from app.models.enums import MediaType, Platform, SourceType
from app.models.types import enum_column

if TYPE_CHECKING:
    from app.models.memory import EchoMemory


class MediaSource(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "media_sources"
    __table_args__ = (
        # Duplicate detection is a single indexed lookup per user (§33).
        Index("ix_media_sources_user_canonical", "user_id", "canonical_url"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    source_type: Mapped[SourceType] = mapped_column(enum_column(SourceType))
    platform: Mapped[Platform] = mapped_column(enum_column(Platform))
    media_type: Mapped[MediaType] = mapped_column(
        enum_column(MediaType), default=MediaType.NONE
    )

    # ``source_url`` is what the user shared; ``canonical_url`` is normalised
    # (tracking params stripped, host unified) and is what dedupe compares.
    source_url: Mapped[str | None] = mapped_column(Text, default=None)
    canonical_url: Mapped[str | None] = mapped_column(Text, default=None)

    title: Mapped[str | None] = mapped_column(Text, default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, default=None)
    # Remote/temp pointer only - never a permanent copy of the video.
    media_uri: Mapped[str | None] = mapped_column(Text, default=None)
    transcript: Mapped[str | None] = mapped_column(Text, default=None)
    # OCR / caption text, or the raw text the user pasted.
    extracted_text: Mapped[str | None] = mapped_column(Text, default=None)

    author: Mapped[str | None] = mapped_column(String(255), default=None)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, default=None)

    source_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    memory: Mapped["EchoMemory | None"] = relationship(
        back_populates="source", uselist=False
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<MediaSource {self.source_type} {self.source_url or '(inline)'}>"
