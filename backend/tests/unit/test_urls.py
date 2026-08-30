"""URL extraction, canonicalisation and platform detection (§33)."""

from __future__ import annotations

import pytest

from app.models.enums import Platform, SourceType
from app.utils.urls import (
    canonicalise,
    detect_source,
    extract_first_url,
    instagram_shortcode,
    looks_like_url,
    youtube_video_id,
)


def test_extract_first_url_from_messy_share():
    text = "Check this out! https://youtube.com/shorts/abc123XYZ via @someone"
    assert extract_first_url(text) == "https://youtube.com/shorts/abc123XYZ"


def test_extract_first_url_upgrades_www():
    assert extract_first_url("see www.example.com/page here") == (
        "https://www.example.com/page"
    )


def test_extract_first_url_none_when_absent():
    assert extract_first_url("just some plain text, no link") is None
    assert extract_first_url("") is None


def test_looks_like_url():
    assert looks_like_url("https://example.com/x") is True
    assert looks_like_url("  https://example.com  ") is True
    assert looks_like_url("this is a sentence") is False


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://youtube.com/shorts/dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ&feature=share",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&si=trackingtoken",
    ],
)
def test_youtube_variants_collapse_to_one_canonical(url):
    # The same video shared as a Short, a youtu.be link, or with a tracking
    # param must produce one identity so it is detected as a duplicate.
    assert canonicalise(url) == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_youtube_video_id_extraction():
    assert youtube_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert youtube_video_id("https://example.com/x") is None


def test_instagram_reel_canonicalises():
    url = "https://www.instagram.com/reel/CxYz123/?igshid=tracking"
    assert canonicalise(url) == "https://www.instagram.com/reel/CxYz123"
    assert instagram_shortcode(url) == "CxYz123"


def test_tracking_params_dropped_but_meaningful_kept():
    url = "https://shop.example.com/item?id=42&utm_source=ig&ref=abc&t=10"
    canon = canonicalise(url)
    assert "utm_source" not in canon
    assert "ref=abc" not in canon
    assert "id=42" in canon
    assert "t=10" in canon


def test_query_param_order_is_stable():
    a = canonicalise("https://example.com/p?b=2&a=1")
    b = canonicalise("https://example.com/p?a=1&b=2")
    assert a == b


@pytest.mark.parametrize(
    "url,platform,source_type",
    [
        ("https://youtube.com/shorts/x", Platform.YOUTUBE, SourceType.YOUTUBE_SHORT),
        ("https://youtube.com/watch?v=x", Platform.YOUTUBE, SourceType.YOUTUBE_VIDEO),
        ("https://instagram.com/reel/x", Platform.INSTAGRAM, SourceType.INSTAGRAM_REEL),
        ("https://instagram.com/p/x", Platform.INSTAGRAM, SourceType.INSTAGRAM_POST),
        ("https://someblog.com/article", Platform.WEB, SourceType.WEB_URL),
    ],
)
def test_detect_source(url, platform, source_type):
    assert detect_source(url) == (platform, source_type)


def test_detect_source_rejects_empty():
    with pytest.raises(ValueError):
        detect_source("")
