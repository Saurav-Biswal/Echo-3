"""Job status (§31-32) and the synchronous /process escape hatch.

``GET /jobs/{id}`` is what the client polls. ``POST /process`` runs a job to a
terminal state in-request instead of on the worker - the dashboard and the demo
seeder use it so a capture's result is available without waiting on the queue.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.repositories import JobRepository
from app.schemas.job import JobDetailRead
from app.utils.errors import JobNotFoundError
from app.workers import process_job

router = APIRouter(tags=["jobs"])


@router.get("/jobs/{job_id}", response_model=JobDetailRead)
async def get_job(
    job_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> JobDetailRead:
    job = await JobRepository(session).get(job_id, user_id=user.id)
    if job is None:
        raise JobNotFoundError()
    return JobDetailRead.model_validate(job)


@router.post("/process", response_model=JobDetailRead)
async def process(
    body: dict, user: CurrentUser, session: SessionDep
) -> JobDetailRead:
    jobs = JobRepository(session)

    job_id = body.get("job_id")
    memory_id = body.get("memory_id")
    if job_id is not None:
        target = await jobs.get(uuid.UUID(str(job_id)), user_id=user.id)
    elif memory_id is not None:
        target = await jobs.latest_for_memory(uuid.UUID(str(memory_id)))
        if target is not None and target.user_id != user.id:
            target = None
    else:
        raise JobNotFoundError(detail="process requires job_id or memory_id")

    if target is None:
        raise JobNotFoundError()

    # Runs in its own session/transaction; re-read to return the fresh state.
    await process_job(target.id)
    await session.commit()
    refreshed = await jobs.get(target.id, user_id=user.id)
    if refreshed is None:  # pragma: no cover - just processed it
        raise JobNotFoundError()
    await session.refresh(refreshed)
    return JobDetailRead.model_validate(refreshed)
