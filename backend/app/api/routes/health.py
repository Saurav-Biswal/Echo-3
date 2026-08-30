"""GET /api/health - liveness plus which AI provider is actually wired up."""

from __future__ import annotations

from fastapi import APIRouter

from app.config import settings
from app.db.session import engine
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        app=settings.app_name,
        env=settings.app_env,
        # Reflects reality (mock when no key), not just the configured value.
        ai_provider=settings.resolved_ai_provider(),
        database=engine.dialect.name,
        demo_mode=settings.demo_mode_enabled,
    )
