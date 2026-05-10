# V9 Security Fixes — 2026-05-10

## 1. BRIDGE_TOKEN: Hardcoded Default Removed

**Files changed:**
- `bridge/v9_streams/base_stream.py` (line 19)
- `backend/v9/api/v9/auth.py` (line 6)
- `frontend/v9/src/v9/lib/api.ts` (line 2)

**Before:** `BRIDGE_TOKEN = os.getenv("BRIDGE_TOKEN", "michael-mems26-2026")`
**After:** `BRIDGE_TOKEN = os.getenv("BRIDGE_TOKEN", "")` + fail-fast RuntimeError if empty.

**Action required:** Set `BRIDGE_TOKEN` in:
- Render environment variables (backend)
- `.env` on the Windows bridge machine
- `.env.local` in frontend (as `NEXT_PUBLIC_BRIDGE_TOKEN`)

Both bridge and backend will refuse to start without the env var set.

## 2. Redis LTRIM Monitoring

**File:** `bridge/v9_streams/base_stream.py`

- `_redis_cmd()` now reads and returns the response body (was discarded).
- `_redis_lpush()` checks LTRIM response for errors.
- After each LPUSH, runs LLEN to check list size:
  - `> 200`: WARNING log (LTRIM may be silently failing)
  - `> 10,000`: ERROR log (unbounded growth alert)

## 3. Backend Table Routing Fixes

**File:** `backend/v9/api/v9/bars.py`

| Endpoint | Before | After |
|----------|--------|-------|
| POST /volume_profile | INSERT new V9Bar5Min rows (duplicates) | UPDATE existing V9Bar5Min (match by ts window) |
| POST /cumulative_delta | INSERT new V9Bar5Min rows (duplicates) | UPDATE existing V9Bar5Min (match by ts window) |
| POST /footprint | V9BarTickReversal with tick_size=0 | V9BarFootprint (dedicated table) |

**New files:**
- `backend/v9/db/models/bars_footprint.py` — V9BarFootprint model
- `schema/v9_migrations/V9_012_bars_footprint.sql` — migration

**Migration required:** Run `V9_012_bars_footprint.sql` on the database.

## 4. Frontend Trade Markers

**File:** `frontend/v9/src/v9/components/chart/TradeMarkerOverlay.tsx`

Replaced `createSeriesMarkers()` (arrows/circles/squares) with HTML overlay divs that render as colored translucent vertical bars spanning the trade's time range on the chart. Each bar:
- Color = system color from SYSTEM_COLORS
- Background = system color at 13% opacity
- Border style = solid (LIVE), none (SIM), dashed (SHADOW)
- Entry arrow + exit icon at edges
- Click opens trade detail modal
- Hover shows tooltip with trade info

## 5. SettingsDrawer SIM Border

**File:** `frontend/v9/src/v9/components/settings/SettingsDrawer.tsx`

SIM mode button border changed from hardcoded `dotted` to use `SYSTEM_BORDER_STYLE[m]` constant (which maps SIM to `none`).
