"""Structured logging.

The pipeline logs one event per stage (§49) with stable event names so a run can
be followed end to end. Content is logged by *shape* - lengths, categories,
counts - not by value, so summaries and transcripts stay out of the log (§49).
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from app.config import settings

_configured = False


def configure_logging() -> None:
    global _configured
    if _configured:
        return

    level = logging.DEBUG if settings.debug else logging.INFO

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
        force=True,
    )
    # These two are chatty and say nothing we don't already log ourselves.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    # Human-readable locally, JSON in production where something parses it.
    processors.append(
        structlog.dev.ConsoleRenderer(colors=False)
        if settings.app_env == "dev"
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    _configured = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    configure_logging()
    return structlog.get_logger(name)


def safe_len(value: str | None) -> int:
    """Log how much text we had without logging the text."""
    return len(value) if value else 0
