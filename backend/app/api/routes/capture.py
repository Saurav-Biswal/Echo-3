"""Capture endpoints (§31, §33).

Capture returns a job id immediately and never blocks on the AI. A cheap
duplicate pre-check runs synchronously so the client can show "You already
saved this" without a round-trip through the worker; everything heavier happens
in the pipeline.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile, status

from app.api.deps import CurrentUser, SessionDep
from app.config import settings
from app.models import InputType, JobStatus, ProcessingJob
from app.repositories import JobRepository, SourceRepository
from app.schemas.capture import CaptureRequest, CaptureResponse
from app.services import source as source_service
from app.utils.errors import InvalidInputError, MediaTooLargeError
from app.utils.urls import canonicalise
from app.workers import enqueue

router = APIRouter(tags=["capture"])

# Screenshots are streamed to a temp file; cap the size we accept up front.
_IMAGE_READ_LIMIT = settings.media_max_download_bytes


async def _duplicate_memory_id(
    session: SessionDep, *, user_id: uuid.UUID, content: str
) -> uuid.UUID | None:
    url = source_service.resolve_url(content)
    if url is None:
        return None
    existing = await SourceRepository(session).find_duplicate(
        user_id=user_id, canonical_url=canonicalise(url)
    )
    if existing is None or existing.memory is None:
        return None
    return existing.memory.id


@router.post(
    "/capture",
    response_model=CaptureResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def capture(
    payload: CaptureRequest, user: CurrentUser, session: SessionDep
) -> CaptureResponse:
    jobs = JobRepository(session)

    duplicate_id = await _duplicate_memory_id(
        session, user_id=user.id, content=payload.content
    )

    job = ProcessingJob(
        user_id=user.id,
        input_type=payload.input_type,
        raw_content=payload.content,
        note=payload.note,
        origin=payload.source,
    )
    if duplicate_id is not None:
        job.status = JobStatus.COMPLETED
        job.is_duplicate = True
        job.duplicate_of_memory_id = duplicate_id
        job.memory_id = duplicate_id
        job.progress = 1.0
        job.stage_message = "You already saved this."
    await jobs.create(job)
    await session.commit()

    if duplicate_id is not None:
        return CaptureResponse(
            job_id=job.id,
            status=JobStatus.COMPLETED,
            duplicate=True,
            memory_id=duplicate_id,
            message="You already saved this.",
        )

    await enqueue(job.id)
    return CaptureResponse(
        job_id=job.id, status=JobStatus.QUEUED, message="Understanding your save…"
    )


@router.post(
    "/capture/image",
    response_model=CaptureResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def capture_image(
    user: CurrentUser,
    session: SessionDep,
    file: UploadFile = File(...),
    source: str = Form("api"),
    note: str | None = Form(None),
) -> CaptureResponse:
    payload = await file.read()
    if not payload:
        raise InvalidInputError(detail="empty image upload")
    if len(payload) > _IMAGE_READ_LIMIT:
        raise MediaTooLargeError(detail=f"{len(payload)} bytes")

    settings.media_temp_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "").suffix or ".jpg"
    path = settings.media_temp_dir / f"upload-{uuid.uuid4().hex}{suffix}"
    path.write_bytes(payload)

    job = ProcessingJob(
        user_id=user.id,
        input_type=InputType.IMAGE,
        raw_content=str(path),
        note=note,
        origin=source,
    )
    await JobRepository(session).create(job)
    await session.commit()

    await enqueue(job.id)
    return CaptureResponse(
        job_id=job.id, status=JobStatus.QUEUED, message="Reading your screenshot…"
    )
