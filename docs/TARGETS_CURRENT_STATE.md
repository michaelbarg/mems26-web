# Targets & Stop Calculation — Current State (1/5/2026)

## 1. Live Implementation (truth-state)

### Stop Calculation

**File:** `backend/main.py:1031` (Phase 6 logger) + `backend/main.py:2706-2714` (/trade/execute)

Shadow/sim setups: Stop = entry +/- `risk_pts`, where `risk_pts = abs(entry - stop)` from the frontend request. For the opposite direction (dual logging), `risk_pts` defaults to the same value. If frontend sends `stop = price - 5`, then `risk_pts = 5`.

Live execution path: Stop is validated:
- Min: `STOP_MIN_PT = 3.0pt` (auto-expanded if below, `main.py:2706`)
- Max: `STOP_MAX_PT = 15.0pt` (rejected if above, `main.py:2550`)
- If stop < 3pt: auto-adjusted to entry +/- 3pt (`main.py:2710-2712`)

**In practice (shadow sim):** QualityScorePanel sends `stop = price - 5` (hardcoded 5pt risk in `QualityScorePanel.tsx:75`). So ALL shadow setups use 5pt fixed stop.

### C1 (T1) Calculation

**File:** `backend/quality_score.py:209`

```python
c1 = round(entry + (target_rules["c1_R"] * R * sign), 2)
```

Day-adaptive `c1_R`:
| Day Type | c1_R | Result (5pt risk) |
|---|---|---|
| NORMAL | 1.0 | entry +/- 5pt |
| DEVELOPING | 1.0 | entry +/- 5pt |
| TREND_DAY | 1.0 | entry +/- 5pt |
| RANGE_DAY | 0.8 | entry +/- 4pt |
| GAP_FILL | 1.0 | entry +/- 5pt |

### C2 (T2) Calculation

**File:** `backend/quality_score.py:210-259`

Base: `c2 = entry + (c2_R * R * sign)`

Day-adaptive `c2_R`:
| Day Type | c2_R | Base (5pt risk) | Special |
|---|---|---|---|
| NORMAL | 2.0 | +10pt | TPO confluence (VAH/POC, `quality_score.py:228-248`) |
| DEVELOPING | 2.0 | +10pt | TPO confluence |
| TREND_DAY | 3.0 | +15pt | None |
| RANGE_DAY | 1.5 | +7.5pt | None |
| GAP_FILL | 2.0 | +10pt | PDC (Previous Day Close, `quality_score.py:216-225`) |

C2 cap: `MAX_C2_R = 4.0` (6.0 for GAP_FILL). Max C2 distance = 4R = 20pt (`quality_score.py:250-259`).

TPO confluence (`quality_score.py:228-248`): For NORMAL/DEVELOPING, if TPO VAH (LONG) or VAL (SHORT) is beyond c2_r_based, c2 extends to that level. This means C2 can be > 2R if TPO level supports it.

### C3 (T3) Calculation

**File:** `backend/quality_score.py:264`

```python
"c3_enabled": target_rules["c3_enabled"]
```

| Day Type | c3_enabled | Note |
|---|---|---|
| NORMAL | True | But no price computed — field is boolean only |
| DEVELOPING | True | Same |
| TREND_DAY | True | Same |
| RANGE_DAY | **False** | C3 disabled |
| GAP_FILL | **False** | C3 disabled |

**Critical gap:** `c3_enabled` is a boolean flag returned in the targets dict, but NO c3 price is ever computed. The `calculate_targets()` function returns `c3_enabled: True` but no `c3` field. The `c3_target` in DB is always NULL for all setups.

### Contracts Allocation

**File:** `backend/quality_score.py:181-193`

```python
score >= full_thresh → qty=3, exits=["C1","C2","C3"]
score >= half_thresh → qty=2, exits=["C1","C2"]
score < half_thresh  → qty=0 (reject/warn)
```

Day-adaptive thresholds (`day_config.py:13-19`):
| Day Type | full (3c) | half (2c) |
|---|---|---|
| NORMAL | 70 | 50 |
| DEVELOPING | 70 | 50 |
| TREND_DAY | 60 | 45 |
| RANGE_DAY | 70 | 55 |
| GAP_FILL | 65 | 50 |

Shadow sim uses `contracts = 3 if score >= 70 else 2 if score >= 50 else 1` (`main.py:428`).

### BE Strategy

**File:** `backend/day_config.py:29-35`

| Day Type | be_strategy |
|---|---|
| NORMAL | on_c2_fill |
| DEVELOPING | on_c2_fill |
| TREND_DAY | after_c2_plus_half_R |
| RANGE_DAY | on_c1_fill |
| GAP_FILL | on_c1_fill |

### Live Sample (verification)

```
setup_id: cc1111a005d37d82
direction: LONG
day_type: NORMAL
initial_entry: 7257.25
initial_stop: 7252.25  (entry - 5pt = -1R)
c1_target: 7262.25     (entry + 5pt = +1R, c1_R=1.0)
c2_target: 7267.25     (entry + 10pt = +2R, c2_R=2.0, no TPO confluence triggered)
c3_target: null         (c3_enabled=True but no price computed)
contracts_used: 3       (score=79 >= 70 = FULL_SIZE)
be_strategy: on_c2_fill (NORMAL day)
close_reason: STOP
pnl_pts: -15.0          (3 contracts × -5pt)
pnl_usd: -75.0          (3 × -5pt × $5/pt)
```

Verification: 7257.25 + 1.0 × 5.0 = 7262.25 (C1). 7257.25 + 2.0 × 5.0 = 7267.25 (C2). Matches.

---

## 2. Spec Docs Say

### V6.5.3 Spec (April 20, 2026)
- C1 (50%): +1R
- C2 (25%): +2R
- C3 (25%): Runner — trail at swing low/high
- Stop: Structural (sweep wick + 0.5pt buffer), min 3pt, max 8pt
- BE: Move to entry after C1 fill

### Full Audit V4 (Hybrid, NOT implemented)
- C1: min(+1R, next_level - 0.25)
- C2: structural level (POC/VAH/PDH), constrained 2R-5R
- C3: trailing stop from +3R, follows 5-bar swing high/low
- Stop: Structural, max 8pt
- BE: After internal MSS confirmation

### Research Mode (current sim config)
- Stop max: 15pt (raised from 8pt in V7.8.2)
- BE: Varies by day type (Phase 5)
- Targets: R-based (Phase 5 day-adaptive)

### Phase 5 (V7.14.0, deployed)
- Day-adaptive weights, thresholds, targets, BE
- c3_enabled flag per day type
- C2 cap at 4R (6R for GAP_FILL)
- TPO confluence for C2 (NORMAL/DEVELOPING only)

---

## 3. The Gap (Live vs Spec)

| Aspect | Live Today | Spec V6.5.3 Says | Gap |
|---|---|---|---|
| Stop source | Fixed 5pt (frontend hardcode) | Structural (wick + buffer) | Full gap — no structural stop |
| Stop bounds | 3-15pt | 3-8pt | Partial — max raised |
| C1 | +1R (R-based) | +1R or structural | Partial — no structural option |
| C2 | +2R or TPO confluence | Structural (POC/VAH) | Partial — TPO confluence exists but rarely triggers |
| C3 price | NULL always | Trailing from +3R | Full gap — c3_enabled=True but no price |
| C3 contracts | 3rd contract allocated | 25% runner position | Flag exists, target missing |
| BE trigger | Day-adaptive (on_c2_fill etc.) | After C1 fill | Different by design (Phase 5) |
| Risk source | 5pt hardcoded in QualityScorePanel | Computed from structure | Full gap |

---

## 4. Open Questions for Phase 3.2 Observation (3-7/5)

- **Q1:** Do setups with structural levels < 5pt away (POC/VAH within 3pt of entry) produce different WR than those with levels > 10pt away? Would justify structural C1/stop.
- **Q2:** What % of STOP-closed setups had MFE > 5pt? (i.e., price went in our direction first, then reversed past stop). If high, stop is too tight or entry timing is off.
- **Q3:** What's the average MFE on closed setups? Does it exceed C2 distance (10pt) regularly? If yes, C3 trailing would capture significant additional profit.
- **Q4:** For NORMAL day setups, does TPO confluence C2 outperform fixed 2R C2? Compare WR of setups where `c2_method=TPO_confluence` vs `c2_method=R_based`.
- **Q5:** Does TREND_DAY's c2_R=3.0 (+15pt) produce more T2 hits than NORMAL's c2_R=2.0 (+10pt), or does the larger distance cause more timeouts?

---

## 5. When This Doc Updates

- Phase 3.2 EOD reports (3/5 - 7/5): append observations per question
- Phase 3.5 design (10/5): use as baseline for Hybrid targets implementation
- Phase 3.5 implementation (~14/5): mark section 1 as "v1 (superseded)", add v2
