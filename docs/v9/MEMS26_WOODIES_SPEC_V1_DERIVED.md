# MEMS26 — Woodies CCI System (System 4) — Specification V1

## V1.0 · 2026-05-10 · DERIVED from DLL + audit (no separate spec existed)
## Status: DERIVED — per §6.5 auto-resolution

---

## SECTION 1 — IDENTITY

Component ID: WOODIES_CCI_ENGINE
Component Name: Woodies CCI Pattern Detection & Firing Engine
Type: FIRING System (executes trades)
Category: Independent Firing System (parallel)
Color: #fb950b (orange)
System ID: 4

---

## SECTION 2 — ROLE

System 4 is an independent FIRING system that:

1. Receives 30-minute synthetic Woodies bars from DLL (via bridge)
2. Computes 11 CCI-based studies per bar
3. Detects 8 Woodies CCI patterns (4 continuation + 4 reversal)
4. Classifies setups and fires trades independently
5. Does NOT depend on any other system's signals

---

## SECTION 3 — INPUTS

From Sierra Chart DLL (sole source):
- File: `woodies_30min.json`
- Bar period: 30 minutes (10 × 3-min chart bars aggregated)
- Configurable history depth via Input[8] (default: 50 bars)

---

## SECTION 4 — 11 CCI STUDIES (from DLL)

All computed in `v9_woodies_export.h`:

| # | Study | Field | Formula |
|---|-------|-------|---------|
| 1 | CCI-14 (main) | `cci_14` | Standard CCI, period 14 |
| 2 | CCI-6 / TCCI (turbo) | `cci_6_tcci` | Standard CCI, period 6 |
| 3 | EMA-34 | `ema_34` | Exponential MA, period 34 |
| 4 | LSMA-25 | `lsma_value` | Least Squares MA, period 25 |
| 5 | LSMA above price | `lsma_above_price` | bool: LSMA > close |
| 6 | Sidewinder (SWI) | `swi_value` | CCI(14) - CCI(14)[3 bars ago] |
| 7 | ChopZone (CZI) | `czi_value` | (close - EMA) / ATR × 100 |
| 8 | Trend State | `trend_state` | "BLUE" / "RED" / "GRAY" / "YELLOW" |
| 9 | CCI Predictor | `predictor_next_cci` | CCI + (CCI - prev_CCI) |
| 10 | ZLR Detected | `zlr_detected` | bool: Zero Line Reject found |
| 11 | ZLR Direction | `zlr_direction` | "UP" / "DOWN" / "NONE" |

### Trend State Logic (from DLL):
- **BLUE**: CCI > 50 AND prev CCI > 0 AND SWI > 20 (uptrend)
- **RED**: CCI < -50 AND prev CCI < 0 AND SWI < -20 (downtrend)
- **YELLOW**: CCI crossed zero recently (transition)
- **GRAY**: choppy / no clear trend

### ZLR Detection Logic (from DLL, 12-bar lookback):
- **ZLR UP**: CCI was > +100, pulled back toward 0 (stays > -50), bounces up
- **ZLR DOWN**: CCI was < -100, pulled back toward 0 (stays < +50), drops

---

## SECTION 5 — 8 PATTERNS

### Group A: Continuation (4)

| # | Pattern | Detection Method |
|---|---------|-----------------|
| A1 | **ZLR** (Zero Line Reject) | `zlr_detected` + `zlr_direction` (native in DLL) |
| A2 | **TLB** (Trend Line Break) | CCI-14 slope analysis over history array |
| A3 | **TT** (Turbo Touch) | `cci_6_tcci` crosses `cci_14` (crossover detection) |
| A4 | **GB100** (Ghost Break 100) | CCI-14 crossing ±100 line with confirming `trend_state` |

### Group B: Reversal (4)

| # | Pattern | Detection Method |
|---|---------|-----------------|
| B1 | **VEGAS** | CCI-14 double divergence vs price (cci_14 + ohlc history) |
| B2 | **GHOST** | CCI-14 HH/HL vs price HL/HH divergence (cci_14 + ohlc history) |
| B3 | **FAMIR** | CCI-14 fails to reach ±200 on retest (cci_14 history) |
| B4 | **HTLB** (Horizontal TLB) | CCI-14 breaking horizontal support/resistance (cci_14 history) |

All 8 patterns detectable from exported data per woodies_audit.md.

---

## SECTION 6 — JSON EXPORT CONTRACT

### File: `v9_export/woodies_30min.json`

```json
{
  "type": "woodies_30min",
  "version": "v9.x.x",
  "export_ts": 1715270400,
  "bar_period_minutes": 30,
  "total_bars": 50,
  "history": [
    {
      "ts": 1715270400,
      "ohlc": { "o": 5246.50, "h": 5248.25, "l": 5245.00, "c": 5247.75, "vol": 12340 },
      "cci_14": 87.5,
      "cci_6_tcci": 112.3,
      "lsma_value": 5247.10,
      "lsma_above_price": false,
      "swi_value": 42.1,
      "czi_value": 65.3,
      "ema_34": 5246.80,
      "trend_state": "BLUE",
      "predictor_next_cci": 105.2,
      "zlr_detected": true,
      "zlr_direction": "UP"
    }
  ],
  "current_bar": {
    "...same fields...",
    "cci_14_prev": 75.3,
    "cci_14_3ago": 45.1
  }
}
```

### Notes:
- `current_bar` has 2 extra fields: `cci_14_prev` and `cci_14_3ago`
- `history` array ordered oldest→newest
- OHLC nested under `ohlc` key (not flat)

---

## SECTION 7 — DB STORAGE

Table: `v9_bars_30min_woodies`
Model: `V9Bar30MinWoodies`

Columns match JSON fields: `ts`, `open`, `high`, `low`, `close`, `volume`,
`cci_14`, `cci_6_tcci`, `lsma_value`, `swi_value`, `czi_value`, `ema_34`,
`trend_state`, `predictor_next_cci`, `zlr_detected`, `zlr_direction`

---

## SECTION 8 — API

- **POST** `/api/v9/bars/woodies` — bridge push (ingestion)
- **GET** `/api/v9/bars/woodies?limit=50` — read recent bars
- Auth: `BRIDGE_TOKEN` (Bearer)

---

## SECTION 9 — WHAT THIS DOES NOT DO

❌ Does not depend on System 1 (Day Type)
❌ Does not depend on System 2 (5-Min Chart)
❌ Does not depend on System 3 (Footprint)
❌ Does not gate on System 6 (Killzone)
❌ Does not compute its own CCI — receives pre-computed from DLL

---

## SECTION 10 — DLL IMPLEMENTATION DETAILS

Source: `sc_study/v9_woodies_export.h` (280 lines)

### Key Functions:
- `v9_build_30min_bars()` — aggregates 3-min chart bars into 30-min synthetic
- `v9_calc_cci()` — standard CCI: (TP - SMA(TP,n)) / (0.015 × MeanDev)
- `v9_calc_ema()` — EMA with 3×period warmup
- `v9_calc_lsma()` — least squares regression (predict at last point)
- `v9_calc_sidewinder()` — CCI[0] - CCI[-3]
- `v9_calc_chopzone()` — (close - EMA) / ATR × 100
- `v9_woodies_trend_state()` — BLUE/RED/GRAY/YELLOW classification
- `v9_cci_predictor()` — linear extrapolation: CCI + (CCI - prev)
- `v9_detect_zlr()` — 12-bar lookback for Zero Line Reject
- `v9_woodies_30min_to_json()` — master export function

### Performance:
- ACSIL-safe: uses `v9_max/v9_min/v9_abs` (no std::max/min macros)
- Header-only (no separate .cpp)
- Pre-allocated vectors with `.reserve()`
- Single ostringstream for JSON (pre-sized)

---

*DERIVED spec — auto-generated from `docs/v9/woodies_audit.md` + `sc_study/v9_woodies_export.h` per §6.5.*
