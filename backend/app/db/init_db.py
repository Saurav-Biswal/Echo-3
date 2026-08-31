"""Schema creation and the demo-user bootstrap.

``create_all`` is enough for the MVP; Alembic is installed and configured so the
first real migration can be generated from these same models without rework.

``create_all`` only ever *creates* - it will not add a column to a table that
already exists, so a dev database created before a model gained a field would
fail every query against it. :func:`_add_missing_columns` closes that gap for
SQLite in dev, additively and only for columns the models declare. It never
drops, renames or retypes anything; anything beyond adding a nullable/defaulted
column is a real migration and belongs in Alembic.
"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, select, text
from sqlalchemy.schema import CreateColumn

from app.config import settings
from app.db.session import SessionFactory, engine
from app.models import Base, User

logger = logging.getLogger(__name__)


def _add_missing_columns(connection) -> list[str]:  # noqa: ANN001 - sync connection
    """Add model columns absent from an existing table. Returns what it added."""
    inspector = inspect(connection)
    existing_tables = set(inspector.get_table_names())
    added: list[str] = []

    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue  # create_all just made it, so it is already current
        present = {column["name"] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in present:
                continue
            if not (column.nullable or column.default is not None):
                # SQLite cannot add a NOT NULL column without a default, and
                # guessing a backfill value is a migration decision, not ours.
                logger.warning(
                    "db.column_needs_migration table=%s column=%s",
                    table.name,
                    column.name,
                )
                continue
            ddl = CreateColumn(column).compile(bind=connection.engine)
            connection.execute(
                text(f"ALTER TABLE {table.name} ADD COLUMN {ddl}")
            )
            added.append(f"{table.name}.{column.name}")
    return added


async def create_schema() -> None:
    settings.media_temp_dir.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        added = await connection.run_sync(_add_missing_columns)
    if added:
        logger.info("db.columns_added %s", ", ".join(added))
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
