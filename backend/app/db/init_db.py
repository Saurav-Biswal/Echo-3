"""Schema creation and the demo-user bootstrap.

``create_all`` is enough for the MVP; Alembic is installed and configured so the
first real migration can be generated from these same models without rework.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.config import settings
from app.db.session import SessionFactory, engine
from app.models import Base, User

logger = logging.getLogger(__name__)


async def create_schema() -> None:
    settings.media_temp_dir.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    logger.info("db.schema_ready tables=%d", len(Base.metadata.tables))


async def ensure_demo_user() -> User:
    """Idempotently create the single MVP user."""
    async with SessionFactory() as session:
        result = await session.execute(
            select(User).where(User.email == settings.demo_user_email)
        )
        user = result.scalar_one_or_none()
        if user is not None:
            return user

        user = User(
            email=settings.demo_user_email,
            name=settings.demo_user_name,
            is_demo=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info("db.demo_user_created id=%s", user.id)
        return user


async def init_db() -> User:
    await create_schema()
    return await ensure_demo_user()
