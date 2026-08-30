"""Repository layer.

The only code that builds SQLAlchemy queries. Services and routes speak in
domain objects and never assemble a ``select`` themselves, so the storage shape
stays swappable (§37). Every repository is constructed with the request's
``AsyncSession``; it neither opens nor commits transactions - that is the
caller's job (a request or a worker's ``session_scope``).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession


class Repository:
    """Common base: holds the session, nothing more."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
