"""FastAPI application factory.

Wires the three cross-cutting concerns the spec is strict about: a lifespan that
creates the schema and starts the in-process worker (§31), CORS for the
dashboard, and exception handlers that turn every failure into the single error
envelope of §41 - a stable code and a safe message, never a stack trace.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.config import settings
from app.db.init_db import init_db
from app.db.session import dispose_engine
from app.schemas.common import ErrorBody, ErrorResponse
from app.utils.errors import EchoError
from app.utils.logging import configure_logging, get_logger
from app.workers import start_scanner, start_worker, stop_scanner, stop_worker

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    await init_db()
    await start_worker()
    await start_scanner()
    logger.info("app.started", env=settings.app_env, ai=settings.resolved_ai_provider())
    try:
        yield
    finally:
        await stop_scanner()
        await stop_worker()
        await dispose_engine()
        logger.info("app.stopped")


def _error_response(status_code: int, body: ErrorBody) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(error=body).model_dump(),
    )


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(EchoError)
    async def _handle_echo_error(_: Request, exc: EchoError) -> JSONResponse:
        # detail is internal - it is logged, never returned (§41).
        logger.info("request.echo_error", code=exc.code, detail=exc.detail)
        return _error_response(
            exc.http_status,
            ErrorBody(code=exc.code, message=exc.message, hint=exc.hint),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _error_response(
            422,
            ErrorBody(
                code="INVALID_INPUT",
                message="Echo couldn't read that request.",
                hint="Check the fields and try again.",
            ),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        # Last line of defence: log the real error, tell the user nothing leaky.
        logger.exception("request.unhandled_error", error=type(exc).__name__)
        return _error_response(
            500,
            ErrorBody(
                code="INTERNAL_ERROR",
                message="Something went wrong on Echo's side.",
                hint="Please try again in a moment.",
            ),
        )

    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
