"""Source routing (§5-6).

Given what the client says it shared, decide which processor turns it into a
:class:`NormalizedMedia`. The routing is forgiving: a "url" capture that is
really pasted text, or share text with a link buried in it, still lands on the
right processor. The AI layer only ever sees a NormalizedMedia, never a raw URL.
"""

from __future__ import annotations

from pathlib import Path

from app.models.enums import InputType
from app.services.media.normalized import NormalizedMedia
from app.services.source.processors import (
    process_screenshot,
    process_text,
    process_url,
)
from app.utils.errors import InvalidUrlError
from app.utils.urls import extract_first_url, looks_like_url

__all__ = ["normalize", "resolve_url"]


def resolve_url(content: str) -> str | None:
    """The URL a capture refers to, if any - direct or buried in share text."""
    if looks_like_url(content):
        return content.strip()
    return extract_first_url(content)


async def normalize(
    *,
    input_type: InputType,
    content: str,
    note: str | None = None,
    image_path: Path | None = None,
) -> NormalizedMedia:
    if input_type == InputType.IMAGE:
        if image_path is None:
            raise InvalidUrlError(detail="image capture with no file")
        return process_screenshot(image_path, note=note)

    url = resolve_url(content)
    if url is not None:
        return await process_url(url, note=note)

    if input_type == InputType.URL:
        # Claimed a URL but we could not find one.
        raise InvalidUrlError(detail="no URL found in url-typed capture")

    return process_text(content, note=note)
