"""Application configuration.

Every tunable in Echo lives here so that model choice, confidence thresholds,
geofence radius and reminder lead times can be changed without touching logic.
Secrets are read from the environment / ``backend/.env`` and never shipped to a
client.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------------------------------------------------------------- app
    app_name: str = "Echo"
    app_env: Literal["dev", "test", "prod"] = "dev"
    debug: bool = True
    api_prefix: str = "/api"
    host: str = "0.0.0.0"
    port: int = 8000

    # Comma-separated in the environment, list in code. NoDecode stops
    # pydantic-settings from trying to JSON-parse the raw env string (so a
    # bare "*" or "a.com,b.com" is accepted); the validator below splits it.
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["*"])

    # ----------------------------------------------------------- database
    # SQLite today; swap to postgresql+asyncpg://... for Supabase/Postgres.
    # Nothing else in the codebase needs to change.
    database_url: str = f"sqlite+aiosqlite:///{(BACKEND_ROOT / 'echo.db').as_posix()}"
    database_echo: bool = False

    # ------------------------------------------------------------------ ai
    # "gemini" uses the real API; "mock" is a deterministic offline provider
    # implementing the identical interface (used by tests and by demos with no key).
    ai_provider: Literal["gemini", "mock"] = "gemini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    # Used when the primary model is unavailable or rate-limited.
    gemini_fallback_model: str = "gemini-2.5-flash-lite"
    gemini_timeout_seconds: float = 120.0
    gemini_max_attempts: int = 3
    # Files API is used above this size; inline bytes below it.
    gemini_inline_upload_limit_bytes: int = 18 * 1024 * 1024
    gemini_file_active_timeout_seconds: float = 90.0

    # -------------------------------------------------------- confidence
    # §13: >= high -> auto-save; medium..high -> save + lightweight confirm;
    # < medium -> ask the user what they intended (status NEEDS_REVIEW).
    confidence_high_threshold: float = 0.80
    confidence_medium_threshold: float = 0.55

    # ------------------------------------------------------------- media
    media_temp_dir: Path = BACKEND_ROOT / ".media_tmp"
    media_max_download_bytes: int = 80 * 1024 * 1024
    media_max_duration_seconds: int = 300
    media_acquisition_timeout_seconds: float = 90.0
    # Keep raw media only for the length of the job (§43 privacy).
    media_retain_downloads: bool = False

    # ---------------------------------------------------------- triggers
    geofence_default_radius_meters: int = 300
    geofence_min_radius_meters: int = 100
    geofence_max_radius_meters: int = 2000
    event_reminder_lead_hours: int = 24
    # Fallback nudge for TIME-based categories (recipes/tools/topics).
    default_time_trigger_delay_hours: int = 72
    trigger_scan_interval_seconds: int = 60

    # ---------------------------------------------------------- workers
    worker_concurrency: int = 2
    job_queue_max_size: int = 256

    # -------------------------------------------------------------- auth
    # MVP: a single demo user, but every row is keyed by user_id so real auth
    # slots in without a migration of application logic.
    demo_user_email: str = "demo@echo.app"
    demo_user_name: str = "Demo"
    demo_mode_enabled: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key and self.gemini_api_key.strip())

    def resolved_ai_provider(self) -> Literal["gemini", "mock"]:
        """Fall back to the mock provider rather than crashing without a key."""
        if self.ai_provider == "gemini" and not self.gemini_configured:
            return "mock"
        return self.ai_provider


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
