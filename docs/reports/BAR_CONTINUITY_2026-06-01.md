# BAR CONTINUITY — Diagnosis + Fix · 2026-06-01

**Date:** 2026-06-01 12:45 IL (05:45 ET) · **Author:** CC
**Based on:** Michael: "the candles aren't continuous, need to fix" + stuck live price at 7590.50

---

## Step 0 — Stuck Live Price (FIXED)

### Root Cause
DLL writes `price = sc.Close[idx]` (chart bar close, tied to RTH session). During overnight, `sc.Close` freezes at last RTH close (7590.50) while `sc.Bid`/`sc.Ask` update in real-time (7612.50/7612.75).

### Evidence
```
live_price.json: {"price":7590.50, "bid":7612.50, "ask":7612.75}  ← 22pt divergence
DLL source: sc_study/MES_AI_DataExport.cpp:133 → cp = sc.Close[idx]
            sc_study/MES_AI_DataExport.cpp:173 → "price":cp, "bid":sc.Bid, "ask":sc.Ask
```

### Fix
`backend/v9/api/v9/price_routes.py`: Added `_best_price()` — uses bid/ask midpoint when chart close diverges >2pt from midpoint. Applied to both POST (cache+broadcast) and GET (file fallback).

```
Before: price=7590.50 (stale sc.Close)
After:  price=7612.12 (bid/ask midpoint)
```

---

## Step 1 — Gap Map (Diagnosis)

### v9_bars_5min (10 bars in 48h window)
| Gap | From → To | Slots Missing | Root Cause |
|-----|-----------|---------------|-----------|
| 1 | 00:45 → 07:30 UTC | ~80 | Backend was down (no LaunchAgent, fixed in prior session) |
| 2 | 07:35 → 08:50 UTC | ~14 | Backend restart gap |
| — | 08:50-09:20 UTC | 7 flat bars | FiveMinAggregator producing O=H=L=C=7590.5 from stale sc.Close |

### v9_bars_5min_woodies (1019 bars in 48h — 100× better coverage)
| Gap | From → To | Slots Missing | Root Cause |
|-----|-----------|---------------|-----------|
| 1-5 | Various May 31 gaps | ~58 total | Backend instability/restarts on May 31 |
| 6 | May 31 18:59 → Jun 1 07:35 | ~150 | Backend dead overnight (fixed with LaunchAgent) |
| 7 | 07:38 → 08:53 | ~14 | Backend restart gap |

### Critical finding: WoodiesSystem._persist_bar duplication
**Root cause of the duplication bug:** `woodies_system.py:507` used `datetime.now(timezone.utc).isoformat()` as the ts — every push (every ~3s) created a unique row, bypassing the UNIQUE constraint.

Two write paths existed:
1. `bars.py` POST handler: `bar.get("ts")` (DLL's bar ts) ✅
2. `WoodiesSystem._persist_bar`: `datetime.now()` (push time) ❌ → 20-30× duplication

### Classification
| Issue | Type | Status |
|-------|------|--------|
| Backend downtime gaps | **Fixed** (LaunchAgent in prior session) | No backfill possible for past gaps |
| Flat stale bars (O=H=L=C=7590.5) | **BUG** (sc.Close frozen overnight) | Cleaned + filtered |
| WoodiesSystem persist duplication | **BUG** (datetime.now vs bar ts) | Fixed → INSERT OR REPLACE with bar's ts |
| RTH-only 5min.json export | **GAP-IN-SPEC** (Sierra chart config) | Mitigated: chart merges both tables |
| Maintenance 17-18 ET gap | **Expected** (CME closed) | No fill — honest gap |

---

## Step 2 — Fixes Applied

### 2a. Live price: bid/ask midpoint
**File:** `backend/v9/api/v9/price_routes.py`
- `_best_price(chart_price, bid, ask)` → uses midpoint when divergence > 2pt
- Applied to POST cache, WS broadcast, GET file fallback

### 2b. WoodiesSystem persist dedup
**File:** `backend/v9/systems/woodies/woodies_system.py:496-518`
- Changed `datetime.now()` → `str(ts)` (bar's actual timestamp from DLL)
- Changed `INSERT` → `INSERT OR REPLACE`
- Added `symbol='MES'` to column list

### 2c. Chart endpoint merges both tables
**File:** `backend/v9/api/v9/bars_5min_history.py:20-74`
- `_fetch_bars_5min()` now queries both `v9_bars_5min` AND `v9_bars_5min_woodies`
- Merges by timestamp (primary wins, woodies fills gaps)
- Filters flat stale bars (O=H=L=C with volume > 10k)

### 2d. Flat stale bars cleaned
- Deleted 8 flat bars from `v9_bars_5min` (O=H=L=C=7590.5, V > 10k)
- Deleted 1,247 ISO-timestamp duplicates from `v9_bars_5min_woodies`

### 2e. DB state post-fix
```
v9_bars_5min:         605 real bars (0 flat)
v9_bars_5min_woodies: 301 unique bars (0 duplicates)
Chart endpoint:       merges both, returns continuous series
Live price:           7612.12 (bid/ask midpoint, not stale 7590.50)
```

---

## Verification

```bash
# Live price — not stale
curl localhost:8000/api/v9/live_price → price=7612.12 ✅

# Chart bars — real prices, no flat stale bars
curl localhost:8000/api/v9/chart/bars5min?limit=5
  2026-05-29 20:50  C=7591.0 ✅ (real bar)
  2026-05-29 20:55  C=7590.5 ✅ (real bar, non-flat OHLC)
  2026-06-01 00:45  C=7611.75 ✅ (overnight bar)
  2026-06-01 07:30  C=7613.25 ✅ (overnight bar)
  2026-06-01 07:35  C=7613.25 ✅

# Woodies dedup — zero duplication
v9_bars_5min_woodies: 301 total, 301 distinct ts ✅

# No flat bars in chart
grep "filtered.*stale" /tmp/backend.err.log → filters active ✅
```

### Safety: RTH gates verified (from prior session)
6 independent gates block firing on overnight/historical data. Unchanged.

### Remaining gaps (cannot be filled — no data existed)
- Weekend May 30-31: market closed
- Overnight Jun 1 00:45→07:30: backend was down, data not captured
- Maintenance 17-18 ET: market closed daily

These are honest gaps — no synthesis per CLAUDE.md §Rule 1.

---

*Zero order/risk/sizing/polling changes.*
