"""Memory CRUD, the overview aggregate, and the correction path (§14, §26)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, SessionDep
from app.models import Category, MemoryStatus
from app.repositories import MemoryRepository
from app.schemas.common import Ack, Page
from app.schemas.memory import (
    CategoryCount,
    MemoryCorrection,
    MemoryRead,
    MemoryUpdate,
    OverviewResponse,
)
from app.services.memory import MemoryService
from app.utils.errors import MemoryNotFoundError
from app.utils.timeparse import utcnow

router = APIRouter(tags=["memories"])


@router.get("/overview", response_model=OverviewResponse)
async def overview(user: CurrentUser, session: SessionDep) -> OverviewResponse:
    repo = MemoryRepository(session)
    by_status = await repo.count_by_status(user_id=user.id)
    by_category = await repo.count_by_category(user_id=user.id)
    recent = await repo.recent(user_id=user.id)
    return OverviewResponse(
        active=by_status.get(MemoryStatus.ACTIVE, 0),
        resurfaced=by_status.get(MemoryStatus.RESURFACED, 0),
        completed=by_status.get(MemoryStatus.COMPLETED, 0),
        needs_review=by_status.get(MemoryStatus.NEEDS_REVIEW, 0),
        by_category=[
            CategoryCount(category=category, count=count)
            for category, count in by_category
        ],
        upcoming_trigger_at=await repo.next_trigger_at(user_id=user.id),
        recent=[MemoryRead.model_validate(m) for m in recent],
    )


@router.get("/memories", response_model=Page[MemoryRead])
async def list_memories(
    user: CurrentUser,
    session: SessionDep,
    status: MemoryStatus | None = None,
    category: Category | None = None,
    q: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Page[MemoryRead]:
    items, total = await MemoryRepository(session).list(
        user_id=user.id,
        status=status,
        category=category,
        q=q,
        limit=limit,
        offset=offset,
    )
    return Page(
        items=[MemoryRead.model_validate(m) for m in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/memories/{memory_id}", response_model=MemoryRead)
async def get_memory(
    memory_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> MemoryRead:
    memory = await MemoryRepository(session).get(memory_id, user_id=user.id)
    if memory is None:
        raise MemoryNotFoundError()
    return MemoryRead.model_validate(memory)


@router.patch("/memories/{memory_id}", response_model=MemoryRead)
async def update_memory(
    memory_id: uuid.UUID,
    payload: MemoryUpdate,
    user: CurrentUser,
    session: SessionDep,
) -> MemoryRead:
    repo = MemoryRepository(session)
    memory = await repo.get(memory_id, user_id=user.id)
    if memory is None:
        raise MemoryNotFoundError()

    if payload.status is not None:
        memory.status = payload.status
        if payload.status == MemoryStatus.COMPLETED:
            memory.completed_at = utcnow()
    if payload.title is not None:
        memory.title = payload.title
    if payload.why_saved is not None:
        memory.why_saved = payload.why_saved

    await session.commit()
    await session.refresh(memory)
    return MemoryRead.model_validate(memory)


@router.post("/memories/{memory_id}/correct", response_model=MemoryRead)
async def correct_memory(
    memory_id: uuid.UUID,
    payload: MemoryCorrection,
    user: CurrentUser,
    session: SessionDep,
) -> MemoryRead:
    repo = MemoryRepository(session)
    memory = await repo.get(memory_id, user_id=user.id)
    if memory is None:
        raise MemoryNotFoundError()

    await MemoryService(session).apply_correction(memory, payload)
    await session.commit()
    await session.refresh(memory)
    return MemoryRead.model_validate(memory)


@router.delete("/memories/{memory_id}", response_model=Ack)
async def delete_memory(
    memory_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> Ack:
    repo = MemoryRepository(session)
    memory = await repo.get(memory_id, user_id=user.id)
    if memory is None:
        raise MemoryNotFoundError()
    await repo.delete(memory)
    await session.commit()
    return Ack(message="Memory deleted.")
