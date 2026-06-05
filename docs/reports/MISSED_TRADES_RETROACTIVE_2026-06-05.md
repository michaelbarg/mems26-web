# Missed-Trade Retroactive Analysis · 2026-06-05

## Market Context
- **Day type:** Normal (S1 classified, confidence 0.48)
- **Trend:** RED from open (CCI14 deeply negative, -261 at 08:45 CT)
- **IB:** EXTREME (7552.75 / 7505.75 = 47pts)
- **RTH range so far:** 7552.75 → 7485 (≈68pts selloff)
- **Trades fired:** 0

## Candidate Table (RTH 08:30–11:00 CT)

```
Time CT  Close    CCI14  Trend  Candidate Pattern        Sys  Detected?  Gate/Block Reason
──────── ──────── ────── ────── ────────────────────────  ──── ────────── ─────────────────────────
08:40    7527.50  -245   RED    HFE_SHORT_candidate       S2   signal     size=reject (location=far)
08:45    7518.50  -262   RED    HFE_SHORT_candidate       S2   signal     size=reject (location=far)
08:50    7524.25  -193   RED    [deep_selloff_no_signal]   —    —          no pattern matched
09:35    7526.00   —     —      DOUBLE_TOP_candidate      S2   structure  size=reject (location=far)
09:45    7518.00  -31    RED    ZLR_SHORT_candidate        S2   signal     size=reject (location=far)
09:50    7520.50  -26    RED    ZLR_SHORT_candidate        S2   signal     size=reject (location=far)
10:00    7519.25  -13    RED    ZLR_SHORT_candidate        S2   signal     size=reject (location=far)
10:10    7507.25  -180   RED    [deep_selloff_no_signal]   —    —          trend move, no pattern
10:15    7511.00  -163   RED    [deep_selloff_no_signal]   —    —          trend move, no pattern
10:20    7503.25  -171   RED    [deep_selloff_no_signal]   —    —          trend move, no pattern
10:35    7492.50  -154   RED    [deep_selloff_no_signal]   —    —          trend move, no pattern
10:40    7490.00  -158   RED    [deep_selloff_no_signal]   —    —          trend move, no pattern
10:55    7490.00  -97    RED    ZLR_SHORT_candidate        S2   signal     size=reject (location=far)
11:00    7485.25  -98    RED    ZLR_SHORT_candidate        S2   signal     size=reject (location=far)
```

**S2 live state confirms:** `last_pattern=DOUBLE_TOP_AA_SHORT`, `last_reasoning_notes="DOUBLE_TOP_AA SHORT size=reject: 3-bar pattern, COT=-19652 vs AMT=-16065, location=far"`

**S4 (Woodies):** `zlr_detected=0, hfe_detected=0` throughout all bars. Sierra study flags never set despite CCI conditions being present. `classification=NO_SETUP, active_patterns=[]`.

## Root Cause: Why 0 Fires

### Primary block: `location_vs_poc_vol = "far"` (S2)

`five_min_system.py:665-705` `calculate_size()`:
- `bars_formed=3` ✅
- `cot < amt` (SHORT) ✅ (COT=-19652 < AMT=-16065)
- `location="far"` ❌ → returns "reject"

The sizing function requires `location in ("at", "near")` for `half` sizing (2 contracts). With `location=far`, even valid patterns get rejected. The 1.0pt/3.0pt thresholds vs POC are very tight.

**POC from Sierra:** 7526.0 (tpo.json). Market moved to 7490 = 36pts from POC → `far`.

### Secondary: S4 Sierra study flags not set

Woodies `zlr_detected=0` and `hfe_detected=0` in all v9_bars_5min_woodies rows, despite CCI conditions (-261, RED trend) that should trigger HFE detection. This suggests the DLL's pattern detection flags are not firing or not being exported correctly.

### Auth table: NOT the blocker

`DOUBLE_TOP_AA_SHORT × Normal = FULL (3,2,2)` — auth table would ALLOW this pattern. The block is upstream in calculate_size, not in the auth table.

## Sierra Cross-Check

```
CCI14 from v9_bars_5min_woodies (Sierra source):
  08:40 CT: -245.26  (deeply bearish → HFE territory)
  08:45 CT: -261.86  (most extreme)
  09:45 CT: -30.85   (approaching zero → ZLR territory)
  10:05 CT: -101.30  (re-dive)
  10:10 CT: -179.53  (deep again)

trend_state: RED throughout (except brief GRAY at 09:40, 09:55)
```

These CCI values are consistent with a trend-down day where SHORT setups should fire.

## Summary for Michael

| Factor | Status | Impact |
|--------|--------|--------|
| Pattern detection (S2) | ✅ Working | DOUBLE_TOP_AA detected |
| Auth table (day_type) | ✅ FULL allowed | Not blocking |
| COT/AMT flow | ✅ Aligned SHORT | Not blocking |
| **POC location** | ❌ **"far" = reject** | **PRIMARY BLOCKER — 100% of candidates** |
| S4 Sierra flags | ❌ Not set | ZLR/HFE never flagged by DLL |
| choppiness_ok | ⚠️ Was stale | Fixed this session (continuous update) |

**Michael's 7 shorts were blocked by a single gate: `location_vs_poc_vol = "far"`.** The market moved 36pts from POC but the threshold is 3pts for "near". This gate is extremely tight for trend days where price runs away from POC.
