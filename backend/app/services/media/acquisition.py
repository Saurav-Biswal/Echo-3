"""Media acquisition - the only place that knows *how* content is fetched.

§6: one abstraction accepts a supported URL, identifies the platform, obtains a
usable representation, and returns :class:`NormalizedMedia`. Provider details
(yt-dlp option dicts, og-tag scraping, subtitle formats) stop here; nothing
above this module learns them, so a provider can be replaced without touching
the AI layer.

Failure is expected, not exceptional. A private post, a 40-minute video or a
site that blocks bots all still leave *something* - a title, a description,
captions - and §42 says to keep degrading rather than give up: the trail is
recorded in ``acquired`` / ``degraded_reason`` and only a total absence of
signal raises.
"""

from __future__ import annotations

import asyncio
import html as html_module
import json
import mimetypes
import re
import uuid
from pathlib import Path
from typing import Any

import httpx

from app.config import settings
from app.models.enums import MediaType, Platform, SourceType
from app.services.media.normalized import NormalizedMedia
from app.utils.errors import (
    MediaAcquisitionError,
    MediaTooLargeError,
    SourceInaccessibleError,
)
from app.utils.logging import get_logger
from app.utils.urls import canonicalise, youtube_thumbnail, youtube_video_id

logger = get_logger(__name__)

# Substrings in a provider error that mean "this will never work", so retrying
# would only waste a job slot (see ``EchoError.permanent``).
_INACCESSIBLE_MARKERS = (
    "private",
    "login required",
    "sign in",
    "requires authentication",
    "not available",
    "unavailable",
    "no longer available",
    "has been removed",
    "was deleted",
    "does not exist",
    "age-restricted",
    "members-only",
    "blocked",
    "cookies",
    "captcha",
)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

_META_TAG = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
_META_ATTR = re.compile(
    r"""(property|name|content)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""",
    re.IGNORECASE,
)
_TITLE_TAG = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_SCRIPTISH = re.compile(
    r"<(script|style|noscript|template|svg)\b.*?</\1>", re.IGNORECASE | re.DOTALL
)
_ANY_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")

_PREFERRED_SUBTITLE_LANGS = ("en", "en-US", "en-GB", "en-orig", "en-auto")
_SUBTITLE_FORMATS = ("json3", "vtt", "srt")

# Caps: enough signal for intent extraction, small enough to keep prompts cheap.
_TRANSCRIPT_CHAR_LIMIT = 12_000
_PAGE_TEXT_CHAR_LIMIT = 6_000
_HTML_READ_LIMIT = 1_500_000
_DESCRIPTION_CHAR_LIMIT = 4_000

# yt-dlp keys worth keeping for the record, none of which are content.
_METADATA_KEYS = (
    "extractor",
    "view_count",
    "like_count",
    "comment_count",
    "upload_date",
    "channel_id",
    "uploader_id",
    "width",
    "height",
    "fps",
    "live_status",
)


class MediaAcquisitionService:
    """Fetches whatever a URL can give us, as a :class:`NormalizedMedia`."""

    def __init__(self, *, temp_dir: Path | None = None) -> None:
        self._temp_dir = temp_dir or settings.media_temp_dir

    async def acquire(
        self,
        url: str,
        *,
        source_type: SourceType,
        platform: Platform,
        user_note: str | None = None,
        want_video: bool = True,
    ) -> NormalizedMedia:
        """Acquire content for ``url``.

        ``want_video`` is a request, not a guarantee - the caller (a source
        processor) decides whether video is worth trying for this source type,
        and acquisition decides whether it is possible.
        """
        if platform in {Platform.YOUTUBE, Platform.INSTAGRAM}:
            media = await self._acquire_platform(
                url,
                source_type=source_type,
                platform=platform,
                user_note=user_note,
                want_video=want_video,
            )
        else:
            media = await self._acquire_web(
                url,
                source_type=source_type,
                platform=platform,
                user_note=user_note,
            )
        logger.info("media.acquired", **media.to_log_dict())
        return media

    def release(self, media: NormalizedMedia) -> None:
        """Delete the temp file backing ``media`` (§43: raw media is not kept)."""
        path = media.local_path
        if path is None or settings.media_retain_downloads:
            return
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:  # pragma: no cover - platform-specific
            logger.warning("media.cleanup_failed", error=type(exc).__name__)
        media.local_path = None

    # ------------------------------------------------- youtube / instagram

    async def _acquire_platform(
        self,
        url: str,
        *,
        source_type: SourceType,
        platform: Platform,
        user_note: str | None,
        want_video: bool,
    ) -> NormalizedMedia:
        media = NormalizedMedia(
            source_type=source_type,
            platform=platform,
            source_url=url,
            canonical_url=canonicalise(url),
            user_note=user_note,
        )

        info = await self._extract_info(url)
        self._apply_info(media, info)

        duration = media.duration_seconds or 0
        too_long = duration > settings.media_max_duration_seconds

        transcript = await self._fetch_transcript(info)
        if transcript:
            media.transcript = transcript
            media.note_acquired("transcript")

        if want_video and not too_long:
            path = await self._download_video(url)
            if path is not None:
                media.local_path = path
                media.media_type = MediaType.VIDEO
                media.mime_type = (
                    mimetypes.guess_type(path.name)[0] or "video/mp4"
                )
                media.note_acquired("video_download")
            else:
                media.degraded_reason = "video_download_unavailable"
        elif too_long:
            media.degraded_reason = (
                f"video_longer_than_{settings.media_max_duration_seconds}s"
            )
        elif not want_video:
            media.degraded_reason = "video_not_requested"

        return self._finalise(media, too_long=too_long)

    def _finalise(self, media: NormalizedMedia, *, too_long: bool) -> NormalizedMedia:
        """Classify what we ended up with, and refuse to pretend when it is nothing."""
        if media.media_type == MediaType.NONE and media.text_context.strip():
            media.media_type = MediaType.TEXT

        if media.has_any_signal:
            return media
        if too_long:
            raise MediaTooLargeError(
                detail="duration over limit and no text signal to fall back on"
            )
        raise MediaAcquisitionError(
            "Echo couldn't get anything readable from that link.",
            hint="Try pasting the text or a different link.",
            detail="no signal after acquisition",
        )

    def _apply_info(self, media: NormalizedMedia, info: dict[str, Any]) -> None:
        media.title = _clean(info.get("title"))
        media.description = _clean(info.get("description"), _DESCRIPTION_CHAR_LIMIT)
        media.author = _clean(
            info.get("uploader") or info.get("channel") or info.get("creator")
        )
        duration = info.get("duration")
        if isinstance(duration, (int, float)) and duration > 0:
            media.duration_seconds = int(duration)

        media.thumbnail_url = info.get("thumbnail") or None
        webpage_url = info.get("webpage_url")
        if isinstance(webpage_url, str) and webpage_url:
            media.canonical_url = canonicalise(webpage_url)
        if media.thumbnail_url is None and media.canonical_url:
            video_id = youtube_video_id(media.canonical_url)
            if video_id:
                media.thumbnail_url = youtube_thumbnail(video_id)

        extras = {key: info[key] for key in _METADATA_KEYS if info.get(key) is not None}
        tags = info.get("tags")
        if isinstance(tags, list) and tags:
            extras["tags"] = [str(tag) for tag in tags[:12]]
        media.metadata.update(extras)
        media.note_acquired("metadata")

    # ------------------------------------------------------------- yt-dlp

    def _ydl_options(self, *, target: Path | None = None) -> dict[str, Any]:
        options: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "socket_timeout": 20,
            "retries": 2,
            "cachedir": False,
            "nocheckcertificate": False,
            "extract_flat": False,
        }
        if target is None:
            options["skip_download"] = True
            return options
        # A single pre-merged stream: merging video+audio would need ffmpeg,
        # which we do not require to be installed.
        options.update(
            {
                "format": "b[height<=720][ext=mp4]/b[ext=mp4]/b",
                "outtmpl": f"{target}.%(ext)s",
                "max_filesize": settings.media_max_download_bytes,
                "overwrites": True,
                "noprogress": True,
            }
        )
        return options

    async def _extract_info(self, url: str) -> dict[str, Any]:
        def _run() -> dict[str, Any]:
            from yt_dlp import YoutubeDL

            with YoutubeDL(self._ydl_options()) as ydl:
                info = ydl.extract_info(url, download=False)
                return dict(info) if info else {}

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_run),
                timeout=settings.media_acquisition_timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise MediaAcquisitionError(
                "Echo couldn't open that post in time.",
                detail="metadata extraction timed out",
            ) from exc
        except Exception as exc:
            raise _classify_provider_error(exc) from exc

    async def _download_video(self, url: str) -> Path | None:
        """Best-effort download. Returns ``None`` instead of raising: a missing
        video is a degradation (§42), and the text signal may still be enough."""
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        stem = self._temp_dir / f"echo-{uuid.uuid4().hex}"

        def _run() -> Path | None:
            from yt_dlp import YoutubeDL

            with YoutubeDL(self._ydl_options(target=stem)) as ydl:
                ydl.download([url])
            matches = sorted(self._temp_dir.glob(f"{stem.name}.*"))
            return matches[0] if matches else None

        try:
            path = await asyncio.wait_for(
                asyncio.to_thread(_run),
                timeout=settings.media_acquisition_timeout_seconds,
            )
        except Exception as exc:
            logger.warning("media.download_failed", error=type(exc).__name__)
            return None

        if path is None or not path.exists():
            return None
        size = path.stat().st_size
        if size == 0 or size > settings.media_max_download_bytes:
            path.unlink(missing_ok=True)
            logger.warning("media.download_rejected", size_bytes=size)
            return None
        return path

    # -------------------------------------------------------- transcripts

    async def _fetch_transcript(self, info: dict[str, Any]) -> str | None:
        track = _pick_subtitle_track(info)
        if track is None:
            return None
        url, extension = track
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=20.0,
                headers={"User-Agent": _USER_AGENT},
            ) as client:
                response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("media.transcript_failed", error=type(exc).__name__)
            return None
        return _parse_subtitles(response.text, extension)

    # ---------------------------------------------------------------- web

    async def _acquire_web(
        self,
        url: str,
        *,
        source_type: SourceType,
        platform: Platform,
        user_note: str | None,
    ) -> NormalizedMedia:
        media = NormalizedMedia(
            source_type=source_type,
            platform=platform,
            source_url=url,
            canonical_url=canonicalise(url),
            user_note=user_note,
        )
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=settings.media_acquisition_timeout_seconds,
                headers={"User-Agent": _USER_AGENT, "Accept-Language": "en"},
            ) as client:
                response = await client.get(url)
        except httpx.HTTPError as exc:
            raise MediaAcquisitionError(
                detail=f"web fetch failed: {type(exc).__name__}"
            ) from exc

        status = response.status_code
        if status in {401, 403, 404, 410, 451}:
            raise SourceInaccessibleError(detail=f"http_{status}")
        if status >= 400:
            raise MediaAcquisitionError(detail=f"http_{status}")

        content_type = (
            response.headers.get("content-type", "").split(";")[0].strip().lower()
        )
        if content_type.startswith("image/"):
            self._store_web_image(media, response, content_type)
            return self._finalise(media, too_long=False)
        if content_type and "html" not in content_type and "text" not in content_type:
            raise MediaAcquisitionError(
                "Echo can only read pages, images and posts.",
                detail=f"unsupported content-type {content_type}",
            )

        self._apply_html(media, response.text[:_HTML_READ_LIMIT], str(response.url))
        return self._finalise(media, too_long=False)

    def _store_web_image(
        self,
        media: NormalizedMedia,
        response: httpx.Response,
        content_type: str,
    ) -> None:
        """A link that *is* an image - treat it like a shared screenshot."""
        payload = response.content
        if len(payload) > settings.media_max_download_bytes:
            raise MediaTooLargeError(
                "That image is too large for Echo to analyse.",
                detail=f"{len(payload)} bytes",
            )
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        suffix = mimetypes.guess_extension(content_type) or ".jpg"
        path = self._temp_dir / f"echo-{uuid.uuid4().hex}{suffix}"
        path.write_bytes(payload)
        media.local_path = path
        media.media_type = MediaType.IMAGE
        media.mime_type = content_type
        media.thumbnail_url = str(response.url)
        media.note_acquired("image_download")

    def _apply_html(self, media: NormalizedMedia, body: str, final_url: str) -> None:
        meta = _parse_meta_tags(body)
        media.title = _clean(
            meta.get("og:title") or meta.get("twitter:title") or _title_tag(body)
        )
        media.description = _clean(
            meta.get("og:description")
            or meta.get("twitter:description")
            or meta.get("description"),
            _DESCRIPTION_CHAR_LIMIT,
        )
        media.author = _clean(meta.get("article:author") or meta.get("author"))
        media.thumbnail_url = meta.get("og:image") or meta.get("twitter:image") or None
        media.canonical_url = canonicalise(meta.get("og:url") or final_url)
        if meta.get("og:site_name"):
            media.metadata["site_name"] = meta["og:site_name"]
        if meta.get("article:published_time"):
            media.metadata["published_time"] = meta["article:published_time"]
        media.note_acquired("metadata")

        page_text = _visible_text(body)
        if page_text:
            media.extracted_text = page_text
            media.note_acquired("page_text")
        else:
            media.degraded_reason = "page_text_empty"


# --------------------------------------------------------------- helpers


def _clean(value: object, limit: int | None = None) -> str | None:
    if not isinstance(value, str):
        return None
    text = _WHITESPACE.sub(" ", html_module.unescape(value)).strip()
    if not text:
        return None
    return text[:limit] if limit else text


def _classify_provider_error(exc: Exception) -> MediaAcquisitionError:
    """Permanent (private/removed) vs transient (blip) - it decides retries."""
    message = str(exc).lower()
    if any(marker in message for marker in _INACCESSIBLE_MARKERS):
        return SourceInaccessibleError(detail=f"{type(exc).__name__}: {exc}"[:300])
    return MediaAcquisitionError(detail=f"{type(exc).__name__}: {exc}"[:300])


def _pick_subtitle_track(info: dict[str, Any]) -> tuple[str, str] | None:
    """Prefer real subtitles over auto-captions, English over anything else."""
    for key in ("subtitles", "automatic_captions"):
        tracks = info.get(key)
        if not isinstance(tracks, dict) or not tracks:
            continue
        ordered = [lang for lang in _PREFERRED_SUBTITLE_LANGS if lang in tracks]
        ordered += [
            lang
            for lang in tracks
            if lang.lower().startswith("en") and lang not in ordered
        ]
        for lang in ordered:
            candidates = tracks.get(lang)
            if not isinstance(candidates, list):
                continue
            for extension in _SUBTITLE_FORMATS:
                for candidate in candidates:
                    if not isinstance(candidate, dict):
                        continue
                    url = candidate.get("url")
                    if url and (candidate.get("ext") or "").lower() == extension:
                        return str(url), extension
    return None


def _parse_subtitles(payload: str, extension: str) -> str | None:
    """Turn a caption file into flat prose - timings are noise to the model."""
    if extension == "json3":
        text = _parse_json3(payload)
    else:
        text = _parse_cue_format(payload)
    if not text:
        return None
    return text[:_TRANSCRIPT_CHAR_LIMIT]


def _parse_json3(payload: str) -> str:
    try:
        document = json.loads(payload)
    except (ValueError, TypeError):
        return ""
    pieces: list[str] = []
    for event in document.get("events") or []:
        for segment in event.get("segs") or []:
            fragment = segment.get("utf8")
            if fragment and fragment != "\n":
                pieces.append(fragment)
    return _WHITESPACE.sub(" ", "".join(pieces)).strip()


def _parse_cue_format(payload: str) -> str:
    """VTT/SRT: drop headers, cue numbers and timing lines, dedupe rolling text."""
    lines: list[str] = []
    for raw in payload.splitlines():
        line = raw.strip()
        if not line or "-->" in line or line.isdigit():
            continue
        if line.upper().startswith(("WEBVTT", "KIND:", "LANGUAGE:", "NOTE")):
            continue
        line = _WHITESPACE.sub(" ", _ANY_TAG.sub("", html_module.unescape(line))).strip()
        # Auto-captions repeat the previous line as they scroll.
        if line and (not lines or lines[-1] != line):
            lines.append(line)
    return " ".join(lines).strip()


def _parse_meta_tags(body: str) -> dict[str, str]:
    """Collect og:/twitter:/name meta tags. Regex, not a parser: we want four
    known keys out of possibly-broken markup, not a DOM."""
    found: dict[str, str] = {}
    for tag in _META_TAG.findall(body):
        key: str | None = None
        content: str | None = None
        for attribute, quoted, single, bare in _META_ATTR.findall(tag):
            value = quoted or single or bare
            lowered = attribute.lower()
            if lowered in {"property", "name"} and key is None:
                key = value.strip().lower()
            elif lowered == "content" and content is None:
                content = value
        if key and content and key not in found:
            cleaned = _clean(content)
            if cleaned:
                found[key] = cleaned
    return found


def _title_tag(body: str) -> str | None:
    match = _TITLE_TAG.search(body)
    return _clean(match.group(1)) if match else None


def _visible_text(body: str) -> str | None:
    stripped = _SCRIPTISH.sub(" ", body)
    text = _clean(_ANY_TAG.sub(" ", stripped), _PAGE_TEXT_CHAR_LIMIT)
    # A shell page ("Enable JavaScript") is worse than admitting we got nothing.
    return text if text and len(text) >= 40 else None


_service: MediaAcquisitionService | None = None


def get_media_acquisition_service() -> MediaAcquisitionService:
    """Shared instance; the service is stateless apart from its temp directory."""
    global _service
    if _service is None:
        _service = MediaAcquisitionService()
    return _service
