# D-WDIAG: Woodies ZLR/HFE/Trend Audit · 2026-06-01

**Decision tag:** `D-WDIAG` · **Status:** 🟢 IMPLEMENTED

---

## Audit Results (Raw Evidence)

### ZLR — DLL and Python AGREE ✅
```
73/73 DLL ZLR detections had confirmed bounce (current > prev)
0 pullback-only detections
```
**Finding:** DLL DOES require bounce. Commit `58d6538` (DLL trust) is CORRECT — it doesn't add pullback-only entries. No change needed.

### Gray Classifier — BUG CONFIRMED ⚠️
```
6 bars with |CCI| ≥ 200 classified as GRAY:
  CCI=331.01 → GRAY ❌ (extreme upward momentum)
  CCI=254.62 → GRAY ❌
  CCI=226.58 → GRAY ❌
  CCI=225.73 → GRAY ❌
  CCI=-257.55 → YELLOW ❌
```
**Root cause:** Sierra's trend classifier has transition lag — first bars crossing +100 from opposite side are GRAY before 6-bar persistence. But |CCI|≥200 = undeniable strong momentum.

**Fix applied:** Override GRAY/YELLOW → BLUE/RED when |CCI|≥200. (commit `1c0397a`)

### HFE — Already Correct ✅
```
HFE detections: 75 total
  BLUE: 46 (61%) — would fire ✅
  GRAY: 18 (24%) — blocked by P-W5 (now partially unblocked for ±200)
  RED: 8 (11%) — would fire ✅
  YELLOW: 3 (4%) — blocked by P-W5
```
HFE already `low` tier in `PATTERN_TIER`. Counter-trend by nature. No change needed.

## Decisions Implemented

| Decision | Option | Implemented | Commit |
|----------|--------|-------------|--------|
| ZLR bounce | N/A (DLL already correct) | ✅ No change needed | — |
| HFE tier | Keep low-tier | ✅ Already correct | — |
| Gray classifier | Override ±200 bars | ✅ | `1c0397a` |

---

*D-WDIAG complete. Michael approved gray classifier fix 2026-06-01.*
