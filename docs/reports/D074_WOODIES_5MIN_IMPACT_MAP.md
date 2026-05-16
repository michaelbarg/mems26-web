# D-074 Woodies 5-Minute Impact Map

**Date:** 2026-05-16  
**Decision:** S4 Woodies runtime target is 5-minute bars, not 30-minute bars.  
**Status:** Decision locked; implementation not yet migrated.

## Current References Found

| Area | Current reference | Required action |
|------|-------------------|-----------------|
| DLL source | `sc_study/v9_woodies_export.h` builds `Woodies30MinBar` and writes `woodies_30min.json` | Build 5-minute Woodies export or consume native 5-minute bars with Woodies studies |
| DLL wrapper | `sc_study/MES_AI_DataExport.cpp` writes `woodies_30min.json` | Rename/add `woodies_5min.json` export |
| Bridge stream | `bridge/v9_streams/woodies_30min_stream.py` | Add `woodies_5min_stream.py` or migrate existing stream |
| Backend system | `backend/v9/systems/woodies/woodies_system.py` subscribes to `woodies_30min` | Subscribe to `woodies_5min` |
| DB model/migration | `v9_bars_30min_woodies` | Create `v9_bars_5min_woodies` or decide to enrich `v9_bars_5min` |
| API push path | `backend/v9/api/v9/bars.py` routes `woodies_30min` | Route `woodies_5min` |
| Health | `backend/v9/services/stream_health/health.py` tracks `woodies_30min` | Track `woodies_5min` |
| Tests | tests assert `woodies_30min` subscriptions | Update to D-074 target |
| UI | Woodies labels mention 30-min | Change labels to 5-min |
| Docs | multiple audit/spec docs say 30-min | Keep historical docs, add D-074 supersession notes |

## Migration Order

1. Decide DB strategy:
   - Option A: dedicated `v9_bars_5min_woodies`
   - Option B: reuse `v9_bars_5min` plus Woodies study fields
2. Add/rename DLL export to `woodies_5min.json`.
3. Add bridge stream `woodies_5min`.
4. Migrate `WoodiesSystem` subscription and hydration.
5. Update API routing and stream health.
6. Update tests and UI labels.
7. Keep compatibility only if needed for historical replay.

## Recommendation

Use a dedicated `v9_bars_5min_woodies` table for the first migration. It keeps
S4 isolated and avoids overloading the general 5-minute bar table while the
Woodies fields and tests stabilize.

## Not In Scope

- This does not enable SHADOW, DEMO, or LIVE.
- This does not change non-S4 concepts that correctly use 30-minute windows
  (TPO letters, Day Type open window, cooldown).

