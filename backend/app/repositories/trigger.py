"""Resurfacing-trigger persistence and the queries the evaluators run (§19)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Select, func, select

from app.models import (
    EchoMemory,
    ResurfacingTrigger,
    TriggerStatus,
    TriggerType,
)
from app.repositories.base import Repository


class TriggerRepository(Repository):
    async def create(self, trigger: ResurfacingTrigger) -> ResurfacingTrigger:
        self.session.add(trigger)
        await self.session.flush()
        return trigger

    async def get(
        self, trigger_id: uuid.UUID, *, user_id: uuid.UUID
    ) -> ResurfacingTrigger | None:
        trigger = await self.session.get(ResurfacingTrigger, trigger_id)
        if trigger is None or trigger.user_id != user_id:
            return None
        return trigger

    async def find_by_dedupe(
        self, *, memory_id: uuid.UUID, dedupe_key: str
    ) -> ResurfacingTrigger | None:
        """The uniqueness §21 relies on to never build the same reminder twice."""
        result = await self.session.execute(
            select(ResurfacingTrigger).where(
                ResurfacingTrigger.memory_id == memory_id,
                ResurfacingTrigger.dedupe_key == dedupe_key,
            )
        )
        return result.scalar_one_or_none()

    def _filtered(
        self,
        *,
        user_id: uuid.UUID,
        status: TriggerStatus | None,
        trigger_type: TriggerType | None,
        memory_id: uuid.UUID | None,
    ) -> Select[tuple[ResurfacingTrigger]]:
        stmt = select(ResurfacingTrigger).where(
            ResurfacingTrigger.user_id == user_id
        )
        if status is not None:
            stmt = stmt.where(ResurfacingTrigger.status == status)
        if trigger_type is not None:
            stmt = stmt.where(ResurfacingTrigger.trigger_type == trigger_type)
        if memory_id is not None:
            stmt = stmt.where(ResurfacingTrigger.memory_id == memory_id)
        return stmt

    async def list(
        self,
        *,
        user_id: uuid.UUID,
        status: TriggerStatus | None = None,
        trigger_type: TriggerType | None = None,
        memory_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ResurfacingTrigger], int]:
        base = self._filtered(
            user_id=user_id,
            status=status,
            trigger_type=trigger_type,
            memory_id=memory_id,
        )
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        result = await self.session.execute(
            base.order_by(ResurfacingTrigger.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), int(total or 0)

    async def geofences(
        self, *, user_id: uuid.UUID
    ) -> list[ResurfacingTrigger]:
        """Pending LOCATION triggers with coordinates - what Android registers."""
        result = await self.session.execute(
            select(ResurfacingTrigger)
            .where(
                ResurfacingTrigger.user_id == user_id,
                ResurfacingTrigger.status == TriggerStatus.PENDING,
                ResurfacingTrigger.trigger_type == TriggerType.LOCATION,
                ResurfacingTrigger.latitude.is_not(None),
                ResurfacingTrigger.longitude.is_not(None),
            )
            .order_by(ResurfacingTrigger.created_at.desc())
        )
        return list(result.scalars().all())

    async def pending_by_type(
        self,
        *,
        user_id: uuid.UUID,
        trigger_type: TriggerType,
    ) -> list[ResurfacingTrigger]:
        result = await self.session.execute(
            select(ResurfacingTrigger).where(
                ResurfacingTrigger.user_id == user_id,
                ResurfacingTrigger.status == TriggerStatus.PENDING,
                ResurfacingTrigger.trigger_type == trigger_type,
            )
        )
        return list(result.scalars().all())

    async def due(
        self, *, user_id: uuid.UUID, as_of: datetime
    ) -> list[ResurfacingTrigger]:
        """Pending DATE/TIME triggers whose ``fire_at`` has arrived."""
        result = await self.session.execute(
            select(ResurfacingTrigger).where(
                ResurfacingTrigger.user_id == user_id,
                ResurfacingTrigger.status == TriggerStatus.PENDING,
                ResurfacingTrigger.trigger_type.in_(
                    (TriggerType.DATE, TriggerType.TIME)
                ),
                ResurfacingTrigger.fire_at.is_not(None),
                ResurfacingTrigger.fire_at <= as_of,
            )
        )
        return list(result.scalars().all())

    async def due_user_ids(self, *, as_of: datetime) -> list[uuid.UUID]:
        """Distinct users who have at least one due DATE/TIME trigger.

        The autonomous scan loop uses this to visit only users with work
        pending, then fires each through the canonical resurface path rather
        than firing triggers here (keeping one firing code path, §45).
        """
        result = await self.session.execute(
            select(ResurfacingTrigger.user_id)
            .where(
                ResurfacingTrigger.status == TriggerStatus.PENDING,
                ResurfacingTrigger.trigger_type.in_(
                    (TriggerType.DATE, TriggerType.TIME)
                ),
                ResurfacingTrigger.fire_at.is_not(None),
                ResurfacingTrigger.fire_at <= as_of,
            )
            .distinct()
        )
        return list(result.scalars().all())

    async def pending_for_memory(
        self, memory_id: uuid.UUID
    ) -> list[ResurfacingTrigger]:
        result = await self.session.execute(
            select(ResurfacingTrigger).where(
                ResurfacingTrigger.memory_id == memory_id,
                ResurfacingTrigger.status == TriggerStatus.PENDING,
            )
        )
        return list(result.scalars().all())

    async def memory_for(
        self, trigger: ResurfacingTrigger
    ) -> EchoMemory | None:
        return await self.session.get(EchoMemory, trigger.memory_id)

    async def delete(self, trigger: ResurfacingTrigger) -> None:
        await self.session.delete(trigger)
