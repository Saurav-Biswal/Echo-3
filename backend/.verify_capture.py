"""Throwaway end-to-end verifier: capture -> poll -> print the saved memory.

Hits the running backend over HTTP exactly as a client would, so a pass here is
(c) manually-verified-end-to-end, not just (b) implemented. Prints the trigger's
fire_at in UTC *and* in a chosen local zone, because that difference is the
Phase 1 defect under investigation.

Usage:  python .verify_capture.py text  "some content"
        python .verify_capture.py url   "https://youtube.com/shorts/..."

Delete after Phase 1 verification.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

BASE = "http://127.0.0.1:8000/api"
LOCAL_ZONE = ZoneInfo("Asia/Kolkata")


def post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def get(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=30) as r:
        return json.load(r)


def show_dt(label: str, raw: str | None) -> None:
    if not raw:
        print(f"    {label:14} None")
        return
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        print(f"    {label:14} {raw!r} (unparseable)")
        return
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
        naive = "  <- was NAIVE, assumed UTC"
    else:
        naive = ""
    print(
        f"    {label:14} {dt.isoformat()}{naive}\n"
        f"    {'':14} = {dt.astimezone(LOCAL_ZONE).isoformat()} (Asia/Kolkata)"
    )


def main() -> int:
    kind, content = sys.argv[1], sys.argv[2]
    body = {"input_type": kind, "content": content}

    job = post("/capture", body)
    if job.get("duplicate"):
        print(f"DUPLICATE of memory {job['memory_id']}")
        return 0
    job_id = job["job_id"]
    print(f"job {job_id}")

    detail = {}
    for _ in range(80):
        detail = get(f"/jobs/{job_id}")
        status = detail["status"]
        if status in ("COMPLETED", "FAILED"):
            break
        print(f"  .. {status}")
        time.sleep(1.5)

    print(f"  -> {detail['status']}")
    if detail["status"] == "FAILED":
        print(f"  error_code   : {detail['error_code']}")
        print(f"  failed_stage : {detail['failed_stage']}")
        for entry in detail.get("timeline", []):
            if entry.get("detail"):
                print(f"  detail       : {entry['detail'][:400]}")
        return 1

    memory_id = detail["memory_id"]
    m = get(f"/memories/{memory_id}")
    print(f"\n  MEMORY {memory_id}")
    print(f"    category     {m['category']}")
    print(f"    title        {m['title']!r}")
    print(f"    why_saved    {m['why_saved']!r}")
    print(f"    intent       {m['intent_action']}  conf={m['intent_confidence']} "
          f"band={m['confidence_band']}  status={m['status']}")
    print(f"    ai_model     {m.get('ai_model')}")

    src = m.get("source") or {}
    if src:
        print(f"\n  SOURCE")
        for key in ("source_type", "platform", "title", "author", "duration_seconds"):
            if src.get(key) is not None:
                print(f"    {key:14} {src[key]!r}")

    for e in m.get("entities", []):
        print(f"\n  ENTITY {e['entity_type']} {e['name']!r}")
        for key in ("location", "address", "latitude", "longitude", "venue",
                    "event_date", "event_time", "price", "url"):
            if e.get(key) is not None:
                print(f"    {key:14} {e[key]!r}")
        show_dt("starts_at", e.get("starts_at"))

    for t in m.get("triggers", []):
        print(f"\n  TRIGGER {t['trigger_type']} status={t['status']}")
        print(f"    reason       {t['reason']!r}")
        show_dt("fire_at", t.get("fire_at"))
        for key in ("latitude", "longitude", "radius_meters", "place_label"):
            if t.get(key) is not None:
                print(f"    {key:14} {t[key]!r}")
        print(f"    payload      {t.get('payload')}")

    for a in m.get("actions", []):
        print(f"\n  ACTION {a['action_type']} primary={a['is_primary']}")
        print(f"    label        {a['label']!r}")
        print(f"    deep_link    {a.get('deep_link')!r}")
        print(f"    web_link     {(a.get('web_link') or '')[:110]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
