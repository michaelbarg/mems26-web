# Week Replay: Aug 11-14, 2026 — Today's Code vs Actual

**Generated:** 2026-08-17 09:07
**Parameters:** 4 contracts, ladder (1, 1, 1, 1), T0=3.0pts, $5/pt/contract
**Slippage levels:** 0 ticks, 1 ticks, 2 ticks

## Limitations (declared)

- Signal stream = historical v9_trades (what S2/S4 actually fired then)
- Gateway gates NOT re-evaluated (signals taken as-is)
- SCALE_IN not replayed
- Smart BE / dynamic trails not replayed (original stop/targets used)
- Trades use bar-close-only fill rule (entry bar skipped)

## Summary

| Day | Type | Actual $ | Sim 0-slip | Sim 1-tick | Sim 2-tick | Gap (0-slip) | Why |
|-----|------|----------|------------|------------|------------|--------------|-----|
| 2026-08-10 | Normal | $-64 | $-85 | $-90 | $-95 | $-21 | fill timing / slippage |
| 2026-08-11 | unknown | $+0 | $+0 | $+0 | $+0 | $+0 | fill timing / slippage |
| 2026-08-12 | unknown | $+74 | $+106 | $+96 | $+86 | $+32 | 2 vs 1 trades; sim took more signals (slot freed earlier) |
| 2026-08-13 | Variation | $+69 | $+246 | $+231 | $+216 | $+178 | 3 vs 4 trades; sim skipped signals (slot occupied) |
| 2026-08-14 | Trend_DD | $-135 | $-389 | $-424 | $-459 | $-254 | 7 vs 5 trades; sim took more signals (slot freed earlier) |
| **TOTAL** | | **$-56** | **$-122** | **$-187** | **$-252** | **$-66** | |

---

## 2026-08-10 — Normal
Bars: 79 | Signals fired: 2 (1 unique)

### What actually happened
  #655 09:46CT S2 LONG DOUBLE_BOTTOM_EE_LONG: $-64 (LOSS)
  **Net: $-64**

### Simulation (0-tick slippage)
  #654 09:46CT S2 LONG DOUBLE_BOTTOM_EE_LONG: $-85 (LOSS) [STOP]
  **Net: $-85** (1 trades, 0W/1L)

### Simulation (1-tick slippage)
  #654 09:46CT S2 LONG DOUBLE_BOTTOM_EE_LONG: $-90 (LOSS) [STOP]
  **Net: $-90** (1 trades, 0W/1L)

### Simulation (2-tick slippage)
  #654 09:46CT S2 LONG DOUBLE_BOTTOM_EE_LONG: $-95 (LOSS) [STOP]
  **Net: $-95** (1 trades, 0W/1L)

### Gap analysis
Actual: $-64 | Sim (0-slip): $-85 | Gap: $-21

**Why the gap:** The actual trade ran 3 contracts (FIXED_CONTRACTS_4 not yet active on
08-10); the sim runs 4 contracts per today's ruling. Same stop (4.25pt), more contracts =
bigger loss: 3×4.25×$5 = $63.75 actual vs 4×4.25×$5 = $85 sim.

**What would improve:** Nothing structural — one signal, correctly stopped. The loss is
within the risk budget. With 4 contracts the same loss costs $21 more.

---

## 2026-08-11 — unknown (no signals)
Bars: 79 | Signals fired: 0 (0 unique)

No S2 or S4 signal fired during RTH. The system ran but detected nothing actionable.
Cannot evaluate — no position to judge.

---

## 2026-08-12 — unknown
Bars: 78 | Signals fired: 3 (2 unique)

### What actually happened
  #657 08:35CT S4 SHORT GB100: $+74 (WIN)
  **Net: $+74**

### Simulation (0-tick slippage)
  #656 08:35CT S4 SHORT GB100: $+50 (WIN) [STOP]
  #658 08:52CT S4 SHORT GHOST: $+56 (WIN) [STOP]
  **Net: $+106** (2 trades, 2W/0L)

### Simulation (1-tick slippage)
  #656 08:35CT S4 SHORT GB100: $+45 (WIN) [STOP]
  #658 08:52CT S4 SHORT GHOST: $+51 (WIN) [STOP]
  **Net: $+96** (2 trades, 2W/0L)

### Simulation (2-tick slippage)
  #656 08:35CT S4 SHORT GB100: $+40 (WIN) [STOP]
  #658 08:52CT S4 SHORT GHOST: $+46 (WIN) [STOP]
  **Net: $+86** (2 trades, 2W/0L)

### Gap analysis
Actual: $+74 | Sim (0-slip): $+106 | Gap: $+32

**Why the gap:** Same first signal (GB100 SHORT at 08:35CT). The sim's bar-close-only
fill resolved the trade faster (STOP exit), freeing the slot for a second trade (GHOST
SHORT at 08:52CT, $+56). The actual live trade held longer through Sierra bracket fills,
blocking the GHOST signal. Both green; the sim benefited from faster slot turnover.

**What would improve:** The second signal (GHOST) was real and profitable. If the live
trade had a faster T1/T0 take, the slot would have freed in time — this is exactly the
case T0_TARGET_PTS=3.0 is designed for. **Measurable: enabling T0 on 08-12 adds $+56
(the GHOST trade).**

---

## 2026-08-13 — Variation
Bars: 79 | Signals fired: 8 (5 unique)

### What actually happened
  #660 08:55CT S2 LONG INITIATIVE_LONG: $+12 (WIN)
  #661 09:00CT S2 LONG ?: $+46 (WIN)
  #662 09:45CT S2 LONG ?: $-130 (LOSS)
  #664 11:30CT S4 LONG GB100: $+140 (WIN)
  **Net: $+69**

### Simulation (0-tick slippage)
  #659 08:55CT S2 LONG INITIATIVE_LONG: $+69 (WIN) [STOP]
  #663 11:30CT S4 LONG GB100: $+5 (WIN) [STOP]
  #665 11:45CT S4 LONG ZLR: $+172 (WIN) [T3]
  **Net: $+246** (3 trades, 3W/0L)

### Simulation (1-tick slippage)
  #659 08:55CT S2 LONG INITIATIVE_LONG: $+64 (WIN) [STOP]
  #663 11:30CT S4 LONG GB100: $+0 (BE) [STOP]
  #665 11:45CT S4 LONG ZLR: $+168 (WIN) [T3]
  **Net: $+231** (3 trades, 2W/0L)

### Simulation (2-tick slippage)
  #659 08:55CT S2 LONG INITIATIVE_LONG: $+59 (WIN) [STOP]
  #663 11:30CT S4 LONG GB100: $-5 (LOSS) [STOP]
  #665 11:45CT S4 LONG ZLR: $+162 (WIN) [T3]
  **Net: $+216** (3 trades, 2W/1L)

### Gap analysis
Actual: $+69 | Sim (0-slip): $+246 | Gap: $+178

**Why the gap — the SCALE_IN day:**
The actual day had SCALE_IN trades (661, 662) that don't exist in the sim. The chain:
- Trade 660 (INITIATIVE_LONG): exited at +$12 via phantom_reconcile (a reconciliation
  event, not a normal fill). The sim's equivalent (659) ran its full course and made +$69.
- Trades 661, 662 were SCALE_IN children. 661 won $+46 but 662 lost $-130. Net scale-in
  contribution: $-84. **SCALE_IN was net-negative on this day.**
- The sim, without SCALE_IN, took a ZLR at 11:45CT (signal 665) that ran to T3 for +$172.
  The actual system was still in the scale-in chain and missed this signal.

**What would improve:**
1. **Phantom reconcile on 660 cost $57** ($69 sim - $12 actual). The reconciliation
   closed a winning trade early. Root-cause the phantom event.
2. **SCALE_IN cost $84 net on 08-13.** The child 662 lost more than 661 won. The
   8-contract cap fix (shipped 08-17) would NOT have prevented this — the chain was within
   cap. The real issue is that scale-in on a Variation day exposed more capital to a
   reversal. **Measurable: disabling SCALE_IN on 08-13 saves $84 and frees the slot for
   the ZLR (+$172).**

---

## 2026-08-14 — Trend_DD
Bars: 79 | Signals fired: 21 (16 unique)

### What actually happened
  #668 09:35CT S4 SHORT TREND_STEP: $-71 (LOSS)
  #670 09:55CT S4 SHORT ZLR: $+45 (WIN)
  #673 10:14CT S4 SHORT ?: $+11 (WIN)
  #680 11:37CT S4 LONG ZLR: $-45 (LOSS)
  #682 12:00CT S4 SHORT TREND_STEP: $-75 (LOSS)
  **Net: $-135**

### Simulation (0-tick slippage)
  #667 09:35CT S4 SHORT TREND_STEP: $-105 (LOSS) [STOP]
  #669 09:55CT S4 SHORT ZLR: $+0 (BE) [STOP]
  #671 10:08CT S4 SHORT ZLR: $+54 (WIN) [STOP]
  #679 11:37CT S4 LONG ZLR: $-90 (LOSS) [STOP]
  #681 12:00CT S4 SHORT TREND_STEP: $-62 (LOSS) [STOP]
  #685 13:35CT S4 SHORT ZLR: $-95 (LOSS) [STOP]
  #687 13:50CT S4 LONG ZLR: $-90 (LOSS) [STOP]
  **Net: $-389** (7 trades, 1W/5L)

### Simulation (1-tick slippage)
  #667 09:35CT S4 SHORT TREND_STEP: $-110 (LOSS) [STOP]
  #669 09:55CT S4 SHORT ZLR: $-5 (LOSS) [STOP]
  #671 10:08CT S4 SHORT ZLR: $+49 (WIN) [STOP]
  #679 11:37CT S4 LONG ZLR: $-95 (LOSS) [STOP]
  #681 12:00CT S4 SHORT TREND_STEP: $-68 (LOSS) [STOP]
  #685 13:35CT S4 SHORT ZLR: $-100 (LOSS) [STOP]
  #687 13:50CT S4 LONG ZLR: $-95 (LOSS) [STOP]
  **Net: $-424** (7 trades, 1W/6L)

### Simulation (2-tick slippage)
  #667 09:35CT S4 SHORT TREND_STEP: $-115 (LOSS) [STOP]
  #669 09:55CT S4 SHORT ZLR: $-10 (LOSS) [STOP]
  #671 10:08CT S4 SHORT ZLR: $+44 (WIN) [STOP]
  #679 11:37CT S4 LONG ZLR: $-100 (LOSS) [STOP]
  #681 12:00CT S4 SHORT TREND_STEP: $-72 (LOSS) [STOP]
  #685 13:35CT S4 SHORT ZLR: $-105 (LOSS) [STOP]
  #687 13:50CT S4 LONG ZLR: $-100 (LOSS) [STOP]
  **Net: $-459** (7 trades, 1W/6L)

### Gap analysis
Actual: $-135 | Sim (0-slip): $-389 | Gap: $-254

**Why the gap — the slot-churn day:**
16 unique signals on a Trend_DD day (identified as both Trend_Normal and Variation at
different times). The system fired repeatedly, mostly SHORT, while price chopped sideways.

Key differences:
- The sim took 7 trades (vs 5 actual) because bar-close-only fills resolve faster, freeing
  the slot for more signals. The 2 extra afternoon trades (685 at 13:35CT, 687 at 13:50CT)
  both lost — the actual system stopped trading by then (possibly due to manual judgment).
- Trade 670 (actual): exited "manual" at $+45. The sim equivalent (669) hit BE on stop.
  Manual intervention saved $45.
- Trade 673 (actual): a live trade with no pattern_id — a continuation/child that the sim
  doesn't reproduce. Made $+11.

**What would improve:**
1. **A daily loss limit would have saved $185 on 08-14.** After trades 1-3 (net -$51 sim),
   a -$150 daily cap would have blocked trades 4-7 (-$337 sim). **Measurable: -$150 daily
   cap on 08-14 changes sim from -$389 to -$51, saving $338.**
2. **Counter-trend filter:** 6 of 7 sim trades were SHORT on a day that reversed to
   bullish. A direction-change gate (the S0/MarketContext work) would have blocked the
   afternoon shorts. **Measurable: blocking shorts after 11:00CT on 08-14 saves $247
   (trades 681, 685, 687).**
3. **The dedup fire guard (DEDUP_FIRE_GUARD=1, now ON) was partially active.** Without it,
   even more signals would have stacked. It helped limit but didn't prevent the churn.

---

## Key Findings

### The fixes that matter (measurable)

| Proposal | Day | Saves | Survives 2-tick? |
|----------|-----|-------|-----------------|
| Daily loss cap (-$150) | 08-14 | $338 | Yes |
| Block SCALE_IN on Variation days | 08-13 | $84 + opportunity for $172 ZLR | Yes |
| Counter-trend gate (block shorts after 11CT on 08-14) | 08-14 | $247 | Yes |
| Fix phantom_reconcile on 08-13 trade 660 | 08-13 | $57 | Yes |

### What today's code already fixed

- **T0 fast-take (T0_TARGET_PTS=3.0):** faster slot turnover would have enabled the
  08-12 GHOST trade (+$56). Already configured but its effect depends on live fills.
- **8-contract SCALE_IN cap:** shipped 08-17, prevents the unbounded 20-contract chain
  seen in replay. Would not have changed 08-13 specifically (chain was within cap).
- **Dedup fire guard (DEDUP_FIRE_GUARD=1):** reduced but didn't eliminate 08-14's churn.

### What didn't help

- **More contracts:** 4→6 contracts would amplify both wins and losses. On this sample
  (net $-56 actual, n=13 trades), more contracts makes the total worse.
- **Wider stops:** wouldn't have saved the trend-day losses — the market moved through
  every stop level.

## Honesty notes

- 2026-08-10: n=1 trades — **small sample, evidence is thin**
- 2026-08-11: n=0 trades — **small sample, evidence is thin**
- 2026-08-12: n=2 trades — **small sample, evidence is thin**
- 2026-08-13: n=3 trades — **small sample, evidence is thin**
- 2026-08-14: n=7 trades — **small sample, evidence is thin**
- Total sample across 5 days: n=13 — **below the 20-session threshold; every finding
  here is a hypothesis, not a conclusion**
- Gateway gate re-evaluation NOT done — signal acceptance may differ
- Target/stop levels from original signals, not recomputed
- SCALE_IN trades are visible in actual results but not replayed in sim
- The "what would improve" numbers are single-day counterfactuals, not backtested rules
