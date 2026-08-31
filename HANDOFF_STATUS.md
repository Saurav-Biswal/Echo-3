# Echo — Handoff Status

> **Last updated**: 2026-08-31 by Antigravity IDE (Session 2)
> **Previous session**: Claude Code (cut off mid-task, no handoff doc created)

---

## Repository State

- **Branch**: `main` (2 commits)
- **Working tree**: clean
- **Commits**:
  - `f7a06ed` — Initial architecture: full capture→analyze→trigger pipeline, share sheet, UI, demo endpoints
  - `7fe8935` — Phase 1: device notification delivery + tap-through (38 files, +1504 lines)

---

## What's Done

### Phase 0 — Full Architecture (commit f7a06ed)

| Layer | What | Status |
|-------|------|--------|
| Backend models | Memory, Trigger, Notification, Entity, Action, Job, User | ✅ architecture exists |
| Backend AI | Gemini + mock provider, IntentAnalysis schema | ✅ architecture exists |
| Backend pipeline | Capture → acquire media → AI analysis → memory + trigger creation | ✅ implemented |
| Backend triggers | TriggerType enum (DATE/TIME/LOCATION/MANUAL), evaluator registry | ✅ architecture exists |
| Backend notifications | `ResurfacingService.resurface()` — single firing path (§45) | ✅ architecture exists |
| Backend demo | `/api/demo/seed`, `/api/demo/simulate-location`, `/api/demo/simulate-date`, `/api/test/resurface` | ✅ implemented |
| Backend geofence feed | `GET /api/triggers/geofences` → `GeofenceRead[]` | ✅ implemented |
| Android share sheet | `ShareActivity` receives text/image from any app | ✅ implemented |
| Android home | Dashboard with overview counts, recent memories, inline capture | ✅ implemented |
| Android UI | MemoryCard, ProcessingAnimation, ScanlineEffect, acid-green theme | ✅ implemented |

### Phase 1 — Notification Delivery (commit 7fe8935)

| Component | What | Status |
|-----------|------|--------|
| `NotificationPoller` | Foreground service polling SENT notifications every 30s | ✅ implemented |
| `EchoNotifier` | System notification with high-importance channel, tap-through intent | ✅ verified on device (foreground) |
| `SeenStore` | Device-side dedupe via SharedPreferences | ✅ implemented |
| `MainActivity.handleIntent()` | Opens focused memory dialog from notification EXTRA_MEMORY_ID | ✅ verified on device |
| `HomeViewModel.openMemory()` | Loads memory by id and surfaces it | ✅ implemented |
| Scan loop (`workers/scan.py`) | Autonomous DATE/TIME trigger firing | ✅ implemented |
| Timezone handling | `resolve_zone()`, wall-clock time anchoring | ✅ implemented |
| Backend user/auth | Demo user auto-creation, `X-Echo-User` header | ✅ implemented |

**Foreground notification**: ✅ Verified end-to-end on real device
**Background notification**: ⚠️ OEM battery optimization may kill the foreground service — documented limitation, not a bug

### Phase 2 — Simulate Nearby (this session)

| Component | What | Status |
|-----------|------|--------|
| `POST /api/demo/simulate-nearby` | Force-resurface a specific memory | ✅ implemented |
| `EchoApi.simulateNearby()` | Android API call | ✅ implemented |
| `EchoRepository.simulateNearby()` | Repository wrapper | ✅ implemented |
| `HomeViewModel.simulateNearby()` | ViewModel action with status feedback | ✅ implemented |
| MemoryCard ⚡ SIMULATE_NEARBY button | Per-card demo action | ✅ implemented |
| Notification delivery via existing pipeline | Same `NotificationPoller` → `EchoNotifier` path | ✅ reuses Phase 1 |
| Poller interval reduced for demo | 15s instead of 30s | ✅ implemented |

---

## Do Not Break List

These components are verified working. Changes must not regress them:

1. **`EchoNotifier.notify()`** — system notification creation
2. **`EchoNotifier.ensureChannels()`** — channel setup
3. **`NotificationPoller` polling loop** — SENT feed → system notifications
4. **`SeenStore` dedupe** — no duplicate system notifications
5. **`ResurfacingService.resurface()` → `_fire()` → `build_notification()`** — the one firing path
6. **Scan loop** (`workers/scan.py`) — autonomous DATE/TIME firing
7. **Share sheet pipeline** — `ShareActivity` → backend capture
8. **Demo endpoints** — seed, simulate-location, simulate-date
9. **`MainActivity.handleIntent()`** — notification tap-through to memory dialog

---

## What's Deferred (Not MVP)

- Real Android geofence registration (`GeofencingClient`, location permissions)
- Google Maps/Places geocoding API
- Instagram reel/post support
- Dashboard web app (Next.js scaffold exists in `/dashboard`)
- Comprehensive test suite
- UI polish beyond functional demo
- Production auth (current: demo user)
- FCM push notifications (current: polling)

---

## MVP Submission Scope Reminder

Priority order for remaining work:

1. ✅ **Phase 1**: Notification delivery pipeline (done)
2. 🔄 **Phase 2**: Simulate Nearby demo action (this session)
3. **Phase 3**: Full demo loop (share → process → trigger → notification → action)
4. **Phase 4**: Demo mode polish (seed data quality, timing)

Only attempt UI polish, tests, Instagram, or dashboard if Phases 1–4 are solid.

---

## For the Next Session

1. Read this file first
2. Run `git log --oneline` and `git status` to verify state matches
3. Check if Phase 2's Simulate Nearby is verified on device (may need manual test)
4. Continue with Phase 3 (full demo loop verification) or Phase 4 (demo polish)
5. Update this file before ending your session
