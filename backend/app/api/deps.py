"""Request dependencies.

Auth is deliberately a single seam (§MVP): every row is keyed by ``user_id``,
but the MVP resolves that id from an optional ``X-Echo-User`` email header,
defaulting to the demo user. Swapping in real auth means changing only this
function - no route or repository learns how identity is established.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_session
from app.models import User
from app.repositories import UserRepository

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    session: SessionDep,
    x_echo_user: Annotated[str | None, Header(alias="X-Echo-User")] = None,
) -> User:
    email = (x_echo_user or settings.demo_user_email).strip().lower()
    repo = UserRepository(session)
    user = await repo.get_by_email(email)
    if user is None:
        # First time we have seen this identity - create it so its rows have an
        # owner. Committed here because a read-only route will not commit.
        user = User(
            email=email,
            name=email.split("@", 1)[0] or "Echo user",
            is_demo=email == settings.demo_user_email,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
