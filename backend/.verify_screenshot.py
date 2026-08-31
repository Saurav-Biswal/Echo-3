"""Throwaway: synthesise a realistic screenshot and run it through /capture/image.

Gemini vision reads pixels, so a hand-drawn listing card is a fair test of the
screenshot path - the fields below appear nowhere in the request except as
rendered text in the image.

Delete after Phase 0 verification.
"""

from __future__ import annotations

import io
import json
import sys
import time
import urllib.request
import uuid

from PIL import Image, ImageDraw

BASE = "http://127.0.0.1:8000/api"

BG = (18, 18, 20)
FG = (242, 240, 234)
DIM = (150, 150, 156)
ACCENT = (178, 255, 89)

PLACE_LINES = [
    (28, "Naru Noodle Bar", FG),
    (18, "4.8  *****   (2,146 reviews)", ACCENT),
    (18, "Ramen restaurant  -  $$", DIM),
    (18, "", DIM),
    (18, "969, 12th Main Rd, HAL 2nd Stage,", FG),
    (18, "Indiranagar, Bengaluru 560008", FG),
    (18, "", DIM),
    (18, "Open  -  Closes 10:30 pm", ACCENT),
    (18, "Tue - Sun   12:00 pm - 3:00 pm,", DIM),
    (18, "            7:00 pm - 10:30 pm", DIM),
    (18, "Closed Mondays", DIM),
    (18, "", DIM),
    (18, "Tonkotsu bowl  Rs 690", FG),
    (18, "Reservations required - book 7 days ahead", DIM),
]


def render(path: str) -> None:
    img = Image.new("RGB", (900, 1400), BG)
    d = ImageDraw.Draw(img)
    y = 90
    for size, text, colour in PLACE_LINES:
        if text:
            # Default bitmap font; scale by drawing into a temp and resizing so
            # the text is large enough for the model to read comfortably.
            tmp = Image.new("RGB", (760, 22), BG)
            ImageDraw.Draw(tmp).text((0, 4), text, fill=colour)
            factor = max(1, round(size / 11))
            tmp = tmp.resize((760 * factor, 22 * factor), Image.LANCZOS)
            img.paste(tmp.crop((0, 0, min(860, tmp.width), tmp.height)), (40, y))
            y += 22 * factor + 14
        else:
            y += 24
    d.rectangle([(40, y + 20), (420, y + 90)], outline=ACCENT, width=3)
    lbl = Image.new("RGB", (300, 22), BG)
    ImageDraw.Draw(lbl).text((0, 4), "DIRECTIONS", fill=ACCENT)
    img.paste(lbl.resize((600, 44), Image.LANCZOS).crop((0, 0, 360, 44)), (60, y + 42))
    img.save(path, quality=95)


def post_image(path: str) -> dict:
    boundary = uuid.uuid4().hex
    with open(path, "rb") as fh:
        payload = fh.read()
    body = io.BytesIO()
    body.write(f"--{boundary}\r\n".encode())
    body.write(
        b'Content-Disposition: form-data; name="file"; filename="screenshot.jpg"\r\n'
        b"Content-Type: image/jpeg\r\n\r\n"
    )
    body.write(payload)
    body.write(f"\r\n--{boundary}--\r\n".encode())
    req = urllib.request.Request(
        f"{BASE}/capture/image",
        data=body.getvalue(),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def get(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=30) as r:
        return json.load(r)


def main() -> int:
    image_path = ".screenshot_place.jpg"
    render(image_path)
    print(f"rendered {image_path}")

    job = post_image(image_path)
    if job.get("duplicate"):
        print(f"DUPLICATE of {job['memory_id']}")
        return 0
    job_id = job["job_id"]
    print(f"job {job_id}")

    detail: dict = {}
    for _ in range(80):
        detail = get(f"/jobs/{job_id}")
        if detail["status"] in ("COMPLETED", "FAILED"):
            break
        print(f"  .. {detail['status']}")
        time.sleep(1.5)
    print(f"  -> {detail['status']}")
    if detail["status"] == "FAILED":
        print(f"  error_code   : {detail['error_code']}")
        print(f"  failed_stage : {detail['failed_stage']}")
        for e in detail.get("timeline", []):
            if e.get("detail"):
                print(f"  detail       : {e['detail'][:400]}")
        return 1

    m = get(f"/memories/{detail['memory_id']}")
    print(f"\n  MEMORY {m['id']}")
    print(f"    category     {m['category']}")
    print(f"    title        {m['title']!r}")
    print(f"    why_saved    {m['why_saved']!r}")
    print(f"    intent       {m['intent_action']} conf={m['intent_confidence']} "
          f"band={m['confidence_band']} status={m['status']}")
    print(f"    ai_model     {m.get('ai_model')}")
    src = m.get("source") or {}
    print(f"    source_type  {src.get('source_type')!r} platform={src.get('platform')!r}")
    for e in m.get("entities", []):
        print(f"\n  ENTITY {e['entity_type']} {e['name']!r}")
        for k in ("location", "address", "latitude", "longitude", "venue",
                  "opening_hours", "price", "url", "notes"):
            if e.get(k) is not None:
                print(f"    {k:14} {e[k]!r}")
    for t in m.get("triggers", []):
        print(f"\n  TRIGGER {t['trigger_type']} status={t['status']}")
        print(f"    reason       {t['reason']!r}")
        for k in ("fire_at", "latitude", "longitude", "radius_meters", "place_label"):
            print(f"    {k:14} {t.get(k)!r}")
    for a in m.get("actions", []):
        print(f"\n  ACTION {a['action_type']} primary={a['is_primary']}")
        print(f"    label        {a['label']!r}")
        print(f"    deep_link    {a.get('deep_link')!r}")
        print(f"    web_link     {(a.get('web_link') or '')[:120]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
