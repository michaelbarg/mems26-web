# Always-Relative Thresholds + Opening Reasoning + Block Reasons · 2026-06-01

**Date:** 2026-06-01 · **Author:** CC

---

## #1 — Thresholds Always Relative

### Converted to always-relative (flag gating removed)

| System | Threshold | Before | After |
|--------|-----------|--------|-------|
| S1 | IB width classification | Flag ON=ratio, OFF=fixed 15/25pt | **Always IB/ATR ratio** |
| S2 | Expansion range | Flag ON=1.5-2.0×ATR, OFF=1.5-1.75pt | **Always k×ATR** |
| S2 | POC return tolerance | Flag ON=0.2×ATR, OFF=0.5pt | **Always 0.2×ATR** |
| S3 | Min level volume | Flag ON=0.3×median, OFF=10 fixed | **Always 0.3×median** |

### ATR=None fallback (documented, not fixed-point)
When ATR not yet available (< 5 bars at session start):
- S1: default ATR = 20pt (MES historical)
- S2: default ATR = 3pt (5-min MES historical)
- S3: falls back to MIN_LEVEL_VOL=10 only when no footprint data

### Remaining fixed thresholds (43 total)
Most are **structural** (bar counts, CCI ±100/±200 per Woodies methodology, ratio-based thresholds that are already relative by nature). See audit in report for full table.

## #4 — Opening Reasoning in Build Status

Day Type inspector now includes `opening_reasoning` component with:
- `opening_type`: OPEN_DRIVE / OPEN_TEST_DRIVE / OPEN_REJECTION / OPEN_AUCTION_IN / etc.
- `drive_direction`: LONG/SHORT/NEUTRAL
- `confidence`: probability
- `cvd_shadow`: CVD opening analysis data (when S1_CVD_OPENING flag ON)

## #5 — Per-Pattern Block Reasons

All 5 systems now show exact block reason per pattern:

```
S2 REACTIVE_LONG         ❌ Missing: detection.b2_volume_drop
S2 INITIATIVE_LONG       ❌ Auth Table SKIP for INITIATIVE_LONG × Normal
S4 ZLR                   ❌ Stage A1 veto: trend_state=GRAY (WSI rule)
S4 HTLB                  ✅ Fired today at 13:34
S3 absorption            ❌ Insufficient buffer (0 bars, need ≥ 5)
S1 day_type_current      ✅ Classification COMPLETE: Normal (p=0.68)
```

### New: S3 Footprint Inspector
Created `footprint_inspector.py` with 4 detector statuses: Absorption, Stacked Imbalance, Sweep Return, Exhaustion. Each shows buffer size, bars processed today, and detection status.

## Commits

1. `50609ad` — IB width always-ratio
2. `0b298f3` — S2/S3 always-relative, flag gating removed
3. `8c6b0b4` — opening reasoning + S3 inspector + block reasons

---

*k-values (ratio multipliers) remain unchanged — to be calibrated post-SHADOW soak.*
