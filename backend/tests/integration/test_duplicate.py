"""Duplicate detection at the repository level (§33).

Only a prior save that actually produced a memory counts as a duplicate; a
source row left behind by a failed job must not block a retry.
"""

from __future__ import annotations

from sqlalchemy import select

from app.config import settings
from app.models import EchoMemory, MediaSource, User
from app.models.enums import (
    Category,
    IntentAction,
    MediaType,
    Platform,
    SourceType,
)
from app.repositories import SourceRepository

_CANONICAL = "https://www.youtube.com/watch?v=dupTest1234"


async def _demo_user(session) -> User:
    result = await session.execute(
        select(User).where(User.email == settings.demo_user_email)
    )
    return result.scalar_one()


def _source(user_id, canonical: str) -> MediaSource:
    return MediaSource(
        user_id=user_id,
        source_type=SourceType.YOUTUBE_VIDEO,
        platform=Platform.YOUTUBE,
        media_type=MediaType.VIDEO,
        source_url=canonical,
        canonical_url=canonical,
    )


async def test_duplicate_matches_source_that_produced_a_memory(session):
    user = await _demo_user(session)

    orphan = _source(user.id, _CANONICAL)  # a failed job left this behind
    session.add(orphan)
    await session.flush()

    saved = _source(user.id, _CANONICAL)
    session.add(saved)
    await session.flush()

    memory = EchoMemory(
        user_id=user.id,
        source_id=saved.id,
        category=Category.TOPIC,
        title="A saved video",
        why_saved="You probably saved this because you want to watch it later.",
        intent_action=IntentAction.READ,
    )
    session.add(memory)
    await session.flush()

    found = await SourceRepository(session).find_duplicate(
        user_id=user.id, canonical_url=_CANONICAL
    )
    assert found is not None
    assert found.id == saved.id


async def test_orphan_source_is_not_a_duplicate(session):
    user = await _demo_user(session)
    orphan = _source(user.id, "https://www.youtube.com/watch?v=noMemory99")
    session.add(orphan)
    await session.flush()

    found = await SourceRepository(session).find_duplicate(
        user_id=user.id, canonical_url="https://www.youtube.com/watch?v=noMemory99"
    )
    assert found is None
