"""URL extraction, canonicalisation and platform detection.

Android share payloads are messy - "Check this out! https://youtube.com/shorts/x
via @someone" is typical - so extraction is deliberately forgiving. Canonicalisation
is deliberately strict, because it is what duplicate detection compares (§33):
the same Short shared from the app and from the browser must produce one key.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.models.enums import Platform, SourceType

# Matches http(s) URLs and bare "www."/domain-ish starts inside shared text.
_URL_PATTERN = re.compile(
    r"""(?ix)
    \b(
        https?://[^\s<>"'\]\)]+
        |
        www\.[^\s<>"'\]\)]+
    )
    """
)

# Params that identify a *share*, not a *resource*. Dropping them is what makes
# the same video shared twice collapse into one canonical URL.
_TRACKING_PARAMS = frozenset(
    {
        "si",
        "feature",
        "app",
        "igsh",
        "igshid",
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
        "ref",
        "ref_src",
        "ref_url",
        "source",
        "share_id",
        "pp",
        "themeRefresh",
    }
)
_TRACKING_PREFIXES = ("utm_",)

# Params that genuinely identify the resource and must survive.
_MEANINGFUL_PARAMS = frozenset({"v", "list", "t", "start", "id", "q"})

_YOUTUBE_HOSTS = frozenset(
    {"youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be", "youtube-nocookie.com"}
)
_INSTAGRAM_HOSTS = frozenset({"instagram.com", "instagr.am", "ig.me"})

_YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{6,20}$")


def extract_first_url(text: str) -> str | None:
    """Pull the first plausible URL out of arbitrary shared text."""
    if not text:
        return None
    match = _URL_PATTERN.search(text)
    if match is None:
        return None
    candidate = match.group(1).rstrip(".,;:!?)”\"'")
    if candidate.lower().startswith("www."):
        candidate = f"https://{candidate}"
    return candidate


def looks_like_url(text: str) -> bool:
    stripped = text.strip()
    if " " in stripped:
        return False
    return bool(_URL_PATTERN.fullmatch(stripped) or _URL_PATTERN.match(stripped))


def _clean_query(query: str) -> str:
    pairs = [
        (key, value)
        for key, value in parse_qsl(query, keep_blank_values=False)
        if key not in _TRACKING_PARAMS
        and not any(key.startswith(prefix) for prefix in _TRACKING_PREFIXES)
    ]
    # Stable ordering so ?v=x&t=1 and ?t=1&v=x canonicalise identically.
    pairs.sort()
    return urlencode(pairs)


def _strip_host(host: str) -> str:
    host = host.lower().removeprefix("www.")
    # Drop the port only when it is the scheme default.
    return host.removesuffix(":80").removesuffix(":443")


def youtube_video_id(url: str) -> str | None:
    """Extract the 11-ish char video id from any YouTube URL shape."""
    parts = urlsplit(url)
    host = _strip_host(parts.netloc)
    if host not in _YOUTUBE_HOSTS:
        return None

    if host == "youtu.be":
        candidate = parts.path.strip("/").split("/")[0]
        return candidate if _YOUTUBE_ID.match(candidate) else None

    segments = [segment for segment in parts.path.split("/") if segment]
    if segments and segments[0] in {"shorts", "embed", "live", "v"} and len(segments) > 1:
        return segments[1] if _YOUTUBE_ID.match(segments[1]) else None

    query = dict(parse_qsl(parts.query))
    candidate = query.get("v")
    return candidate if candidate and _YOUTUBE_ID.match(candidate) else None


def instagram_shortcode(url: str) -> str | None:
    """Extract the shortcode from a reel/post/tv URL."""
    parts = urlsplit(url)
    if _strip_host(parts.netloc) not in _INSTAGRAM_HOSTS:
        return None
    segments = [segment for segment in parts.path.split("/") if segment]
    for index, segment in enumerate(segments):
        if segment in {"reel", "reels", "p", "tv"} and index + 1 < len(segments):
            return segments[index + 1]
    return None


def canonicalise(url: str) -> str:
    """Return the stable identity of a URL.

    YouTube collapses to ``https://www.youtube.com/watch?v=<id>`` regardless of
    whether it arrived as a Short, a ``youtu.be`` link or an embed, because they
    are the same video and saving one twice is a duplicate.
    """
    if not url:
        return url
    if "://" not in url:
        url = f"https://{url}"

    parts = urlsplit(url)
    host = _strip_host(parts.netloc)

    video_id = youtube_video_id(url)
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"

    shortcode = instagram_shortcode(url)
    if shortcode:
        kind = "reel" if "/reel" in parts.path or "/reels" in parts.path else "p"
        return f"https://www.instagram.com/{kind}/{shortcode}"

    path = parts.path.rstrip("/") or "/"
    return urlunsplit(("https", host, path, _clean_query(parts.query), ""))


def detect_source(url: str) -> tuple[Platform, SourceType]:
    """Classify a URL into (platform, source_type)."""
    if not url:
        raise ValueError("url must not be empty")
    if "://" not in url:
        url = f"https://{url}"

    parts = urlsplit(url)
    host = _strip_host(parts.netloc)
    path = parts.path.lower()

    if host in _YOUTUBE_HOSTS:
        if "/shorts/" in path:
            return Platform.YOUTUBE, SourceType.YOUTUBE_SHORT
        return Platform.YOUTUBE, SourceType.YOUTUBE_VIDEO

    if host in _INSTAGRAM_HOSTS:
        if "/reel" in path:
            return Platform.INSTAGRAM, SourceType.INSTAGRAM_REEL
        return Platform.INSTAGRAM, SourceType.INSTAGRAM_POST

    return Platform.WEB, SourceType.WEB_URL


def youtube_thumbnail(video_id: str) -> str:
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
