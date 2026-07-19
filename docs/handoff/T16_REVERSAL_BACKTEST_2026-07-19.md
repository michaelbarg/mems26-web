# T16 "Reversal-Tighten" Backtest — 2026-07-15 / 07-16 / 07-17

**Author:** cowork-dev (read-only analyst pass) · **Date run:** 2026-07-19
**Status:** ANALYSIS ONLY. No code, `.env`, or trading state was changed. This file is
left for cowork/Michael review — not committed/pushed per task instructions.

## 0. TL;DR

- 7 live/demo RTH trades total across the 3 dates qualify for consideration (0 on
  07-16 — see §2). Only **2 of 7 ever hit T1**, so only those 2 are things the T16
  rule could possibly touch; the other 5 get delta = $0 by construction.
- **Net effect if T16 had been live: +$36.25** over the 3 days (both the conservative
  and the looser trigger — they land on the identical bar in both qualifying trades
  in this sample, see §6).
- **1 HELPED** (id 400, +$32.50 — a clean case: rule would have banked T1-area profit
  on 2 runner contracts instead of giving it back to a breakeven stop). **6 NEUTRAL**
  (5 never reached T1; 1 has a +$3.75 edge case muddied by a data gap, see §5).
  **0 HURT.**
- **Honest read: N is far too small to mean anything.** 2 touched trades is an
  anecdote, not a backtest. Directionally encouraging (no downside observed), but
  this sample happens to contain zero whipsaw-after-reversal cases where tightening
  would have clipped a runner that later ran further in the original direction —
  which is the actual risk T16 introduces. Do not ship on this evidence alone.

---

## 1. Access verification

```
$ curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v9/health
200
```

Backend reachable, proceeded.

## 2. Trade universe: mode in (live, demo), RTH 09:30-16:00 ET, 2026-07-15/16/17

Data pulled via:
```
curl -s "http://localhost:8000/api/v9/chart/replay?date=2026-07-15" -o /tmp/replay_0715.json
curl -s "http://localhost:8000/api/v9/chart/replay?date=2026-07-16" -o /tmp/replay_0716.json
curl -s "http://localhost:8000/api/v9/chart/replay?date=2026-07-17" -o /tmp/replay_0717.json
curl -s "http://localhost:8000/api/v9/trades/recent?limit=100" -o /tmp/trades_recent_100.json
```
`chart/replay` JSON shape: `{date, bars_source, counts, bars[], cvd[], levels, trades[]}`.
`bars_source` = `"woodies"` for all 3 days (the clean/canonical source per
`docs/SOURCE_OF_TRUTH.md`, not the flagged-stale `v9_bars_5min`).

`counts` per day: 07-15 `{bars:165, cvd:72, trades:11}` · 07-16 `{bars:158, cvd:78,
trades:0}` · 07-17 `{bars:204, cvd:78, trades:10}`. (Those trade counts are
pre-mode-filter, all systems/modes.)

Filter applied (mode in live/demo, RTH 09:30-16:00 ET), computed programmatically
(not by eye) from `/tmp/trades_recent_100.json` (covers ids 287-404, comfortably
spanning all 3 dates):

```python
from datetime import datetime, time
from zoneinfo import ZoneInfo
ET = ZoneInfo('America/New_York')
RTH_START, RTH_END = time(9,30), time(16,0)
# filter: t['mode'] in ('live','demo'), entry_ts.astimezone(ET).date() in {15,16,17},
# RTH_START <= entry_et.time() <= RTH_END
```
Result (id, mode, date, entry ET, in_RTH, dir, t1_hit, pnl_usd, exit_reason):
```
(377, 'live', '2026-07-15', '11:05:44', True,  SHORT, False,  -82.50, STOP_HIT)
(379, 'live', '2026-07-15', '11:57:13', True,  SHORT, True,   +77.50, T2_HIT)
(381, 'live', '2026-07-15', '14:00:07', True,  SHORT, False,  -56.25, STOP_HIT)
(383, 'live', '2026-07-15', '14:10:03', True,  LONG,  False,    0.00, phantom_reconcile)
(385, 'live', '2026-07-15', '14:24:38', True,  LONG,  False,  -37.50, STOP_HIT)
(388, 'demo', '2026-07-17', '02:01:42', False, LONG,  False,    0.00, manual)   <- EXCLUDED, pre-market
(396, 'live', '2026-07-17', '10:55:03', True,  SHORT, False,  -78.75, STOP_HIT)
(400, 'live', '2026-07-17', '14:10:07', True,  SHORT, True,   +20.00, STOP_HIT)
```
7 trades qualify. Only 379 and 400 have `t1_hit=True` — the rule can only ever
touch these two; the other 5 are automatically delta=$0 (rule triggers "after the
T1 fill", which never happened).

**07-16 has ZERO trades of ANY mode.** Verified three independent ways: (a)
`chart/replay?date=2026-07-16` counts.trades=0; (b) `/api/v9/trades/recent?limit=100`
contains no row with `entry_ts` on 07-16 (checked programmatically over all 100
rows, any mode); (c) trade ids 387 and 389-394 (the gap between 07-15's last id 386
and 07-17's first id 388/395) all return `{"detail":"Trade not found"}` — they were
never created, not deleted. `day_type/classify_replay?date=2026-07-16` shows
`ib_class: NARROW`, `vol_ratio: 0.665` (below-average volume) — a quiet day, not a
feed outage (bars/cvd data exist normally). **T16 has nothing to evaluate on 07-16.**

## 3. Contract-structure finding (deviates from the task brief — flagged per Rule 2)

The task brief describes 4 contracts (C1→T0 scalp, C2→T1, C3→T2, C4→T3/runner).
**The actual DB records for all 7 qualifying trades show exactly 3 legs**
(`contracts_pnl: [C1, C2, C3]` mapped to `t1, t2, t3` — no `t0` field exists on the
trade record at all). Example (`trades/recent`, id 400):
```json
"contracts_pnl": [
  {"id":"C1","status":"HIT","exit_price":7504.75,"pnl_usd":17.5,"pnl_r":14.0},
  {"id":"C2","status":"OPEN","exit_price":7508.0,"pnl_usd":1.25,"pnl_r":1.0},
  {"id":"C3","status":"OPEN","exit_price":7508.0,"pnl_usd":1.25,"pnl_r":1.0}
]
```
This matches project memory's standing ruling ("07-10 RULING: 2 contracts —
SUPERSEDED 07-12: חזרה ל-3 חוזים") and the code: `backend/v9/systems/stop_anchors/sizing.py:116-128`
implements `FIXED_CONTRACTS_3` (and newer `_2`/`_4` overrides). **Current `.env`
(read today, 2026-07-19) has `FIXED_CONTRACTS_4=1` (top precedence), `_3=0`, `_2=0`**
— i.e. the system is CURRENTLY configured for 4 contracts, but the historical trades
being backtested here (07-15/07-17) were executed under the 3-contract regime (every
single record confirms 3 legs, none show 4). **The 4-contract flip happened after
these trade dates.** I used the real 3-contract data as ground truth (Rule 1/2) rather
than force-fitting the task's 4-contract/T0 framing onto data that doesn't have it.
This also means: a repeat of this backtest on trades occurring after the `_4` flip
would need a 4-leg version of the same logic — mechanically the same approach
(contracts that already hit keep their real P&L; the rest get pulled at the reversal
bar), just with one more leg.

Verified `$5.00/point/contract` (task's stated conversion) against the real records
before trusting it for the counterfactual math: id 400 C1 = $17.50 for a 3.5pt move
(17.50/3.5 = $5.00/pt); id 379 C1 = $25.00 for 5.0pt (5.00/pt), C2 = $52.50 for 10.5pt
(5.00/pt). Confirmed for both trades regardless of the `metadata.sizing` label
("full"/"half"/`4`/`0`) — each `contracts_pnl` leg in these two trades represents
1 contract at $5/pt.

## 4. Rule operationalization — exact choices made where the brief was ambiguous

1. **Eligibility**: only trades with `t1_hit=True` (379, 400). The other 5 get
   `reversal_detected = N/A (never reached T1)`, delta = $0.00 by construction.
2. **Bar source**: `bars[]` from `chart/replay` (`bars_source=woodies`), field
   `cum_delta` (non-null during RTH) as cumulative delta as-of that bar's close.
   Bar-to-bar delta = `cum_delta[i] - cum_delta[i-1]`. Cross-checked against the
   separate `cvd[]` array's `d` field wherever timestamps could be matched by value
   (e.g. cum=-2297 matched a `cvd` entry with `d:-129`, and -2297-(-2168)=-129 from
   the bars series too) — confirms the derived per-bar delta is correct.
3. **Timestamps**: `bars[].ts` carries an explicit `+03:00` offset; converted to UTC
   (-3h, exact) then to ET (-4h more, EDT in July) via `zoneinfo`. Cross-validated
   against the trade timeline's own UTC-tagged `MGMT_*` events (e.g.
   `MGMT_T1_HIT.detail.ts = "...+00:00"`) — the arithmetic itself is exact/unambiguous.
4. **Bar indexing after the fill**: T1 fills mid-bar. Call that bar **B0** — it
   straddles the fill instant, so it is NOT itself eligible as an "after the fill"
   close for the 2-consecutive-closes count (using it would also create a causality
   problem — see trade 379 in §5). B1, B2, ... follow in order. Earliest possible
   trigger bar is **B2** (needs close[B1] vs close[B0], AND close[B2] vs close[B1],
   both adverse).
5. **"CVD flips against the position"**: operationalized as the TRIGGER bar's own
   bar-to-bar delta sign being adverse (positive/buying for a SHORT, negative/selling
   for a LONG). This is a level-check on the trigger bar itself, not a same-bar
   sign-change from the prior bar — the 2-consecutive-closes condition already
   supplies the "reversal" dynamic; CVD is the confirming filter.
6. **Fill assumption (per task instruction)**: once triggered, remaining contracts
   are assumed to fill exactly at "current bar's close ± 2 ticks (0.5pt) in the
   trade's favor" (close − 0.5pt for a SHORT, + 0.5pt for a LONG) — I did not
   additionally check whether the next bar's range would actually reach that price;
   the task explicitly simplifies this to an assumed fill. Part (b), "move stop to
   lock," doesn't change the P&L model since part (a)'s fill is assumed to complete
   first (stop is a backstop that's moot if the target-pull fills as assumed).
7. **Contracts that already hit their real target before the trigger bar** keep
   their actual recorded P&L unchanged (per task instruction).

## 5. Data-quality caveat: bars-vs-trades timestamp/price alignment (read before trusting exact minute labels)

Before trusting absolute clock alignment, I tried to verify it (Rule 2) and found a
real discrepancy: the trade record's own entry/target/stop prices frequently do NOT
fall inside the OHLC range of the `woodies` bar whose time-converted label matches
that trade event's timestamp. Example: id 400 entry = 7508.25 @ ET 14:10:07, but the
bar labeled ET 14:10:00-14:15:00 has range [7492.25, 7500.00] — doesn't contain
7508.25. The bar that DOES contain 7508.25 (range [7502.25, 7510.00]) is labeled
ET 14:00:00-14:05:00, ~10 minutes earlier. I tested several trades/events for a
single constant offset that would fix this and found none — the mismatch magnitude
varies (roughly 5-20+ minutes across different events), which is consistent with
project memory's own prior finding of a **"wandering" (non-constant) lag** in bar
timestamps (`docs/handoff` notes on the `TS-HOUR-fix` / GHOST-price contamination,
same week as these trade dates) — not something I can resolve inside a read-only
backtest, and out of scope to fix here.

**How I handled it:** I anchored the bar sequence by TIME (the standard, unbiased
method — the alternative, anchoring by price-level matching, is unreliable here
because price chopped back through the same 10-20pt zone repeatedly on both days,
producing multiple spurious "matches"). I then sanity-checked that the resulting
bar sequence tells a directionally-sane story (price moves toward the target after
entry, later reverses) — it does, for both trades below. **Read the specific minute
labels in the bar tables below as approximate; the sequence/order and the
up-down-close / CVD-sign pattern are the reliable part** and are what the rule
actually depends on.

## 6. Per-trade reconstruction — the 2 trades that reached T1

### Trade 379 — 2026-07-15, SHORT, GB100, system 4

Entry 7594.75 @ ET 11:57:13. T1 (7589.75) filled 12:02:29 ET → stop moved to BE
7594.50. T2 (revised 7566.75→7584.25 via `MGMT_TARGET_REALISM` at 12:05:03 ET) filled
**12:06:45 ET — only 4m16s after T1.**

```
ET label   o        h        l        c        cum_delta   bar_delta
11:55:00   7584.00  7586.75  7579.50  7586.50   -3880.0     —
12:00:00   7587.00  7590.75  7585.75  7589.00   -3380.0     +500  <- B0 (T1 fills here)
12:05:00   7589.00  7594.00  7588.25  7591.25   -3929.0     -549  <- B1 (T2 fills 12:06:45, mid-bar)
12:10:00   7591.25  7592.75  7587.75  7587.75   -2918.0    +1011  <- B2
12:15:00   7588.25  7594.75  7587.50  7594.00   -2620.0     +298  <- B3 (up close #1)
12:20:00   7594.00  7596.00  7592.25  7594.50   -1842.0     +778  <- B4 (up close #2 + CVD+778 adverse -> TRIGGER)
```

**T2 cannot be preempted**: the earliest a 2-consecutive-close signal could even be
confirmed is when B1 closes (12:10:00 ET) — a full 3m15s AFTER T2 already filled
naturally off live price (12:06:45 ET). C1 ($25.00) and C2 ($52.50) keep their real
P&L regardless of trigger definition or bar-indexing choice.

**C3 (runner, target t3=7552.75) is undocumented**: `contracts_pnl` shows
`{"id":"C3","status":"OPEN","exit_price":7594.75,"pnl_usd":-0.0}` — exit price equals
entry price and there is NO exit event for C3 anywhere in
`/api/v9/trades/379/timeline` (only ENTRY_FILL, T1_HIT, MGMT_SMART_BE,
MGMT_TARGET_REALISM, T2_HIT/EXIT — 8 events total, none reference C3 closing). I do
**not** know what actually happened to this contract; the recorded $0.00 looks like a
bookkeeping default, not a documented market outcome. **Flagging this explicitly —
reconstruction for this leg is uncertain.**

Scanning bars after B1 for the reversal condition (both variants — price-only and
price+CVD — agree here): 2 consecutive up-closes (7587.75→7594.00→7594.50) confirmed
at the 12:20-labeled bar, whose own CVD delta (+778) is also adverse to the SHORT.
**Reversal detected.** Pulled price = 7594.50 − 0.50 = **7594.00**. Counterfactual
C3 = (7594.75 − 7594.00) × $5 = **$3.75**.

**Trade 379 total: actual $77.50 (25.00+52.50+0.00) → counterfactual $81.25
(25.00+52.50+3.75) → delta +$3.75 → NEUTRAL** (below the ±$5 threshold either way,
so this verdict is robust to the C3 data-gap uncertainty even though the exact
number isn't fully trustworthy).

### Trade 400 — 2026-07-17, SHORT, BEAR_FLAG_SHORT, system 2

Entry 7508.25 @ ET 14:10:07. T1 (7504.75) filled 14:15:18 ET → stop moved to BE
7508.00 (`MGMT_SMART_BE: to 7508.0, from 7512.0`). Stop hit 14:30:29 ET @ 7508.00
(`STOP_HIT`).

```
ET label   o        h        l        c        cum_delta   bar_delta
14:10:00   7499.25  7500.00  7492.25  7492.50   -7648.0     +287
14:15:00   7492.25  7495.25  7490.75  7494.50   -8484.0     -836   <- B0 (T1 fills here)
14:20:00   7494.25  7494.25  7488.50  7488.50   -7601.0     +883   <- B1 (down close, favorable)
14:25:00   7488.50  7498.00  7486.25  7496.75   -7049.0     +552   <- B2 (up close #1)
14:30:00   7497.00  7501.25  7492.50  7495.25   -6887.0     +162   <- B3 (down, resets streak)
14:35:00   7495.25  7500.50  7492.50  7493.50   -5485.0    +1402   <- B4 (down)
14:40:00   7493.50  7501.50  7491.25  7500.00   -4786.0     +699   <- B5 (up close #1)
14:45:00   7500.00  7505.75  7498.50  7505.25   -4444.0     +342   <- B6 (up close #2 + CVD+342 adverse -> TRIGGER)
```

Consecutive-close scan (SHORT, "adverse" = up-close): B0→B1 down · B1→B2 up(#1) ·
B2→B3 down (resets) · B3→B4 down · B4→B5 up(#1) · **B5→B6 up(#2)** — first
2-in-a-row confirmed at B6, whose own CVD delta (+342) is also adverse.
**Both the conservative and the looser trigger fire at the identical bar (B6)** —
in this trade the price-only signal never appears earlier than the CVD-confirmed one.

Pulled price = 7505.25 − 0.50 = **7504.75** (coincidentally equals the original T1
price). C2 and C3 (unfilled at trigger time) counterfactual = (7508.25 − 7504.75) ×
$5 = **$17.50 each**, vs. their actual $1.25 each (closed at the 7508.00 BE stop).

**Trade 400 total: actual $20.00 (17.50 + 1.25 + 1.25) → counterfactual $52.50
(17.50 + 17.50 + 17.50) → delta +$32.50 → HELPED.** This is the cleanest case in
the sample: price ran 22pts in favor after entry (mfe_pts=22.0 per the trade record),
then fully reversed and gave back the runners to breakeven-plus-a-tick. T16 would
have locked most of that move instead.

## 7. Summary table (all 7 qualifying trades)

| date | id | pattern | dir | actual_pnl | cf_pnl (both triggers) | delta | verdict | reversal_detected |
|---|---|---|---|---|---|---|---|---|
| 2026-07-15 | 377 | ZLR | SHORT | -82.50 | -82.50 | 0.00 | NEUTRAL | N/A — never reached T1 |
| 2026-07-15 | 379 | GB100 | SHORT | +77.50 | +81.25 | **+3.75** | NEUTRAL | YES — post-T2, C3 leg only (C3 actual is undocumented, see §6) |
| 2026-07-15 | 381 | HTLB | SHORT | -56.25 | -56.25 | 0.00 | NEUTRAL | N/A — never reached T1 |
| 2026-07-15 | 383 | REACTIVE_LONG | LONG | 0.00 | 0.00 | 0.00 | NEUTRAL | N/A — never reached T1 (also: exited via `phantom_reconcile`, a pre-existing data-quality flag unrelated to T16) |
| 2026-07-15 | 385 | ZLR | LONG | -37.50 | -37.50 | 0.00 | NEUTRAL | N/A — never reached T1 |
| 2026-07-16 | — | — | — | — | — | — | — | **no trades exist for this date (any mode) — see §2** |
| 2026-07-17 | 396 | INITIATIVE_SHORT | SHORT | -78.75 | -78.75 | 0.00 | NEUTRAL | N/A — never reached T1 (stopped 40s after entry) |
| 2026-07-17 | 400 | BEAR_FLAG_SHORT | SHORT | +20.00 | +52.50 | **+32.50** | **HELPED** | YES — both triggers, bar ET~14:45-label (see §6) |


## 8. NET totals

| Trigger variant | actual net | counterfactual net | net delta |
|---|---|---|---|
| Conservative (CVD + 2 adverse closes) | -$157.50 | -$121.25 | +$36.25 |
| Looser (2 adverse closes only, ignore CVD) | -$157.50 | -$121.25 | +$36.25 |

Actual net = -82.50+77.50-56.25+0.00-37.50-78.75+20.00 = **-157.50**.
Counterfactual net = -82.50+81.25-56.25+0.00-37.50-78.75+52.50 = **-121.25**.

**Trades touched by the rule** (at least one leg's outcome would change): **2 of 7**
(379 — one leg only, C3; 400 — two legs, C2+C3). **Helped: 1. Neutral: 6. Hurt: 0.**

## 9. Sensitivity — conservative vs. looser trigger

**No difference in this sample.** In both trade 379 and trade 400, the first bar
that produced 2 consecutive adverse closes was *also* a bar with adverse-sign CVD —
the order-flow filter never delayed or blocked a trigger that the price-only
condition would have caught anyway, and it never fired a bar earlier than the
price-only condition either (CVD alone, without 2 adverse closes, is not sufficient
under either rule reading). **This means the sample cannot show the sensitivity the
task anticipated** — the interesting cases (price reverses without order-flow
confirmation and then continues, which the CVD filter is meant to protect against;
or CVD flips but price hasn't confirmed yet) simply don't occur in these 2 trades.
A larger sample, ideally including at least one whipsaw/failed-reversal day, is
needed before the conservative-vs-loose choice can be evaluated on evidence rather
than argued in the abstract.

## 10. Caveats (read before acting on this)

1. **N is tiny.** 2 touched trades (1 helped, 1 marginal-neutral) is an anecdote.
   Neither trigger variant has been tested against a case where tightening would
   have *hurt* (clipped a runner that kept running) — none of these 3 days happened
   to contain one. Absence of a HURT case here is not evidence T16 has no downside.
2. **Contract-structure mismatch** (§3): backtested against the historical 3-contract
   regime (C1/C2/C3 = T1/T2/T3); current `.env` is now 4-contract
   (`FIXED_CONTRACTS_4=1`). Same logic should generalize but hasn't been tested
   against a 4-leg trade.
3. **Bar/trade timestamp alignment** (§5): woodies bar OHLC doesn't always contain
   the trade's own recorded price at the time-matched clock label; magnitude of the
   mismatch varies (not a fixed offset), consistent with a previously-flagged
   wandering-lag issue in this codebase. Bar sequence/order and close-direction/CVD
   sign are trustworthy; exact minute labels are approximate.
4. **Trade 379's C3 leg has no recorded exit event** — actual outcome ($0.00) is
   undocumented/uncertain, independent of T16. The verdict (NEUTRAL) is robust to
   this because the delta is small either way, but the exact dollar figure isn't
   fully trustworthy.
5. **Trade 383 exited via `phantom_reconcile`** — a non-market, reconciliation-driven
   exit (pre-existing data-quality flag, unrelated to T16; noted for completeness,
   didn't affect any total since `t1_hit=False`).
6. **"Move stop to lock" (part b of the rule) was not separately modeled** — assumed
   moot given the task's instruction to treat part (a)'s fill as given.
7. Several reasonable-but-not-forced definitional choices were made where the task
   was ambiguous (§4) — documented so they can be re-argued; for this specific
   sample, re-litigating them would not change the bar each trade triggers on.

## 11. Bottom line

T16 would have added **+$36.25** net over these 3 days (7 trades, only 2 of which
it ever touched), all upside, no observed downside, with identical results between
the conservative and loose trigger definitions. That is a real, clean win on trade
400 (a textbook case of giving back an in-favor move to a breakeven stop) and a
wash on trade 379. **But this is not a green light** — the sample is 2 touched
trades from 2 of 3 days (07-16 contributed nothing), it contains zero examples of
the failure mode the CVD filter is supposed to guard against (a reversal that
partially confirms and then continues in the original direction anyway, where
tightening would have been wrong, vs. one that snaps back, where tightening would
have banked the runner), and the conservative/loose distinction is untested by this
sample. Recommend: widen the backtest window (more days, ideally including at
least one trend day with a clean pullback that resumed) before treating this as
evidence either way, and specifically hunt for a whipsaw case to pressure-test the
downside before considering a build.

## W1 EXTENSION (cursor 2026-07-19 evening re-run)

Expanded universe beyond 07-15/16/17: **all** live/demo RTH trades with `t1_hit` (N=15).
Days with ≥3 T1: **2026-07-02, 2026-07-10**.

Raw (conservative CVD+2closes before exit):
```
trig=1 helped=1 hurt=0 whipsaw_hurt=0 net=+$175 (#282)
price-only: trig=3 helped=2 hurt=0 whipsaw_hurt=0 net=+$181.25 (+#344 ge3)
```
Prior evening W1 pass (same universe): CVD trig=3 helped=3 hurt=0 net=+$207.5.

**Conclusion line:** T16 **YES build** / **NO AUTO** · trigger = **CVD-adverse + ≥2 adverse closes after T1 before exit**.
Full write-up: `T16_WHIPSAW_HUNT_W1_2026-07-19.md`. Aligns with Michael ruling א' (`SYSTEM6_REVERSAL_TIGHTEN_V1` OFF).
