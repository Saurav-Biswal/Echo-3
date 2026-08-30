"""Demo controls (§45).

These endpoints drive a live demo, but they run the *real* resurfacing path:
``simulate-location`` and ``simulate-date`` build a simulated
:class:`TriggerContext` and hand it to the same evaluator the production worker
uses, so what the audience sees fire is what would fire in the field. Seeding
runs sample captures through the actual pipeline with the mock AI provider.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.api.routes.notifications import _to_read
from app.config import settings
from app.models import InputType, ProcessingJob
from app.repositories import JobRepository
from app.schemas.notification import (
    ResurfaceRequest,
    ResurfaceResponse,
    SimulateDateRequest,
    SimulateLocationRequest,
)
from app.services.notification import ResurfacingService
from app.services.trigger import TriggerContext
from app.utils.errors import DemoModeDisabledError
from app.utils.timeparse import utcnow
from app.workers import process_job

router = APIRouter(tags=["demo"])

# Text captures the mock provider classifies deterministically - no network.
_SEED_CAPTURES: list[str] = [
    "El Xampanyet tapas bar in Barcelona - amazing place, must visit on my "
    "next trip to Spain.",
    "Coldplay live at Wembley Stadium on 2026-09-14 at 7pm. Need to buy "
    "tickets for this concert!",
    "Creamy garlic butter pasta recipe - only 20 minutes. Going to cook this "
    "for dinner this weekend.",
    "Notion Calendar - a productivity tool for planning my week. Want to try "
    "this app soon.",
    "Fascinating long read on how large language models actually work. Save "
    "this article to read later.",
]


def _require_demo() -> None:
    if not settings.demo_mode_enabled:
        raise DemoModeDisabledError()


async def _resurface(
    session: SessionDep,
    *,
    user_id,
    context: TriggerContext,
    memory_id=None,
    trigger_type=None,
) -> ResurfaceResponse:
    service = ResurfacingService(session)
    fired = await service.resurface(
        user_id=user_id,
        context=context,
        memory_id=memory_id,
        trigger_type=trigger_type,
    )
    await session.commit()
    for notification in fired:
        await session.refresh(notification)
    return ResurfaceResponse(
        fired=len(fired),
        notifications=[_to_read(n) for n in fired],
        message=(
            f"{len(fired)} memory resurfaced."
            if fired
            else "Nothing matched - no memory resurfaced."
        ),
    )


@router.post("/test/resurface", response_model=ResurfaceResponse)
async def test_resurface(
    payload: ResurfaceRequest, user: CurrentUser, session: SessionDep
) -> ResurfaceResponse:
    # Force one specific memory to resurface now, whatever its trigger type.
    context = TriggerContext(now=utcnow(), latitude=None, longitude=None, force=True)
    return await _resurface(
        session,
        user_id=user.id,
        context=context,
        memory_id=payload.memory_id,
        trigger_type=payload.trigger_type,
    )


@router.post("/demo/simulate-location", response_model=ResurfaceResponse)
async def simulate_location(
    payload: SimulateLocationRequest, user: CurrentUser, session: SessionDep
) -> ResurfaceResponse:
    _require_demo()
    if payload.memory_id is not None:
        # Naming a memory forces it; coordinates run the real geofence check.
        context = TriggerContext(
            now=utcnow(), latitude=None, longitude=None, force=True
        )
        return await _resurface(
            session, user_id=user.id, context=context, memory_id=payload.memory_id
        )
    context = TriggerContext(
        now=utcnow(),
        latitude=payload.latitude,
        longitude=payload.longitude,
        force=False,
    )
    return await _resurface(
        session, user_id=user.id, context=context, trigger_type=None
    )


@router.post("/demo/simulate-date", response_model=ResurfaceResponse)
async def simulate_date(
    payload: SimulateDateRequest, user: CurrentUser, session: SessionDep
) -> ResurfaceResponse:
    _require_demo()
    as_of = payload.as_of or utcnow()
    force = payload.memory_id is not None
    context = TriggerContext(
        now=as_of, latitude=None, longitude=None, force=force
    )
    return await _resurface(
        session, user_id=user.id, context=context, memory_id=payload.memory_id
    )


@router.post("/demo/seed")
async def seed(user: CurrentUser, session: SessionDep) -> dict[str, int]:
    _require_demo()
    jobs = JobRepository(session)
    job_ids = []
    for content in _SEED_CAPTURES:
        job = ProcessingJob(
            user_id=user.id,
            input_type=InputType.TEXT,
            raw_content=content,
            origin="demo",
        )
        await jobs.create(job)
        job_ids.append(job.id)
    await session.commit()

    created = 0
    for job_id in job_ids:
        await process_job(job_id)
    # process_job commits in its own session; expire our identity-mapped copies
    # so the count below reads the freshly-persisted memory_id, not a stale None.
    session.expire_all()
    for job_id in job_ids:
        refreshed = await jobs.get_any(job_id)
        if refreshed is not None and refreshed.memory_id is not None:
            created += 1
    return {"created": created}
