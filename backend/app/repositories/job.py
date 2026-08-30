"""Processing-job persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models import ProcessingJob
from app.repositories.base import Repository


class JobRepository(Repository):
    async def create(self, job: ProcessingJob) -> ProcessingJob:
        self.session.add(job)
        await self.session.flush()
        return job

    async def get(
        self, job_id: uuid.UUID, *, user_id: uuid.UUID
    ) -> ProcessingJob | None:
        job = await self.session.get(ProcessingJob, job_id)
        if job is None or job.user_id != user_id:
            return None
        return job

    async def get_any(self, job_id: uuid.UUID) -> ProcessingJob | None:
        """Worker-side lookup: the worker already trusts the id it enqueued."""
        return await self.session.get(ProcessingJob, job_id)

    async def latest_for_memory(
        self, memory_id: uuid.UUID
    ) -> ProcessingJob | None:
        result = await self.session.execute(
            select(ProcessingJob)
            .where(ProcessingJob.memory_id == memory_id)
            .order_by(ProcessingJob.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
