"""Aggregate router - every route module mounted under one prefix in main."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    capture,
    demo,
    health,
    jobs,
    memories,
    notifications,
    triggers,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(capture.router)
api_router.include_router(jobs.router)
api_router.include_router(memories.router)
api_router.include_router(triggers.router)
api_router.include_router(notifications.router)
api_router.include_router(demo.router)

__all__ = ["api_router"]
