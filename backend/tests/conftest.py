"""Shared test fixtures.

Environment is pinned *before* any ``app`` import so ``Settings`` (built once at
import time) picks up the test database and the deterministic mock AI provider.
Each test gets a freshly-created schema for full isolation; the app lifespan is
deliberately not run (no background worker), so processing is driven explicitly
through ``POST /api/process`` for determinism.
"""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

_TEST_DB = Path(tempfile.gettempdir()) / f"echo_test_{uuid.uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB.as_posix()}"
os.environ["AI_PROVIDER"] = "mock"
os.environ["GEMINI_API_KEY"] = ""
os.environ["DEBUG"] = "false"
os.environ["DATABASE_ECHO"] = "false"
os.environ["APP_ENV"] = "test"
os.environ["DEMO_MODE_ENABLED"] = "true"

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db.init_db import ensure_demo_user  # noqa: E402
from app.db.session import SessionFactory, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.services.ai import reset_ai_provider  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def _fresh_state():
    """Drop and recreate the schema before every test, then seed the demo user."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await ensure_demo_user()
    reset_ai_provider()
    yield


@pytest_asyncio.fixture
async def session():
    """A raw session for repository/service-level tests."""
    async with SessionFactory() as db_session:
        yield db_session


@pytest_asyncio.fixture
async def client():
    """An ASGI client. Lifespan is not run, so no worker starts."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


def pytest_sessionfinish(session, exitstatus):  # noqa: ANN001, ARG001
    """Best-effort cleanup of the temp SQLite files."""
    for suffix in ("", "-wal", "-shm"):
        try:
            Path(str(_TEST_DB) + suffix).unlink()
        except OSError:
            pass
