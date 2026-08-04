# Efficiency Research — 2026-08-03 (best live day, +$183.75): what the same day could have paid

**Mission (Michael):** yesterday was our best live day. How could it have been MORE efficient —
more profit from the same day, honestly?
**Agent:** quantitative research agent (read-only; this file is the only write).
**Sources:** `v9_trades` (`mode='live'` n=9 CLOSED, `mode='shadow'` n=15 CLOSED, 08-03 IL-date) ·
`v9_bars_5min_woodies` (181 bars 08-03, RTH 78 bars 16:30–22:55 IL) ·
`v9_bars_cumulative_delta` (89 rows 08-03) · `v9_day_type_history` ·
`~/SierraChart_Data/v9_export/gateway_decisions.jsonl` (5,497 rows total; 350 on 08-03, 157 unique,
42 collapsed RTH setups) · score components per `docs/research/SYSTEM7_INTERNAL_EVIDENCE_2026-08-03.md`.

**תקציר בעברית:** היום הרוויח ‎+$183.75‎ (5W/4L, כולם לונגים עם-המגמה). שלושה ממצאים גדולים:
(1) **החוזה השלישי הוא הכסף הגדול** — סולם T1/T2/T3 עם BE היה הופך את היום ל-‎+$751‎ (‎+$568‎);
(2) **כל 4 הסטופים היו סטופי-רעש** (2.5–4.25 נק' מול רצפת-DALTON ‏8.59): עם רצפה כולם פוגעים
ב-T1 קודם ואף אחד לא נעצר — ‎+$229‎; (3) **השערים חסמו 20 כניסות-1R מנצחות** (direction_context
‏6/6 שגוי, lsma_flat ‏5/5, cooldown ‏5/5) בזמן שחסימות ה-EOD והשורטים דווקא צדקו. ציון-S7 כמוגדר
במחקר (מיקום-מול-טווח) היה מפסיד מול fixed-2 ביום כזה — רכיב המיקום שבור בימי-מגמה וחייב
תיקון לפני שמדליקים sizing-לפי-ציון.

---

## Honesty header (Rule-5, granularity, n=)

- **n=9 live trades** (5W/4L), **n=15 shadow**, **n=78 RTH bars**, **n=27 blocked setups simulated**,
  **n=10 pullback-structure candidates**. One day. This is a case study, not statistics — it
  complements (and in one place contradicts) the July n=32 sample; both are stated below.
- All counterfactual sims run on **5-min bars** (trades were managed at ~1-min); same-bar
  stop/target ambiguity resolved **conservatively** (stop first, marked AMBIG). No slippage or
  commissions modeled, in EITHER direction, for all counterfactuals.
- "3rd contract live from today": all 3c figures are *what-if-yesterday*; the July sample says
  fixed-3 was the WORST policy on chop (−$1,281) — day-type-conditionality is the point, not "3c always".
- Counterfactual $ figures are **sample arithmetic on one favorable trend day, not forecasts**,
  and the ranked items OVERLAP — they must not be summed (stacked upper bound given once, §6).
- `pnl_usd` used throughout (sum reproduces the +$183.75 ground truth exactly).

**Base query:**

```sql
SELECT id, firing_system, pattern_id_at_entry, direction, entry_ts, exit_ts, entry_price,
       exit_price, exit_reason, pnl_usd, day_type_at_entry, t1, t2, t3, stop, quality,
       t1_hit_ts, t2_hit_ts, t3_hit_ts
FROM v9_trades
WHERE (entry_ts AT TIME ZONE 'Asia/Jerusalem')::date='2026-08-03'
  AND mode='live' AND state='CLOSED' ORDER BY entry_ts;   -- n=9
```

```
{'mode': 'live',   'state': 'CLOSED', 'n': 9,  'pnl': Decimal('183.75')}
{'mode': 'shadow', 'state': 'CLOSED', 'n': 15, 'pnl': Decimal('336.25')}
```

---

## 0 · Ground truth — the day and the 9 trades

**Day (from `v9_bars_5min_woodies`, RTH 16:30–23:00 IL):** open 7546.0 @16:30, low 7542.75 @16:30,
high 7638.5 @22:00, close 7628.5 @22:55 — **+82.5pt open-to-close up trend day**, low = first bar.
`v9_day_type_history`: OPEN_DRIVE, final label Variation (intraday: None → Trend_Normal →
Variation), IB 7542.75–7600.0 (**IB range 57.25pt**), directional_certainty MEDIUM.
Cumulative delta rose all session: 2,215 (16:39) → 13,948 (21:40) — buyers all day.

| id | sys | pattern | entry IL | exit IL | entry | init_stop (pt) | t1 / t2 / t3 | exit_reason | c | pnl_usd |
|---|---|---|---|---|---|---|---|---|---|---|
| 588 | S4 | HTLB | 16:35 | 16:45 | 7563.50 | 7543.50 (20.0) | 7568.75 / 7572.50 / — | T2_HIT | 2 | +71.25 |
| 591 | S4 | ZLR | 16:45 | 16:46 | 7569.50 | 7565.75 (3.75) | 7572.50 / 7599.50 / 7626.50 | STOP_HIT | 1 | −20.00 |
| 593 | S2 | REACTIVE_LONG | 17:10 | 17:18 | 7588.00 | 7582.00 (6.0) | 7594.25 / 7597.00 / 7687.00 | T2_HIT | 2 | +76.25 |
| 595 | S4 | ZLR | 17:36 | 17:41 | 7599.00 | 7594.75 (4.25) | 7602.75 / 7602.75 / 7641.00 | T2_HIT | 2 | +37.50 |
| 598 | S4 | ZLR | 17:51 | 18:06 | 7602.50 | 7598.50 (4.0) | 7606.50 / 7630.50 / 7644.50 | STOP_HIT | 2 | −7.50 |
| 601 | S4 | GB100 | 18:20 | 18:50 | 7606.00 | 7601.50 (4.5) | 7610.75 / 7613.00 / 7628.50 | T2_HIT | 2 | +58.75 |
| 604 | S4 | ZLR | 19:20 | 19:28 | 7614.25 | 7610.25 (4.0) | 7616.75 / 7616.75 / 7628.50 | T2_HIT | 2 | +25.00 |
| 607 | S4 | ZLR | 19:40 | 19:51 | 7615.75 | 7613.25 (2.5) | 7620.25 / 7628.50 / 7629.50 | STOP_HIT | 2 | −25.00 |
| 610 | S4 | ZLR | 21:45 | 21:46 | 7632.75 | 7629.00 (3.75) | 7637.25 / 7636.50 / 7640.25 | STOP_HIT | 2 | −32.50 |

All 9 LONG (with-day). #591 sized 1c by the opening cap (16:45 < 17:00). Losers: 16:45, 17:51,
19:40, 21:45 IL — 2 after 19:30 as stated. Winner P&L reproduces exactly as 2c T1+T2
(e.g. 588: 5.25pt+9.0pt = $26.25+$45.00 = $71.25).

---

## 1 · Money left on the table — what happened after every T2 exit (n=5 winners)

After ALL five T2 exits, price later printed the day high **7638.5 @22:00**. Simulated 3rd
contract from the recorded `t2_hit_ts`: stop at BE (entry) — the ruled BE-after-T1 management —
target = recorded `t3` (T3-policy) or trail-exit on first 5-min close below LSMA (trail-policy);
EOD flatten 22:55. Raw sim output:

```
588 HTLB          entry 7563.50 T2exit 16:45 | postMaxHi 7638.5 @22:00 | c3_T3pol: EOD +$325.00 | c3_trail: LSMA@17:45 +$186.25
593 REACTIVE_LONG entry 7588.00 T2exit 17:18 | postMaxHi 7638.5 @22:00 | c3_T3pol: EOD +$202.50 | c3_trail: LSMA@17:45 +$63.75
595 ZLR           entry 7599.00 T2exit 17:41 | postMaxHi 7638.5 @22:00 | c3_T3pol: BE@17:45  $0  | c3_trail: BE $0
601 GB100         entry 7606.00 T2exit 18:50 | postMaxHi 7638.5 @22:00 | c3_T3pol: T3@20:55 +$112.50 | c3_trail: LSMA@18:55 +$26.25
604 ZLR           entry 7614.25 T2exit 19:28 | postMaxHi 7638.5 @22:00 | c3_T3pol: BE@19:35  $0  | c3_trail: LSMA@19:30 +$8.75
```

- **T3-ladder 3rd contract: +$642.50** (588 has no T3 → BE-protected ride to EOD; 593's T3 7687
  was unreachable → same; both are how the bracket would mechanically behave). 595/604 honestly
  give $0 — BE was touched within minutes of T2.
- **LSMA-trail runner: +$285.00** — the 06-24 "runners exit at LSMA" rule cuts at the 17:45
  one-bar shakeout and underperforms the plain T3 ladder on this day.
- Whole-day policy totals (per-contract ladder, all 9 trades, losers scaled to 3c):
  **fixed-2 = +$163.75 · fixed-3 T1/T2/T3-ladder = +$751.25** (raw output in §2). The 3rd
  contract was worth **+$587.50** over fixed-2 yesterday. Caveat: on the July chop sample
  fixed-3 was the WORST policy (−$1,281) — this is a trend-day-conditional lever, not "always 3c".

---

## 2 · The four stops — ex-ante signals, and the score-sizing test (n=9)

### 2a. Forensics: all 4 were right-direction trades killed by sub-floor stops

DALTON rec-4 floor = `max(6, 0.15×IB)` = **8.59pt** (IB 57.25). Actual initial stops: 3.75 /
4.00 / 2.50 / 3.75pt — **all four below the floor** (so were 595's 4.25 and 601's 4.5, which
survived only because T1 was ≤4.75pt away). Floor-stop replay (same entries, stop = entry−8.59):

```
591 e7569.50 @16:45 stop 3.75pt | floorSim: T1_FIRST@16:45 -> BE@16:50 | minLowAfter 7565.00 | maxHiAfterStop 7638.5 (+69.0pt)
598 e7602.50 @17:51 stop 4.00pt | floorSim: T1_FIRST@18:20 -> BE@18:25 | minLowAfter 7599.75 | maxHiAfterStop 7638.5 (+36.0pt)
607 e7615.75 @19:40 stop 2.50pt | floorSim: T1_FIRST@20:20 -> T2@20:55 | minLowAfter 7611.25 | maxHiAfterStop 7638.5 (+22.75pt)
610 e7632.75 @21:45 stop 3.75pt | floorSim: T1_FIRST@22:00 -> AMBIG(BE cons.) | minLowAfter 7626.25 | maxHiAfterStop 7638.5 (+5.75pt)
```

**No floor stop would have been touched** (min post-entry lows all above entry−8.59). Result at
actual sizes: losers −$85.00 → **+$143.75** (591 +15 · 598 +20 · 607 +86.25 · 610 +22.50 cons.);
day +$183.75 → **+$412.50 (+$228.75)**. Corroboration from shadow (virtual mgmt, same signals):
#590 (=591) **+$15.00**, #597 (=598) **+$20.00**, #609 (=610) **+$41.25** actual recorded — while
#606 (=607), whose virtual stop was the same 7613.25, died identically to live. The 21:45 signal
alone was a **$73.75 swing** between shadow (+41.25) and live (−32.50) purely on stop placement.

### 2b. Was there an ex-ante signal? Signal-by-signal audit (honest: mostly NO)

| Signal | Losers (591/598/607/610) | Winners | Verdict |
|---|---|---|---|
| Time-of-day | 16:45 (hour-16: 0W/3L live July, −$970 shadow) · 21:45 (21h: −$156 July) flag 591+610 | 593/595/601/604 all 17:00–19:30 | **Partial** — catches 2 of 4 |
| Chase-location (running-range) | locPos 0.947/0.980/0.970/0.973 | locPos 0.933–0.997 (588 None) | **NO** — on a trend day EVERYONE is at 0.93–1.0; factor non-informative |
| CCI/LSMA state | 607: TCCI 25.8 (decelerating vs 103.7 at 604) · 610: CCI-14 46.1 (weakest of day, sub-50 late) · 591/598: 82–86, healthy | winners 84–137 | **Partial** — flags 607+610, not 591/598 |
| Delta (CVD, 3-bar) | **+741 / +1,945 / +1,608 / −8** | −222 / +2 / −24 / −299 | **NO** — losers entered on STRONGER positive delta; no warning at 5-min granularity |
| Stop width vs noise floor | 2.5–4.0pt, all < 8.59 floor | 588 20pt, 593 6pt (others tight but T1-near) | **YES — the one clean mechanical separator** |

### 2c. Score-sizing test — as-researched score would have LOST to fixed-2 yesterday

Components applied at entry: **alignment** (day_type direction known + matches; None→0) ·
**leg** (Woodies trend_state=BLUE on last closed bar; 588 was RED) · **location** (research F3:
not-chase in running range — ALL 9 score 0, see 2b) · **time** (17:00–21:00 IL). Ladder sizing
s≥3→3c, s=2→2c, s≤1→1c; per-contract legs as in §1. Raw output:

```
ACTUAL as-traded:                       $+183.75
FIXED-2 (incl 591->2c):                 $+163.75
FIXED-3 T1/T2/T3-ladder:                $+751.25
VariantA scores {588:0 591:1 593:3 595:3 598:3 601:3 604:3 607:3 610:2}
SCORE-SIZED A (align/leg/loc/time):     $+437.50
VariantB scores {588:0 591:0 593:1 595:1 598:1 601:2 604:1 607:1 610:1}   # F1/F2/F3 as in SYSTEM7 doc
SCORE-SIZED B (research F1/F2/F3):      $+95.00
```

**Answer: depends entirely on the location component.**
- The **as-researched score (B: with-day + structure-pattern + range-location)** yields **+$95.00 —
  WORSE than fixed-2 (+$163.75)**: range-location zeroes every trade on a trend day and the
  pattern-tier starves the with-trend ZLR/REACTIVE winners. The July score was fitted on chop days.
- The **alignment/leg/time variant (A)** yields **+$437.50 (+$273.75 over fixed-2)** — nearly all
  of it from putting the 3rd contract on mid-day with-trend entries. It did NOT avoid the losers
  (598/607 still sized 3c): sizing is not the loser-fix; the stop floor (2a) is.
- Build implication for System-7: the location factor must be **day-type-conditional** —
  running-range anti-chase on balance days, **leg-relative pullback location on
  Trend/Variation days** (all four at-LSMA entries here had GOOD leg-location and failed on
  stop width instead). Score-sizing ships only after that amendment.

---

## 3 · Blocked winners — gateway journal replay (n=27 blocked setups simulated)

Journal: 350 raw 08-03 rows → 157 unique → 42 collapsed RTH setups (pattern+direction+entry+gate)
→ 15 fired (`blocked_by=None`) + 27 blocked simulated. Sim: entry at journal price, R=4.0pt
(median live initial risk of the day), win = +1R touched before −1R, then +2R vs BE tracked;
bars strictly after the block minute; conservative on ambiguity. Raw results:

```
16:35 HTLB LONG 7560.00 awaiting_release   WIN_1R@16:40 +2R@16:40   (fired 1 bar later @7563.5 = live 588)
18:15 ZLR 7602.50/.75  pattern_stop_cooldown WIN_1R@18:20 BE_after_1R   (x2)
18:40 REACTIVE_LONG 7607.50 daytype_playbook WIN_1R@18:45 +2R@19:25
18:40 ZLR 7607.50/7607.25 direction_context  WIN_1R@18:45 +2R@19:25   (x2)
19:15 ZLR 7611.50      lsma_flat            WIN_1R@19:25 BE_after_1R  (fired 5 min later @7614.25 = live 604)
19:40 REACTIVE_SHORT 7614.25 daytype_playbook LOSS_1R                  (GOOD block)
19:55 REACTIVE_SHORT 7612.00 daytype_playbook LOSS_1R                  (GOOD block)
19:57 ZLR 7614.75      direction_context    WIN_1R@20:15 +2R@20:25
20:00 ZLR 7613.75/7614.50 direction_context WIN_1R@20:10-15 (+2R x1)  (x2)
20:05 ZLR 7614.00      lsma_flat            WIN_1R@20:15 +2R@20:20
20:15 ZLR 7616.75/7616.50 lsma_flat         WIN_1R@20:20 +2R@20:30   (x2)
20:50 REACTIVE_LONG 7626.50 daytype_playbook WIN_1R@21:00 +2R@21:05
21:42 ZLR 7630.25      direction_context    WIN_1R@21:50 +2R@22:00   (live fired 21:45 @7632.75 instead -> stopped)
21:45 REACTIVE_LONG 7632.50 daytype_playbook WIN_1R@22:00 BE_after_1R
21:50/21:55 ZLR 7632.5-7633.0 pattern_stop_cooldown WIN_1R@22:00 BE_after_1R (x3)
22:00 ZLR 7632.75      lsma_flat            WIN_1R@22:05 BE_after_1R
22:05 DOUBLE_BOTTOM_EE_LONG 7636.75 location_gate LOSS_1R             (GOOD block)
22:15-22:35 (x4)       eod_entry_cutoff     LOSS_1R all               (GOOD blocks)

blocked simmed: 27 | 1R-winners: 20
winners by gate:  direction_context 6/6 · lsma_flat 5/5 · pattern_stop_cooldown 5/5 · daytype_playbook 3/5 · awaiting_release 1/1
correct blocks:   eod_entry_cutoff 4/4 · location_gate 1/1 · daytype_playbook short-fades 2/2
```

**$ estimate after clustering duplicates** (2c, T1=+1R $20/c banked, T2=+2R $40/c when reached,
BE otherwise; assumptions labeled):
- **Strictly additive** (no live position open at the time): 18:15 (+$20) · 19:57–20:15 cluster
  (+$60) · 20:50 (+$60) · 21:50–22:00 cluster (+$20) = **+$160**.
- **Replacement / second-position** (not additive with the above): 18:40 cluster — shadow #602
  actually banked **+$67.50** at 18:36 while live was managing 601 (single-position limit);
  21:42-for-610 swap (block delayed entry 3 min, 7630.25 → 7632.75) = **+$92.50 swing**;
  entry-taxes measured: awaiting_release on 588 (7560 → 7563.5) = **$35**, lsma_flat on 604
  (7611.5 → 7614.25) = **$27.50**. Subtotal ≈ **+$222.50**.
- Range: **+$160 (strict) … ≈ +$383 (multi-position + swaps)**.

**Mechanism of the worst gate** (`direction_context`, 6/6 wrong, `trading_gateway.py:1312`):
`sustained_lsma_side` (`direction_context_live.py:43-53`) returns DOWN when the k most-recent
closes are ALL below LSMA — which is precisely what a pullback-to-LSMA looks like — and with
3-bar `cvd_slope` ≤ 0 (pullback bars), `lsma_cvd_veto_direction` (`direction_context.py:70-85`)
declares "day-context DOWN" on a day whose cumulative delta rose 2,215 → 13,948. The model
converts the entry condition (pullback) into a veto, exactly at pullback completion. The gates
that were RIGHT yesterday: eod_entry_cutoff saved ≈$160 (4 late longs at 1R loss each),
playbook short-fade blocks saved ≈$80, location_gate saved ≈$40, and the opening 1c cap on 591
saved $20 — the fix is surgical, not "open the gates".

---

## 4 · Missed structure — pullback-to-LSMA holds the systems never saw (n=10 candidates)

Scan (existing-pattern spirit, disclosed): prior bar trend BLUE, bar low ≤ LSMA+1.0, close holds
above LSMA, next bar takes out the pullback-bar high → candidate entry; "covered" = any journal
event (fire or block) or live/shadow entry within ±10 min.

```
16:40 AMBIG | 16:45 AMBIG | 16:50 WIN@16:55 | 17:35 WIN@17:55 | 19:25 LOSS | 20:15 WIN@20:30
20:20 WIN@20:35 | 20:25 WIN@20:50 | 21:00 LOSS | 22:20 LOSS
candidates: 10 | UNCOVERED: []   (all 10 within +-10min of a fire/block/shadow entry)
```

**Honest answer: zero detector-level misses.** Every clean with-trend pullback was seen by the
systems — fired, shadow-fired, or blocked at a gate. Yesterday's inefficiency lived entirely in
(a) gate policy (§3), (b) stop width (§2a), (c) missing 3rd contract (§1) — not in detection.
(The bars' own `zlr_detected` flags at 20:10/20:15/21:40-22:15 confirm the same coverage.)

---

## 5 · Shadow cross-check (n=15, +$336.25)

Shadow out-earned live +$336.25 vs +$183.75 on the same day with the same signals, from exactly
the three mechanisms above: it took the 18:36 re-entry (+$67.50) live skipped (single-position),
and its virtual management survived the noise dips live stops died in (609 vs 610: +$41.25 vs
−$32.50; 597 vs 598: +$20.00 vs −$7.50; 590 vs 591: +$15.00 vs −$20.00). Caveat: shadow fills
are virtual (MAE-report caveat), so treat as direction-of-evidence, not exact $.

---

## 6 · Ranked: change → evidence → expected $ on a day like yesterday

Items OVERLAP — do not sum. Stacked upper bound (floor-stops AND 3c-ladder together, winners 3c
+ losers floor-simmed at 3c): **+$1,121.25** raw output
`STACKED: winners3c=908.75 losers_floor=212.50 total=1121.25`.

| # | Change | Evidence (this day) | Expected $ on a day like 08-03 |
|---|---|---|---|
| 1 | **3rd contract T1/T2/T3-BE ladder on trend/Variation-up days** (live from today — verify vs FIXED_CONTRACTS/clamp config) | §1: fixed-3 ladder +$751.25 vs fixed-2 +$163.75; all 5 winners' post-T2 MFE reached day high 7638.5 | **+$570..+$590** (July chop sample says gate it by day-type — fixed-3 there was worst at −$1,281) |
| 2 | **Stop floor `max(6, 0.15×IB)` on S4/ZLR re-entries** (DALTON rec-4; RR re-checked against the floor, T1 may need structure re-anchor) | §2a: 4/4 losers were sub-floor noise-stops; floor-replay: 4/4 hit T1 first, 0/4 floor touched; shadow same-signal corroboration | **+$225..+$230** at actual sizes (+$212 extra legs if stacked with #1) |
| 3 | **Fix `direction_context` for trend days** — sustained_lsma_side flips DOWN during pullback-to-LSMA; add day_type/CVD-cumulative override (`trading_gateway.py:1312`, `direction_context_live.py:43`, `direction_context.py:70`) | §3: 6/6 blocked setups were 1R winners (4 reached 2R); gate claimed "CVD → DOWN" while day delta rose 2,215→13,948 | **+$60..+$150** (cluster-deduped; overlaps #4/#5 clusters) |
| 4 | **`lsma_flat` scope on confirmed trend days** — mid-trend consolidation is the re-entry zone, not chop (`trading_gateway.py:1377`) | §3: 5/5 blocked 1R winners incl. the 19:15 entry that would have improved live 604 by $27.50 | **+$60..+$90** |
| 5 | **`pattern_stop_cooldown` after a SUB-FLOOR stop-out** — a noise-stop should not lock the pattern for 30min (`trading_gateway.py:1526`); mostly dissolves if #2 ships | §3: 5/5 blocked 1R winners (18:15 after 598, 21:50-55 after 610) | **+$40 residual** (absorbed by #2) |
| 6 | **`daytype_playbook` with-trend side on Variation EXPANSION** — keep the short-fade blocks (2/2 correct), relax "chasing session extreme" for with-trend REACTIVE | §3: 3 blocked 1R winners (18:40, 20:50, 21:45) vs 2 correct short blocks the same day | **+$80..+$120** |
| 7 | **System-7 score-sizing 1–3 only AFTER a day-type-conditional location factor** (leg-relative pullback location on trend days) | §2c: as-researched score = +$95 (LOSES $69 to fixed-2); alignment/leg/time variant = +$437.50 (+$274) | **+$270 IF amended; −$70 if shipped as-researched** |
| 8 | **Second-position / add-on lane while managing a winner** (shadow proof, contradicts July "no evidence on add-ons") | §5: shadow #602 +$67.50 at 18:36 during live 601; single-position limit is the only reason live missed it | **+$60..+$70** |
| 9 | **`awaiting_release` zone-release latency** (1 bar) — entry tax on the opening HTLB | §3: 16:35 block at 7560 → fired 16:35+1bar at 7563.5 = 3.5pt × 2c | **+$35** |
| — | Keep as-is (verified paying yesterday): eod_entry_cutoff (4/4 correct, ≈$160 saved) · playbook short-fades (2/2, ≈$80) · location_gate at extremes (1/1, ≈$40) · opening 1c cap (saved $20 on 591) | §3 | protective, do not relax |

**Bottom line:** the same 9 signals, with today's 3rd contract plus a noise-floor stop, were a
≈**+$1,100 day** (stacked upper bound, one trend day, all assumptions above); the gate fixes are
worth another ≈$160–380 on the re-entry stream. The single change with negative expected value
yesterday was the one we almost built first — range-location score-sizing as researched on July's
chop sample. Day-type-conditionality is the recurring theme in every finding.

---

*Analysis run read-only against `postgresql://localhost/mems26` via `backend.v9.db.read.read_all`
on the trading MacBook, 2026-08-04. Bars source verified live (`v9_bars_5min_woodies`, last 08-03
bar 23:55 IL). This file is the only write; reproducible from the queries + definitions above.*
