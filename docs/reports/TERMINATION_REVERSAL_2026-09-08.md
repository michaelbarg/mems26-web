# TERMINATION AS A TRIGGER — what it would have been worth (2026-09-08)

Michael's question (08.09): *"If the system had acted according to day type AND
structural recognition — recognising that price has FINISHED extending in one
direction, so that termination itself becomes the trigger for the other side —
what would that have been worth?"*

Read-only audit. No code, service, `.env` or flag was touched.

---

## 0. Scope, sources, and the traps that were handled

| Item | Value |
|---|---|
| Bars | `v9_bars_5min_woodies` (canonical live series). `ts` = **bar START** — proven by the live wiring's building-bar drop `while _de_now - ets < 300: pop()` (`five_min_system.py:1452`). Entry therefore executes at `ts + 5min`. |
| RTH window | `(ts AT TIME ZONE 'Asia/Jerusalem')::time BETWEEN '16:30' AND '23:00'` |
| Sessions | last 15 available: **2026-08-18 … 2026-09-07**. 14 are full (79 bars); **2026-09-07 is truncated (42 bars, ends 19:55 IL)** — the T-265 RTH export stall. Flagged, not excluded. |
| Day type | **primary = `v9_day_type_history.day_type`** (EOD-locked record). Secondary = `v9_trades.day_type_at_entry` (the live label). **They disagree on 7 of 15 sessions** — see §4. |
| IB / VAH / VAL / POC | **bar-derived only.** `v9_tpo_history` deliberately not used (time-shifted before 31.08). IB = first 12 RTH bars. Profile = developing bar-TPO proxy (below). |
| Delta | **not used at all** — so the pre-31.08 `v9_bars_cumulative_delta` 3h duplication cannot contaminate anything here. |
| Pricing | MES = **$5/point**. All Σ$ reported at **2 contracts = $10/point**. |
| Short arithmetic | `pts = entry − exit` for SHORT, `exit − entry` for LONG. Asserted in code: *stopped trades with non-negative pts = **0*** (printed by the run). |

**IB cross-check (Rule 2 — verify before you trust):** the bar-derived IB
(max/min of the first 12 RTH bars) was compared against
`v9_day_type_history.ib_high/ib_low` for all 15 sessions → **match on 15/15**.
The bar-derived profile is therefore anchored to the same IB the classifier used.

---

## 1. STEP 0 — DALTON_EDGE_V1 as it actually stands

### 1.1 What the code defines as a termination

`backend/v9/systems/dalton_edge.py` → `detect_dalton_edge()`, evaluated on the
**last closed bar** only. A LONG termination requires **all** of:

1. `bar_range >= 2.0 pt` (`MIN_BAR_RANGE_PTS`)
2. `volume >= VOL_MULT(2.0) × SMA20 of the preceding 20 bars` (candidate excluded)
3. `low <= min(low of the previous 11 bars)` — the N-bar extreme, `LOOKBACK_N=12`
4. `close >= low + 0.6 × range` — the rejection close (`REJECT_CLOSE_FRAC`)

SHORT is the exact mirror at the highest high. Stop = extreme ∓ 2.0 pt,
T1 = 1R, T2 = 2R. Wiring (`five_min_system.py:1396 _maybe_dalton_edge`) adds
three more filters: skip the first `DALTON_EDGE_SKIP_OPEN_BARS=3` RTH slots;
require the newest closed bar to be < 600 s old (anti-phantom); and **one fire
per side per IL day** (`self._de_fired`, reset on IL date change, held in
process memory).

Live config read from `.env`: `DALTON_EDGE_V1=live` (since 28.08), and the three
tunables are unset → defaults `LOOKBACK_N=12 · VOL_MULT=2.0 · STOP_BUFFER=2.0 ·
SKIP_OPEN_BARS=3`.

### 1.2 How it actually performed

```sql
SELECT id,mode,state,direction,day_type_at_entry,pattern_id_at_entry,
       (entry_ts AT TIME ZONE 'Asia/Jerusalem') il_entry, entry_price,stop,
       exit_price,exit_reason,outcome,pnl_usd,pnl_r
FROM v9_trades WHERE pattern_id_at_entry ILIKE '%DALTON%' ORDER BY entry_ts;
```

**n = 1**, all time, live + shadow:

| id | mode | date/time IL | dir | entry | stop | exit | reason | pnl_r | **Σ$ @2c** |
|---|---|---|---|---|---|---|---|---|---|
| 1002 | shadow | 2026-09-04 17:15 | LONG | 7738.25 | 7728.25 | 7728.25 | STOP_HIT | −1.0 | **−$100.00** |

Win/loss split: **0 wins / 1 loss.** (`v9_trades.pnl_usd` reads −$200.00, which
implies 4 contracts; at the ruled reporting size of 2 contracts the 10.00-pt
loss is −$100.00.)

`v9_five_min_setups` holds **0** DALTON rows — that table is not on this
pattern's write path (`route_setup` is called directly), so it is not a valid
census. The one event does appear in `v9_shadow_ledger`:

```
ts=2026-09-04 17:15:02  source=S7  flag=SYSTEM7_SCORE  trade_id=1002
pattern=DALTON_EDGE_LONG  decision=BLOCKED  pnl_sim=30.0 (unit=score_s7)
```

→ the fire **was live-eligible and was blocked by the System-7 score gate
(score 30)**, then recorded as a shadow trade.

I verified the detector reproduces this exact fire: replaying the real module
over the real bars for the 09-04 17:10 candidate returns
`entry=7738.25 stop=7728.25 vol_ratio=2.33` — byte-identical to the `v9_trades`
row. The audit's understanding of the detector is therefore correct.

### 1.3 Why it fires as rarely as it does — two code reasons, both measured

Bar-by-bar replay of the **live wiring** over the continuous feed, 18.08→07.09
(4,080 bars evaluated):

| stage | rejected |
|---|---|
| `SKIP_OPEN_BARS` guard | 45 |
| `bar_range < 2.0 pt` | 891 |
| **`volume < 2.0 × SMA20`** | **2,778** |
| not an N-bar extreme | 87 |
| extreme but no rejection close | 202 |
| **passed the detector** | **75 (1.8 %)** |

> **Reason 1 — the volume gate.** It rejects **88.4 % (2,778 of 3,144)** of every
> bar that reaches it. This is the single condition that sets the fire rate.

But the more damaging one is invisible in the funnel:

> **Reason 2 — the once-per-side-per-IL-day budget is spent overnight.** The
> volume SMA20 deliberately crosses session boundaries, so globex bars clear a
> globex-sized average easily. Of the 75 passing bars, **49 are in globex and 26
> in RTH**. Applying the dedupe in time order: under perfect 24 h uptime the
> system would fire **28 times — 26 in globex, 2 in RTH — and would suppress 24
> RTH candidates** because that side had already fired overnight.

Worked example, 2026-09-04:
`03:00 gx LONG FIRE | 10:00 gx LONG DEDUPED | 13:25 gx SHORT FIRE | 15:05 gx LONG DEDUPED | 15:15 gx LONG DEDUPED | 17:10 RTH LONG DEDUPED`
— the 17:10 RTH candidate is the one that **did** reach the books, which is only
possible because the 03:00 globex LONG was never evaluated live (backend not
processing bars at that hour, or restarted since — `_de_fired` is per-process
in-memory state).

**Honest limit on this claim:** `/tmp/backend.err.log` contains **0** occurrences
of `DaltonEdge`, but that log spans only 2026-09-06 17:05 → now **and carries 0
`five_min_system` lines of any kind**. It cannot confirm or deny fires in the
28.08→07.09 window. The count of 1 rests on `v9_trades` + `v9_shadow_ledger`,
not on log silence.

---

## 2. STEP 1 — the three termination rules (parameters fixed before any outcome)

**Leg** = the dominant one-sided extension = the session's max swing, oriented by
which extreme came last (low→high = UP leg; high→low = DOWN leg). Counter-trade
direction is always against the leg.

| rule | definition | fixed parameters |
|---|---|---|
| **T1 failed extension** | the **running session extreme in the leg direction** is not exceeded for two consecutive 30-min periods | `6 bars/period × 2 periods = 12 bars`; first occurrence per session only |
| **T2 excess** | a bar makes a new session extreme in the leg direction, its wick beyond the **prior** extreme is `≥ 2.0 × body` **and** `≥ 1.00 pt`, and it closes back inside the prior extreme | `mult 2.0`, `min wick 1.00 pt`; first per session |
| **T3 return through origin** | first bar **after the leg extreme** that closes back through the **IB edge the leg broke** | IB = first 12 RTH bars; first per session |
| *T3b (variant, reported)* | same but through the **leg origin price** instead of the IB edge | — |

**Trade construction (exactly as specified):** entry = termination bar's close ·
stop = running session extreme ± 6 ticks (1.50 pt) · target = **nearest** of
POC / opposite value edge / IB mid lying in the counter direction · walk forward
bar by bar, first touch wins, **stop wins a same-bar tie** (conservative) · else
mark at the session's last close.

Profile: developing bar-TPO proxy computed only from bars **up to and including
the termination bar** (no look-ahead) — each RTH bar marks every 0.25 level
between its low and high; POC = most-marked level; VA = 70 % of marks grown from
POC taking the richer adjacent side; VAH/VAL = its edges.

---

## 3. STEP 2 — every candidate, winners and losers

`Σ$` at 2 contracts. `term` = the time the entry executes (bar close).

| date | rule | leg | dir | entry t | entry | stop | risk pt | target | tgt | exit | why | pts | **$@2c** | day type |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 08-18 | T1 | DOWN | LONG | 19:25 | 7726.50 | 7711.75 | 14.75 | 7730.25 | VAH | 7711.75 | STOP | −14.75 | **−147.50** | Variation |
| 08-18 | T2 | DOWN | LONG | 23:00 | 7715.25 | 7708.75 | 6.50 | 7723.75 | POC | 7715.00 | CLOSE | −0.25 | −2.50 | Variation |
| 08-18 | T3 | — | — | — | — | — | — | — | — | — | NO_SIGNAL | — | — | Variation |
| 08-19 | T1 | UP | SHORT | 17:35 | 7741.75 | 7747.75 | 6.00 | 7738.25 | POC | 7747.75 | STOP | −6.00 | −60.00 | Neutral_Extreme |
| 08-19 | T2 | UP | SHORT | 18:05 | 7761.75 | 7766.25 | 4.50 | 7739.50 | POC | 7739.50 | TARGET | +22.25 | **+222.50** | Neutral_Extreme |
| 08-19 | T3 | UP | SHORT | 18:40 | 7744.75 | 7766.25 | 21.50 | 7739.50 | POC | 7739.50 | TARGET | +5.25 | +52.50 | Neutral_Extreme |
| 08-20 | T1 | DOWN | LONG | 18:25 | 7701.00 | 7690.00 | 11.00 | 7703.88 | IB_MID | 7703.88 | TARGET | +2.88 | +28.75 | Neutral_Extreme |
| 08-20 | T2 | DOWN | LONG | 20:45 | 7682.75 | 7678.75 | 4.00 | 7698.25 | POC | 7678.75 | STOP | −4.00 | −40.00 | Neutral_Extreme |
| 08-20 | T3 | — | — | — | — | — | — | — | — | — | NO_SIGNAL | — | — | Neutral_Extreme |
| 08-21 | T1 | UP | SHORT | 17:35 | 7680.00 | 7697.75 | 17.75 | **none** | — | 7697.75 | STOP | −17.75 | **−177.50** | Variation |
| 08-21 | T2 | — | — | — | — | — | — | — | — | — | NO_SIGNAL | — | — | Variation |
| 08-21 | T3 | UP | SHORT | 18:55 | 7695.25 | 7711.50 | 16.25 | 7686.38 | IB_MID | 7686.38 | TARGET | +8.88 | +88.75 | Variation |
| 08-24 | T1 | UP | SHORT | 17:35 | 7670.25 | 7684.25 | 14.00 | 7668.88 | IB_MID | 7668.88 | TARGET | +1.38 | +13.75 | Variation |
| 08-24 | T2 | — | — | — | — | — | — | — | — | — | NO_SIGNAL | — | — | Variation |
| 08-24 | T3 | UP | SHORT | 19:35 | 7679.75 | 7688.00 | 8.25 | 7670.00 | POC | 7670.00 | TARGET | +9.75 | +97.50 | Variation |
| 08-25 | T1 | DOWN | LONG | 18:35 | 7684.00 | 7661.25 | 22.75 | 7690.50 | IB_MID | 7690.50 | TARGET | +6.50 | +65.00 | Variation |
| 08-25 | T2 | DOWN | LONG | 16:45 | 7694.75 | 7690.50 | 4.25 | 7696.50 | POC | 7696.50 | TARGET | +1.75 | +17.50 | Variation |
| 08-25 | T3 | DOWN | LONG | 17:40 | 7683.00 | 7661.25 | 21.75 | 7688.00 | POC | 7688.00 | TARGET | +5.00 | +50.00 | Variation |
| 08-26 | T1 | UP | SHORT | 18:05 | 7694.00 | 7703.50 | 9.50 | 7690.38 | IB_MID | 7690.38 | TARGET | +3.62 | +36.25 | Neutral_Center |
| 08-26 | T2 | — | — | — | — | — | — | — | — | — | NO_SIGNAL | — | — | Neutral_Center |
| 08-26 | T3 | UP | SHORT | 22:10 | 7701.75 | 7707.00 | 5.25 | 7690.38 | IB_MID | 7690.38 | TARGET | +11.38 | **+113.75** | Neutral_Center |
| 08-27 | T1 | UP | SHORT | 19:20 | 7737.75 | 7744.25 | 6.50 | 7737.25 | POC | 7737.25 | TARGET | +0.50 | +5.00 | Variation |
| 08-27 | T2 | UP | SHORT | 17:40 | 7725.00 | 7733.75 | 8.75 | 7718.00 | POC | 7733.75 | STOP | −8.75 | −87.50 | Variation |
| 08-27 | T3 | UP | SHORT | 21:30 | 7726.00 | 7757.25 | 31.25 | 7716.62 | IB_MID | 7738.25 | CLOSE | −12.25 | −122.50 | Variation |
| 08-28 | T1 | DOWN | LONG | 18:15 | 7771.25 | 7725.00 | **46.25** | **none** | — | 7725.00 | STOP | −46.25 | **−462.50** | Neutral_Center |
| 08-28 | T2 | DOWN | LONG | 17:05 | 7746.00 | 7738.00 | 8.00 | 7750.00 | POC | 7738.00 | STOP | −8.00 | −80.00 | Neutral_Center |
| 08-28 | T3 | — | — | — | — | — | — | — | — | — | NO_SIGNAL | — | — | Neutral_Center |
| 08-31 | T1 | UP | SHORT | 17:35 | 7676.50 | 7705.75 | **29.25** | **none** | — | 7705.75 | STOP | −29.25 | **−292.50** | Variation |
| 08-31 | T2 | UP | SHORT | 23:00 | 7698.00 | 7709.75 | 11.75 | 7689.50 | IB_MID | 7700.75 | CLOSE | −2.75 | −27.50 | Variation |
| 08-31 | T3 | UP | — | — | — | — | — | — | — | — | NO_FORWARD_BARS | — | — | Variation |
| 09-01 | T1 | DOWN | LONG | 17:35 | 7672.00 | 7637.00 | **35.00** | **none** | — | 7637.00 | STOP | −35.00 | **−350.00** | Neutral_Center |
| 09-01 | T2 | DOWN | LONG | 20:30 | 7643.50 | 7631.25 | 12.25 | 7644.50 | POC | 7644.50 | TARGET | +1.00 | +10.00 | Neutral_Center |
| 09-01 | T3 | DOWN | LONG | 22:15 | 7641.50 | 7620.00 | 21.50 | 7644.00 | POC | 7644.00 | TARGET | +2.50 | +25.00 | Neutral_Center |
| 09-02 | T1 | UP | SHORT | 19:35 | 7677.25 | 7692.75 | 15.50 | 7667.25 | VAL | 7680.50 | CLOSE | −3.25 | −32.50 | Variation |
| 09-02 | T2 | UP | SHORT | 17:10 | 7663.50 | 7669.25 | 5.75 | 7662.88 | IB_MID | 7669.25 | STOP | −5.75 | −57.50 | Variation |
| 09-02 | T3 | UP | SHORT | 18:50 | 7676.50 | 7692.75 | 16.25 | 7662.88 | IB_MID | 7680.50 | CLOSE | −4.00 | −40.00 | Variation |
| 09-03 | T1 | UP | SHORT | 17:55 | 7711.75 | 7728.00 | 16.25 | 7710.75 | POC | 7710.75 | TARGET | +1.00 | +10.00 | **Trend_Normal** |
| 09-03 | T2 | UP | SHORT | 16:45 | 7723.50 | 7726.00 | 2.50 | 7714.25 | POC | 7726.00 | STOP | −2.50 | −25.00 | **Trend_Normal** |
| 09-03 | T3 | UP | — | — | — | — | — | — | — | — | NO_SIGNAL | — | — | **Trend_Normal** |
| 09-04 | T1 | DOWN | LONG | 19:35 | 7731.00 | 7708.75 | 22.25 | 7740.25 | IB_MID | 7719.00 | CLOSE | −12.00 | −120.00 | Variation |
| 09-04 | T2 | DOWN | LONG | 17:15 | 7738.25 | 7728.75 | 9.50 | 7740.25 | IB_MID | 7728.75 | STOP | −9.50 | −95.00 | Variation |
| 09-04 | T3 | DOWN | LONG | 19:20 | 7730.50 | 7708.75 | 21.75 | 7738.00 | VAH | 7719.00 | CLOSE | −11.50 | −115.00 | Variation |
| 09-07 | T1 | DOWN | LONG | 19:30 | 7708.00 | 7702.00 | 6.00 | 7711.25 | VAH | 7709.00 | CLOSE | +1.00 | +10.00 | Variation † |
| 09-07 | T2 | — | — | — | — | — | — | — | — | — | NO_SIGNAL | — | — | Variation † |
| 09-07 | T3 | DOWN | LONG | 19:15 | 7709.00 | 7702.00 | 7.00 | 7711.25 | VAH | 7709.00 | CLOSE | 0.00 | 0.00 | Variation † |

† truncated session (T-265 export stall) — both 09-07 candidates exit at 19:55, not 23:00.

**T3b (leg-origin variant): 0 candidates in 15 sessions.** Price never closed back
through the leg's origin price after making the extreme. That variant is dead as
specified — the IB edge is the only usable "origin".

### 3.1 Aggregates

**Stop = session extreme + 6 ticks (as specified):**

| rule | n | W | L | hit % | **Σ$ @2c** | Σ R | avg risk | avg win | avg loss | S/T/EOD |
|---|---|---|---|---|---|---|---|---|---|---|
| T1 | 15 | 7 | 8 | 47 % | **−1,473.75** | −5.41 | 18.18 pt | +2.41 | −20.53 | 6/6/3 |
| T2 | 11 | 3 | 8 | 27 % | **−165.00** | −0.84 | 7.07 pt | +8.33 | −5.19 | 6/3/2 |
| T3 | 10 | 6 | 3 | 60 % | **+150.00** | +3.32 | 17.07 pt | +7.13 | −9.25 | 0/6/4 |
| **all three** | **36** | 16 | 19 | 44 % | **−1,488.75** | −2.93 | 14.48 pt | +5.29 | −12.29 | 12/15/9 |

**Variant — stop = the signal bar's own extreme + 6 ticks** (reported per the
"try a variant, report both" rule; this is the ZLR 5-min-bar-structure stop
already ruled in this system):

| rule | n | W | hit % | Σ$ @2c | Σ R |
|---|---|---|---|---|---|
| T1 | 15 | 4 | 27 % | −432.50 | −8.92 |
| T2 | 11 | 3 | 27 % | −165.00 | −0.84 |
| T3 | 10 | 2 | 20 % | −221.25 | −2.99 |
| **all three** | **36** | 9 | 25 % | **−818.75** | −12.75 |

The tight stop halves the dollar loss but triples the R loss (24 of 36 stopped).
**Neither stop works**, and the reason is the same for both — see §3.2.

### 3.2 The decomposition that matters: the read vs the geometry

| rule | avg risk offered | avg target distance | **offered R:R at entry** | avg MFE | candidates with MFE ≥ 4 pt |
|---|---|---|---|---|---|
| T1 | 18.18 pt | 4.15 pt | **0.23 : 1** | 4.63 pt | 7/15 |
| T2 | 7.07 pt | 7.31 pt | **1.03 : 1** | 4.48 pt | 4/11 |
| T3 | 17.07 pt | 7.55 pt | **0.44 : 1** | 7.10 pt | 7/10 |
| all | 14.48 pt | 6.30 pt | **0.43 : 1** | — | — |

At 0.43 : 1 you need a **70 % hit rate to break even**. The realised hit rate is
44 %. The loss is arithmetic, not prediction.

Meanwhile the counter-move **does exist**: average max favourable excursion after
a termination is 4.5–7.1 pt, and on T3 seven of ten candidates gave ≥ 4 pt of
room. The direction call is sound; the construction throws it away.

**The T1 tail is the whole loss.** Five T1 candidates carried > 20 pt of risk and
account for **−$1,160.00 of the −$1,473.75**; the other ten T1 candidates total
−$313.75. Those five, plus 08-21, are exactly the cases where **no POC / value
edge / IB mid lay in the counter direction at all** (4 of 36 candidates) — the
market had already travelled past every reference level before the rule
confirmed. Verified on the raw bars for two of them:

* **08-28** running low 7726.50 set at 17:10; twelve bars later (18:10) still no
  new low → rule says "down leg finished, buy". Close was **7771.25 — 45 points
  above the low** it is stopping against. Risk 46.25 pt. Stopped.
* **08-31** running high 7704.25 set on the 16:30 bar; twelve bars later (17:30)
  still no new high → "up leg finished, sell". Close was **7676.50 — 28 points
  below the high**. Risk 29.25 pt. Stopped.

---

## 4. STEP 3 — per day type

**Label source: `v9_day_type_history` (EOD-locked).** Rules T1+T2+T3.

| day type | sessions | rule | n | W | hit % | **Σ$ @2c** | Σ R |
|---|---|---|---|---|---|---|---|
| **Variation** | 9 | T1 | 9 | 4 | 44 % | −676.25 | −3.11 |
| | | T2 | 6 | 1 | 17 % | −252.50 | −2.86 |
| | | T3 | 7 | 3 | 43 % | −41.25 | +0.79 |
| | | **all** | **22** | 8 | 36 % | **−970.00** | −5.18 |
| **Neutral_Center** | 3 | T1 | 3 | 1 | 33 % | −776.25 | −1.62 |
| | | T2 | 2 | 1 | 50 % | −70.00 | −0.92 |
| | | T3 | 2 | 2 | 100 % | +138.75 | +2.29 |
| | | **all** | **7** | 4 | 57 % | **−707.50** | −0.25 |
| **Neutral_Extreme** | 2 | T1 | 2 | 1 | 50 % | −31.25 | −0.74 |
| | | T2 | 2 | 1 | 50 % | +182.50 | +3.94 |
| | | T3 | 1 | 1 | 100 % | +52.50 | +0.24 |
| | | **all** | **5** | 3 | 60 % | **+203.75** | +3.44 |
| **Trend_Normal** | **1** | all | **2** | 1 | 50 % | −15.00 | −0.94 |

Secondary cut, live label `v9_trades.day_type_at_entry`:

| live label | n | W | hit % | Σ$ @2c | Σ R |
|---|---|---|---|---|---|
| Variation | 24 | 13 | 54 % | −358.75 | +3.15 |
| Trend_Normal | 5 | 3 | 60 % | −330.00 | −1.74 |
| Trend_DD | 3 | 0 | 0 % | −330.00 | −2.07 |
| Normal | 2 | 0 | 0 % | −320.00 | −1.23 |
| (no label) | 2 | 0 | 0 % | −150.00 | −1.04 |

### The professional answer to "on which day types is termination a reversal trigger"

**It is not answerable on this window, and saying otherwise would be inventing a
result.** The 15 sessions label out as Variation ×9, Neutral_Center ×3,
Neutral_Extreme ×2, **Trend_Normal ×1**, Trend_DD ×0, Normal ×0, Nontrend ×0.
There is **one trend-day session**, carrying two candidates. Any statement of the
form "termination fades work / fail on trend days" would rest on n = 1 session.

Two things the data *does* say, both worth acting on:

1. **The day-type label the system would have to trade on is not the label the
   day turns out to have.** `v9_day_type_history` and `v9_trades.day_type_at_entry`
   disagree on **7 of 15 sessions** (08-19, 08-20, 08-26, 08-28, 08-31, 09-01,
   09-04). On 09-04 the live system carried `Trend_DD` on 139 fires while the EOD
   record says `Variation`; on 08-31 it carried `Normal` on 60 fires against an
   EOD `Variation`. A day-type-conditioned reversal rule inherits that error rate
   before it sees a single tick.
2. **The rule ranking is stable across day types even though the levels are not.**
   T3 is the only rule that is non-negative in R in every day type where it has
   candidates (+0.79 / +2.29 / +0.24). T1 is negative in every day type. That
   ranking, unlike the day-type split, is not an artefact of one or two sessions.

---

## 5. STEP 4 — what the system actually did at those 36 moments

`v9_trades`, any mode, `entry_ts` within ±10 min of the entry bar's close.
Tag: **COUNTER-SIDE** = system traded the same direction the termination implied ·
**WITH-LEG** = system traded *into* the leg the termination said was over.

| date | rule | entry t | dir | day type | sim $ | what the system did |
|---|---|---|---|---|---|---|
| 08-18 | T1 | 19:25 | LONG | Variation | −147.50 | **silent** |
| 08-18 | T2 | 23:00 | LONG | Variation | −2.50 | **silent** |
| 08-19 | T1 | 17:35 | SHORT | Neut_Ext | −60.00 | COUNTER-SIDE — shadow/ZLR/SHORT/LOSS @17:25 |
| 08-19 | T2 | 18:05 | SHORT | Neut_Ext | **+222.50** | **silent** |
| 08-19 | T3 | 18:40 | SHORT | Neut_Ext | +52.50 | **silent** |
| 08-20 | T1 | 18:25 | LONG | Neut_Ext | +28.75 | **silent** |
| 08-20 | T2 | 20:45 | LONG | Neut_Ext | −40.00 | **silent** |
| 08-21 | T1 | 17:35 | SHORT | Variation | −177.50 | **silent** |
| 08-21 | T3 | 18:55 | SHORT | Variation | +88.75 | **WITH-LEG** — shadow+live/INITIATIVE_LONG/LONG (LOSS, BE) @18:45 |
| 08-24 | T1 | 17:35 | SHORT | Variation | +13.75 | COUNTER-SIDE — shadow/ZLR/SHORT ×2 LOSS @17:25,17:30 |
| 08-24 | T3 | 19:35 | SHORT | Variation | +97.50 | **WITH-LEG** — shadow/TREND_STEP/LONG/LOSS @19:30 |
| 08-25 | T2 | 16:45 | LONG | Variation | +17.50 | **WITH-LEG** — shadow/ZLR/SHORT/WIN @16:50 |
| 08-25 | T3 | 17:40 | LONG | Variation | +50.00 | **WITH-LEG** — DOUBLE_TOP_AA_SHORT/WIN, ZLR/SHORT/LOSS |
| 08-25 | T1 | 18:35 | LONG | Variation | +65.00 | **silent** |
| 08-26 | T1 | 18:05 | SHORT | Neut_Ctr | +36.25 | **silent** |
| 08-26 | T3 | 22:10 | SHORT | Neut_Ctr | **+113.75** | **WITH-LEG** — live/LONG/BE @22:12 |
| 08-27 | T2 | 17:40 | SHORT | Variation | −87.50 | **silent** |
| 08-27 | T1 | 19:20 | SHORT | Variation | +5.00 | **silent** |
| 08-27 | T3 | 21:30 | SHORT | Variation | −122.50 | COUNTER-SIDE — INITIATIVE_SHORT ×2 (WIN, LOSS) |
| 08-28 | T2 | 17:05 | LONG | Neut_Ctr | −80.00 | **WITH-LEG** — ZLR/SHORT/WIN ×2 + GB100/SHORT/WIN @17:05 |
| 08-28 | T1 | 18:15 | LONG | Neut_Ctr | **−462.50** | COUNTER-SIDE — ZLR/LONG ×3 (LOSS, LOSS, BE) |
| 08-31 | T1 | 17:35 | SHORT | Variation | −292.50 | COUNTER-SIDE — live/SHORT/LOSS @17:35 |
| 08-31 | T2 | 23:00 | SHORT | Variation | −27.50 | **silent** |
| 09-01 | T1 | 17:35 | LONG | Neut_Ctr | −350.00 | COUNTER-SIDE — INITIATIVE_LONG, DOUBLE_BOTTOM_EE_LONG, TREND_STEP all LOSS |
| 09-01 | T2 | 20:30 | LONG | Neut_Ctr | +10.00 | **silent** |
| 09-01 | T3 | 22:15 | LONG | Neut_Ctr | +25.00 | **silent** |
| 09-02 | T2 | 17:10 | SHORT | Variation | −57.50 | **WITH-LEG** — INITIATIVE_LONG/WIN (shadow+live) @17:15 |
| 09-02 | T3 | 18:50 | SHORT | Variation | −40.00 | **WITH-LEG** — TREND_STEP/LONG/LOSS, ZLR/LONG |
| 09-02 | T1 | 19:35 | SHORT | Variation | −32.50 | COUNTER-SIDE — ZLR/SHORT/LOSS @19:40 |
| 09-03 | T2 | 16:45 | SHORT | Trend_Nrm | −25.00 | **silent** |
| 09-03 | T1 | 17:55 | SHORT | Trend_Nrm | +10.00 | **silent** |
| 09-04 | T2 | 17:15 | LONG | Variation | −95.00 | BOTH — incl. **DALTON_EDGE_LONG/LOSS @17:15** |
| 09-04 | T3 | 19:20 | LONG | Variation | −115.00 | COUNTER-SIDE — INITIATIVE_LONG (shadow LOSS / live WIN) |
| 09-04 | T1 | 19:35 | LONG | Variation | −120.00 | COUNTER-SIDE — INITIATIVE_LONG (shadow LOSS / live WIN) |
| 09-07 | T3 | 19:15 | LONG | Variation | 0.00 | COUNTER-SIDE — shadow/ZLR/LONG/LOSS @19:10 |
| 09-07 | T1 | 19:30 | LONG | Variation | +10.00 | COUNTER-SIDE — ZLR/LONG + REACTIVE_LONG, both LOSS |

**Counts: 16 of 36 termination moments the system was completely silent · 20 had
a trade within ±10 min — of which 12 were already on the counter side and 8 were
trading *with* the leg the termination said had ended.**

### The blocker

There is **no blocked-decision table with reasons in the DB**; the only gate
ledger is `v9_shadow_ledger`. Within ±10 min of the 36 termination moments it
holds 62 gate rows across 18 moments:

| flag / decision | count |
|---|---|
| `TREND_STEP_ENTRY_V1` / NO_CHANGE | 31 |
| `SYSTEM7_SCORE` / PASSED | 21 |
| **`SYSTEM7_SCORE` / BLOCKED** | **10** |

**The dominant named blocker is `SYSTEM7_SCORE`** — including the one real
DALTON_EDGE fire (score 30). System-wide over the same 25 days it runs
**254 BLOCKED (avg score 30.0) vs 184 PASSED (avg 44.8)** — it rejects 58 % of
everything it scores.

**Caveat, stated per the "first blocker ≠ only blocker" rule:** a `BLOCKED` row
names the gate that stopped a setup that *already existed*. It does not license
the inference "without S7 this trade would have entered" — there are further
gates downstream, and for 16 of the 36 moments no setup existed at all, so no
gate was involved. The correct reading is: **the system is silent at these
moments far more often than it is blocked.**

---

## 6. Findings

**1. Termination is a real read. The trade specified on top of it is not.**
Across 36 candidates the direction was right often enough (44 % hit; average
favourable excursion 4.5–7.1 pt; T3 6 of 10) — but the construction offers
**0.43 units of reward per unit of risk**, and at 0.43 : 1 you need 70 % to break
even. Σ = **−$1,488.75** at 2 contracts. The money was lost on geometry, not on
the market call.

**2. "Two periods failed to extend" is the wrong trigger as written.** T1
confirms a minimum of 60 minutes after the extreme, by which point price is deep
in the retracement — yet the stop is still anchored at the extreme. Risk is
therefore whatever has already happened: 18.18 pt average, 46.25 pt worst. Five
T1 candidates with > 20 pt risk carry **−$1,160 of the −$1,474**. On four of them
no POC, value edge or IB mid remained in the counter direction at all — the trade
had no destination when it was taken.

**3. The one rule that reads like a professional's is T3 — return through the IB
edge the leg broke.** n = 10, 60 % hit, **+$150.00 / +3.32 R**, zero stop-outs
(all exits were target or session close), average MFE 7.10 pt — the best MFE of
the three, meaning it enters while the counter-move is still in front of it
rather than behind it. Non-negative in R in every day type where it appears. But
n = 10 over 15 sessions is a direction, not a result.

**4. Day type cannot be answered on this window.** One trend session in fifteen.
And the label the system holds at decision time disagrees with the EOD label on
**7 of 15 days** — so even a proven day-type rule could not be executed reliably
today. Fix the label agreement before conditioning anything on the label.

**5. DALTON_EDGE_V1 is not measurably live.** One recorded event in eleven days
of `=live`, blocked by S7, −$100 at 2 contracts. The structural cause is not the
volume gate alone (though it rejects 88.4 % of bars reaching it) but the
**once-per-side-per-IL-day budget being consumed in globex**: 26 of 28 fires land
overnight and 24 RTH candidates are suppressed by an earlier globex fire.

---

## 7. What I would NOT build

* **Do not build T1 (failed extension) in any form that keeps the stop at the
  session extreme.** It is not a marginal loser — it is the entire loss, and its
  worst case is unbounded by construction.
* **Do not "fix" it by tightening the stop to the signal bar.** Measured: the
  variant takes the loss from −$1,473.75 to −$432.50 in dollars but from −5.41 R
  to −8.92 R, and 11 of 15 get stopped. Both stops fail because the target is the
  *nearest* reference level; the trade is risking 14 pt to make 6 pt either way.
* **Do not build T3b (return through the leg origin).** Zero candidates in 15
  sessions. Nothing to trade.
* **Do not act on T3 yet, and do not act on any per-day-type conclusion.** T3 is
  n = 10; the day-type cells are n = 2 to n = 22 with a single trend session.
  Both are below the threshold at which a number should change a trading rule.
* **Do not turn `DALTON_EDGE_V1` off as "not working."** It has not been given a
  fair test — it produced one RTH event in eleven days for structural reasons
  (globex dedupe), not because the pattern failed. Turning it off would discard a
  hypothesis that was never measured. Equally, do not claim it works.
* **Do not remove the `SYSTEM7_SCORE` gate on the strength of this report.** It
  blocked 10 of the 62 gate events near these moments; the far more common state
  was silence (16 of 36). Removing a gate does not create a setup that was never
  generated.

### The one thing that is worth measuring next

Not a new pattern — a **geometry change on the signals that already exist**:
same T3 trigger, but target = the *far* side of value (the opposite value edge or
POC, whichever is further) instead of the nearest level, so the offered R:R
crosses 1 : 1. That is a single-parameter change to an existing rule, testable on
the same 15 sessions, and it addresses the finding that actually explains the
loss. It should be measured in shadow over ≥ 40 sessions before anyone proposes
a flag.

---

## 8. Reproduction

Environment: `cd /Users/michael/Downloads/mems26_web_git && set -a && . ./.env && set +a`
(without this the code falls back to SQLite and returns zeros). All reads via
`backend.v9.db.read.read_all`. Scripts used for this report were written to
`/tmp/term_audit/` (`core.py`, `run1..run6.py`, `funnel.py`, `funnel2.py`,
`verify.py`) — nothing in the repo was modified.

Key queries:

```sql
-- session set + bar-derived IB cross-check
SELECT (ts AT TIME ZONE 'Asia/Jerusalem')::date d, count(*), min(low), max(high)
FROM v9_bars_5min_woodies
WHERE (ts AT TIME ZONE 'Asia/Jerusalem')::time BETWEEN '16:30' AND '23:00'
GROUP BY 1 ORDER BY 1 DESC LIMIT 15;

-- DALTON_EDGE actual performance
SELECT * FROM v9_trades WHERE pattern_id_at_entry ILIKE '%DALTON%';
SELECT * FROM v9_shadow_ledger WHERE pattern ILIKE '%DALTON%';

-- day-type labels, both sources
SELECT date, day_type, ib_high, ib_low FROM v9_day_type_history;
SELECT (entry_ts AT TIME ZONE 'Asia/Jerusalem')::date, day_type_at_entry, count(*)
FROM v9_trades WHERE day_type_at_entry IS NOT NULL GROUP BY 1,2;

-- gate ledger near the termination moments
SELECT flag, decision, count(*) FROM v9_shadow_ledger
WHERE ts > now()-interval '25 days' GROUP BY 1,2;
```

The DALTON funnel replay imports the production module directly
(`from backend.v9.systems.dalton_edge import detect_dalton_edge`) and was
validated against the single real fire: replaying the 2026-09-04 17:10 candidate
returns `entry=7738.25 stop=7728.25 vol_ratio=2.33`, identical to `v9_trades` row
1002.
