"""Shared API schema pieces."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ApiModel(BaseModel):
    """Base for every wire model: tolerant on input, ORM-friendly on output."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class Page(ApiModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        return self.offset + len(self.items) < self.total


class ErrorBody(BaseModel):
    """The single error shape every failure returns (§41).

    ``code`` is stable and machine-readable; ``message`` is safe to show a user;
    ``hint`` optionally tells them what to do next. Stack traces never appear.
    """

    code: str
    message: str
    hint: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class Ack(BaseModel):
    ok: bool = True
    message: str | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str
    env: str
    ai_provider: str = Field(description="'gemini' when a key is configured, else 'mock'.")
    database: str = Field(description="Dialect only - never the connection string.")
    demo_mode: bool
