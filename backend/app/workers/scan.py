"""Autonomous trigger scan loop (§19, §45).

The gap this closes: capture, analysis and trigger *creation* were wired, and
the demo endpoints could force a resurface, but nothing fired a DATE/TIME
trigger on its own. A reminder set for 7pm sat PENDING forever unless a demo
POST nudged it. This loop is the missing heartbeat.

It deliberately does **not** contain any firing logic of its own. It finds the
users with a due trigger and hands each to :meth:`ResurfacingService.resurface`
- the exact call the demo controls make - with a real (non-forced) now-context.
So an autonomously-fired reminder and a demo-fired one travel identical code:
same evaluator, same notification, same dedupe. There is one firing path (§45).

Like the capture worker (:mod:`app.workers.queue`) it is a single asyncio task
in the API process, started on lifespan and cancelled on shutdown. One bad tick
must never kill the loop, so every iteration is wrapped.
"""

from __future__ import annotations

import asyncio

from app.config import settings
from app.db.session import session_scope
from app.repositories import TriggerRepository
from app.services.notification import ResurfacingService
from app.services.trigger import TriggerContext
from app.utils.logging import get_logger
from app.utils.timeparse import utcnow

logger = get_logger(__name__)

_scanner_task: asyncio.Task[None] | None = None


async def scan_once() -> int:
    """Fire every due DATE/TIME trigger once. Returns notifications sent.

    Importable directly so tests can drive one tick deterministically without
    the loop's sleep.
    """
    fired_total = 0
    async with session_scope() as session:
        as_of = utcnow()
        user_ids = await TriggerRepository(session).due_user_ids(as_of=as_of)
        if not user_ids:
            return 0
        service = ResurfacingService(session)
        for user_id in user_ids:
            # A real now-context, force=False: only genuinely-due triggers fire,
            # and LOCATION triggers (no coords here) are correctly skipped.
            context = TriggerContext(now=as_of, latitude=None, longitude=None)
            fired = await service.resurface(user_id=user_id, context=context)
            fired_total += len(fired)
    if fired_total:
        logger.info("scanner.fired", users=len(user_ids), notifications=fired_total)
    return fired_total


async def _scanner_loop() -> None:
    interval = max(1, settings.trigger_scan_interval_seconds)
    logger.info("scanner.started", interval_seconds=interval)
    while True:
        try:
            await scan_once()
        except Exception:  # noqa: BLE001 - a bad tick must not kill the loop
            logger.exception("scanner.tick_crashed")
        await asyncio.sleep(interval)


async def start_scanner() -> None:
    """Start the scan loop if not already running (app startup)."""
    global _scanner_task
    if _scanner_task is None or _scanner_task.done():
        _scanner_task = asyncio.create_task(_scanner_loop())


async def stop_scanner() -> None:
    """Cancel the scan loop on shutdown."""
    global _scanner_task
    if _scanner_task is None:
        return
    _scanner_task.cancel()
    try:
        await _scanner_task
    except asyncio.CancelledError:
        pass
    _scanner_task = None
