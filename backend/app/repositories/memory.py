"""Echo memory persistence, listing and the overview aggregates."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Select, func, or_, select

from app.models import (
    Category,
    EchoMemory,
    Entity,
    MemoryStatus,
    ResurfacingTrigger,
    TriggerStatus,
)
from app.repositories.base import Repository


class MemoryRepository(Repository):
    async def create(self, memory: EchoMemory) -> EchoMemory:
        self.session.add(memory)
        await self.session.flush()
        return memory

    async def get(
        self, memory_id: uuid.UUID, *, user_id: uuid.UUID
    ) -> EchoMemory | None:
        memory = await self.session.get(EchoMemory, memory_id)
        if memory is None or memory.user_id != user_id:
            return None
        return memory

    def _filtered(
        self,
        *,
        user_id: uuid.UUID,
        status: MemoryStatus | None,
        category: Category | None,
        q: str | None,
    ) -> Select[tuple[EchoMemory]]:
        stmt = select(EchoMemory).where(EchoMemory.user_id == user_id)
        if status is not None:
            stmt = stmt.where(EchoMemory.status == status)
        if category is not None:
            stmt = stmt.where(EchoMemory.category == category)
        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    EchoMemory.title.ilike(like),
                    EchoMemory.summary.ilike(like),
                    EchoMemory.why_saved.ilike(like),
                )
            )
        return stmt

    async def list(
        self,
        *,
        user_id: uuid.UUID,
        status: MemoryStatus | None = None,
        category: Category | None = None,
        q: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[EchoMemory], int]:
        base = self._filtered(
            user_id=user_id, status=status, category=category, q=q
        )
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        result = await self.session.execute(
            base.order_by(EchoMemory.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all()), int(total or 0)

    async def delete(self, memory: EchoMemory) -> None:
        # Cascades take triggers, entities, actions and notifications (§43).
        await self.session.delete(memory)

    # -------------------------------------------------------- overview (§26)

    async def count_by_status(self, *, user_id: uuid.UUID) -> dict[MemoryStatus, int]:
        result = await self.session.execute(
            select(EchoMemory.status, func.count())
            .where(EchoMemory.user_id == user_id)
            .group_by(EchoMemory.status)
        )
        return {status: int(count) for status, count in result.all()}

    async def count_by_category(
        self, *, user_id: uuid.UUID
    ) -> list[tuple[Category, int]]:
        result = await self.session.execute(
            select(EchoMemory.category, func.count())
            .where(
                EchoMemory.user_id == user_id,
                EchoMemory.status.not_in(
                    (MemoryStatus.DISMISSED, MemoryStatus.ARCHIVED)
                ),
            )
            .group_by(EchoMemory.category)
            .order_by(func.count().desc())
        )
        return [(category, int(count)) for category, count in result.all()]

    async def recent(
        self, *, user_id: uuid.UUID, limit: int = 6
    ) -> list[EchoMemory]:
        result = await self.session.execute(
            select(EchoMemory)
            .where(EchoMemory.user_id == user_id)
            .order_by(EchoMemory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def next_trigger_at(self, *, user_id: uuid.UUID) -> datetime | None:
        return await self.session.scalar(
            select(func.min(ResurfacingTrigger.fire_at)).where(
                ResurfacingTrigger.user_id == user_id,
                ResurfacingTrigger.status == TriggerStatus.PENDING,
                ResurfacingTrigger.fire_at.is_not(None),
            )
        )
