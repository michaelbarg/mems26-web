# P1-3 Diagnosis: S1 Staging & Reclassification — 2026-06-10

**Date:** 2026-06-11  
**Status:** DIAGNOSIS COMPLETE — 3 root causes identified, 2 actionable  
**Severity:** Medium (S1 classified day as Variation; Michael expected Trend_Normal)

---

## 1. Executive Summary

On 2026-06-10, S1 classified the day as **Variation** (via OPEN_AUCTION_IN × IB).
Michael expected **Trend_Normal** based on the session's trending behavior.
Three root causes explain the gap:

1. **CVD override flipped opening type** from OPEN_REJECTION_REVERSE → OPEN_AUCTION_IN
2. **Shadow reclassifier thresholds too high** — E_dom=0.77 triggered Normal→Variation but Trend_Normal requires E_dom ≥ 1.0 + R ≥ 2.0
3. **Mid-session restart contaminated IB** — ib_w jumped from 23.25 → 69.5 (session range, not locked IB)

---

## 2. Evidence Trail

### 2.1 Actual S1 state (v9_day_type_state, Postgres)

| Field | Value |
|---|---|
| opening_type | OPEN_AUCTION_IN |
| day_type | Variation |
| confidence | 0.48 |
| stage | B2 |
| lock_state | LOCKED_LOW_CONF |

### 2.2 Opening bars (09:30–09:40 ET, from v9_bars_5min)

| Bar | Open | High | Low | Close | Direction |
|---|---|---|---|---|---|
| 09:30 | 7355.00 | 7360.25 | 7338.25 | 7338.25 | BEARISH (-16.75) |
| 09:35 | 7338.50 | 7373.25 | 7335.25 | 7366.50 | BULLISH (+28.00) |
| 09:40 | 7366.25 | 7382.50 | 7353.00 | 7382.00 | BULLISH (+15.75) |

**Net move:** +27 pts (7382 - 7355). **Total range:** 47.25 pts. **Directional ratio:** 0.571.

### 2.3 Price-based detection trace (detector.py:detect_opening_type)

1. **OPEN_DRIVE check (L159-164):** `all_up` = False (bar1 bearish) → **FAIL**
2. **OTD check (L167-179):** pullback_ratio = 28.25/16.75 = 1.69 (> 0.6 max) → **FAIL**
3. **ORR check (L182-190):** first_move = -16.75, last_move = +27, reversed = True, |27| ≥ 8.375 → **MATCH** → `OPEN_REJECTION_REVERSE UP, conf=0.65`

**Price-based result: ORR.** This is correct — bar1 sold off, bar2-3 reversed and drove higher.

### 2.4 CVD override (detector.py:detect_opening_type_cvd)

`S1_CVD_OPENING` flag is **ON**. The CVD path computed:
- Bar1 delta proxy: sign(-16.75) × volume ≈ negative (sell)
- Bar2-3 delta proxy: positive (buy)
- Net CVD nearly balanced (sell + buy cancel), net_cvd_ratio < 0.15
- PE (participation efficiency) < 0.25

**CVD condition at L323 matched: AUCTION** → overrides ORR → returns `OPEN_AUCTION_IN`

### 2.5 Decision matrix lookup

`OPEN_AUCTION_IN × MEDIUM → Normal` (decision_matrix.py L52)  
`OPEN_AUCTION_IN × WIDE → Normal` (decision_matrix.py L53)

### 2.6 Shadow reclassifier transitions (v9_day_type_shadow_transitions)

| session_min | from | to | E_up | E_dn | R | ib_w |
|---|---|---|---|---|---|---|
| 60 (10:30 ET) | Normal | Variation | 0.77 | 0.00 | 0.74 | 23.25 |
| 110 (11:20 ET) | Normal | Variation | 0.00 | 0.21 | 0.46 | **69.5** |
| 130 (11:40 ET) | Normal | Variation | 0.00 | 0.20 | 0.35 | **69.5** |

**Anomaly:** ib_w changed from 23.25 to 69.5 at session_min=110. The IB (7386.75-7363.5 = 23.25) at lock time was correct. But entries 32-33 show IB 7404.75-7335.25 = 69.5, which is the **session range**, not the locked IB. This indicates the uvicorn process restarted mid-session, and `maybe_seed_ib_from_tpo` seeded the machine with corrupted (session-wide) IB values.

### 2.7 Why shadow didn't reach Trend_Normal

Shadow reclassifier thresholds (shadow_reclass.py L28-31):
- **Variation:** E_dom ≥ 0.15 ✅ (0.77 achieved)
- **Trend_Normal:** E_dom ≥ 1.0 **AND** R ≥ 2.0 ❌

With correct IB (23.25 pts), E_up=0.77 at session_min=60. The session high eventually reached 7404.75, giving E_up = (7404.75 - 7386.75) / 23.25 = 0.77. For Trend_Normal, price would need to extend 1.0 × 23.25 = 23.25 pts above IB_H = 7410 (it reached 7404.75 — close but not enough).

After restart with contaminated IB (69.5 pts), the extension ratios became tiny (E_dn=0.21), so Trend_Normal was impossible.

---

## 3. Root Causes

### RC-1: CVD override produces wrong opening type (HIGH impact)

**What:** `S1_CVD_OPENING` flag ON causes CVD analysis to override price-based ORR → AUCTION_IN. The CVD sees balanced flow (bar1 sell, bar2-3 buy → net near zero), but price clearly reversed and drove higher.

**Why it matters:** AUCTION_IN × any_IB_width → Normal. ORR × WIDE → Normal too, so in this specific case both paths lead to Normal. But ORR × NARROW → Variation, which is closer. The CVD override fundamentally misclassifies the opening character.

**Fix:** Either (a) disable CVD override for ORR detections (price reversal is a structural signal CVD shouldn't override), or (b) raise the AUCTION threshold so a 27pt directional move isn't called "balanced."

### RC-2: Shadow reclassifier IB contaminated by mid-session restart (HIGH impact)

**What:** The `_shadow_reclass["instance"]` is set to `None` on restart. The machine's `ib_high`/`ib_low` after TPO seed reflects session extremes, not locked IB. New ShadowReclassifier gets initialized with ib_w=69.5 instead of 23.25.

**Why it matters:** With a 69.5-point "IB", extension ratios are ~3× smaller than reality. Variation threshold (0.15) barely triggers, Trend_Normal (1.0) is unreachable.

**Fix:** Persist the locked IB values in `v9_day_type_state` or a dedicated table, and on restart, read locked IB from DB instead of from the machine's current (potentially re-seeded) values.

### RC-3: Trend_Normal threshold may be too strict (MEDIUM impact)

**What:** E_dom ≥ 1.0 AND R ≥ 2.0 for Trend_Normal means price must extend a full IB width beyond IB_H/IB_L AND total range must be ≥ 2× IB. On a day with IB=23.25, that requires a 46.5+ pt range and 23+ pt extension.

**Why it matters:** The 06-10 session high was 7404.75 vs IB_H=7386.75, giving 18 pts extension (E=0.77). The day was directional but the initial rally was moderate. The shadow correctly said Variation, not Trend.

**Assessment:** This threshold is defensible per Dalton. The real issue is RC-1 (wrong opening type) + RC-2 (contaminated IB), not the threshold itself.

---

## 4. Recommended Actions

| # | Action | Priority | Risk |
|---|---|---|---|
| 1 | **Persist locked IB to DB** — on `ib_locked=True`, write `(session_date, ib_high, ib_low)` to a `v9_s1_locked_ib` table. On restart, read from there instead of from the (re-seeded) machine. | P1 | Low — additive |
| 2 | **Guard ShadowReclassifier init** — check if locked IB already exists in DB before using machine's current values. | P1 | Low |
| 3 | **Review S1_CVD_OPENING** — the CVD override is a shadow feature (E2E 2/2) that was promoted to live path. Consider reverting to shadow-only until CVD PE/ratio thresholds are calibrated against ≥20 sessions. | P2 | Medium — needs Michael decision |
| 4 | **Add ORR exemption** — when price-based detection is ORR (clear reversal), CVD balanced-flow shouldn't override to AUCTION. The reversal structure is price-based, CVD adds confirmation but shouldn't negate it. | P2 | Medium — changes classification |

---

## 5. Comparison: 06-09 vs 06-10

| Dimension | 06-09 | 06-10 |
|---|---|---|
| Opening type (DB) | OPEN_DRIVE | OPEN_AUCTION_IN |
| First 3 bars | Flat → Up → Up | Down → Up → Up |
| Day type (DB) | Trend_Normal → Variation | Variation |
| Session character | Massive selloff (-244 pts) | Moderate uptrend |
| S1 accuracy | Poor — OPEN_DRIVE (up) but day sold off hard | Fair — Variation reasonable, Trend_Normal debatable |

**06-09 note:** Opening bars suggested upward drive (OPEN_DRIVE), but the session reversed into a massive Trend Day DOWN. The opening type detection worked per-spec (first 10 min were indeed driving up), but the day completely reversed. Shadow reclassifier should have caught this via E_dn extension. Day type eventually changed to Variation at 14:57 ET.

---

## 6. Verification Commands

```sql
-- 06-10 S1 state
SELECT ts, day_type, opening_type, confidence, stage, lock_state
FROM v9_day_type_state WHERE ts::date = '2026-06-10' ORDER BY ts DESC LIMIT 5;

-- 06-10 shadow transitions
SELECT session_min, from_type, to_type, e_up, e_dn, r_total, ib_w
FROM v9_day_type_shadow_transitions WHERE session_date = '2026-06-10' ORDER BY ts;

-- 06-10 opening bars
SELECT ts, open, high, low, close FROM v9_bars_5min
WHERE ts >= '2026-06-10 13:30:00+00' AND ts <= '2026-06-10 13:45:00+00' ORDER BY ts;
```
