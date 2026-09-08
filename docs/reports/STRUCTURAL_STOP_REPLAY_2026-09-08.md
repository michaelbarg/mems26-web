# STRUCTURAL STOP REPLAY — 2026-08-10 → 2026-09-07

Measured 2026-09-08 (cowork, read-only, no service touched). One variable: **the initial stop**.
Same entries, same direction, same target ladder, replayed on real `v9_bars_5min_woodies` bars.
MES = **$5.00 / point**; every $ figure below is `points × contracts × $5` and names its contract count.

## 0. Answer first — the flip counts

| flip | n (of 54) | $ moved |
|---|---|---|
| **A-win → B-loss (the killer)** | **4** — #942, #968, #971, #1069 | **−$390.00** |
| A-loss → B-win | **7** — #668, #756, #822, #862, #873, #875, #950 | +$1,230.00 |
| unchanged sign | 43 | — |

The flip table is the *good* news for the structural stop and it is still not enough: the money moves
the other way, because the 23 rows that got **worse** lost more than the 11 that got better
(−$2,451.30 vs +$1,322.50, **net −$1,128.80**). B wins *more often* (28 W vs 25) and loses *far* more
per loss (avg loss −$144.23 vs −$74.44). That is the classic wide-stop signature.

## 1. A vs B — totals

Set: **54 of 68** live trades since 2026-08-10 — the trades with a broker price basis, exactly the set
from `ASYMMETRY_17D_2026-09-08.md` §0 (51 Sierra `Closed Trade Profit/Loss` joined on our order ids ·
2 `pnl_sierra` · 1 DLL-journal-complete). The 14 unpriced (`MAE_SCRATCH`/`SIERRA_FLAT`/
`phantom_reconcile`) are shown separately. **Zero trades excluded for want of forward bars.**

| arm | contracts | n | total $ | W / L | how it ended (STOP / TARGET / CLOSE) |
|---|---|---|---|---|---|
| **A — as traded** (`quality.metadata.stop_initial`) | as traded | 54 | **+$283.80** | 25 / 29 | 34 / 17 / 3 |
| **B1 — structural, same size** | as traded | 54 | **−$845.00** | 28 / 26 | 21 / 21 / 12 |
| **B2 — structural, sizer recomputed** | live sizer | 24 traded, **30 rejected** | **−$444.80** | — | — |
| **B3 — B2 without the min-3 reject** | 1–5 ct | 42 traded, 12 rejected (>30 pt) | **−$1,133.05** | — | — |
| *A restricted to the 24 B2 survivors* | as traded | 24 | *+$80.00* | — | — |

All 68 (sensitivity): A −$552.50 · B1 −$1,400.00 · B2 −$1,306.05 · B3 −$2,024.30. Same sign, same order.
Second variant (swing search bounded to `structure_window_bars: 12` from `config/stop_anchors.yaml`
instead of the whole session): B1 −$807.50 / B2 −$476.05 on the same 54 — **the conclusion does not move.**
BE-after-first-target overlay applied to both arms: A +$751.30 · B1 −$133.75 — still A by $885.

## 2. The sizing coupling is the whole story

`_effective_contracts_raw` (`backend/v9/services/sierra_command.py:692-742`) with the live values
`RISK_BUDGET_USD=225`, `RISK_MIN_CONTRACTS=3`, `RISK_MAX_PTS_HARD=30`, `ruled_contracts()=5`:
`floor(225/(risk_pts×5)) ≥ 3` ⟺ **risk_pts ≤ 15.00**. So:

* Every one of the 54 actual stops is ≤ 15.00 pt, and the max is **exactly 15.00**. The stops are not
  "chosen tight" — they are *bounded by the budget*. That is the mechanism behind the 3.24 ct / 6.07 pt
  loser profile in `ASYMMETRY_17D`.
* **30 of 54 structural stops (56%) exceed 15 pt and are rejected outright**; 12 exceed 30 pt and are
  refused even without the min-contract rule. Those 30 vanished trades booked **+$561.25 of the
  broker-priced +$523.75** — i.e. the sizer would delete more than the entire realised profit.
* On the 24 that survive, the sizer sizes them *up*, not down (avg 3.29 → 3.75 ct), because the surviving
  structural stops are still under 15 pt and the ruled ceiling is 5.

**"Wider structural stops" and `RISK_BUDGET_SIZING_V1` as configured are mutually exclusive on 56% of
this book.** Any structural-stop proposal has to change the budget first, or it is not a stop change —
it is a trade-selection change.

## 3. How much wider (priced 54)

| | mean | median | p90 | max |
|---|---|---|---|---|
| A initial stop (pt) | 6.85 | 6.25 | — | 15.00 |
| B structural stop (pt) | **23.63** | **19.50** | — | 94.25 |
| widening (pt) | +16.78 | +10.50 | — | +89.75 |
| A ÷ that day's avg RTH 5-min bar range | 1.34× | 1.31× | 1.80× | — |
| B ÷ that day's avg RTH 5-min bar range | **4.57×** | **3.44×** | 8.14× | — |

B/A ratio: median **2.56×**, p25 1.81×, p75 4.00×, max 23.4×. **53 of 54 are wider; exactly one is
tighter** (#971, 7.25 → 1.75 pt — and it flips A-win → B-loss). Structural reference used:
swing 43 · prior-day VA edge 9 · IB edge 1 · session extreme 1. The 9 `prior_va` rows carry a median
structural stop of **33.0 pt** and rest on `v9_tpo_sessions.vah_price/val_price`, which is visibly unreliable
(2026-08-11 VA sits entirely below that day's IB) — treat that tier as noise, not as structure.

## 4. The trades that got worse — all 23, individually

`riskA→riskB` in points; $ at the contract count actually traded.

| id | date | dir | sys | ct | riskA→riskB | A | B1 | Δ |
|---|---|---|---|---|---|---|---|---|
| 841 | 08-28 17:15 | S | 4 | 2 | 7.62→31.00 | −76.20 | −310.00 | **−233.80** |
| 764 | 08-21 18:45 | L | 2 | 4 | 8.75→20.25 | −175.00 | −405.00 | **−230.00** |
| 971 | 09-02 20:10 | L | 4 | 5 | 7.25→**1.75** | +172.50 | −43.75 | **−216.25** |
| 809 | 08-26 17:00 | L | 2 | 2 | 7.75→28.75 | −77.50 | −287.50 | −210.00 |
| 762 | 08-21 16:54 | S | 4 | 2 | 7.75→26.75 | −77.50 | −267.50 | −190.00 |
| 948 | 09-01 18:45 | L | 4 | 5 | 7.50→17.00 | −135.00 | −325.00 | −190.00 |
| 655 | 08-10 17:46 | L | 2 | 4 | 4.25→12.50 | −85.00 | −250.00 | −165.00 |
| 987 | 09-03 20:20 | S | 4 | 5 | 5.75→12.25 | −143.75 | −306.25 | −162.50 |
| 885 | 08-31 17:35 | S | 2 | 2 | 6.00→20.00 | −60.00 | −200.00 | −140.00 |
| 840 | 08-28 17:10 | S | 4 | 2 | 7.75→20.75 | −77.50 | −207.50 | −130.00 |
| 760 | 08-21 16:50 | S | 4 | 2 | 5.00→20.50 | −2.50 | −80.00 | −77.50 |
| 770 | 08-21 20:59 | S | 2 | 2 | 6.00→12.75 | −60.00 | −127.50 | −67.50 |
| 942 | 09-01 17:20 | L | 2 | 4 | 7.50→20.25 | +58.75 | −5.00 | −63.75 |
| 1069 | 09-04 19:25 | L | 2 | 5 | 5.25→21.75 | +7.50 | −55.00 | −62.50 |
| 749 | 08-19 21:50 | L | 4 | 4 | 5.00→10.25 | −11.25 | −63.75 | −52.50 |
| 680 | 08-14 19:37 | L | 4 | 2 | 4.50→9.50 | −45.00 | −95.00 | −50.00 |
| 968 | 09-02 19:40 | S | 4 | 5 | 6.50→11.25 | +5.00 | −42.50 | −47.50 |
| 998 | 09-04 16:55 | L | 4 | 5 | 5.50→7.25 | −137.50 | −181.25 | −43.75 |
| 775 | 08-21 22:48 | L | 2 | 2 | 6.25→10.25 | −62.50 | −102.50 | −40.00 |
| 828 | 08-27 19:02 | L | 4 | 2 | 9.00→16.25 | −22.50 | −58.75 | −36.25 |
| 877 | 08-31 17:00 | S | 2 | 5 | 7.25→93.50 | +91.25 | +71.25 | −20.00 |
| 936 | 08-31 21:15 | L | 4 | 2 | 5.50→7.00 | −55.00 | −70.00 | −15.00 |
| 766 | 08-21 19:55 | S | 2 | 4 | 6.00→6.75 | −20.00 | −27.50 | −7.50 |

**Is the gain carried by two lucky rows?** The *gain* side is: the 11 improved rows total +$1,322.50 and
the top two (#950 +$283.75, #668 +$247.50) are **40% of it**. Two of the other big gainers (#875, #873)
sit on 93.5 / 94.25-point `prior_va` stops that would never be sent. So yes — the upside is thin and
partly artefactual, while the downside (−$2,451.30 over 23 rows, top-2 only 19%) is broad.

## 5. Segments (indicative only)

`day_type_at_entry` disagrees with the canonical `classify_replay` on ~17 of 21 labelled rows, and 21 of
54 are NULL. Read the day-type split as a label audit, not as a result.

| segment | n | A | B1 | B2 (rejected) |
|---|---|---|---|---|
| S2 | 25 | +$12.50 | −$231.25 | −$423.12 (16) |
| S4 | 29 | +$271.30 | −$613.75 | −$21.68 (14) |
| LONG | 22 | −$238.75 | −$1,366.25 | −$594.37 (10) |
| SHORT | 32 | +$522.55 | +$521.25 | +$149.57 (20) |
| `Variation` | 23 | +$272.50 | −$307.50 | −$150.43 (10) |
| `Trend_Normal` | 5 | +$237.50 | **+$443.75** | +$406.25 (2) |
| NULL label | 21 | −$367.45 | −$971.25 | −$397.50 (16) |

The only segment where the structural stop is clearly better is `Trend_Normal` (n=5 — not a finding).
The damage is concentrated in LONGs (−$1,127.50 of the −$1,128.80 net delta).

## 6. Verification

**Sign.** 30 ARM-A rows and 21 ARM-B rows exit purely at the stop (no leg reached a target). **Every one
is negative in both arms**; the SHORT pure-stop sets run −$156.25…−$31.25 (A) and −$310.00…−$8.75 (B),
zero non-negative. Worked example #668: SHORT, entry 7811.25, stop 7816.50, 4 ct →
`points = entry − exit = −5.25` → `−5.25 × 4 × $5 = −$105.00`. No inverted stop exists in either arm
(checked: LONG stop < entry, SHORT stop > entry, 68/68, both arms).

**ARM A against booked P&L (sanity only — not resolved).** Replay +$283.80 vs broker-priced +$523.75;
same sign on 46 of 54 rows, median |diff| $20.62. 14 of 17 sessions agree within ±$150; the gap is
almost entirely 2026-08-21 (−$375.00), where the real trades were saved by `SMART_BE` / `MAE_SCRATCH`
management the replay deliberately does not model. Booked reality sits *between* the no-BE model
(+$283.80) and the BE-after-first-target model (+$751.30), which is the expected place for it. Per the
brief, the money basis is contested (T-160 / T-256; `pnl_sierra` NULL on 12 of 32; the account is shared
with Eti) — this is reported, not reconciled.

**Unpriced 14** (not in the headline): A −$836.30, B1 −$555.00 — the only cut where B beats A, and it is
the cut whose real outcomes nobody can price.

## 7. Method — pre-registered before the run

* **Bars** `v9_bars_5min_woodies`, RTH `(ts AT TIME ZONE 'Asia/Jerusalem')::time BETWEEN '16:30' AND '23:00'`
  (= 08:30–15:00 CT). 21 sessions, 79 bars/day, complete — except **2026-09-07 ends 19:55 IL** (T-265);
  one trade (#1191) is marked at that truncated close.
* **ARM A** = `quality.metadata.stop_initial` (68/68 present). The `stop` column is *not* used —
  `SMART_BE` moved it on 30 rows.
* **ARM B** = last structural reference behind entry in the trade's direction, + **6 ticks = 1.50 pt**
  buffer. The buffer is not invented: `config/stop_anchors.yaml → anchor_offset_ticks: 6`
  (Michael 2026-07-20). Priority: (1) most recent **confirmed swing**, N=2 bars either side, strict
  (`low[i] < low[i±1], low[i±2]`), confirmed at the close of bar i+2 and usable only if that close is
  ≤ entry_ts (no lookahead) → (2) IB edge, only after IB lock (open+60 min) → (3) prior CASH session
  VAL/VAH → (4) session extreme so far. Each must sit behind the entry.
* **Ladder** = `{entry ± quality.t0_target_pts when has_t0} ∪ {t1,t2,t3,t4}`, kept only if beyond entry,
  deduped, sorted nearest-first, quantities from `contract_size.ladder_for(contracts)`, remainder to the
  farthest leg.
* **Replay** = bars strictly **after** `entry_ts` (entry bar excluded — identical rule in both arms; this
  hides same-bar stop-outs, which favours the *tight* stop, i.e. it is conservative against ARM B).
  Stop tested first each bar ⇒ same-bar tie the stop wins; a stop closes all remaining legs; unresolved
  legs are marked at the session's last RTH close (12 such rows in B, +$220.00 total).
* **No stop was tuned after seeing results.** Both swing-window variants (whole session / 12 closed bars)
  are reported in §1.

### Reproduce
```bash
cd ~/Downloads/mems26_web_git && set -a && . ./.env && set +a
python3 /tmp/sstop/replay.py       # ARM A + ARM B, whole-session swing search -> /tmp/sstop/replay.json
python3 /tmp/sstop/replay_win.py   # variant: swing search bounded to 12 closed bars
python3 /tmp/sstop/agg2.py /tmp/sstop/replay.json UNBOUNDED   # §1 totals + flips
python3 /tmp/sstop/detail.py       # §4 per-trade worse/better
python3 /tmp/sstop/seg.py          # §3 widening + §5 segments
python3 /tmp/sstop/sign.py         # §6 sign check + A-vs-booked per session
```
Trades: `SELECT id, direction, entry_ts, entry_price, t1,t2,t3,t4, quality FROM v9_trades
WHERE mode='live' AND entry_ts>='2026-08-10' ORDER BY id;` (68 rows).
Price basis: `/tmp/asym/final2.json` field `P`/`Pbasis`, produced by the `ASYMMETRY_17D_2026-09-08.md`
§0 method (`scripts/sierra_activity_join.py`). Scripts are ephemeral `/tmp` working files, same class as
the `/tmp/asym/_m*.py` set named in ASYMMETRY_17D; every definition needed to rebuild them is in §7.

## 8. What a trader would say

**"The stop isn't the leak. Widening it to the last swing turns a +$284 book into −$845 at the same size,
and the risk budget refuses more than half the trades outright — you'd be deleting the winners to save
the losers."** The 7 stops that were later proven right are real, but paying for them costs 23 rows that
get worse, and both totals sit inside the ~$800 spread of the money basis itself (broker +$523.75 vs
`pnl_usd` +$103.75 vs `pnl_sierra` −$310.00 on the same 17 sessions). **On this data the structural-stop
idea is not marginal — it is clearly negative, and the negative sign survives both swing variants, the
BE overlay, the all-68 cut, and every P&L basis.** The one thing this run does establish as real is the
coupling: `RISK_BUDGET_USD=225` + `RISK_MIN_CONTRACTS=3` is a hard **15.00-point ceiling on any stop this
system can send**, which is why the stops cluster at ~1.16–1.31× a 5-min bar. If Michael wants structural
stops at all, the budget is the flag to argue about — not the stop.
