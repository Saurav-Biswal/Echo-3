"""The job pipeline - one capture, driven through the stages of §32.

A capture returns immediately with a job id; this module is what actually runs
behind it: normalise the source, look for a duplicate, extract intent, and save
the memory - advancing ``JobStatus`` and committing after every step so a
polling client sees "Understanding why you saved it…" move in real time (§31).

Two rules the spec is firm about live here: raw media is released the moment we
are done with it (§43), and a failure never leaks a stack trace - the job keeps
a stable ``error_code`` and a sentence safe to show a user (§41).
"""

from __future__ import annotations

import uuid
from pathlib import Path

from app.db.session import session_scope
from app.models import InputType, JobStatus, ProcessingJob
from app.repositories import JobRepository, SourceRepository
from app.services import source as source_service
from app.services.intent import IntentService
from app.services.media.acquisition import get_media_acquisition_service
from app.services.media.normalized import NormalizedMedia
from app.services.memory import MemoryService
from app.utils.errors import EchoError
from app.utils.logging import get_logger
from app.utils.timeparse import utcnow

logger = get_logger(__name__)

# Copy the client renders verbatim while a job is in flight (§32).
_STAGE_MESSAGES: dict[JobStatus, str] = {
    JobStatus.FETCHING: "Fetching what you shared…",
    JobStatus.ANALYZING: "Looking at the content…",
    JobStatus.EXTRACTING_INTENT: "Understanding why you saved it…",
    JobStatus.VALIDATING: "Double-checking what we found…",
    JobStatus.SAVING: "Saving your memory…",
    JobStatus.COMPLETED: "Saved.",
}
_PROGRESS: dict[JobStatus, float] = {
    JobStatus.QUEUED: 0.0,
    JobStatus.FETCHING: 0.2,
    JobStatus.ANALYZING: 0.45,
    JobStatus.EXTRACTING_INTENT: 0.65,
    JobStatus.VALIDATING: 0.8,
    JobStatus.SAVING: 0.9,
    JobStatus.COMPLETED: 1.0,
    JobStatus.FAILED: 1.0,
}

_INTERNAL_ERROR_MESSAGE = (
    "Something went wrong while Echo was processing this. Please try again."
)

async def process_job(job_id: uuid.UUID) -> None:
    """Entry point: run one job to a terminal state. Never raises to the caller."""
    async with session_scope() as session:
        job = await JobRepository(session).get_any(job_id)
        if job is None:
            logger.warning("job.missing", job_id=str(job_id))
            return
        if job.is_terminal:
            return
        await _JobRun(session, job).run()


class _JobRun:
    """Runs a single job, owning the session for the duration of the work."""

    def __init__(self, session: object, job: ProcessingJob) -> None:
        self.session = session
        self.job = job
        self.acquisition = get_media_acquisition_service()

    async def run(self) -> None:
        media: NormalizedMedia | None = None
        self.job.attempts += 1
        self.job.started_at = self.job.started_at or utcnow()
        try:
            await self._advance(JobStatus.FETCHING)
            media = await self._normalize()
            self.job.source_type = media.source_type
            self.job.platform = media.platform

            duplicate = await self._find_duplicate(media)
            if duplicate is not None:
                await self._complete_duplicate(duplicate)
                return

            await self._advance(JobStatus.ANALYZING)
            await self._advance(JobStatus.EXTRACTING_INTENT)
            result = await IntentService().analyze(media)

            await self._advance(
                JobStatus.VALIDATING, detail=f"band={result.band.value}"
            )

            await self._advance(JobStatus.SAVING)
            await self._save(media, result)

            self.job.finished_at = utcnow()
            await self._advance(JobStatus.COMPLETED)
        except EchoError as exc:
            # The client only ever sees the stable code + safe message. The
            # internal reason (exc.detail) is logged and carried into the
            # timeline for developers, never surfaced as the user-facing copy (§41).
            await self._fail(exc.code, exc.message, detail=exc.detail)
        except Exception:  # noqa: BLE001 - last line of defence; never leak (§41)
            logger.exception("job.unexpected_error", job_id=str(self.job.id))
            await self._fail(
                "INTERNAL_ERROR", _INTERNAL_ERROR_MESSAGE, detail="unhandled"
            )
        finally:
            if media is not None:
                # §43: the raw video/image is not ours to keep past the job.
                self.acquisition.release(media)

    async def _normalize(self) -> NormalizedMedia:
        image_path = (
            Path(self.job.raw_content)
            if self.job.input_type == InputType.IMAGE
            else None
        )
        return await source_service.normalize(
            input_type=self.job.input_type,
            content=self.job.raw_content,
            note=self.job.note,
            image_path=image_path,
        )

    async def _find_duplicate(self, media: NormalizedMedia):
        """A prior *saved* capture of the same canonical URL by this user (§33)."""
        if media.canonical_url is None:
            return None
        existing = await SourceRepository(self.session).find_duplicate(
            user_id=self.job.user_id, canonical_url=media.canonical_url
        )
        return existing.memory if existing is not None else None

    async def _complete_duplicate(self, memory) -> None:
        self.job.is_duplicate = True
        self.job.duplicate_of_memory_id = memory.id
        self.job.memory_id = memory.id
        self.job.finished_at = utcnow()
        await self._advance(JobStatus.COMPLETED, detail="duplicate")

    async def _save(self, media: NormalizedMedia, result) -> None:
        service = MemoryService(self.session)
        source = await service.create_source(media, user_id=self.job.user_id)
        memory = await service.create_from_analysis(
            user_id=self.job.user_id,
            media=media,
            source=source,
            intent_result=result,
        )
        self.job.source_id = source.id
        self.job.memory_id = memory.id

    async def _advance(self, status: JobStatus, *, detail: str | None = None) -> None:
        self.job.status = status
        self.job.stage_message = _STAGE_MESSAGES.get(status, self.job.stage_message)
        self.job.progress = _PROGRESS.get(status, self.job.progress)
        self._append_timeline(status, detail)
        await self.session.commit()

    async def _fail(
        self, code: str, message: str, *, detail: str | None = None
    ) -> None:
        # Clear any half-applied transaction, then re-load the row to write a
        # clean terminal state that a poller can trust.
        await self.session.rollback()
        job = await self.session.get(ProcessingJob, self.job.id)
        if job is None:  # pragma: no cover - the row was created moments ago
            return
        self.job = job
        job.status = JobStatus.FAILED
        job.error_code = code
        job.error_message = message
        job.stage_message = message
        job.progress = 1.0
        job.finished_at = utcnow()
        # The timeline carries the internal reason so a developer polling the job
        # can see *why* it failed instead of only the generic message (§41). It is
        # length-capped and never contains the API key or a stack trace.
        self._append_timeline(JobStatus.FAILED, detail or code)
        await self.session.commit()
        # Full internal detail goes to the server log, keyed by job id, so a
        # failure is never silently swallowed behind "couldn't analyse".
        logger.info(
            "job.failed",
            job_id=str(job.id),
            code=code,
            failed_stage=job.failed_stage,
            detail=detail,
        )

    def _append_timeline(self, status: JobStatus, detail: str | None) -> None:
        entry: dict[str, str] = {"status": status.value, "at": utcnow().isoformat()}
        if detail:
            entry["detail"] = detail
        # JSON columns only re-persist on identity change, so build a new list.
        self.job.timeline = [*(self.job.timeline or []), entry]


__all__ = ["process_job"]
