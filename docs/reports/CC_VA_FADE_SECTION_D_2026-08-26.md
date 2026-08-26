# §D VA_FADE — 26 Variation Days · 2026-08-26

## Verdict: **NEGATIVE — VA_FADE stays OFF**

## Numbers

| Metric | Value |
|--------|-------|
| Sessions | 26 (21 OK, 5 NOT_JUDGEABLE) |
| Total candidates | 35 (1.35/day) |
| Total P&L | **-$1,316.25** |
| Median/day | **-$31.88** |
| Days positive | 9/26 (35%) |
| Worst day | -$292.50 |

## Per-Day Detail

| Date | Candidates | P&L | Quality |
|------|-----------|-----|---------|
| 07-07 | 2 | +$101.25 | OK |
| 07-09 | 1 | -$116.25 | OK |
| 07-13 | 1 | -$183.75 | OK |
| 07-14 | 2 | -$82.50 | OK |
| 07-15 | 2 | +$30.00 | NJ |
| 07-16 | 0 | $0.00 | NJ |
| 07-17 | 1 | -$183.75 | OK |
| 07-20 | 2 | +$67.50 | OK |
| 07-21 | 0 | $0.00 | NJ |
| 07-22 | 2 | +$116.25 | NJ |
| 07-23 | 1 | -$183.75 | OK |
| 07-24 | 2 | -$228.75 | OK |
| 07-27 | 2 | -$288.75 | OK |
| 07-28 | 1 | -$90.00 | NJ |
| 07-29 | 2 | +$33.75 | OK |
| 07-30 | 2 | -$292.50 | OK |
| 07-31 | 1 | +$71.25 | OK |
| 08-03 | 1 | -$75.00 | OK |
| 08-06 | 1 | -$168.75 | OK |
| 08-11 | 1 | +$97.50 | OK |
| 08-14 | 1 | -$56.25 | OK |
| 08-18 | 0 | $0.00 | OK |
| 08-19 | 2 | -$7.50 | OK |
| 08-20 | 2 | +$172.50 | OK |
| 08-21 | 1 | +$41.25 | OK |
| 08-25 | 2 | -$90.00 | OK |

## 25.08 Anchor Analysis

**2/4 rotations detected** (LONG@10:35 + SHORT@12:30). Rotations 3+4 (13:25 LONG,
14:50 SHORT) exist in the data but are blocked by `already_fired` per-side-per-session.

Fix: re-arm after stop-out. The 10:35 LONG stopped out → should re-arm the LONG side
for the 13:25 rotation. This is a YAML parameter (`rearm_after_stop: true`).

## Calibration Proposal (YAML, not code)

```yaml
va_fade:
  edge_zone_pts: 2.0        # current; try 1.5 for tighter quality
  close_pos_threshold: 0.33  # NEW: rejection bar close in outer 33% (was 50%)
  rearm_after_stop: true     # NEW: re-arm the side after a stop-out
  stop_offset_pts: 2.0       # was 1.5; more room for the trade
```

The core issue is **win rate (~35%)**. The edge detection finds real rotations, but the
entry timing (rejection bar = first probe) is too early. This is the same finding as the
extreme detection audit (83-88% reversal rate but entry too early → MAE eats MFE).

## Conclusion

VA_FADE as-is is **negative**. The detector works (finds real rotations at VA edges),
but the entry mechanics need refinement:
1. Require stronger rejection (close in outer 33%, not 50%)
2. Re-arm after stop-out (captures multi-rotation days like 25.08)
3. Wider stop (2.0pt offset instead of 1.5pt)

**VA_FADE stays OFF until calibration fixes are tested and §D turns positive.**

*cc-macbook · 2026-08-26*
