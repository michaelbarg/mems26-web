# MEMS26 — Master Simulation Registry V3.1

**Version:** V3.1 — Critical Improvements Integration
**Created:** Tuesday, 5 May 2026 (Phase 3.2 Day 2, evening)
**Supersedes:** V3.0 (same day, mid-day)
**Trigger:** External review identified 9 critical gaps

---

## ⚠️ What Changed Since V3.0 (Same-Day Update)

V3.0 was ambitious. V3.1 is **rigorous**. External critique identified:

```
🔴 LIVE BLOCKERS (must fix before 28/5):
   1. CFG-α sample size insufficient → Monte Carlo + extended backtest
   2. Tier sizing uses raw contracts → R-multiple risk normalization
   3. STOP-01 mislabels DEVELOPING → moved to ENT layer
   4. STOP-05 lacks max threshold → ATR fallback added

🟢 IMPROVEMENTS (Phase 3.4 ready):
   5. CONF-01 needs time decay window (60-180 min)
   6. CONF-03 needs relative volume (z-score, not absolute)
   7. CONF-05 should integrate with Footprint direction

🟡 PROCESS:
   8. Day Plan: run 3 priority sims first, 9 others after sanity check
   9. All sims must pass outcome-validation (no MFE proxy)
```

---

## Table of Contents

1. [LIVE Blockers — What Must Be Fixed First](#1-live-blockers)
2. [Updated Confluence Engine (CONF-XX)](#2-confluence)
3. [Updated Smart Stop Management (STOP-XX)](#3-stops)
4. [Tier R-Multiple Sizing Model](#4-tier)
5. [Validated Production Candidates](#5-cfg)
6. [Existing Sims Catalog (Unchanged)](#6-existing)
7. [Recommended Path Forward (V3.1)](#7-recommendation)
8. [Updated 5-Day Execution Plan](#8-execution)
9. [Acceptance Criteria & Quality Gates](#9-acceptance)

---

<a name="1-live-blockers"></a>
## 1. 🔴 LIVE Blockers — Must Fix Before 28/5

### Blocker #1: CFG-α Sample Insufficient

```
Current state:    14 trades, 3 days, 100% OOS WR (sample of 3-4)
Problem:          Statistically insignificant for LIVE deployment
Impact:           High risk of Day-1 LIVE drawdown
Fix required:     SIM-RBT-04 (NEW): Monte Carlo on CFG-α
                  + SIM-CMP-03 (NEW): Extended 30-day backtest if data exists
```

**SIM-RBT-04: CFG-α Monte Carlo Stress Test (NEW — CRITICAL)**
```
Purpose:    Statistical robustness of 14-trade sample
Method:     Bootstrap 1000x random subsamples (8-12 trades each)
            Compute WR distribution
            Compute PnL 5th/50th/95th percentiles
Acceptance: 5th percentile WR > 60% (not 84.6% — realistic floor)
            5th percentile PnL >= breakeven
Frequency:  Once before LIVE, weekly during LIVE
Owner:      CC + manual review
Decision:   If 5th percentile fails → DO NOT LIVE
```

**SIM-CMP-03: Extended Backtest (NEW — CRITICAL)**
```
Purpose:    Validate CFG-α on longest available data
Method:     Run on full MDS .scid data (29.6M ticks, 30+ days)
            Sequential filter applied
            Outcome-based (post-bug-fix)
Acceptance: WR >= 70% on >100 trades
            Daily PnL distribution: 5th percentile >= -$300
Frequency:  Once before LIVE, every 5 LIVE days after
Decision:   If <70% on 100+ trades → suspend LIVE
```

### Blocker #2: Tier Sizing — Move to R-Multiple

See section [4. Tier R-Multiple Sizing Model](#4-tier) below.

### Blocker #3: STOP-01 Mislabel

```
Was:  STOP-01 contained "DEVELOPING: skip altogether"
Fix:  Move "skip DEVELOPING" rule to ENT-08 (entry filter)
      STOP-01 now ONLY handles stop distance variation
```

### Blocker #4: STOP-05 Max Threshold

```
Was:  Structural Stop = nearest swing high/low + 1pt buffer
      Could result in 15+ pt stops in volatile sessions
Fix:  Cap structural stop at ATR_5min * 2.0
      If structural would exceed cap → fallback to STOP-04 (ATR-based)
      If ATR-based also exceeds 15pt → REJECT setup entirely
Logic:
   if structural_stop_pts <= ATR * 2.0:
       use structural
   elif ATR * 1.2 <= 15:
       use ATR * 1.2
   else:
       REJECT setup (volatility too high for safe entry)
```

---

<a name="2-confluence"></a>
## 2. 🆕 Updated Confluence Engine (CONF-XX)

### CONF-01: Failed Attempts Counter (UPDATED)

```
מה זה:        Tracking failed breaks of key levels with TIME DECAY
Detection:    Every time price touches level X but rejects within 1pt
              ★ NEW: Only count attempts within last 120 minutes
              ★ NEW: Sweep test windows of 60/120/180 min
Score logic:  attempt_2 reject (recent) = strong reversal signal
              attempt_3 break (recent) = strong continuation
              Old attempts (>120min) = ignored
Implementation: DLL persistent counter + timestamp per attempt
Test sweep:    SIM-CONF-01: window in [60, 90, 120, 180] min
Hypothesis:    Optimal window emerges from sim
Acceptance:    Best window gives +5pp WR vs no-tracking baseline
```

### CONF-02: POC Magnetism Score (UNCHANGED)

```
מה זה:        How strongly price reacts to POC (current/prior day)
Detection:    Distance from POC + time near POC + cross count
Score logic:  Near POC + bouncing → support/resistance
              Far from POC + extending → trend mode
Implementation: Backend calculation on existing TPO data
Hypothesis:   Setups within 2pt of POC have +8pp better WR
Acceptance:   POC-aware setups beat POC-blind by >5pp WR
Day type:     Most relevant in RANGE_DAY, GAP_FILL
```

### CONF-03: Volume at Level (UPDATED — RELATIVE NOT ABSOLUTE)

```
מה זה:        Volume strength behind a level
Detection:    ★ NEW: Z-score vs 20-bar rolling mean
              vol_strength = (level_volume - mean_20bar) / stddev_20bar
Score logic:  z >= +2 → HVN (strong barrier)
              z in [-1, +2] → normal
              z < -1 → LVN (weak barrier)
Why relative: 200 contracts at NY Open = noise
              200 contracts at OFF_HOURS = wall
Implementation: TPO + footprint integration
Hypothesis:   z>=+2 setups outperform z<=-1 by >10pp WR
Acceptance:   Relative-volume model beats absolute by >3pp WR
```

### CONF-04: Pattern Sequence Memory (UNCHANGED)

```
מה זה:        Statistical follow-through of pattern sequences
Detection:    Pattern A precedes B in N% of historical cases
Score logic:  After "Failed High" → 67% chance of "Pullback to POC"
              After "Sweep + MSS" → 73% chance of "Continuation"
Implementation: Backend pattern history table
Hypothesis:   Setups within "expected sequence" outperform random
Acceptance:   Sequence-confirmed setups +6pp WR vs base
Day type:     Universal value
```

### CONF-05: Price Action Velocity + Footprint (UPDATED)

```
מה זה:        Speed of price move into setup, ★ qualified by FP direction
Detection:    velocity = ATR_1min over last 5min before setup
              ★ NEW: combined with footprint_delta direction
Score logic:  HIGH velocity + FP same direction → MOMENTUM (continuation)
              HIGH velocity + FP opposite direction → EXHAUSTION (reversal)
              LOW velocity + FP weak → consolidation
Implementation: DLL velocity calculation + FP integration
Hypothesis:   "Initiative" (velocity + FP same) outperforms "Liquidation" (velocity + FP opposite)
Acceptance:   Initiative trades +8pp WR vs Liquidation trades
Day type:     TREND_DAY (Initiative), RANGE_DAY (Liquidation)
```

### CONF-06: Multi-TF Confluence (UNCHANGED)

```
מה זה:        Multi-timeframe agreement (1m/5m/15m/30m/1h)
Detection:    Per-TF trend direction (above/below VWAP, EMA)
Score logic:  3+ TFs agree → high confidence entry
              0-1 TFs agree → low confidence, skip
Status:       mtf_aligned exists but not integrated into score
Hypothesis:   3-of-5 TF agreement gives +10pp WR
Acceptance:   Use existing field, validate impact
Day type:     TREND_DAY most valuable
```

---

<a name="3-stops"></a>
## 3. 🆕 Updated Smart Stop Management (STOP-XX)

### STOP-01: Day-Type Adaptive Initial Stop (FIXED LABEL)

```
מה זה:        Stop distance varies by day type
              ★ DEVELOPING removed — that's an ENT filter, not STOP rule
Logic:        TREND_DAY:    8pt (volatility allowance)
              RANGE_DAY:    3pt (mean revert tight)
              NORMAL:       5pt (current default)
              GAP_FILL:     5pt (with PDC target)
              [DEVELOPING handled at entry — never reaches here]
Implementation: backend day_config.py update
Hypothesis:   -15% stop-out rate on TREND days, -5% on RANGE
Acceptance:   Daily PnL improves by >$30 across day types
```

### STOP-02 through STOP-04 (UNCHANGED from V3.0)

### STOP-05: Structural Stop with MAX THRESHOLD (UPDATED)

```
מה זה:        Stop = nearest swing high/low ± 1pt buffer
              ★ NEW: Hard cap at ATR_5min * 2.0
              ★ NEW: ATR fallback if structural exceeds cap
              ★ NEW: REJECT setup if both exceed 15pt
Logic:
   atr_cap = ATR_5min * 2.0
   if structural_stop_pts <= atr_cap:
       use structural_stop
   elif ATR_5min * 1.2 <= 15:
       use ATR_5min * 1.2  # fallback
   else:
       REJECT (volatility too extreme)
Implementation: backend (data already exists in shadow_structural_stop)
Hypothesis:   Structural stops outperform fixed by >$10/trade
              No outlier 20pt+ stops kill WR
Acceptance:   Cross-validate against fixed 5pt over 30 days
```

### STOP-06: Time-Decay Stop (UNCHANGED)

---

<a name="4-tier"></a>
## 4. ⭐ Tier R-Multiple Sizing Model (CRITICAL UPDATE)

This is the biggest change in V3.1. See companion document `TIER_R_MULTIPLE_SPEC.md` for full implementation details.

### Concept Shift

```
V3.0 (RAW CONTRACTS):
   Tier-S → 3 contracts (always)
   Tier-A → 2 contracts (always)
   Tier-B → 1 contract (always)
   
   Problem: A 5pt stop with 3 contracts risks $75
            An 8pt stop with 3 contracts risks $120
            Same Tier-S, different actual risk!

V3.1 (R-MULTIPLE):
   Tier-S → risks 1.5% of capital
   Tier-A → risks 1.0% of capital
   Tier-B → risks 0.5% of capital
   
   Logic: Tier defines RISK BUDGET
          Stop distance defines CONTRACTS
          Larger stop → fewer contracts
          Smaller stop → more contracts
          Risk per trade = constant per Tier
```

### TIER-01 (REVISED): Confluence Score → Risk Budget

```
Confluence Score (sum of CONF-01..06, normalized 0-100):
   90-100  →  Tier-S  →  risk 1.5% (homerun setups)
   70-89   →  Tier-A  →  risk 1.0% (high quality)
   50-69   →  Tier-B  →  risk 0.5% (small acceptable)
   <50     →  REJECT  →  risk 0%

Position Sizing Calculation:
   account_risk_pct = tier_pct (e.g., 1.5% for Tier-S)
   account_risk_dollars = account_value * account_risk_pct
   contract_risk_pts = stop_distance_pts
   contract_risk_dollars = contract_risk_pts * $5 (MES tick value)
   contracts = floor(account_risk_dollars / contract_risk_dollars)
   
Example (account = $5000):
   Tier-S, stop=5pt:
      risk = $5000 * 1.5% = $75
      contracts = floor($75 / ($5 * 5)) = floor(3) = 3 contracts
   Tier-S, stop=8pt:
      risk = $5000 * 1.5% = $75
      contracts = floor($75 / ($5 * 8)) = floor(1.875) = 1 contract
      ★ Same Tier, but smaller position due to wider stop
   Tier-A, stop=5pt:
      risk = $5000 * 1.0% = $50
      contracts = floor($50 / $25) = 2 contracts
```

### TIER-02 (REVISED): Day-Type × Tier Risk Adjustment

```
Different day types call for different risk appetites:

TREND_DAY (best edge, allow more risk):
   Tier-S risk: 2.0% (was 1.5%)
   Tier-A risk: 1.5%
   Tier-B risk: 1.0%

RANGE_DAY (chop, reduce risk):
   Tier-S risk: 1.0% (was 1.5%)
   Tier-A risk: 0.5%
   Tier-B risk: skip

NORMAL (baseline):
   Tier-S risk: 1.5%
   Tier-A risk: 1.0%
   Tier-B risk: 0.5%

GAP_FILL (high conviction):
   Tier-S risk: 1.5%
   Tier-A risk: 1.0%
   Tier-B risk: skip

DEVELOPING:
   ALL tiers REJECTED at entry (V2 filter)
```

### TIER-03 (UNCHANGED): Stop × Tier Interaction

```
Tier-S: full stop per Day Type, BE per spec
Tier-A: tighter stop (1pt less), BE faster (after T1)
Tier-B: tightest stop (2pt less), T1-only exit

Logic: lower confidence = faster protection
       higher confidence = let it work
```

### Daily Risk Cap (NEW — SAFETY)

```
Max account risk per day:    3.0% (regardless of tier sums)
Once reached:                stop trading for the day
Per LIVE rules:              $200 daily cap → no exceptions

This means: even if 5 Tier-S setups appear,
            only first ~2 may execute before cap hits
```

---

<a name="5-cfg"></a>
## 5. Validated Production Candidates (UPDATED)

### CFG-α (Alpha) — TOP CANDIDATE (CONDITIONAL)

```
Status:           VALIDATED (small sample), AWAITING Monte Carlo (SIM-RBT-04)
Spec:             score>=70, skip OFF_HOURS, weights V20/T20/F40/FP20, BE-on-C1
Performance:      14 trades / 3 days, 84.6% WR, +$112/day
PF:               5.50
Sample warning:   ★ NOT YET STATISTICALLY SIGNIFICANT
Bug-resilience:   IDENTICAL pre/post outcome fix
LIVE-ready:       CONDITIONAL on SIM-RBT-04 + SIM-CMP-03 passing
```

### CFG-β (Beta) — ALTERNATIVE

```
Status:           VALIDATED, similar caveats to CFG-α
Spec:             score>=60, skip OFF_HOURS, V25/T30/F25/FP20, BE-current
Performance:      15 trades / 3 days, 85.7% WR, +$101/day
PF:               7.00
LIVE-ready:       CONDITIONAL on extended validation
```

### Both CFG-α and CFG-β need same validation gates before LIVE.

---

<a name="6-existing"></a>
## 6. Existing Sims Catalog (UNCHANGED FROM V3.0)

All 31 existing sims (SYS, DAY, ENT, MGT, SCO, COM, RBT, CMP, OBS, OPT, DEC, DISC, CFG) remain valid. New entries:

- **SIM-RBT-04** (NEW): CFG-α Monte Carlo Stress Test
- **SIM-CMP-03** (NEW): Extended 30-day backtest
- **ENT-08** (NEW): Skip DEVELOPING entries (moved from STOP-01)

---

<a name="7-recommendation"></a>
## 7. ⭐ Recommended Path Forward (V3.1)

### Two-Track Strategy (UPDATED)

```
┌─────────────────────────────────────────────────────────┐
│  TRACK A (PRIMARY): LIVE 28/5 with CFG-α — CONDITIONAL  │
│  ───────────────────────────────────────────           │
│  Pre-LIVE blockers:                                     │
│    [ ] SIM-RBT-04 passes (Monte Carlo)                  │
│    [ ] SIM-CMP-03 passes (Extended backtest)            │
│    [ ] R-multiple Tier model implemented                │
│    [ ] STOP-05 max threshold integrated                 │
│    [ ] ENT-08 (skip DEVELOPING) wired                   │
│                                                         │
│  Phase 3.3 Day 1 ships:                                 │
│    • CFG-α + R-Multiple sizing                          │
│    • System Status Layer                                │
│    • Validated, low risk                                │
│                                                         │
│  IF blockers fail → DELAY LIVE                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  TRACK B (PARALLEL): Phase 3.4 — Confluence Engine     │
│  ────────────────────────────────────────              │
│  Develops in parallel via SIM-CONF-01..06              │
│  + SIM-STOP-01..06 + SIM-TIER-01..03                   │
│                                                         │
│  Day 3 (6/5):  Top-3 priority sims (sanity gate)       │
│  Day 3 PM:     Remaining 9 sims (if Day 3 OK)          │
│  Day 4 (7/5):  Combinations + per-day-type playbooks   │
│  Day 5 (8/5):  Phase 3.4 spec ready                    │
└─────────────────────────────────────────────────────────┘
```

---

<a name="8-execution"></a>
## 8. Updated 5-Day Execution Plan

### Day 2 (Today, 5/5 evening)
```
✅ V3.0 written (mid-day)
✅ External critique reviewed
✅ V3.1 written (this document)
🔲 TIER_R_MULTIPLE_SPEC.md (companion document)
🔲 Commit both to docs/
```

### Day 3 (6/5)
```
🔲 SIM-RBT-04: CFG-α Monte Carlo (priority — LIVE blocker)
🔲 SIM-CMP-03: Extended backtest (priority — LIVE blocker)
🔲 Top-3 CONF/STOP sims:
   • SIM-CONF-04 (Pattern Memory) — low effort, high theory
   • SIM-CONF-06 (Multi-TF) — low effort, data exists
   • SIM-STOP-05 (Structural with cap) — data exists, lowest risk
🔲 Sanity gate: do top-3 produce expected results?
🔲 IF YES: launch remaining 9 sims in batch
🔲 IF NO: investigate, fix methodology, retry
```

### Day 4 (7/5)
```
🔲 Review all CONF/STOP results
🔲 Filter to "valid" ideas (>5pp WR improvement, >50 trades)
🔲 Test pairs/triples of valid CONFs
🔲 Per-day-type top combinations
```

### Day 5 (8/5) — Phase 3.3 Day 1 Begins
```
🔲 Final per-day-type playbook (Phase 3.4 input)
🔲 Phase 3.3 Day 1 starts:
   • CFG-α implementation (with R-Multiple sizing)
   • System Status Layer
🔲 Confluence work continues offline for Phase 3.4
```

---

<a name="9-acceptance"></a>
## 9. Acceptance Criteria & Quality Gates

### LIVE Gate (28/5)

```
Must pass ALL:
[ ] SIM-RBT-04 5th percentile WR >= 60%
[ ] SIM-CMP-03 30-day WR >= 70% on 100+ trades
[ ] R-Multiple sizing implemented and tested
[ ] STOP-05 max threshold logic verified
[ ] ENT-08 (skip DEVELOPING) wired and tested
[ ] System Status Layer functional
[ ] Daily cap $200 enforced at engine level
[ ] Manual kill switch tested
```

### Phase 3.4 Gate (Late May)

```
Must pass ALL:
[ ] Top 3 CONF factors validated
[ ] Top 3 STOP variants validated
[ ] Combined sims show >$50/day improvement over CFG-α
[ ] Walk-forward stable (OOS degradation <30%)
[ ] R-Multiple Tier model validated on 100+ trades
```

### Daily Quality Gate (Phase 3.2 Day 3-5)

```
Each new sim must:
[ ] Use outcome-based win definition (NOT MFE)
[ ] Include sanity check vs production data
[ ] Include sample size disclosure
[ ] Include OOS test if applicable
[ ] Walk-forward if config sweep
```

---

## Document Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 5 May 2026 00:30 | Initial 26 sims, 9 categories |
| 2.0 | 5 May 2026 01:30 | CFG candidates + Phase 3.3 strategy B' |
| 3.0 | 5 May 2026 evening | Confluence + Tier (Two-Track) |
| 3.1 | 5 May 2026 night | Critical improvements: R-Multiple, Monte Carlo, fixes |

---

**Maintained by:** Michael (with Claude assistance)
**Companion document:** `TIER_R_MULTIPLE_SPEC.md`
**Next review:** Day 3 morning (6/5)
**Status:** Locked for Day 3 execution
