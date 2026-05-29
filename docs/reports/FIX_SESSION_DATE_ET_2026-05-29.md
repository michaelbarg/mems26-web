# Fix Report — session_date ET conversion · 2026-05-29

**Commit:** `570f10d` on `stabilize/mems26-local-truth-2026-05-16`
**Author:** CC
**Reviewed by:** Michael (verbal approval before implementation)

---

## Problem

Build status showed **"✅ Fired: Normal (p=0.68)"** for May 29 before RTH opened.
This was misleading — it was yesterday's classification carried over.

### Root cause

`consumer.py:_extract_session_date()` used `ts.date()` on a UTC timestamp.
A bar at 20:00 ET May 28 = 00:00 UTC May 29 → `session_date = 2026-05-29`.
The consumer wrote a new row for May 29 with May 28's stale values.

### Prior workaround (removed)

CC added a `🕐 History` label to the inspector that checked if
`last_updated_at < today's RTH open`. Michael correctly identified this
as a patch-on-patch — the inspector shouldn't need to guess whether
the data is stale; the consumer should write to the correct date.

---

## Fix

**File:** `backend/v9/systems/day_type/consumer.py:138-155`

**Change:** `_extract_session_date` now converts to `America/New_York`
before extracting the date:

```python
# BEFORE:
return ts.date()  # UTC date — 20:00 ET = next day in UTC

# AFTER:
et = ts.astimezone(ZoneInfo("America/New_York"))
return et.date()  # ET date — 20:00 ET = same day
```

**Inspector cleanup:** Removed the `🕐 History` / `is_stale_carryover`
block from `day_type_inspector.py` — no longer needed.

**DB cleanup:** Deleted the stale `2026-05-29` row from
`v9_day_type_history` that was created by the old UTC logic.

---

## Verification

```
# Unit test: 3 timestamp scenarios
00:00 UTC May 29 (=20:00 ET May 28) → session_date=2026-05-28  ✅
05:00 UTC May 29 (=01:00 ET May 29) → session_date=2026-05-29  ✅
14:00 UTC May 29 (=10:00 ET May 29) → session_date=2026-05-29  ✅

# Build status after restart (pre-RTH):
status: unknown
label:  ❓ Unknown
reason: No classification for today

# Regression: 970 passed, 0 new failures
```

---

## What Cursor should verify

1. After RTH opens (09:30 ET), the build status should transition from
   `❓ Unknown` → `🟡 Armed` → `✅ Fired` as the state machine classifies
2. No stale row appears for the next calendar day during overnight session
3. The `v9_day_type_history` table has exactly one row per trading day,
   keyed by ET date (not UTC date)

---

## Audit trail — what was removed

| Item | Added | Removed | Reason |
|------|-------|---------|--------|
| `🕐 History` label in inspector | This session | This session | Patch-on-patch — root cause fixed instead |
| `is_stale_carryover` detection | This session | This session | Same — no longer needed |
| `v9_day_type_history` row for 2026-05-29 | Overnight bars (bug) | Manual DELETE | Stale carry-over from old UTC logic |
