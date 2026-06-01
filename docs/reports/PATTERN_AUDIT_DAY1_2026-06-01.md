# Pattern Audit Day 1 — Why S2/S4 Didn't Fire · 2026-06-01

**Date:** 2026-06-01 RTH · **Author:** CC
**Data:** 55 bars, 146 trades (S2=0, S3=142, S4=4)

---

## S2 Five-Min — 0 Fires (10 patterns)

### REACTIVE (CRITICAL — blocks EVERY day)
**ROOT CAUSE:** `DROP_THRESHOLD_PCT = 0.10` (90% volume drop) is **physically impossible** in MES 5min.
- Today's minimum b2/b1 ratio: **0.1201** (88% drop — close but fails)
- **Zero** pairs with ≤ 10% ratio out of 54
- With 50% threshold: **11 opportunities**
- **FIX:** `0.10 → 0.50` — strategic-stop, needs Michael approval

### INITIATIVE (by spec)
**ROOT CAUSE:** Auth Table SKIP for Normal day. D-091 allows Initiative on TN/TDD/NV only.
- Not a bug — spec decision.

### H&S / Double Top / Flags (legitimate)
- H&S: 7 swing highs, 5 swing lows — but no symmetric triplet formed
- Double Top: peaks at 7632/7629 (0% diff) but price ABOVE neckline (7599) — no breakout
- Flags: longest bull run 4 bars (need 5) — no valid pole

---

## S4 Woodies — 4 Fires (HTLB only)

### Trend: BLUE 140min, RED 50min, GRAY 55min
Choppy day — trend switched 7 times.

### DLL Detections vs System
| Pattern | DLL Detected | System Fired | Gap |
|---------|-------------|-------------|-----|
| ZLR | 9 bars ★ | 0 | **DLL flags weren't passed** (FIXED 730f913) |
| HFE | 16 bars ★ | 0 | Blocked by GRAY trend (P-W5) |
| HTLB | yes | 4 trades ✅ | Working |
| Others | 0 | 0 | Conditions not met (legitimate) |

### Fixes Applied Today
- ✅ DLL flags pass-through (730f913)
- ✅ DLL trust as primary source (58d6538)

---

## Recommendations (needs Michael approval)

| # | Fix | Impact | Type |
|---|-----|--------|------|
| **1** | `DROP_THRESHOLD_PCT 0.10 → 0.50` | Reactive will fire (~10 opps/day) | **CRITICAL — priors change** |
| 2 | P-W5: allow HFE in GRAY? | 16 detections today blocked | Spec decision |
| 3 | Initiative on Normal? | Auth Table change | Spec decision |
| 4 | ZLR/HFE DLL trust | ✅ Done | — |

---

*S3 Footprint fired 142 trades — proof the pipeline works. S2's zero fires is a threshold bug, not a pipeline bug.*
