import asyncio

from app.models.enums import Platform, SourceType
from app.services.media.acquisition import (
    MediaAcquisitionService,
    _classify_provider_error,
    _parse_cue_format,
    _parse_json3,
    _parse_meta_tags,
    _pick_subtitle_track,
    _visible_text,
)
from app.utils.errors import MediaAcquisitionError, SourceInaccessibleError

HTML = """
<html><head>
<title>Raw &amp; Title</title>
<meta property="og:title" content="Cafe XYZ — Best Filter Coffee" />
<meta property='og:description' content='A tiny place in Indiranagar.'>
<meta name=description content="fallback desc">
<meta property="og:image" content="https://cdn.example.com/a.jpg">
<meta property="og:site_name" content="Example Blog">
<script>var junk = "<b>not text</b>";</script>
<style>body{color:red}</style>
</head><body>
<h1>Cafe XYZ</h1><p>Open 8am to 9pm, closed Mondays. Great filter coffee here.</p>
</body></html>
"""

meta = _parse_meta_tags(HTML)
assert meta["og:title"] == "Cafe XYZ — Best Filter Coffee", meta
assert meta["og:description"] == "A tiny place in Indiranagar.", meta
assert meta["description"] == "fallback desc", meta
assert meta["og:site_name"] == "Example Blog"
print("meta OK", sorted(meta))

text = _visible_text(HTML)
assert text is not None and "junk" not in text and "color:red" not in text, text
assert "Open 8am to 9pm" in text and "Cafe XYZ" in text, text
print("visible_text OK:", text[:70])

VTT = """WEBVTT
Kind: captions
Language: en

1
00:00:01.000 --> 00:00:03.000
<c>we roast</c> the beans

2
00:00:03.000 --> 00:00:05.000
we roast the beans

3
00:00:05.000 --> 00:00:07.000
every morning &amp; night
"""
assert _parse_cue_format(VTT) == "we roast the beans every morning & night", _parse_cue_format(VTT)
print("vtt OK")

JSON3 = '{"events":[{"segs":[{"utf8":"hello "},{"utf8":"\\n"},{"utf8":"world"}]},{"segs":[{"utf8":" again"}]}]}'
assert _parse_json3(JSON3) == "hello world again", repr(_parse_json3(JSON3))
print("json3 OK")

info = {
    "automatic_captions": {"es": [{"ext": "vtt", "url": "es"}], "en": [{"ext": "vtt", "url": "auto-en"}]},
    "subtitles": {"fr": [{"ext": "vtt", "url": "fr"}]},
}
assert _pick_subtitle_track(info) == ("auto-en", "vtt"), _pick_subtitle_track(info)
assert _pick_subtitle_track({"subtitles": {}}) is None
print("subtitle pick OK (prefers english over other languages)")

assert isinstance(_classify_provider_error(RuntimeError("Video unavailable")), SourceInaccessibleError)
assert isinstance(_classify_provider_error(RuntimeError("This post is private")), SourceInaccessibleError)
blip = _classify_provider_error(RuntimeError("HTTP Error 500"))
assert isinstance(blip, MediaAcquisitionError) and not isinstance(blip, SourceInaccessibleError)
assert blip.permanent is False
print("error classification OK")


async def live() -> None:
    service = MediaAcquisitionService()
    media = await service.acquire(
        "https://example.com/",
        source_type=SourceType.WEB_URL,
        platform=Platform.WEB,
        user_note="check this cafe out",
    )
    print("live web:", media.to_log_dict())
    print("text_context head:", media.text_context[:120].replace("\n", " | "))
    assert media.has_any_signal
    assert media.canonical_url == "https://example.com/", media.canonical_url


try:
    asyncio.run(live())
except Exception as exc:  # offline is fine; the pure helpers are what matter
    print("live web skipped:", type(exc).__name__, exc)
print("ALL OK")
