"""Domain errors.

Every failure the user can cause or observe has a stable ``code``, a message
that is safe to show them, and an optional ``hint`` telling them what to do
next. The API layer turns these into the single error envelope in §41; raw
exceptions never reach a client.
"""

from __future__ import annotations


class EchoError(Exception):
    """Base class for all expected failures."""

    code = "ECHO_ERROR"
    http_status = 500
    message = "Something went wrong on Echo's side."
    hint: str | None = None
    # False for infrastructure blips worth retrying, True for user-input problems.
    permanent = True

    def __init__(
        self,
        message: str | None = None,
        *,
        hint: str | None = None,
        detail: str | None = None,
    ) -> None:
        self.message = message or self.message
        self.hint = hint or self.hint
        # Internal-only context: logged, never serialised to a client.
        self.detail = detail
        super().__init__(self.message)

    def as_dict(self) -> dict[str, str | None]:
        return {"code": self.code, "message": self.message, "hint": self.hint}


# ------------------------------------------------------------------ input


class InvalidInputError(EchoError):
    code = "INVALID_INPUT"
    http_status = 400
    message = "Echo couldn't read what you shared."
    hint = "Try sharing the link again, or paste it directly."


class InvalidUrlError(InvalidInputError):
    code = "INVALID_URL"
    message = "That doesn't look like a link Echo can open."
    hint = "Share the post or video link, not a screenshot of it."


class UnsupportedSourceError(InvalidInputError):
    code = "UNSUPPORTED_SOURCE"
    message = "Echo doesn't understand this kind of link yet."
    hint = "YouTube, Instagram, web links, screenshots and plain text all work."


class DuplicateMemoryError(EchoError):
    code = "DUPLICATE_MEMORY"
    http_status = 409
    message = "You already saved this."
    hint = "Open the memory you already have."

    def __init__(self, memory_id: str, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.memory_id = memory_id


# ------------------------------------------------------------ acquisition


class MediaAcquisitionError(EchoError):
    code = "MEDIA_UNAVAILABLE"
    http_status = 502
    message = "Echo couldn't open that post."
    hint = "It may be private or removed. Try a different link."
    permanent = False


class SourceInaccessibleError(MediaAcquisitionError):
    code = "SOURCE_INACCESSIBLE"
    message = "That post is private or no longer available."
    hint = "Echo can only read publicly visible posts."
    permanent = True


class MediaTooLargeError(MediaAcquisitionError):
    code = "MEDIA_TOO_LARGE"
    http_status = 413
    message = "That video is too long for Echo to analyse."
    hint = "Short-form videos work best."
    permanent = True


# --------------------------------------------------------------------- ai


class AiError(EchoError):
    code = "AI_FAILED"
    http_status = 502
    message = "Echo couldn't analyse this right now."
    hint = "Try again in a moment."
    permanent = False


class AiRateLimitedError(AiError):
    code = "AI_RATE_LIMITED"
    http_status = 429
    message = "Echo is thinking about too many things at once."
    hint = "Try again in a minute."
    permanent = False


class AiTimeoutError(AiError):
    code = "AI_TIMEOUT"
    http_status = 504
    message = "Analysing this took too long."
    permanent = False


class MalformedAiOutputError(AiError):
    code = "AI_MALFORMED_OUTPUT"
    message = "Echo got a confusing answer while analysing this."
    permanent = False


class LowConfidenceError(EchoError):
    """Not a failure exactly - it routes the memory to NEEDS_REVIEW (§42)."""

    code = "LOW_CONFIDENCE"
    http_status = 200
    message = "Echo couldn't confidently understand why you saved this."
    hint = "Tell Echo what you had in mind."


# ------------------------------------------------------------------ store


class NotFoundError(EchoError):
    code = "NOT_FOUND"
    http_status = 404
    message = "Echo couldn't find that."


class MemoryNotFoundError(NotFoundError):
    code = "MEMORY_NOT_FOUND"
    message = "That memory no longer exists."


class JobNotFoundError(NotFoundError):
    code = "JOB_NOT_FOUND"
    message = "Echo lost track of that save."


class TriggerNotFoundError(NotFoundError):
    code = "TRIGGER_NOT_FOUND"
    message = "That reminder no longer exists."


class NotificationNotFoundError(NotFoundError):
    code = "NOTIFICATION_NOT_FOUND"
    message = "That notification no longer exists."


class DemoModeDisabledError(EchoError):
    code = "DEMO_DISABLED"
    http_status = 403
    message = "Demo controls are turned off."


def hint_for_code(code: str | None) -> str | None:
    """The canonical, user-safe hint registered for a stable error code.

    Lets a stored ``error_code`` (all we persist on a failed job) be turned back
    into its "what to do next" hint at serialisation time, so the job payload can
    carry a hint without a dedicated column. Returns None for unknown codes.
    """
    if not code:
        return None
    return _HINT_BY_CODE.get(code)


def _collect_hints() -> dict[str, str]:
    registry: dict[str, str] = {}

    def walk(cls: type[EchoError]) -> None:
        hint = getattr(cls, "hint", None)
        if hint:
            registry.setdefault(cls.code, hint)
        for sub in cls.__subclasses__():
            walk(sub)

    walk(EchoError)
    return registry


_HINT_BY_CODE: dict[str, str] = _collect_hints()
