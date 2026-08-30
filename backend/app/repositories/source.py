"""Media source persistence and the duplicate-detection lookup (§33)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import MediaSource
from app.repositories.base import Repository


class SourceRepository(Repository):
    async def create(self, source: MediaSource) -> MediaSource:
        self.session.add(source)
        await self.session.flush()
        return source

    async def get(self, source_id: uuid.UUID) -> MediaSource | None:
        return await self.session.get(MediaSource, source_id)

    async def find_duplicate(
        self, *, user_id: uuid.UUID, canonical_url: str
    ) -> MediaSource | None:
        """A prior save of the same canonical URL by the same user (§33).

        Only sources that actually produced a memory count as duplicates: a
        source row left behind by a failed job must not block a retry.
        """
        result = await self.session.execute(
            select(MediaSource)
            .where(
                MediaSource.user_id == user_id,
                MediaSource.canonical_url == canonical_url,
            )
            .options(selectinload(MediaSource.memory))
            .order_by(MediaSource.created_at.desc())
        )
        for source in result.scalars():
            if source.memory is not None:
                return source
        return None
