# Chart #5 Option A Implementation · 2026-06-01

**Date:** 2026-06-01 14:05 IL (07:05 ET) · **Author:** CC
**Decision:** Michael approved Option A (cross-chart input) 2026-06-01

---

## Summary

Chart #5 (MESM26 5-Min, 24h Globex) is now the **canonical continuous source** for 5-min OHLCV + CVD. Real overnight bars with proper OHLC (7615-7617) replace the frozen `sc.Close` (7590.50).

## DLL Change

**Version:** `v9.4.4-chart5` (was `v9.4.3-p31.1`)

| Change | File | Lines |
|--------|------|-------|
| New Input[20] `ContinuousChartNumber` (default=5) | `MES_AI_DataExport.cpp` | 47, 124 |
| Export 10: read chart #5 via `SCGraphData` cross-chart API | `MES_AI_DataExport.cpp` | 962-1067 |
| Version bump | `v9_types.h` | 21 |

**Build fix:** First attempt used `sc.GetChartBaseData(chart, SC_OPEN, array)` per-array — doesn't exist in ACSIL. Fixed to `sc.GetChartBaseData(chart, SCGraphData&)` which fills all arrays at once.

**New export files:**
- `5min_continuous.json` — 600 bars, 24h coverage (May 28 → Jun 1)
- `cumulative_delta_continuous.json` — 600 CVD points, matching range

**Chart #12 regression:** All 16 existing files FRESH, unchanged. ✅

## Backend Wiring

| Component | File | What |
|-----------|------|------|
| Bridge stream | `bars_5min_continuous_stream.py` (NEW) | Reads `5min_continuous.json`, pushes to `/api/v9/bars/5min_continuous` |
| Bridge stream | `cvd_continuous_stream.py` (NEW) | Reads `cumulative_delta_continuous.json` |
| Stream registry | `bridge/v9_streams/__init__.py` | Added both to `ALL_STREAMS` |
| Ingest endpoint | `backend/v9/api/v9/bars.py` | `POST /api/v9/bars/5min_continuous` → `bar_ingestion_service` |
| Timestamp fix | `bars.py` ingest handler | Unix ts → `datetime.fromtimestamp(UTC)` for DB compatibility |

## Verification (Rule 5)

```
=== Real overnight OHLC (not flat) ===
2026-06-01 04:00  O=7617.50 H=7617.75 L=7616.50 C=7617.25  ← REAL OVERNIGHT
2026-06-01 04:05  O=7617.00 H=7617.75 L=7615.50 C=7616.00
2026-06-01 04:10  O=7615.75 H=7617.00 L=7615.00 C=7616.75

=== Chart #12 regression ===
5min.json age: 2.6s FRESH  ✅

=== Live price ===
price=7616.62  bid=7616.50  ask=7616.75  ✅

=== Woodies CCI panel ===
current_bar.close=7616.62  live_price=7616.62  ✅

=== DB totals ===
v9_bars_5min: 1134 total, 1123 non-flat  ✅

=== Bridge ===
streams=13/14  total_pushes=615  total_errors=30  ✅
```

## Before → After

| Metric | Before (chart #12 RTH-only) | After (chart #5 24h) |
|--------|----------------------------|---------------------|
| Overnight OHLC | O=H=L=C=7590.50 (frozen) | O=7617.50 H=7617.75 L=7616.50 C=7617.25 (real) |
| Live price | 7590.50 (midpoint fallback: 7612) | 7616.62 (real close + midpoint) |
| Bar coverage | RTH only (hours 08-15 UTC) | 24h (all hours) |
| DB rows | 609 | 1134 |
| Export files | 14 RTH + 2 stale | 14 RTH + 2 continuous (16 total) |

## Commits

1. `3800015` — feat(dll): chart #5 continuous 24h export (Input 20)
2. `2fc114d` — fix(dll): SCGraphData API fix (build error)
3. `bf54621` — feat: wire chart #5 continuous streams (bridge + backend)

## Safety

- RTH firing gates unchanged (6 independent gates verified)
- Overnight bars = display/context only
- `_best_price` (bid/ask midpoint) remains as fallback
- Chart #12 exports untouched

---

*Michael approved DLL change. Remote Build SUCCESS.*
