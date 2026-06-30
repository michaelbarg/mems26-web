# SIM 2026-06-30: What Should Have Fired — End-to-End Trace

**Session:** Variation (LOCKED_LOW_CONF), opened OPEN_DRIVE, +72pt range (7495.75→7567.75)
**Result:** 0 trades from 20 detections (11 S4 + 9 S2). **All fixes now committed.**

---

## Signal Trace Table — S4 Woodies (11 signals in `v9_woodies_signals`)

| ID | ET Time | Pattern | Dir | CCI | CONT/REV | Day-Type@Signal | DIED_AT | Reason |
|----|---------|---------|-----|-----|----------|-----------------|---------|--------|
| 5099 | 12:40 | ZLR | LONG | 74 | CONT | Variation | **A7** | `fire_setup=None` (best.stop gate) |
| 5100 | 12:45 | ZLR | LONG | 87 | CONT | Variation | **A7** | same |
| 5101 | 13:30 | GHOST | SHORT | -42 | REV | Variation | Gateway | `Variation → REV blocked` (Stage-1 family) |
| 5102 | 13:40 | GHOST | SHORT | -151 | REV | Variation | Gateway | same |
| 5103 | 13:45 | GHOST | SHORT | -29 | REV | Variation | Gateway | same |
| 5104 | 13:50 | ZLR | SHORT | -109 | CONT | Variation | **A7** | `fire_setup=None` |
| 5105 | 14:08 | ZLR | SHORT | -4 | CONT | Variation | **A7** | same |
| 5106 | 15:25 | GHOST | SHORT | 91 | REV | Variation | Gateway | REV blocked + counter-trend (BLUE) |
| 5107 | 15:30 | GHOST | SHORT | 41 | REV | Variation | Gateway | same |
| 5108 | 15:35 | GHOST | SHORT | -32 | REV | Variation | Gateway | REV blocked |
| 5109 | 15:40 | GHOST | SHORT | -110 | REV | Variation | Gateway | REV blocked + late session |

## Signal Trace Table — S2 Five-Min (9 setups in `v9_five_min_setups`)

| ID | ET Time | Pattern | Dir | CONT/REV | day_type_at_fire | DIED_AT | Reason |
|----|---------|---------|-----|----------|------------------|---------|--------|
| 262 | 09:55 | INITIATIVE_LONG | LONG | CONT | **(empty)** | **Auth** | UNKNOWN→Neutral_Center→SKIP |
| 263 | 10:30 | DOUBLE_BOTTOM_EE_LONG | LONG | REV | (empty) | Auth | same |
| 264 | 10:40 | REACTIVE_LONG | LONG | REV | (empty) | Auth | UNKNOWN→Neutral_Center→FULL, but position gate: UNKNOWN |
| 265 | 10:45 | REACTIVE_SHORT | SHORT | REV | (empty) | Auth | same |
| 266 | 10:50 | INITIATIVE_SHORT | SHORT | CONT | (empty) | Auth | UNKNOWN→SKIP |
| 267 | 12:40 | REACTIVE_LONG | LONG | REV | Variation | Gateway | `Variation → REV blocked` |
| 268 | 13:10 | REACTIVE_SHORT | SHORT | REV | Variation | Gateway | same |
| 269 | 14:15 | REACTIVE_LONG | LONG | REV | Variation | Gateway | same |
| 270 | 15:10 | DOUBLE_BOTTOM_EE_LONG | LONG | REV | Variation | Gateway | same |

---

## Root Causes — Definitive

### ROOT 1: `fire_setup=None` → A7 FAIL → `ready_to_route=False` (S4 CONT signals)

**The SINGLE real blocker for with-trend S4 signals.** ZLR LONG/SHORT (the +EV CONT patterns) all died at A7 because `fire_setup` stayed `None`.

Code path: `woodies_system.py:616` gated on `best.entry_price and best.stop`. When `best.stop` was falsy, the entire L617-823 block was skipped → `fire_setup=None` → A7 returned FAIL("missing fire_setup for routable pattern") → `ready_to_route=False` → no route.

**Fix committed:** `fd153c3` — `_effective_stop` fallback (tries `best.stop`, then `_last_v2_sizing.stop_price`).

### ROOT 2: Day-type UNKNOWN for first 90 min of RTH (S2 CONT signals)

**The SINGLE real blocker for early S2 CONT signals.** `day_type_at_fire` empty for all S2 setups before 11:00 ET. The auth table maps `UNKNOWN → Neutral_Center → SKIP` for INITIATIVE. Setup 262 (INITIATIVE_LONG, the only CONT S2 signal in the first hour) was killed by this.

**Fix committed:** `bc1a1fd` — `get_live_day_type()` shared helper reads live `app.state.day_type_machine.day_type` for both gate and auth.

### ROOT 3: REV correctly blocked on Variation (NOT a bug)

GHOST SHORT (5 signals), REACTIVE (3 signals post-lock), DOUBLE_BOTTOM (1 signal) — all REV family. `DAYTYPE_PATTERN_AWARE_V1` correctly blocks REV on Variation/Trend. **Backtest: REV on trend = −34.6R (74 trades, 38% win). This is working as designed.**

---

## The "Should Have Fired" Call

| Signal | Pattern | Dir | Valid? | Would Trade With Fix? |
|--------|---------|-----|--------|-----------------------|
| 5099 | ZLR LONG | LONG | **YES** — CCI 74, BLUE trend, Variation (CONT allowed) | **YES** — `fd153c3` builds fire_setup → A7 PASS → route → gateway allows CONT on Variation |
| 5100 | ZLR LONG | LONG | **YES** — CCI 87, BLUE, Variation | **YES** — same |
| 262 | INITIATIVE_LONG | LONG | **YES** — 09:55 ET, early uptrend | **YES** — `bc1a1fd` reads live day_type → auth FULL (not SKIP) |
| 5104 | ZLR SHORT | SHORT | **MAYBE** — CCI -109, RED trend, but Variation with upward expansion → counter-expansion | Gateway would block: Variation SHORT above IBH = counter-expansion |
| 5105 | ZLR SHORT | SHORT | **NO** — CCI -4, weak signal | Marginal |

**Bottom line:** 2-3 valid with-trend CONT longs (ZLR 5099/5100 + INITIATIVE 262) should have traded. Combined fix (`fd153c3` + `bc1a1fd`) unblocks both paths.

---

## Outstanding Questions for Next Session

1. **ZLR RISK_CAP:** Were ZLR 5099/5100 stops within the 15pt cap? Without log traces (log was rotated), we can't confirm. The `breakout_bar/1` config change should keep stops tight (~7pt), but need live verification.
2. **DLL ZLR flag mechanism:** The `ZLR-TRACE` instrumentation (`3a8c16b`) is live — check the next session's logs for `Mechanism A` (current_bar override drops flag) vs `Mechanism C` (not-new-bar early return).
3. **S2 five_min feed:** `v9_bars_5min` was frozen 06-29 and recovery unverified. If S2 doesn't receive bars, no REACTIVE/INITIATIVE detection occurs (market-dependent, not a gate bug).

---

## Fix Summary — All Committed

| Fix | Commit | Status |
|-----|--------|--------|
| fire_setup=None A7 FAIL | `fd153c3` | Committed, needs restart |
| Day-type live source (gate + auth) | `bc1a1fd` + `b5eb3e9` | Committed, `DAYTYPE_GATE_LIVE_V1=1` in .env |
| is_synthetic in INSERT | `e6b9d69` | Committed |
| ZLR breakout_bar/1 stop | `config/stop_anchors.yaml` | Applied live |
| Stage-1 family gate (REV blocked on trend) | `57fb501` | Correct, working as designed |

## NOT-DONE
- ❌ Reversals NOT enabled (backtest −34.6R)
- ❌ GIANT_BAR_EXCLUDE not changed (Michael decision)
- ❌ DLL ZLR flag mechanism diagnosis — pending next session logs
- ❌ S2 five_min feed recovery — pending next RTH open

---

## Cowork Verification Addendum (2026-06-30, post-CC, Rule 5)

**Verified raw:** signals 5099–5109 match this table (`v9_woodies_signals` ts/dir/cci). ROOT 1 (A7 `fire_setup=None`) + ROOT 2 (UNKNOWN→SKIP auth) confirmed real + committed (`fd153c3`, `bc1a1fd`). The with-trend ZLR 5099/5100 fired **12:40/12:45 ET = 11:40/11:45 CT — BEFORE `fd153c3` went live (13:08 CT restart)** → died at A7 pre-fix (correct). REV-blocked confirmed by design (−34.6R backtest).

**NEW finding — Mechanism D (transient zlr flag):** `v9_bars_5min_woodies.zlr_detected` is **mutated 1→0 by later upserts**. Cowork observed bars **21:35/21:40 IL with `zlr_detected=1` at ~21:50 IL, then `zlr_detected=0` for the same bars** ~10 min later. The bridge `INSERT OR REPLACE` (`bars.py:914`) overwrites each bar per push; a later DLL re-export without the flag erases the transient `zlr=1`. **Implication:** the DLL ZLR flag is short-lived — for `process_bar` to build the DLL-ZLR it must receive a push with `zlr=1` **AND** that push must be a new-bar (else Mechanism C early-return `woodies_system.py:351` skips it). The flag often arrives **mid-bar (non-new-bar push)** → skipped → then overwritten → **no ZLR signal ever created** (which is why this divergence is invisible to a `v9_woodies_signals`-based trace). **D likely compounds with C and is the core of the chart↔backend ZLR divergence.**

**Next-session verdict** (scheduled `mems26-zlr-trace-verdict`, 07-01 09:45 CT): correlate the `ZLR-TRACE` lines with the bar's `zlr_detected` over time to confirm A vs C vs D. Fix per mechanism (C/D → build the DLL-ZLR on the `0→1` flag transition even on a non-new-bar push, before it's overwritten; flag-gated + Michael sign-off).

**Minor:** signal 5110 (LONG, CCI 32, 19:55 UTC = 15:55 ET) appeared after CC wrote this — outside the table, consistent (late-session CONT long).
