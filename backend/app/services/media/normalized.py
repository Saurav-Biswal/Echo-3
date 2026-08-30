"""The normalised media representation.

This is the boundary between "how we got the content" and "what the AI sees".
Every processor produces one of these, and the intent engine accepts nothing
else - so replacing yt-dlp, adding a platform, or losing access to a source
never reaches the AI layer (§6).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.models.enums import MediaType, Platform, SourceType


@dataclass(slots=True)
class NormalizedMedia:
    source_type: SourceType
    platform: Platform
    media_type: MediaType = MediaType.NONE

    source_url: str | None = None
    canonical_url: str | None = None

    # Remote URI (e.g. a Gemini Files API handle) or a temp path string. Never a
    # promise of permanence - see ``local_path``.
    media_uri: str | None = None
    # Set only while the file exists on disk for this job; deleted afterwards (§43).
    local_path: Path | None = None
    mime_type: str | None = None

    title: str | None = None
    description: str | None = None
    transcript: str | None = None
    # OCR output, on-screen captions, or the literal text the user pasted.
    extracted_text: str | None = None
    thumbnail_url: str | None = None
    author: str | None = None
    duration_seconds: int | None = None

    # A note the user typed alongside the save - the strongest intent signal
    # available, so it is carried separately rather than merged into description.
    user_note: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)
    # Human-readable trail of what acquisition managed to get, surfaced in logs
    # and in the job timeline: "metadata", "video_download", "transcript".
    acquired: list[str] = field(default_factory=list)
    # Why a richer path was not used, if it was not.
    degraded_reason: str | None = None

    @property
    def has_video(self) -> bool:
        return self.media_type == MediaType.VIDEO and (
            self.local_path is not None or self.media_uri is not None
        )

    @property
    def has_image(self) -> bool:
        return self.media_type == MediaType.IMAGE and self.local_path is not None

    @property
    def text_context(self) -> str:
        """Everything textual we know, as one block for the prompt.

        Ordered most-signal-first: a user's own note beats a platform title.
        """
        sections: list[tuple[str, str | None]] = [
            ("User's note", self.user_note),
            ("Source URL", self.source_url),
            ("Title", self.title),
            ("Author", self.author),
            ("Description", self.description),
            ("Transcript", self.transcript),
            ("Text visible in the content", self.extracted_text),
        ]
        return "\n\n".join(
            f"{label}: {value.strip()}"
            for label, value in sections
            if value and value.strip()
        )

    @property
    def has_any_signal(self) -> bool:
        """False means there is nothing to analyse and we must fail honestly."""
        return bool(self.has_video or self.has_image or self.text_context.strip())

    def note_acquired(self, what: str) -> None:
        if what not in self.acquired:
            self.acquired.append(what)

    def to_log_dict(self) -> dict[str, Any]:
        """Shape, not content - safe to log (§49)."""
        return {
            "source_type": self.source_type.value,
            "platform": self.platform.value,
            "media_type": self.media_type.value,
            "has_video": self.has_video,
            "has_image": self.has_image,
            "title_len": len(self.title or ""),
            "description_len": len(self.description or ""),
            "transcript_len": len(self.transcript or ""),
            "extracted_text_len": len(self.extracted_text or ""),
            "duration_seconds": self.duration_seconds,
            "acquired": list(self.acquired),
            "degraded_reason": self.degraded_reason,
        }
