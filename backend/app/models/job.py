"""Processing jobs.

Capture returns a job id immediately (§31); the pipeline advances the status
through the stages in §32 and records why it failed if it did. The Android app
polls this row to drive its "Understanding..." UI.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UuidPrimaryKeyMixin
from app.models.enums import InputType, JobStatus, Platform, SourceType
from app.models.types import enum_column

if TYPE_CHECKING:
    from app.models.memory import EchoMemory


class ProcessingJob(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "processing_jobs"
    __table_args__ = (Index("ix_jobs_user_status", "user_id", "status"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    input_type: Mapped[InputType] = mapped_column(enum_column(InputType))
    # The shared URL or pasted text. Images are referenced by temp path here.
    raw_content: Mapped[str] = mapped_column(Text)
    # An optional note the user typed alongside the save - the strongest intent
    # signal we get, carried through to the AI layer (§9).
    note: Mapped[str | None] = mapped_column(Text, default=None)
    # "android_share", "dashboard", "api", "demo".
    origin: Mapped[str] = mapped_column(String(40), default="api")

    source_type: Mapped[SourceType | None] = mapped_column(
        enum_column(SourceType), default=None
    )
    platform: Mapped[Platform | None] = mapped_column(
        enum_column(Platform), default=None
    )

    status: Mapped[JobStatus] = mapped_column(
        enum_column(JobStatus), default=JobStatus.QUEUED, index=True
    )
    # Short label the client can show verbatim: "Understanding why you saved it".
    stage_message: Mapped[str | None] = mapped_column(String(160), default=None)
    progress: Mapped[float] = mapped_column(default=0.0)

    memory_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("echo_memories.id", ondelete="SET NULL"),
        default=None,
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("media_sources.id", ondelete="SET NULL"),
        default=None,
    )

    # Stable machine code (e.g. "UNSUPPORTED_SOURCE") plus a message that is
    # safe to show a user - never a stack trace (§41).
    error_code: Mapped[str | None] = mapped_column(String(60), default=None)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    attempts: Mapped[int] = mapped_column(default=0)

    # True when this capture matched an existing memory (§33).
    is_duplicate: Mapped[bool] = mapped_column(default=False)
    duplicate_of_memory_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("echo_memories.id", ondelete="SET NULL"),
        default=None,
    )

    # Append-only stage transitions for observability (§49).
    timeline: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    memory: Mapped["EchoMemory | None"] = relationship(
        foreign_keys=[memory_id], lazy="selectin"
    )

    @property
    def is_terminal(self) -> bool:
        return self.status in (JobStatus.COMPLETED, JobStatus.FAILED)

    @property
    def failed_stage(self) -> str | None:
        """The stage the job was in when it failed - read back from the
        timeline so a developer can see *where* it broke, not just that it did.
        None unless the job actually failed."""
        if self.status != JobStatus.FAILED:
            return None
        last_active: str | None = None
        for entry in self.timeline or []:
            status = entry.get("status")
            if status and status != JobStatus.FAILED.value:
                last_active = status
        return last_active

    @property
    def error_hint(self) -> str | None:
        """The user-safe "what to do next" hint for this job's error code (§41).
        Derived from the code, so no extra column is needed to surface it."""
        from app.utils.errors import hint_for_code

        return hint_for_code(self.error_code)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ProcessingJob {self.id} {self.status}>"
