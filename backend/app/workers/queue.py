"""In-process job queue (§31).

Echo's worker is an asyncio task in the same process as the API, fed by an
``asyncio.Queue``. That is deliberately the simplest thing that satisfies the
contract - capture enqueues and returns, the worker drains one job at a time -
and it swaps for a real broker without touching callers: they only ever see
``enqueue``. ``process_job`` is also importable directly, which is how tests and
the demo seeder run a capture synchronously.
"""

from __future__ import annotations

import asyncio
import uuid

from app.utils.logging import get_logger
from app.workers.pipeline import process_job

logger = get_logger(__name__)

_queue: asyncio.Queue[uuid.UUID] | None = None
_worker_task: asyncio.Task[None] | None = None


def _get_queue() -> asyncio.Queue[uuid.UUID]:
    global _queue
    if _queue is None:
        _queue = asyncio.Queue()
    return _queue


async def enqueue(job_id: uuid.UUID) -> None:
    """Hand a freshly created job to the worker and return at once."""
    await _get_queue().put(job_id)


async def _worker_loop() -> None:
    queue = _get_queue()
    logger.info("worker.started")
    while True:
        job_id = await queue.get()
        try:
            await process_job(job_id)
        except Exception:  # noqa: BLE001 - one bad job must not kill the loop
            logger.exception("worker.job_crashed", job_id=str(job_id))
        finally:
            queue.task_done()


async def start_worker() -> None:
    """Start the background worker if it is not already running (app startup)."""
    global _worker_task
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.create_task(_worker_loop())


async def stop_worker() -> None:
    """Cancel the worker on shutdown; drain nothing - jobs re-run on restart."""
    global _worker_task
    if _worker_task is None:
        return
    _worker_task.cancel()
    try:
        await _worker_task
    except asyncio.CancelledError:
        pass
    _worker_task = None
