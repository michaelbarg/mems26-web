# Woodies CCI Export Audit — W1.5

## Audit Date: 9.5.26
## DLL Version: v9.0.0

## Pre-Audit State

The DLL (v3.0) had **only Woodies Pivots** (PP/R1/R2/S1/S2) — price-level support/resistance calculations. None of the 11 CCI studies required for pattern recognition existed.

## Required vs Found vs Added

| # | Study | Required | Pre-Audit | Post-Audit | Notes |
|---|-------|----------|-----------|------------|-------|
| 1 | WoodieCCITrend2 (trend state) | ✅ | ❌ Missing | ✅ Added | BLUE/RED/GRAY/YELLOW |
| 2 | CCI 14 (main line) | ✅ | ❌ Missing | ✅ Added | Standard CCI formula |
| 3 | CCI 6 / TCCI (turbo) | ✅ | ❌ Missing | ✅ Added | Same formula, period=6 |
| 4 | LSMAAboveBelow | ✅ | ❌ Missing | ✅ Added | LSMA-25 + above/below price flag |
| 5 | Sidewinder (SWI) | ✅ | ❌ Missing | ✅ Added | CCI momentum (current - 3 bars ago) |
| 6 | ChopZone (CZI) | ✅ | ❌ Missing | ✅ Added | Price-EMA distance / ATR × 100 |
| 7 | WoodiesPanel (composite) | ✅ | ❌ Missing | ✅ Added | All values in single JSON object |
| 8 | CCIPredictor | ✅ | ❌ Missing | ✅ Added | Linear extrapolation: CCI + (CCI - prev) |
| 9 | WoodiesZLR | ✅ | ❌ Missing | ✅ Added | 12-bar lookback, UP/DOWN detection |
| 10 | WoodiesEMA (EMA 34) | ✅ | ❌ Missing | ✅ Added | Standard EMA |
| 11 | LSMA (panel) | ✅ | ❌ Missing | ✅ Added | Least Squares MA, period 25 |
| — | Woodies Pivots (PP/R/S) | bonus | ✅ Existed | ✅ Kept | Unchanged from v3.0 |

**Result: 0/11 existed → 11/11 added. Plus pivots retained.**

## Bar Timeframe

- Chart: 3-minute bars (underlying Sierra Chart)
- Export: 30-minute synthetic bars (10 chart bars aggregated)
- Configurable via Input[8] "V9 Woodies 30min History Bars" (default: 50)

## Pattern Detection Capability

| Group | Pattern | Data Fields Used | Detectable? |
|-------|---------|-----------------|-------------|
| A (Cont.) | ZLR (Zero Line Reject) | `zlr_detected`, `zlr_direction`, `cci_14` history | ✅ Native detection |
| A (Cont.) | TLB (Trend Line Break) | `cci_14` history (slope analysis) | ✅ From history array |
| A (Cont.) | TT (Turbo CCI Touch) | `cci_6_tcci` vs `cci_14` crossover | ✅ From history array |
| A (Cont.) | GB100 (Ghost Break 100) | `cci_14` crossing ±100 with trend_state | ✅ From history array |
| B (Rev.) | VEGAS | `cci_14` double divergence vs price | ✅ cci_14 + ohlc history |
| B (Rev.) | GHOST | `cci_14` HH/HL vs price HL/HH divergence | ✅ cci_14 + ohlc history |
| B (Rev.) | FAMIR | `cci_14` fails to reach ±200 on retest | ✅ cci_14 history |
| B (Rev.) | HTLB (Horizontal TLB) | `cci_14` breaking horizontal support/resistance | ✅ cci_14 history |

**All 8 patterns can be detected from the exported data.**

## JSON Output

File: `v9_export/woodies_30min.json`

### Per-bar fields (11 studies + 4 derived):
```
cci_14              — CCI period 14 (main indicator)
cci_6_tcci          — Turbo CCI period 6
lsma_value          — LSMA period 25
lsma_above_price    — bool: LSMA > price
swi_value           — Sidewinder momentum
czi_value           — ChopZone angle
ema_34              — EMA period 34
trend_state         — "BLUE"|"RED"|"GRAY"|"YELLOW"
predictor_next_cci  — Predicted next CCI value
zlr_detected        — bool: ZLR pattern found
zlr_direction       — "UP"|"DOWN"|"NONE"
ohlc.o/h/l/c/vol    — 30-min OHLCV
ts                  — Unix timestamp
```

### current_bar extras:
```
cci_14_prev         — Previous bar CCI-14
cci_14_3ago         — CCI-14 from 3 bars ago (for SWI calculation)
```

## Files Created/Modified

| File | Action |
|------|--------|
| `sc_study/v9_woodies_export.h` | **NEW** — 280 lines, all Woodies calculations + JSON export |
| `sc_study/MES_AI_DataExport.cpp` | Modified — added include, Input[8], export call |
| `docs/v9/woodies_audit.md` | **NEW** — this file |

## ACSIL Compliance
- ✅ `v9_max/v9_min/v9_abs` used (no std::max/min)
- ✅ No `SCT_OSC_REJECTED` (doesn't exist in ACSIL)
- ✅ Header-only implementation (no separate .cpp)
- ✅ All math is inline, no external dependencies
