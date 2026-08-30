"""Memory read/write schemas.

``MemoryRead`` is shaped so a card can be rendered without a second request:
every card must answer What / Why / When / Action (§26), so title+summary,
why_saved, the resurfacing line, and resolved actions all travel together.
"""

from __future__ import annotations

import uuid
from datetime import date as date_type
from datetime import datetime
from typing import Any

from pydantic import Field

from app.models.enums import (
    ActionType,
    Category,
    ConfidenceBand,
    EntityType,
    IntentAction,
    MediaType,
    MemoryStatus,
    Platform,
    SourceType,
)
from app.schemas.common import ApiModel
from app.schemas.trigger import TriggerRead


class EntityRead(ApiModel):
    id: uuid.UUID
    entity_type: EntityType
    name: str
    description: str | None = None

    location: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    event_date: date_type | None = None
    event_time: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    venue: str | None = None

    url: str | None = None
    price: str | None = None
    duration_minutes: int | None = None
    details: dict[str, Any] = Field(default_factory=dict)

    confidence: float = 0.0
    is_primary: bool = False


class ActionRead(ApiModel):
    id: uuid.UUID
    action_type: ActionType
    label: str
    deep_link: str | None = None
    web_link: str | None = None
    action_metadata: dict[str, Any] = Field(default_factory=dict)
    is_primary: bool = False
    sort_order: int = 0


class SourceRead(ApiModel):
    id: uuid.UUID
    source_type: SourceType
    platform: Platform
    media_type: MediaType
    source_url: str | None = None
    title: str | None = None
    description: str | None = None
    thumbnail_url: str | None = None
    author: str | None = None
    duration_seconds: int | None = None


class MemoryRead(ApiModel):
    id: uuid.UUID

    # --- what ---
    category: Category
    title: str
    summary: str | None = None

    # --- why (the product) ---
    why_saved: str
    intent_action: IntentAction
    intent_confidence: float
    confidence_band: ConfidenceBand

    # --- lifecycle ---
    status: MemoryStatus
    needs_review_reason: str | None = None
    resurface_count: int = 0
    resurfaced_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    user_confirmed: bool = False
    user_corrected: bool = False
    ai_model: str | None = None

    source: SourceRead | None = None
    entities: list[EntityRead] = Field(default_factory=list)
    triggers: list[TriggerRead] = Field(default_factory=list)
    actions: list[ActionRead] = Field(default_factory=list)


class MemoryUpdate(ApiModel):
    """PATCH /api/memories/{id} - only lifecycle and light text edits."""

    status: MemoryStatus | None = None
    title: str | None = Field(default=None, min_length=1, max_length=300)
    why_saved: str | None = Field(default=None, min_length=1, max_length=1_000)


class MemoryCorrection(ApiModel):
    """POST /api/memories/{id}/correct - the "Not quite" path (§14).

    Correcting the category re-derives the trigger and actions, because the
    whole point of the correction is to fix what Echo will *do*.
    """

    category: Category | None = None
    intent_action: IntentAction | None = None
    # "Visit" | "Attend" | "Cook" | "Try" | "Learn" | "Other" as typed by the user.
    note: str | None = Field(default=None, max_length=500)
    confirmed: bool = False


class CategoryCount(ApiModel):
    category: Category
    count: int


class OverviewResponse(ApiModel):
    """Dashboard header numbers, in one request."""

    active: int
    resurfaced: int
    completed: int
    needs_review: int
    by_category: list[CategoryCount]
    upcoming_trigger_at: datetime | None = None
    recent: list[MemoryRead] = Field(default_factory=list)
