"""Capture: what the Android share sheet and dashboard post to Echo."""

from __future__ import annotations

import uuid

from pydantic import Field, field_validator

from app.models.enums import InputType, JobStatus
from app.schemas.common import ApiModel


class CaptureRequest(ApiModel):
    input_type: InputType = InputType.URL
    # A URL, or pasted text. Images use the multipart endpoint instead.
    content: str = Field(min_length=1, max_length=20_000)
    # "android_share" | "dashboard" | "api" | "demo"
    source: str = Field(default="api", max_length=40)
    # Optional user note - a strong intent signal when present.
    note: str | None = Field(default=None, max_length=1_000)

    @field_validator("content")
    @classmethod
    def _strip(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("content must not be blank")
        return cleaned


class CaptureResponse(ApiModel):
    """Returned immediately - the client never waits for the AI (§31)."""

    job_id: uuid.UUID
    status: JobStatus = JobStatus.QUEUED
    # True when this exact source was already saved (§33). The client shows
    # "You already saved this. [View Memory]" instead of a progress spinner.
    duplicate: bool = False
    memory_id: uuid.UUID | None = None
    message: str | None = None
