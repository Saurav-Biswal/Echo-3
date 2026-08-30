"""Notification persistence and the resurfacing history feed."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select

from app.models import Notification, NotificationStatus
from app.repositories.base import Repository


class NotificationRepository(Repository):
    async def create(self, notification: Notification) -> Notification:
        self.session.add(notification)
        await self.session.flush()
        return notification

    async def get(
        self, notification_id: uuid.UUID, *, user_id: uuid.UUID
    ) -> Notification | None:
        notification = await self.session.get(Notification, notification_id)
        if notification is None or notification.user_id != user_id:
            return None
        return notification

    def _filtered(
        self,
        *,
        user_id: uuid.UUID,
        status: NotificationStatus | None,
    ) -> Select[tuple[Notification]]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if status is not None:
            stmt = stmt.where(Notification.status == status)
        return stmt

    async def list(
        self,
        *,
        user_id: uuid.UUID,
        status: NotificationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Notification], int]:
        base = self._filtered(user_id=user_id, status=status)
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        result = await self.session.execute(
            base.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all()), int(total or 0)
