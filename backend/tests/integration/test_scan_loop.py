"""Autonomous trigger scan loop: a due DATE/TIME trigger fires with no demo POST.

This is the heartbeat that was missing (§19): trigger *creation* was wired, but
nothing fired a time trigger on its own. These drive one scan tick deterministic-
ally via ``scan_once()`` (the loop's body without its sleep) and assert it travels
the same canonical resurface path the demo endpoints use.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import select

from app.db.session import SessionFactory
from app.models import (
    MemoryStatus,
    Notification,
    ResurfacingTrigger,
    TriggerStatus,
    TriggerType,
)
from app.utils.timeparse import utcnow
from app.workers.scan import scan_once

_EVENT_TEXT = (
    "Coldplay live at Wembley Stadium on 2026-09-14 at 7pm. Need to buy "
    "tickets for this concert!"
)


async def _capture_event(client) -> str:
    resp = await client.post(
        "/api/capture", json={"input_type": "text", "content": _EVENT_TEXT}
    )
    assert resp.status_code == 202, resp.text
    job_id = resp.json()["job_id"]
    resp = await client.post("/api/process", json={"job_id": job_id})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "COMPLETED"
    return body["memory_id"]


async def _time_trigger(memory_id: str) -> ResurfacingTrigger:
    async with SessionFactory() as session:
        result = await session.execute(
            select(ResurfacingTrigger).where(
                ResurfacingTrigger.memory_id == uuid.UUID(memory_id),
                ResurfacingTrigger.trigger_type.in_(
                    (TriggerType.DATE, TriggerType.TIME)
                ),
            )
        )
        trigger = result.scalars().first()
        assert trigger is not None, "event capture should yield a DATE/TIME trigger"
        return trigger


async def _set_fire_at(trigger_id, moment) -> None:
    async with SessionFactory() as session:
        trigger = await session.get(ResurfacingTrigger, trigger_id)
        trigger.fire_at = moment
        trigger.status = TriggerStatus.PENDING
        await session.commit()


async def test_scan_fires_due_trigger_autonomously(client):
    memory_id = await _capture_event(client)
    trigger = await _time_trigger(memory_id)

    # Pull its moment into the past so it is genuinely due right now.
    await _set_fire_at(trigger.id, utcnow() - timedelta(hours=1))

    fired = await scan_once()
    assert fired == 1

    # The trigger is now FIRED (fires once) and a notification exists - all via
    # the same ResurfacingService the demo endpoints call.
    async with SessionFactory() as session:
        refreshed = await session.get(ResurfacingTrigger, trigger.id)
        assert refreshed.status == TriggerStatus.FIRED
        assert refreshed.fired_at is not None
        notifs = (
            (await session.execute(select(Notification).where(
                Notification.memory_id == uuid.UUID(memory_id)
            ))).scalars().all()
        )
        assert len(notifs) == 1

    feed = await client.get("/api/notifications")
    assert feed.json()["total"] >= 1


async def test_scan_leaves_future_trigger_pending(client):
    memory_id = await _capture_event(client)
    trigger = await _time_trigger(memory_id)

    # Firmly in the future: the scan must not fire it early.
    await _set_fire_at(trigger.id, utcnow() + timedelta(days=3))

    fired = await scan_once()
    assert fired == 0

    async with SessionFactory() as session:
        refreshed = await session.get(ResurfacingTrigger, trigger.id)
        assert refreshed.status == TriggerStatus.PENDING


async def test_scan_fires_each_trigger_only_once(client):
    memory_id = await _capture_event(client)
    trigger = await _time_trigger(memory_id)
    await _set_fire_at(trigger.id, utcnow() - timedelta(hours=1))

    assert await scan_once() == 1
    # Second tick: already FIRED, so nothing new fires and no duplicate notice.
    assert await scan_once() == 0

    async with SessionFactory() as session:
        notifs = (
            (await session.execute(select(Notification).where(
                Notification.memory_id == uuid.UUID(memory_id)
            ))).scalars().all()
        )
        assert len(notifs) == 1
