# D-S1DYN: IB-Relative Dynamic Day-Type Reclassification · 2026-06-01

**Decision tag:** `D-S1DYN` · **Status:** 🟢 IMPLEMENTED-SHADOW (Phase 0-2)
**Stage 3 (live gating):** OUT OF SCOPE — requires Michael approval

---

## Phase 0 — Diagnosis (4 confirmed points)

| # | Finding | Confirmed | Evidence |
|---|---------|-----------|----------|
| 1 | C1 locks at conf≥0.85 / 2 votes / session≥210min | ✅ | `schemas.py:10`, `state_machine.py:742` |
| 2a | `move_30=None` hardcoded — direction trigger dead | ✅ | `state_machine.py:783` |
| 2b | `bar.atr=None` (no atr column in DB) — range trigger dead | ✅ | `PRAGMA table_info(v9_bars_5min)` |
| 3 | rescore uses behavior/range, NOT IB-extension | ✅ | `_rescore_from_behavior:660` |
| 4 | Today: Normal p=0.68, E_up=1.77, R=2.77 → should be Trend | ✅ | DB + systems-snapshot |

## Phase 1 — Shadow Log (commit `caeb984`)

**Flag:** `S1_DYNAMIC_RECLASS` (default OFF, enabled in plist)

**IB-relative metrics per bar:**
- `E_up = max(0, session_high - IB_H) / IB_width`
- `E_dn = max(0, IB_L - session_low) / IB_width`
- `R = total_range / IB_width`

**Monotonic chain:**
- Normal → Variation: `E_dom ≥ 0.15`
- Variation → Trend: `E_dom ≥ 1.0, R ≥ 2.0`
- Neutral guard: both sides extended → Neutral_Extreme
- False-breakout hold: price returns inside IB → don't upgrade

**Table:** `v9_day_type_shadow_transitions`

**Today's shadow transitions:**
```
Normal → Variation @min387 (E_up=0.74, price=7610.75)
Normal → Variation @min397 (E_up=0.95, price=7614.75)
```

## Phase 2 — Build Status Display (commit `df16d03`)

```
🔮 SHADOW: Shadow: Variation (live: Normal)
   chain: Normal→Variation @min387 (E↑0.74) · Normal→Variation @min397 (E↑0.95)
```

## Phase 3 — Validation

**Against today's full session (known ground truth):**
```
E_up = 1.77 IB widths → Trend territory
R = 2.77 IB widths → confirms Trend
Live: Normal (stuck)
Shadow: Variation → should reach Trend_Normal with full data
```

**Calibration (Day 1 — preliminary):**
- NORMAL_TO_VAR = 0.15 → 3.1pt extension (with IB_w=20.5)
- VAR_TO_TREND = 1.0 → 20.5pt extension
- Need 10+ trading days for meaningful calibration

## Commits
1. `caeb984` — Phase 1: shadow_reclass.py + wiring + flag
2. `df16d03` — Phase 2: shadow chain in Build Status
3. `9d8ff30` — fix: R calc guard

## Stage 3 (OUT OF SCOPE)
Wiring shadow chain to live Auth Table gating requires:
- 10+ days of shadow data validation
- Michael explicit approval (changes which patterns fire)

---

*D-S1DYN — shadow-log only. Live day_type unchanged.*
