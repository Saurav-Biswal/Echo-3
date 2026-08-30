"""End-to-end API loop with the mock provider: SAVE -> UNDERSTAND -> RESURFACE -> ACT.

The app lifespan (and thus the background worker) is not started under test, so
processing is driven synchronously through ``POST /api/process`` for determinism.
"""

from __future__ import annotations

import pytest

_PLACE_TEXT = (
    "Amazing rooftop cafe and restaurant on MG Road, Bangalore. Great coffee "
    "and brunch spot, located near the beach - must visit this place."
)
_EXPECTED_STAGES = [
    "FETCHING",
    "ANALYZING",
    "EXTRACTING_INTENT",
    "VALIDATING",
    "SAVING",
    "COMPLETED",
]


async def _capture_and_process(client, content: str, note: str | None = None) -> dict:
    payload = {"input_type": "text", "content": content}
    if note is not None:
        payload["note"] = note
    resp = await client.post("/api/capture", json=payload)
    assert resp.status_code == 202, resp.text
    job_id = resp.json()["job_id"]

    resp = await client.post("/api/process", json={"job_id": job_id})
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_capture_runs_all_stages_to_completed(client):
    job = await _capture_and_process(client, _PLACE_TEXT, note="want to visit")
    assert job["status"] == "COMPLETED"
    assert job["memory_id"] is not None
    stages = [entry["status"] for entry in job["timeline"]]
    assert stages == _EXPECTED_STAGES


async def test_place_memory_has_why_trigger_and_action(client):
    job = await _capture_and_process(client, _PLACE_TEXT, note="want to visit")
    resp = await client.get(f"/api/memories/{job['memory_id']}")
    assert resp.status_code == 200
    memory = resp.json()

    assert memory["category"] == "PLACE"
    assert memory["confidence_band"] == "HIGH"
    assert memory["why_saved"].startswith("You probably saved this because")
    assert len(memory["entities"]) >= 1
    assert any(t["trigger_type"] == "LOCATION" for t in memory["triggers"])
    assert any(a["action_type"] == "OPEN_MAPS" for a in memory["actions"])


async def test_overview_reflects_new_memory(client):
    await _capture_and_process(client, _PLACE_TEXT)
    resp = await client.get("/api/overview")
    body = resp.json()
    assert body["active"] >= 1
    assert any(c["category"] == "PLACE" and c["count"] >= 1 for c in body["by_category"])


async def test_resurface_fires_and_creates_notification(client):
    job = await _capture_and_process(client, _PLACE_TEXT)
    memory_id = job["memory_id"]

    resp = await client.post(
        "/api/demo/simulate-location", json={"memory_id": memory_id}
    )
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["fired"] == 1
    assert len(result["notifications"]) == 1
    assert result["notifications"][0]["memory_id"] == memory_id

    feed = await client.get("/api/notifications")
    assert feed.json()["total"] >= 1


async def test_acknowledge_notification(client):
    job = await _capture_and_process(client, _PLACE_TEXT)
    await client.post("/api/demo/simulate-location", json={"memory_id": job["memory_id"]})

    feed = await client.get("/api/notifications")
    notif_id = feed.json()["items"][0]["id"]

    acted = await client.post(
        f"/api/notifications/{notif_id}/ack", json={"action": "open"}
    )
    assert acted.status_code == 200

    dismissed = await client.post(
        f"/api/notifications/{notif_id}/ack", json={"action": "dismiss"}
    )
    assert dismissed.json()["message"] == "Dismissed."


async def test_correction_rederives_trigger(client):
    # A place saved as PLACE gets a LOCATION trigger; correcting to EVENT must
    # re-derive a DATE trigger (§14) - the whole point is to fix what Echo does.
    job = await _capture_and_process(client, _PLACE_TEXT)
    memory_id = job["memory_id"]

    resp = await client.post(
        f"/api/memories/{memory_id}/correct", json={"category": "EVENT"}
    )
    assert resp.status_code == 200, resp.text
    memory = resp.json()
    assert memory["category"] == "EVENT"
    assert memory["user_corrected"] is True
    assert any(t["trigger_type"] == "DATE" for t in memory["triggers"])


async def test_low_confidence_routes_to_needs_review(client):
    job = await _capture_and_process(client, "hmm ok")
    assert job["memory_id"] is not None
    resp = await client.get(f"/api/memories/{job['memory_id']}")
    assert resp.json()["status"] == "NEEDS_REVIEW"


async def test_health_reports_mock_provider(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ai_provider"] == "mock"
    assert body["status"] == "ok"


async def test_demo_seed_creates_a_memory_per_capture(client):
    # All five built-in seed captures run through the real pipeline and each
    # produces a memory - the count must not undercount due to a stale read.
    resp = await client.post("/api/demo/seed")
    assert resp.status_code == 200, resp.text
    assert resp.json()["created"] == 5

    overview = (await client.get("/api/overview")).json()
    assert overview["active"] + overview["needs_review"] >= 5
