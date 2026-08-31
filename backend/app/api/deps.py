"""Request dependencies.

Auth is deliberately a single seam (§MVP): every row is keyed by ``user_id``,
but the MVP resolves that id from an optional ``X-Echo-User`` email header,
defaulting to the demo user. Swapping in real auth means changing only this
function - no route or repository learns how identity is established.

The same seam carries the client's timezone (``X-Echo-Timezone``). It is stored
on the user rather than read per-request, because a reminder derived by the
background scan loop has no request to read a header from.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_session
from app.models import User
from app.repositories import UserRepository
from app.utils.logging import get_logger
from app.utils.timezones import is_valid_zone

logger = get_logger(__name__)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    session: SessionDep,
    x_echo_user: Annotated[str | None, Header(alias="X-Echo-User")] = None,
    x_echo_timezone: Annotated[str | None, Header(alias="X-Echo-Timezone")] = None,
) -> User:
    email = (x_echo_user or settings.demo_user_email).strip().lower()
    declared_zone = _valid_zone(x_echo_timezone)

    repo = UserRepository(session)
    user = await repo.get_by_email(email)
    if user is None:
        # First time we have seen this identity - create it so its rows have an
        # owner. Committed here because a read-only route will not commit.
        user = User(
            email=email,
            name=email.split("@", 1)[0] or "Echo user",
            is_demo=email == settings.demo_user_email,
            timezone=declared_zone or settings.default_timezone,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    # The phone is the authority on where its owner is. Persist a change so
    # background work (the trigger scan loop) sees the same zone the app does.
    if declared_zone and declared_zone != user.timezone:
        logger.info(
            "user.timezone_updated", was=user.timezone or "unset", now=declared_zone
        )
        user.timezone = declared_zone
        await session.commit()
        await session.refresh(user)
    return user


def _valid_zone(raw: str | None) -> str | None:
    """Accept an IANA zone from a client, ignore anything else.

    A junk header must not fail the request: the user still wants their capture
    saved, and the stored zone is a safe fallback.
    """
    if raw is None:
        return None
    candidate = raw.strip()
    if not candidate:
        return None
    if not is_valid_zone(candidate):
        logger.warning("user.timezone_rejected", requested=candidate[:64])
        return None
    return candidate


CurrentUser = Annotated[User, Depends(get_current_user)]
