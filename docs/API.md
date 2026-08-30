# Echo API contract

Base URL: `http://localhost:8000`, all routes under `/api`.
Auth (MVP): optional `X-Echo-User: <email>` header. Omitted → the demo user.
Errors: every failure returns `{"error": {"code", "message", "hint"?}}`. Never a stack trace.

## Enums

```
Category        PLACE | EVENT | RECIPE | TOOL | TOPIC
IntentAction    VISIT | GO | EXPLORE | ATTEND | COOK | TRY | USE | LEARN | READ | RESEARCH | OTHER
MemoryStatus    ACTIVE | RESURFACED | COMPLETED | DISMISSED | ARCHIVED | NEEDS_REVIEW
ConfidenceBand  HIGH | MEDIUM | LOW
TriggerType     DATE | TIME | LOCATION | MANUAL
TriggerStatus   PENDING | FIRED | CANCELLED
ActionType      OPEN_MAPS | ADD_TO_CALENDAR | OPEN_EVENT | VIEW_RECIPE | OPEN_TOOL | OPEN_SOURCE | OPEN_URL | SET_REMINDER
JobStatus       QUEUED | FETCHING | ANALYZING | EXTRACTING_INTENT | VALIDATING | SAVING | COMPLETED | FAILED
SourceType      youtube_short | youtube_video | instagram_reel | instagram_post | web_url | screenshot | text
Platform        youtube | instagram | web | device
MediaType       video | image | text | none
InputType       url | text | image
NotificationStatus  SCHEDULED | SENT | ACTED | DISMISSED
EntityType      PLACE | EVENT | RECIPE | TOOL | TOPIC
```

## Endpoints

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/health` | – | `HealthResponse` |
| POST | `/api/capture` | `CaptureRequest` | `202 CaptureResponse` |
| POST | `/api/capture/image` | multipart `file`, `source?`, `note?` | `202 CaptureResponse` |
| GET | `/api/jobs/{job_id}` | – | `JobDetailRead` |
| POST | `/api/process` | `{"memory_id"?, "job_id"?}` | `202 CaptureResponse` |
| GET | `/api/overview` | – | `OverviewResponse` |
| GET | `/api/memories` | `?status&category&limit&offset&q` | `Page<MemoryRead>` |
| GET | `/api/memories/{id}` | – | `MemoryRead` |
| PATCH | `/api/memories/{id}` | `MemoryUpdate` | `MemoryRead` |
| DELETE | `/api/memories/{id}` | – | `204` |
| POST | `/api/memories/{id}/correct` | `MemoryCorrection` | `MemoryRead` |
| GET | `/api/triggers` | `?status&trigger_type&memory_id&limit&offset` | `Page<TriggerRead>` |
| POST | `/api/triggers` | `TriggerCreate` | `201 TriggerRead` |
| DELETE | `/api/triggers/{id}` | – | `204` |
| GET | `/api/triggers/geofences` | – | `GeofenceRead[]` |
| GET | `/api/notifications` | `?status&limit&offset` | `Page<NotificationRead>` |
| POST | `/api/notifications/{id}/ack` | `{"action":"SENT"\|"ACTED"\|"DISMISSED"}` | `NotificationRead` |
| POST | `/api/test/resurface` | `ResurfaceRequest` | `ResurfaceResponse` |
| POST | `/api/demo/simulate-location` | `SimulateLocationRequest` | `ResurfaceResponse` |
| POST | `/api/demo/simulate-date` | `SimulateDateRequest` | `ResurfaceResponse` |
| POST | `/api/demo/seed` | – | `{"created": n}` |

`Page<T>` = `{"items": T[], "total": n, "limit": n, "offset": n}`.

## Capture

```jsonc
// POST /api/capture
{ "input_type": "url", "content": "https://youtube.com/shorts/abc", "source": "android_share", "note": null }
// 202
{ "job_id": "uuid", "status": "QUEUED", "duplicate": false, "memory_id": null, "message": null }
// 202 when already saved (§33)
{ "job_id": "uuid", "status": "COMPLETED", "duplicate": true, "memory_id": "uuid", "message": "You already saved this." }
```

## Job polling

```jsonc
// GET /api/jobs/{id}
{
  "id": "uuid",
  "status": "ANALYZING",
  "stage_message": "Understanding why you saved it...",
  "progress": 0.45,
  "input_type": "url", "origin": "android_share",
  "source_type": "youtube_short", "platform": "youtube",
  "memory_id": null, "is_duplicate": false, "duplicate_of_memory_id": null,
  "error_code": null, "error_message": null, "attempts": 1,
  "created_at": "…", "started_at": "…", "finished_at": null,
  "timeline": [{ "status": "QUEUED", "at": "…", "detail": null }]
}
```

Client loop: poll every ~1.2 s until `status` is `COMPLETED` or `FAILED`, then `GET /api/memories/{memory_id}`.
`stage_message` is server-authored copy — render it verbatim.

## MemoryRead

```jsonc
{
  "id": "uuid",
  "category": "PLACE",
  "title": "Cafe XYZ",
  "summary": "A short café in Bandra known for filter coffee.",
  "why_saved": "You probably saved this because you may want to visit this place.",
  "intent_action": "VISIT",
  "intent_confidence": 0.94,
  "confidence_band": "HIGH",
  "status": "ACTIVE",
  "needs_review_reason": null,
  "resurface_count": 0, "resurfaced_at": null, "completed_at": null,
  "created_at": "…", "updated_at": "…",
  "user_confirmed": false, "user_corrected": false, "ai_model": "gemini-2.5-flash",

  "source": {
    "id": "uuid", "source_type": "youtube_short", "platform": "youtube",
    "media_type": "video", "source_url": "https://…",
    "title": "5 cafés in Mumbai", "description": null,
    "thumbnail_url": "https://…", "author": "@handle", "duration_seconds": 48
  },

  "entities": [{
    "id": "uuid", "entity_type": "PLACE", "name": "Cafe XYZ",
    "description": null, "location": "Mumbai", "address": null,
    "latitude": 19.076, "longitude": 72.8777,
    "event_date": null, "event_time": null, "starts_at": null, "ends_at": null, "venue": null,
    "url": null, "price": "₹400 for two", "duration_minutes": null,
    "details": {}, "confidence": 0.9, "is_primary": true
  }],

  "triggers": [{
    "id": "uuid", "memory_id": "uuid", "trigger_type": "LOCATION",
    "status": "PENDING", "reason": "You may want this when you are nearby",
    "fire_at": null, "latitude": 19.076, "longitude": 72.8777,
    "radius_meters": 300, "place_label": "Cafe XYZ",
    "fired_at": null, "fire_count": 0, "created_at": "…"
  }],

  "actions": [{
    "id": "uuid", "action_type": "OPEN_MAPS", "label": "Open Maps",
    "deep_link": "geo:19.076,72.8777?q=Cafe%20XYZ",
    "web_link": "https://www.google.com/maps/search/?api=1&query=Cafe%20XYZ",
    "action_metadata": {}, "is_primary": true, "sort_order": 0
  }]
}
```

Notes for renderers:
- `entities[]` may be empty; fall back to `title`.
- `triggers[]` may be empty (`MANUAL` memories sometimes have none) — then show "Saved for later".
- `actions[]` is ordered; `is_primary` is the one button to emphasise.
- `deep_link` is for Android intents, `web_link` for the browser. Either may be null.

## Overview

```jsonc
{
  "active": 12, "resurfaced": 3, "completed": 5, "needs_review": 1,
  "by_category": [{ "category": "PLACE", "count": 6 }],
  "upcoming_trigger_at": "2026-09-14T09:00:00Z",
  "recent": [ /* MemoryRead[] */ ]
}
```

## Correction (§14)

```jsonc
// POST /api/memories/{id}/correct
{ "category": "EVENT", "intent_action": "ATTEND", "note": "it's a meetup", "confirmed": false }
```
Changing `category` re-derives triggers and actions, then returns the updated `MemoryRead`.
`{"confirmed": true}` alone records a "Yes, that's why" with no other change.

## NotificationRead

```jsonc
{
  "id": "uuid", "memory_id": "uuid", "category": "PLACE", "trigger_type": "LOCATION",
  "title": "📍 You're near Cafe XYZ",
  "body": "You saved this earlier.",
  "why": "You may want this when you are nearby",
  "status": "SCHEDULED", "scheduled_at": null, "sent_at": null, "created_at": "…",
  "actions": [ /* ActionRead[] snapshot */ ],
  "payload": {}
}
```

## Demo controls (§45)

```jsonc
POST /api/demo/simulate-location  { "memory_id": "uuid" }                  // or {latitude, longitude}
POST /api/demo/simulate-date      { "memory_id": "uuid" }                  // or {as_of: "2026-09-14T09:00:00Z"}
POST /api/test/resurface          { "memory_id": "uuid", "trigger_type": null }
// all →
{ "fired": 1, "notifications": [ /* NotificationRead[] */ ], "message": "…" }
```

These run the real evaluator + notification path; only the *context* is simulated.
