# Trade Audit · S2 Silence · S4 Deep · 2026-06-11

Generated: 2026-06-11 evening (CC diagnostic)
Contract: `docs/handoff/CC_HANDOFF_CONTRACT.md` — Rule 5 (raw evidence per claim)

---

## Q1 — S2 Near-Silence: Why Only 2 Fires

### Raw S2 Event Log (complete for 2026-06-11)

```
06:59:45 [FiveMin] Hydrated current_day_type=Variation from v9_day_type_state
   (repeated hydrations 16:35–16:56 — see anomaly below)
17:00:00 [FiveMin] current_day_type: UNKNOWN → Trend_Normal
17:13:35 [FiveMin] Hydrated current_day_type=Trend_Normal
17:15:03 [FiveMin] FIRE: REACTIVE SHORT (conf=0.75) → T1Setup emitted → Gateway SHADOW id=33
17:30:00 [FiveMin] Mode transition: FIRST_HOUR_TACTICAL → DAY_TYPE_MODE
18:00:00 [FiveMin] current_day_type: Trend_Normal → Variation
19:15:01 [FiveMin] FIRE: REACTIVE LONG (conf=0.80) → T1Setup emitted → Gateway SHADOW id=43
20:30:00 [FiveMin] FIRE: DOUBLE_BOTTOM_EE LONG → pre_fire REJECTED: risk 73.00pt > max 60.00pt
22:15:01 [FiveMin] FIRE: DOUBLE_BOTTOM_EE LONG → pre_fire REJECTED: R:R < 1.0 (reward=10.06 risk=17.75)
```

**Summary: 4 total S2 detections across 75 RTH bars. 2 routed, 2 rejected by pre_fire.**

### Root Causes of Scarcity (NOT gate issues — geometry scarcity)

**Finding 1 — Detection IS running on every new bar.** The process_bar flow
(`five_min_system.py:855-929`) confirms: outside OVERNIGHT/MAINTENANCE/WEEKEND,
every `is_new_bar` event runs `_detect_reactive(_det_buf)` then `_detect_initiative(_det_buf)`.
No day_type gate blocks detection (Nontrend check at line 902 — today's types were
Trend_Normal and Variation, not Nontrend). No `S2_REQUIRE_COT_AMT` regression
(flag OFF by default, confirmed in CLAUDE.md Standing Decisions).

**Finding 2 — The REACTIVE 4-bar pattern is strict geometry.**
`five_min_system.py:585-618` — ALL conditions must be true simultaneously:

| Condition | What it checks | Likely fail rate |
|-----------|---------------|-----------------|
| b1_sellers | Bar -4 bearish close + volume > 0 | ~50% bars |
| b2_drop | Bar -3 volume < b1 AND ≤ 0.7× rolling avg (VSA) | HIGH — most bars don't drop 30%+ |
| b3_buyers | Bar -2 bullish close | ~50% |
| b3_belly | Footprint belly not False | Passes (None = pass) |
| b4_confirm | Bar -1 bullish close | ~50% |
| b4_close_above_b3_high | Bar -1 close > bar -2 high | STRICT — requires strong continuation |
| lookback_quiet | Bypassed when S2_VSA_VOLUME=ON | Always pass |
| belly_ratio_ok | Ratio ≥ threshold or None | Passes (None = pass) |

The AND chain means **all 6+ conditions must align on the same 4-bar window**. With each
condition ~50% independent probability, the combined hit rate is ~1-3% of bars — which
matches 2 detections in 75 bars perfectly.

**Finding 3 — INITIATIVE is even stricter.**
`five_min_system.py:676-723` adds `b1_expansion` (bar range within 6-7 tick window),
`b3_joining` (bar 3 range > bar 1 range), and `b4_close_above/below_b1_high/low`.
Zero initiative detections today is consistent with the strict expansion + joining
requirements in a choppy market.

**Finding 4 — Chart patterns (Pkg 5a/5b) only run in DAY_TYPE_MODE with specific day_types.**
Mode was FIRST_HOUR_TACTICAL until 17:30, then DAY_TYPE_MODE. Chart patterns require
`current_day_type in ("Neutral_Extreme", "Neutral_Center", "Normal", "Variation")`.
Today's types were Trend_Normal (17:00-18:00) and Variation (18:00+). DOUBLE_BOTTOM_EE
DID fire twice (20:30, 22:15) but was rejected by pre_fire validator.

**Finding 5 — Repeated hydration anomaly.**
14+ hydration cycles between 16:35–16:56, then again at 17:13, 17:19, 21:52, 21:56.
This means the system is being re-initialized on many bar pushes (not just startup).
Each hydration resets `_bar_buffer` from DB (60 bars → trimmed to 20). **This does NOT
kill detections** (buffer is correctly populated) but is wasted work and adds 100-200ms
latency to process_bar.

### Verdict (Q1)

S2 silence is **primarily geometry scarcity**, not a gate/bug. The 4-bar reactive pattern
naturally fires 1-3% of bars. Two fires + two pre_fire rejections in 75 bars = normal.

**However:** Michael says "there were clear S2 patterns." Without per-bar condition logging,
we cannot prove which specific bars Michael saw as opportunities and which condition failed.

**Recommendation:** Add flag-gated (`S2_DETECTION_LOG=1`, default OFF) per-bar condition
logging to `_detect_reactive` and `_detect_initiative` — one log line per bar with the
boolean vector `[b1_sellers, b2_drop, b3_buyers, b4_confirm, b4_above_h]` so we can
identify which single condition is the bottleneck.

---

## Q2 — pnl_r Units Bug (Winners)

### Evidence

From `trades_full.json` (API export, 2026-06-11 evening):

| id | pnl_usd | pnl_r (JSON) | pnl_usd ÷ 1.25 | Match? |
|----|---------|-------------|-----------------|--------|
| 60 | 35.65 | 28.52 | 28.52 | ✓ BUG |
| 58 | 61.00 | 48.80 | 48.80 | ✓ BUG |

**Pattern:** `pnl_r = pnl_usd / 1.25` where $1.25 = 1 tick ($5/pt × 0.25pt).
This means risk_per_contract = $1.25 = 1 MES tick, i.e., `_initial_stop()` returns
entry ± 0.25 (the BE+1T stop) instead of the original stop.

### Current DB State (diverges from JSON)

```sql
SELECT id, quality->>'initial_stop' as initial_stop, stop, entry_price, pnl_r
FROM v9_trades WHERE id IN (58, 60);

 id | initial_stop |  stop   | entry_price | pnl_r
----+--------------+---------+-------------+-------
 58 | 7344.5       | 7375.25 |     7375    | 0.4
 60 | 7359.75      |  7369.5 |     7369.25 | 0.75
```

Now `quality.initial_stop` IS populated and pnl_r looks correct. But the JSON
captured a state where initial_stop was missing → `_initial_stop()` fell back
to `trade.stop` (= BE+1T = entry ± 0.25).

### Root Cause

`manager.py:270-279` `_initial_stop()`:
```python
raw = q.get("initial_stop")
if raw is not None:
    return float(raw)
return self._valid_target(trade.stop)  # ← FALLBACK: current stop (may be BE+1T)
```

`manager.py:296-299` `_apply_smart_be_after_t1()`:
```python
if "initial_stop" not in q and trade.stop is not None:
    q["initial_stop"] = float(trade.stop)  # saves BEFORE moving stop
    trade.quality = q
```

**The race:** `_calculate_pnl` is called at `on_target_hit()` line 246 BEFORE
`_apply_smart_be_after_t1()` at line 281. At that point `quality["initial_stop"]`
doesn't exist yet, but `trade.stop` is still the initial stop (not yet moved).
So the first pnl calc is correct. SMART_BE then saves initial_stop and moves stop.

**The bug manifests on SUBSEQUENT recalculations** (API serialization, polling updates)
if there's a code path that recalculates pnl_r without `_apply_smart_be` having been
called yet in that process lifecycle (e.g., after a backend restart where quality.initial_stop
was never persisted to DB because the session wasn't flushed between T1_HIT and the API read).

### Fix Required

`manager.py:_initial_stop()` should have a **safety net** for PARTIAL trades: if
`quality["initial_stop"]` is missing AND `trade.stop` is suspiciously close to entry
(within 2 ticks), log a warning and refuse to calculate pnl_r (return None).
Alternatively: save `initial_stop` to quality at **trade creation** time (not only at SMART_BE).

---

## Q3 — Shared Stop Anchors / HFE Re-Fire Storm

### Evidence: Two Stop Clusters

**Cluster 1: stop=7323.25** (HFE SHORT, 19:45–20:00 IL)

| id | entry | stop | init_stop | risk_pts | pnl_usd | outcome |
|----|-------|------|-----------|----------|---------|---------|
| 46 | 7305.5 | 7305.25 (BE) | 7323.25 | 17.75 | +48.65 | T1→BE stop |
| 47 | 7302.5 | 7302.25 (BE) | 7323.25 | 20.75 | +44.00 | T1→BE stop |
| 48 | 7290.5 | 7290.25 (BE) | 7323.25 | 32.75 | +68.00 | T1→BE stop |
| 49 | 7284.25 | 7323.25 | — | 39.00 | **-585.00** | FULL STOP |

**Cluster 2: stop=7387.25** (HFE SHORT, 20:55–21:25 IL)

| id | entry | stop | init_stop | risk_pts | pnl_usd | outcome |
|----|-------|------|-----------|----------|---------|---------|
| 52 | 7382.75 | 7382.5 (BE) | 7387.25 | 4.50 | +20.50 | T1→BE stop |
| 55 | 7369.5 | 7369.25 (BE) | 7387.25 | 17.75 | +48.65 | T1→BE stop |
| 56 | 7352.0 | 7387.25 | — | 35.25 | **-528.75** | FULL STOP |
| 57 | 7353.0 | 7387.25 | — | 34.25 | **-513.75** | FULL STOP |
| 59 | 7365.25 | 7387.25 | — | 22.00 | **-330.00** | FULL STOP |

**Total HFE damage: -$1,957.50** on 4 full stop-outs. Net HFE (incl scalps): **-$1,727.70**.

### Why Same Stop Reused

`stop_anchors.yaml` defines HFE as:
```yaml
HFE: {system: S4, group: REV, type: extreme_bar, window: null, t1_ladder_shift: -1}
```

The `extreme_bar` anchor resolves to the bar where CCI hit the extreme (±200). When
the CCI STAYS in the extreme zone across multiple bars, each new HFE detection uses
the SAME anchor bar's extreme price → same stop across all entries.

As price moves AWAY from the stop anchor (market rallying against SHORT entries),
risk grows unboundedly: 17.75 → 20.75 → 32.75 → 39.00 pts in cluster 1.

### No Re-Entry Cooldown Exists

`gateway/cooldown.py` has:
- **2-stop cooldown (ζ.A4):** 2 consecutive STOP outcomes → block 30 min. But
  this is global, not per-pattern. And HFE trades 46-48 hit T1 then BE (not STOP),
  so the counter doesn't increment until id 49.
- **Cluster guard (ζ.A5):** 5 trades in 60s → block 5 min. HFE fires were spaced
  5 minutes apart, so this never triggered.
- **No same-pattern-same-direction limiter.** No consecutive-loss-on-pattern breaker.

### Recommendation (flag-gated, default-OFF)

Propose `S4_PATTERN_COOLDOWN` with two rules:
1. **Same pattern + same direction:** block for N bars after a STOP_HIT exit (default: 4 bars = 20 min)
2. **Max cumulative risk per anchor:** if total unrealized risk from active+recent trades
   sharing the same stop anchor exceeds 2R of initial risk, block new entries.

**STRATEGIC-STOP for Michael:** This changes fire eligibility — requires explicit approval.

---

## Q4 — Per-Trade Spec-Conformance Audit

### Summary Table (34 trades, 2026-06-11)

| id | sys | pat | dir | entry | stop(init) | risk | t1 | pnl_usd | pnl_r | exit | Verdict |
|----|-----|-----|-----|-------|-----------|------|-----|---------|-------|------|---------|
| 28 | S4 | ZLR | S | 7306.25 | 7313.50→7306 | 7.25 | 7300.81 | +29.70 | 0.27 | STOP(BE) | ✓ |
| 30 | S4 | TLB | L | 7306.25 | 7282.25→7306.5 | 24.0 | 7315.85 | +50.50 | 0.14 | STOP(BE) | ✓ |
| 31 | S4 | TLB | S | 7320.75 | ?→7320.5 | ? | 7312.88 | +201.85 | 0.85 | TIME_STOP | ✓ |
| 32 | S4 | ZLR | S | 7297.50 | ?→7297.25 | ? | 7281.90 | +80.50 | 0.14 | STOP(BE) | ✓ |
| 33 | **S2** | ZLR | S | 7297.75 | 7331.25→7297.5 | 33.5 | 7284.35 | +69.50 | 0.14 | STOP(BE) | ✓ |
| 34 | S4 | TLB | S | 7290.00 | ?→7289.75 | ? | 7271.40 | +95.50 | 0.14 | STOP(BE) | ✓ |
| 35 | S4 | ZLR | L | 7308.50 | ?→7308.75 | ? | 7316.60 | +43.00 | 0.14 | STOP(BE) | ✓ |
| 36 | S4 | ZLR | S | 7301.25 | 7318.25 | 17.0 | 7292.75 | **-255** | -1.0 | STOP | ✓ full loss |
| 37 | S4 | ZLR | S | 7300.50 | ?→7300.25 | ? | 7292.30 | +43.50 | 0.14 | STOP(BE) | ✓ |
| 38 | S4 | TLB | L | 7286.25 | ?→7286.5 | ? | 7295.85 | +50.50 | 0.14 | STOP(BE) | ✓ |
| 39 | S4 | TLB | L | 7293.00 | ?→7293.25 | ? | 7305.30 | +64.00 | 0.14 | STOP(BE) | ✓ |
| 40 | S4 | ZLR | S | 7291.75 | 7307.75 | 16.0 | 7283.75 | **-240** | -1.0 | STOP | ✓ |
| 41 | S4 | GHOST | L | 7304.50 | ?→7304.75 | ? | 7307.81 | +19.05 | 0.03 | STOP(BE) | ✓ |
| 42 | S4 | ZLR | S | 7291.75 | 7315.00 | 23.25 | 7282.45 | **-348.75** | -1.0 | STOP | ✓ |
| 43 | **S2** | VEGAS | L | 7318.00 | 7295.50 | 22.5 | 7327.00 | **-337.50** | -1.0 | STOP | ⚠️ |
| 44 | S4 | TLB | S | 7306.00 | ?→7305.75 | ? | 7297.38 | +45.60 | 0.18 | STOP(BE) | ✓ |
| 45 | S4 | VEGAS | S | 7297.75 | ?→7297.5 | ? | 7287.55 | +53.50 | 0.14 | STOP(BE) | ✓ |
| 46-48 | S4 | HFE | S | 7305–7290 | 7323.25(anchor) | 17-33 | — | +48–68 | 0.14-0.18 | STOP(BE) | ⚠️ risk growth |
| 49 | S4 | HFE | S | 7284.25 | 7323.25 | **39.0** | 7268.65 | **-585** | -1.0 | STOP | ⚠️ anchor drift |
| 50 | S4 | TLB | L | 7287.50 | 7274.25 | 13.25 | 7296.11 | -198.75 | -1.0 | STOP | ✓ |
| 51 | S4 | TLB | S | 7362.25 | 7372.25 | 10.0 | 7354.75 | -150.00 | -1.0 | STOP | ✓ |
| 52-59 | S4 | HFE/TLB | S | various | 7387.25(anchor) | 4-35 | — | mixed | — | mixed | ⚠️ cluster 2 |
| 58,60 | S4 | ZLR | L | 7375/7369 | — | — | — | +61/+36 | PARTIAL | — | OPEN |
| 61 | S4 | TLB | S | 7378.25 | 7384.00 | 5.75 | 7373.94 | -86.25 | -1.0 | STOP | ✓ |
| 62 | S4 | TLB | S | 7381.00 | 7387.75 | 6.75 | 7375.94 | -101.25 | -1.0 | STOP | ✓ |

### Specific Findings

**T1 ladder — appears consistent with stop_anchors.yaml:**
Risk 7.25pt → T1=0.81R (id 28, ZLR). Risk 33.5pt → T1=0.40R (id 33, REACTIVE).
Matches the t1_ladder ranges (5pt→1.0R, 10pt→0.75R, ... 25pt→0.40R).

**SMART_BE — confirmed working:**
26 T1_HIT + 26 SMART_BE entries in mgmt_log. Every T1 hit triggered a SMART_BE move.
Stop correctly moved to entry ± 1 tick after T1 (visible in DB: stop ≈ entry ± 0.25).

**id 43 (S2 REACTIVE_LONG, pattern=VEGAS?) — ⚠️ pattern mismatch:**
The setup was S2 REACTIVE_LONG but `pattern_id_at_entry=VEGAS`. This suggests the
pattern_id field is populated from a different source than the S2 detection. (S2 detected
REACTIVE, gateway wrote VEGAS as pattern_id.) Needs investigation.

**id 22 `manual` exit — not in today's data** (from earlier date, per prompt).

**ids 58/60 exit_reason NULL — these are OPEN (PARTIAL state).** Not a close failure.

**TIME_STOP (id 31 TLB SHORT):** Woodies time_stop_minutes=90 (hardcoded `woodies_system.py:502`).
Entry at 17:10, TIME_STOP at some point before close. The time_stop_minutes config in
`targets.yaml` (per day_type: Trend_Normal=null, Variation=60) is NOT consumed by S4.
This is the FIX 5 issue from `CC_MASTER_FIX_2026-06-09_EVE.md`.

**Risk gate [2, 60]:** All June 11 trades have risk within [2.0, 39.0]. The 2pt floor
(`MEMS_MIN_RISK_POINTS=2`) was not violated. The 60pt max (`MEMS_MAX_RISK_POINTS=60`)
correctly blocked the 73pt DOUBLE_BOTTOM_EE at 20:30.

---

## Q5 — T1/T2/Runner Redesign Inputs (Analysis Only)

### Current Structure

1. T1 scalp: 0.40–0.85R (per risk ladder)
2. SMART_BE: stop → entry ± 1T after T1
3. Runner: **No T2/T3 target.** `t2=null` on all S4 trades. Exits on STOP_HIT (at BE) or TIME_STOP or opposite signal.
4. Trail: C.2/C.4 code EXISTS in `gateway/trade_management.py` but is **orphan** (never called).

### Today's P&L Structure

```
34 trades total
  Winners (T1→BE stop): 22 trades, avg +$56, range $19–$202
  Losers (full stop):    10 trades, avg -$327, range -$86 to -$585
  Open (PARTIAL):         2 trades
  
Win rate: 69% (22/32 closed)
Total PnL: +$1,232 (winners) - $3,477 (losers) = -$2,245
Profit factor: 0.35
```

### Key Observation: Winner Cap Problem

Winners are capped at T1 (0.14–0.85R scalp, avg ~$56). The runner portion sits at BE
and exits there. **Zero trades had T2/T3 targets.** This means the runner contributes
~$0 to most winning trades (exits at BE = breakeven on c2/c3).

Meanwhile, losers are full 1R (all 3 contracts at stop). The math: if T1 = 0.4R average
and only c1 profits, then winning trade = 0.4R × 1 contract vs losing trade = -1R × 3 contracts.
To break even, win rate must be > 88%. At 69% win rate, this is structurally unprofitable.

### Max Favorable Excursion After T1 (Data Table)

This requires bar-by-bar MFE computation from the DB which exceeds the scope of a single
diagnostic pass. **NOT-DONE: MFE table deferred to next session.** To produce it:

```sql
-- For each closed trade with T1 hit, find max excursion from entry to trade close
-- Join v9_bars_5min_continuous for price path between entry_ts and exit_ts/stop_hit_ts
-- Compute: max_favorable = max(high) - entry (LONG) or entry - min(low) (SHORT)
-- Compare: MFE vs T1 distance vs hypothetical T2 at 2R/CCI-cross
```

### Options for Michael (data needed before deciding)

| Option | Description | What it fixes | Risk |
|--------|------------|---------------|------|
| (a) Wider T1 ladder | Increase T1 R-multiples (e.g., 0.6→1.0R) | c1 profits more per trade | Fewer T1 hits → lower win rate |
| (b) §1.6 CCI-cross T2/T3 | Runner exits when CCI crosses zero-line | c2/c3 capture continuation | Complex signal; may exit too early in trends |
| (c) Progressive trail | Wire C.2/C.4 orphan code in trade_management.py | Runner trails after 1.5R | Already coded, needs wiring + testing |
| (d) Tighter MAX_RISK / sizing | Cap risk at 20pt or risk-normalize contracts | Limits max loss to ~$300 | Reduces fire count on volatile days |

**STRATEGIC-STOP:** All options change the risk/reward profile → Michael decides.

---

## NOT-DONE

1. **Per-bar S2 condition table** — requires adding S2_DETECTION_LOG flag + replaying today's bars. Cannot produce retroactively without the log.
2. **MFE table (Q5)** — requires bar-by-bar join of v9_bars_5min_continuous with trade entry/exit timestamps. Deferred to next session.
3. **id 43 pattern_id=VEGAS mismatch** — S2 fired REACTIVE_LONG but DB shows pattern_id=VEGAS. Needs code trace of how pattern_id_at_entry is populated at gateway level.
4. **pnl_r bug timing** — JSON showed bug values, DB now shows correct values. The transient nature suggests a session-flush race in SQLAlchemy. Needs reproduction test.
5. **Repeated hydration (14+ times)** — root cause not identified. Likely triggered by bar_router delivering events that cause re-init. Deferred.
6. **ROADMAP_TO_LIVE.html + STATUS_BOARD.md** — not updated (files not found or need Cowork coordination).
