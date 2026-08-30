"""Canonical Echo enums.

Single source of truth shared by ORM models, API schemas, and the AI contract.
Values are the exact strings that cross the wire to Android and the dashboard,
so they must stay stable.
"""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """str-valued enum that serialises as its value."""

    def __str__(self) -> str:  # pragma: no cover - trivial
        return str(self.value)


class Category(StrEnum):
    """The five Echo categories. Every memory has exactly one."""

    PLACE = "PLACE"
    EVENT = "EVENT"
    RECIPE = "RECIPE"
    TOOL = "TOOL"
    TOPIC = "TOPIC"


class IntentAction(StrEnum):
    """What the user probably wants to *do* because they saved this."""

    VISIT = "VISIT"
    GO = "GO"
    EXPLORE = "EXPLORE"
    ATTEND = "ATTEND"
    COOK = "COOK"
    TRY = "TRY"
    USE = "USE"
    LEARN = "LEARN"
    READ = "READ"
    RESEARCH = "RESEARCH"
    OTHER = "OTHER"


class MemoryStatus(StrEnum):
    ACTIVE = "ACTIVE"
    RESURFACED = "RESURFACED"
    COMPLETED = "COMPLETED"
    DISMISSED = "DISMISSED"
    ARCHIVED = "ARCHIVED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class TriggerType(StrEnum):
    """Implemented trigger types.

    ``CALENDAR``/``WEATHER``/``ROUTINE``/``SEARCH``/``CONTEXT`` are deliberately
    absent: the evaluator registry in ``services.trigger`` is open for extension,
    so adding one means adding an evaluator, not editing this enum's consumers.
    """

    DATE = "DATE"
    TIME = "TIME"
    LOCATION = "LOCATION"
    MANUAL = "MANUAL"


class TriggerStatus(StrEnum):
    PENDING = "PENDING"
    FIRED = "FIRED"
    CANCELLED = "CANCELLED"


class ActionType(StrEnum):
    OPEN_MAPS = "OPEN_MAPS"
    ADD_TO_CALENDAR = "ADD_TO_CALENDAR"
    OPEN_EVENT = "OPEN_EVENT"
    VIEW_RECIPE = "VIEW_RECIPE"
    OPEN_TOOL = "OPEN_TOOL"
    OPEN_SOURCE = "OPEN_SOURCE"
    OPEN_URL = "OPEN_URL"
    SET_REMINDER = "SET_REMINDER"


class SourceType(StrEnum):
    YOUTUBE_SHORT = "youtube_short"
    YOUTUBE_VIDEO = "youtube_video"
    INSTAGRAM_REEL = "instagram_reel"
    INSTAGRAM_POST = "instagram_post"
    WEB_URL = "web_url"
    SCREENSHOT = "screenshot"
    TEXT = "text"


class Platform(StrEnum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    WEB = "web"
    DEVICE = "device"


class MediaType(StrEnum):
    VIDEO = "video"
    IMAGE = "image"
    TEXT = "text"
    NONE = "none"


class InputType(StrEnum):
    """What the client says it is handing us at /api/capture."""

    URL = "url"
    TEXT = "text"
    IMAGE = "image"


class JobStatus(StrEnum):
    QUEUED = "QUEUED"
    FETCHING = "FETCHING"
    ANALYZING = "ANALYZING"
    EXTRACTING_INTENT = "EXTRACTING_INTENT"
    VALIDATING = "VALIDATING"
    SAVING = "SAVING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


TERMINAL_JOB_STATUSES = frozenset({JobStatus.COMPLETED, JobStatus.FAILED})


class NotificationStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    SENT = "SENT"
    ACTED = "ACTED"
    DISMISSED = "DISMISSED"


class EntityType(StrEnum):
    PLACE = "PLACE"
    EVENT = "EVENT"
    RECIPE = "RECIPE"
    TOOL = "TOOL"
    TOPIC = "TOPIC"


class ConfidenceBand(StrEnum):
    """Decides whether Echo saves silently, saves-and-asks, or asks first."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
