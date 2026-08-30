"""Job status - what drives the "Understanding your save..." screen."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.models.enums import InputType, JobStatus, Platform, SourceType
from app.schemas.common import ApiModel


class JobRead(ApiModel):
    id: uuid.UUID
    status: JobStatus
    # Copy shown verbatim by the client, so the wording stays server-controlled.
    stage_message: str | None = None
    progress: float = 0.0

    input_type: InputType
    origin: str
    source_type: SourceType | None = None
    platform: Platform | None = None

    memory_id: uuid.UUID | None = None
    is_duplicate: bool = False
    duplicate_of_memory_id: uuid.UUID | None = None

    error_code: str | None = None
    error_message: str | None = None
    # Developer diagnostics (§41): the stage it broke at and the user-safe hint.
    # These are read-only, derived server-side, and never contain secrets.
    failed_stage: str | None = None
    error_hint: str | None = None
    attempts: int = 0

    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class JobTimelineEntry(ApiModel):
    status: JobStatus
    at: datetime
    detail: str | None = None


class JobDetailRead(JobRead):
    timeline: list[JobTimelineEntry] = []
