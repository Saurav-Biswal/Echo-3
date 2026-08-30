"""User lookups. The MVP has one demo user; every row still keys on user_id."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models import User
from app.repositories.base import Repository


class UserRepository(Repository):
    async def get(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
