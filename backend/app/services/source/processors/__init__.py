"""Source processors.

Each processor turns one kind of input into a :class:`NormalizedMedia`. URL
processors delegate fetching to the acquisition service and only decide *policy*
- chiefly whether downloading the video is worth it for this source type. Text
and screenshot inputs need no acquisition at all.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

from app.models.enums import MediaType, Platform, SourceType
from app.services.media.acquisition import get_media_acquisition_service
from app.services.media.normalized import NormalizedMedia
from app.utils.urls import canonicalise, detect_source

# Short-form video is worth downloading for vision; long-form leans on the
# transcript and metadata instead, to keep jobs fast and prompts cheap.
_WANT_VIDEO = {SourceType.YOUTUBE_SHORT, SourceType.INSTAGRAM_REEL}


async def process_url(url: str, *, note: str | None) -> NormalizedMedia:
    platform, source_type = detect_source(url)
    service = get_media_acquisition_service()
    return await service.acquire(
        url,
        source_type=source_type,
        platform=platform,
        user_note=note,
        want_video=source_type in _WANT_VIDEO,
    )


def process_text(text: str, *, note: str | None) -> NormalizedMedia:
    return NormalizedMedia(
        source_type=SourceType.TEXT,
        platform=Platform.DEVICE,
        media_type=MediaType.TEXT,
        extracted_text=text,
        user_note=note,
    )


def process_screenshot(path: Path, *, note: str | None) -> NormalizedMedia:
    mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    return NormalizedMedia(
        source_type=SourceType.SCREENSHOT,
        platform=Platform.DEVICE,
        media_type=MediaType.IMAGE,
        local_path=path,
        mime_type=mime_type,
        user_note=note,
    )


__all__ = [
    "canonicalise",
    "process_screenshot",
    "process_text",
    "process_url",
]
