# Six Days · The Moments — bar-by-bar Dalton review with our instruments only

**Date:** 2026-09-08 · **Author:** cowork-dev (read-only forensic pass, no code/service/flag touched)
**Sessions:** BEST `2026-08-28` `2026-09-02` `2026-08-27` · WORST `2026-09-01` `2026-08-31` `2026-08-14`
**Window:** RTH `(ts AT TIME ZONE 'Asia/Jerusalem')::time BETWEEN '16:30' AND '23:00'` (= 08:30–15:00 CT)

---

## 0 · Method, and what makes every number reproducible

**Bars.** `v9_bars_5min_woodies` — the contiguous live source per `docs/SOURCE_OF_TRUTH.md`.
79 RTH bars on every one of the six days (0 gaps). **`ts` is the bar OPEN**, established from the
volume step at the cash open (09-01: 16:25 V=4,143 → 16:30 V=26,699; 09-02: 8,275 → 24,551).
Therefore **IB = bars 16:30…17:25 inclusive** (12 bars), which reproduces `v9_tpo_sessions.ib_high/ib_low`
exactly on 4 of 6 days (08-27, 08-28, 08-31, 09-02) and to one bar on the other two.

```sql
SELECT to_char(ts AT TIME ZONE 'Asia/Jerusalem','HH24:MI') t, open,high,low,close,volume,
       cci_14, lsma_value, trend_state, zlr_detected, zlr_direction, hfe_detected, hfe_direction
FROM v9_bars_5min_woodies
WHERE (ts AT TIME ZONE 'Asia/Jerusalem')::date = date '<D>'
  AND (ts AT TIME ZONE 'Asia/Jerusalem')::time BETWEEN time '16:30' AND time '23:00'
ORDER BY ts;
```

**Structure.** `v9_tpo_sessions WHERE session_type='CASH'` (`trading_date` is VARCHAR — pass ISO text)
for prior-day VAH/POC/VAL and today's IB; `v9_day_type_history` for the S1 label / opening type.

**Order flow.** `v9_bars_cumulative_delta` (`delta` = per-bar delta, `cumulative` = running).
Audited for the duplication warning — result (RTH window only):

| day | RTH bars | CVD rows | on 5-min grid | off-grid | minutes with >1 row |
|---|---|---|---|---|---|
| 08-14 | 79 | 78 | 78 | 0 | 0 |
| 08-27 | 79 | 78 | **53** | **25** | 0 |
| 08-28 | 79 | **104** | 79 | **25** | 0 |
| 08-31 | 79 | 79 | 79 | 0 | 0 |
| 09-01 | 79 | 79 | 79 | 0 | 0 |
| 09-02 | 79 | 79 | 79 | 0 | 0 |

So: **no duplicated grid minute on any of the six days** — the artifact is 25 *off-grid* rows on 08-27
and 08-28. The join used the `HH:MI` grid key, so every delta quoted below is 1:1 with its bar.
**On 08-27, 26 of 79 bars have no on-grid delta at all** — no claim below leans on delta at those bars.

**Did our systems see it.** Two persistent sources (the `/api/v9/gateway/decisions` feed is an
in-memory ring of 300 and `/tmp/backend.err.log` only reaches back to 2026-09-06, so neither can
answer for August):

1. `~/SierraChart_Data/v9_export/decisions_archive/gateway_decisions.<date>.jsonl` — one
   `GATE_DECISION` per candidate with `system, pattern, direction, entry, blocked_by, reason,
   outcome, live_blocked_by, trade_id`. All six days present.
2. `v9_trades` (all modes) + `v9_shadow_ledger` (a VIEW over `v9_s7_shadow_log`/`v9_tsf_shadow_log`;
   it only carries rows that already have a `trade_id`, so it can confirm a fire but can never
   record a block).

**Classification rule (fixed in advance, ±10 min, same direction as the moment):**
* **TAKEN** — a `v9_trades` row with `mode='live'`.
* **SEEN-BUT-BLOCKED** — a `GATE_DECISION` with non-null `blocked_by` (never reached an executor).
* **DETECTED-IN-SHADOW** — `outcome='shadow_only'` (shadow trade only; name `live_blocked_by` if set).
* **NOT SEEN AT ALL** — no decision and no trade in that direction inside the window.

**P&L.** Every payoff below is computed from the bars themselves — forward-walking each bar's
high/low from the entry bar's close, stopping at the structural stop if it is touched first.
**Nothing is taken from `v9_trades.pnl_usd`**, which is unsafe for this purpose (T-160 phantom
synthetic P&L, T-252 shadow re-bar duplication, T-270 empty `exit_fills`).
MES = **$5/point**; every `$` below is at **2 contracts** (= $10/point). Shorts: points = entry − exit.

**Anti-hindsight rule.** Each moment is defined from information available **at that bar's close
only**, and the information is written out. A candidate was rejected if its case — or its stop
placement — needed a later bar. **9 candidates were rejected on this ground** (§4).

---

## 1 · The days

### 2026-08-28 — BEST · Neutral_Center, OPEN_DRIVE, IB 7726.50–7760.50 (w 34.0)
Prior CASH value 7736.75–7746.50 (POC 7736.75). Open 7746.25 — right on prior VAH.
RTH 7711.75 / 7782.50, close 7722.50.

* **17:30 LONG @7750.75** — at that close: the 17:00–17:10 probe drove to 7726.50 (10 pts below
  prior POC) and was rejected; 17:30 closes +8.75 with delta +1270, CCI back through zero, LSMA
  turning, `zlr_detected=UP`+`hfe_detected=UP`. Failed downside auction below value → rotate back
  through value. Stop below the 17:30 low **7738.00** (risk 12.75). First target IB high 7760.50 —
  **hit 17:40, +9.75 pts = $97.50**. Extreme before stop 7782.50 @18:00 — **+31.75 pts = $317.50, R 2.49**.
  → **SEEN-BUT-BLOCKED** · `lsma_flat` at 17:35:03 and 17:35:06 on S4 ZLR LONG **@7750.75 — the
  identical price** (`|LSMA slope 0.1633| < 0.2500`); also `awaiting_release` at 17:21:47.
* **18:40 SHORT @7757.50** — the up-extension to 7782.50 (18:00) failed and 18:40 is the first close
  back **inside** the IB (< 7760.50), on three consecutive negative-delta bars (−962/−1556/−1008) with
  CCI −110 and trend RED. Textbook look-above-and-fail. Stop above the last lower high **7775.50**
  (risk 18.0). First target IB low 7726.50 — **hit 19:15, +31.00 pts = $310**. Extreme 7711.75 @20:10 —
  **+45.75 pts = $457.50, R 2.54**.
  → **SEEN-BUT-BLOCKED** · `awaiting_release` at 18:40:04, S2 DOUBLE_TOP_AA_SHORT @7765.75
  ("left the zone without volume — not convincing"). The same idea fired **live 15 min later**
  at 7750.00 (S2 INITIATIVE_SHORT, tid 851) — 7.5 pts of the move already gone.
* **19:20 SHORT @7724.00** — range extension down: 19:15/19:20 break the IB low on delta −2363/−1689,
  cumulative −9,188. Stop above 7741.50 (risk 17.5). Extreme 7711.75 @20:10 — **+12.25 pts = $122.50, R 0.70**.
  → **DETECTED-IN-SHADOW** · 19:16:04 S4 ZLR SHORT @7734.75 `outcome=shadow_only`,
  `live_blocked_by=live_slot_occupied` (shadow trade id 855).

RTH blocker histogram 08-28 (n=76): `(passed)` 21 · **daytype_playbook 18** · **awaiting_release 12** ·
eod_entry_cutoff 8 · **lsma_flat 7** · rr_hard_floor 3 · cold_start_guard 2 · location_gate 2.

### 2026-09-02 — BEST · Variation, OPEN_AUCTION_IN, IB 7643.25–7682.50 (w 39.25)
Prior CASH value 7637.25–7673.75 (POC 7644.00). Open 7650.50 — inside prior value, at prior POC.
RTH 7643.25 / 7691.25, close 7680.50.

* **16:55 LONG @7656.75** — at that close: the 16:45 sell (delta −2,564) was fully absorbed and 16:55
  closes at the session high with delta +1,469; price is holding above prior POC with cumulative
  delta turning positive. Open-in-value → initiative buy toward the value edge. Stop below 16:45 low
  **7645.75** (risk 11.0). First target prior VAH 7673.75 — **hit 17:15, +17.00 pts = $170**.
  Extreme 7691.25 @18:30 — **+34.50 pts = $345, R 3.14**.
  → **SEEN-BUT-BLOCKED** · `awaiting_release` ×4 inside the window (16:45:03 S2 FAILED_BREAK_LONG
  @7654.50; 16:53:24, 16:55:02, 16:55:06 S4 ZLR LONG @7650.50–7652.00), plus four more
  `awaiting_release` blocks on the same long at 16:35/16:40.
* **17:15 LONG @7674.75** — first close **above prior-day VAH** on the 4th consecutive up bar,
  cumulative delta +5,820, CCI 177, LSMA rising ~4 pts/bar. Acceptance above prior value.
  Stop below the last higher low **7662.75** (risk 12.0). First target IB high 7682.50 — **hit 17:25,
  +7.75 pts = $77.50**. Extreme 7691.25 @18:30 — **+16.50 pts = $165, R 1.38**.
  → **TAKEN** · 17:15:06 S2 INITIATIVE_LONG @7668.75 → live, trade 953.
* **20:45 LONG @7676.50** — the afternoon pullback bottoms at 7670.00, i.e. **above** prior VAH
  7673.75 only marginally but above the breakout shelf; 20:40/20:45 print delta +1,807/+777 and CCI
  flips −135 → +96. Old resistance holding as support. Stop below **7670.00** (risk 6.5).
  First target 7686.00 — **hit 21:15, +9.50 pts = $95**. Extreme 7687.50 — **+11.00 pts = $110, R 1.69**.
  → **DETECTED-IN-SHADOW** · 20:45:05 and 20:50:02 S2 CEILING_FLIP_LONG `outcome=shadow_only`
  (shadow-only flag, no live blocker). The parallel S2 REACTIVE_LONG @7676.50 was blocked by
  `daytype_playbook` ("REACTIVE responsive LONG not at VAL (mid_value) on Variation").

RTH blocker histogram 09-02 (n=57): `(passed)` 22 · **awaiting_release 16** · entry_not_confirmed 5 ·
rr_hard_floor 3 · daytype_playbook 3 · rr_entry_gate 3 · location_gate 2 · eod_entry_cutoff 2.

### 2026-08-27 — BEST · Variation, OPEN_REJECTION_REVERSE, IB 7702.75–7730.50 (w 27.75)
Prior CASH value 7673.75–7679.50. Open 7716.25 — ~37 pts **above** prior VAH.
RTH 7702.75 / 7755.75, close 7738.25.

* **16:40 LONG @7723.25** — at that close: the gap-above-value open sold to 7703.00 and 7702.75 on the
  first two bars, then the third bar closed **above the opening print and above bar-1's high**, CCI
  −125 → +226, trend RED → BLUE. The downside probe found no sellers → ORR. Stop below the rejection
  low **7702.75** (risk 20.5). First target 7738.25 — **hit 18:00, +15.00 pts = $150**.
  Extreme 7755.75 @20:10 — **+32.50 pts = $325, R 1.59**.
  → **NOT SEEN AT ALL** (±10 min, LONG): zero gateway decisions and zero trades. The only two
  decisions in that stretch were 16:30:07 and 16:31:39 S4 ZLR **SHORT**, both blocked by
  `cont_trend_filter`. The idea did fire **15 minutes later** — 16:55:04 S2 OPENING_ORR LONG
  @7723.50 → live, trade 822 — i.e. at the *same price*, but with a ~10-pt stop instead of the
  20.5-pt structural one, and it was stopped for −$100 while the idea ran +32.5 pts.
* **17:45 LONG @7733.75** — first close above the locked IB high 7730.50, delta +1,401, CCI 135,
  LSMA rising. Range extension up on a day that already rejected lower. Stop below the last higher
  low **7724.50** (risk 9.25). First target IB high + ½ IB width = 7744.25 — **hit 19:35, +10.50 pts
  = $105**. Extreme 7755.75 @20:10 — **+22.00 pts = $220, R 2.38** (stop finally taken 21:25).
  → **SEEN-BUT-BLOCKED** · 17:46:04 S4 ZLR LONG @7728.75 → `daytype_playbook` ("ZLR SKIP on Normal");
  17:50:03 S2 DOUBLE_BOTTOM_EE_LONG @7734.00 → `structural_targets_wrong_side`.
* **20:45 SHORT @7745.75** — the up-auction stalled at 7755.75 (20:10) and 20:45 is the third lower
  high with delta −832 and CCI −165; LSMA rolls over. Responsive selling back into value.
  Stop above the session high **7755.75** (risk 10.0). First target today's POC 7736.75 — **hit 21:00,
  +9.00 pts = $90**. Extreme 7722.75 @21:55 — **+23.00 pts = $230, R 2.30**.
  → **SEEN-BUT-BLOCKED** · 20:45:01 S4 GB100 SHORT and 20:45:04 S2 INITIATIVE_SHORT, both @7747.75,
  both `lsma_flat` (`|LSMA slope 0.0000| < 0.1300`). Fired live 15 min later at 7743.50 (trade 830).

RTH blocker histogram 08-27 (n=46): `(passed)` 11 · **awaiting_release 9** · **lsma_flat 7** ·
daytype_playbook 6 · structural_targets_wrong_side 4 · eod_entry_cutoff 4 · cont_trend_filter 2.

### 2026-09-01 — WORST · Neutral_Center, OPEN_AUCTION_OUT, IB 7638.50–7667.25 (w 28.75)
Prior CASH value 7692.00–7695.50 (a 3.5-pt balance). Open 7647.00 — ~45 pts **below** prior VAL.
RTH 7621.50 / 7673.75, close 7643.00.

* **19:10 SHORT @7662.00** — at that close: two failed attempts to climb back toward prior value
  (7672.25 @17:30, 7673.75 @18:50) = a double top; cumulative delta collapsed +3,740 → −225 on five
  straight negative bars; CCI through zero; price back below the IB high. The return-to-value attempt
  is dead. Stop above the double top **7673.75** (risk 11.75). First target IB low 7638.50 —
  **hit 20:25, +23.50 pts = $235**. Extreme 7621.50 @21:45 — **+40.50 pts = $405, R 3.45**.
  **This is the trade of the whole six-day sample.**
  → **SEEN-BUT-BLOCKED** · `awaiting_release`, 24 consecutive blocks on S2_DELTA_DBL_SHORT
  @7668.00–7669.50 between 18:57:55 and 19:02:42 ("only 1–2 bars since the extreme"), then again at
  19:20:01 on S4 GB100 SHORT @7657.00. The system finally went live at 19:35 @7643.75 — 18 points
  lower, at the bottom of the first leg — and was stopped for −$156.25.
* **21:30 SHORT @7634.50** — breaks the 19:45–21:20 balance (≈7639.25–7650.75) and the session low
  7632.75, cumulative delta −10,194 (day's most negative), CCI −225. Stop above the 21:20 swing high
  **7645.25** (risk 10.75). Measured-move target 7621.25 — **not reached (low 7621.50)**;
  extreme 7621.50 @21:45 — **+13.00 pts = $130, R 1.21**.
  → **SEEN-BUT-BLOCKED** · 21:25:05 `awaiting_release`, 21:25:08 `extreme_chase_guard`
  ("SHORT entry 7641.00 too close to session_low 7632.75, dist 8.25 < 8.6"), 21:35:04 `location_gate`
  ("Neutral_Extreme: SHORT fade at near_val — wrong location").
* **21:55 LONG @7634.00** — 21:40 capitulated to 7623.50 on delta −1,841 and 21:45 answered with
  +1,889 (day's largest buy bar) and `hfe_detected=UP`; 21:55 makes the higher low 7628.25.
  Stop below **7621.50** (risk 12.5). First target 7643.00 — **hit 22:15, +9.00 pts = $90**.
  Extreme 7647.25 @23:00 — **+13.25 pts = $132.50, R 1.06**.
  → **SEEN-BUT-BLOCKED** · 22:05:04 S4 FAMIR LONG @7638.50 → `awaiting_release`.

RTH blocker histogram 09-01 (n=77): **awaiting_release 41** · **daytype_playbook 14** · `(passed)` 9 ·
entry_not_confirmed 4 · news_blackout 2 · location_gate 2 · rr_entry_gate 1 · pattern_stop_cooldown 1 ·
extreme_chase_guard 1. (14 of the 14 `daytype_playbook` are "ZLR SKIP on Neutral_Extreme", 20:00–20:55.)

### 2026-08-31 — WORST · Variation, OPEN_DRIVE, IB 7674.75–7704.25 (w 29.5)
Prior CASH value 7758.25–7781.50. Open 7701.25 — ~57 pts below prior VAL.
RTH 7674.75 / 7708.25, close 7700.75. Low made in the IB, high in the last ten minutes.

* **17:35 LONG @7684.25** — at that close: the open-drive-down bottomed at 7674.75 on the last IB bar,
  17:30 made a higher low, and 17:35 printed **+2,231 delta — the largest buy bar of the session** —
  and +9.5 pts of range. Drive exhausted at the IB low, responsive buying. Stop below the session low
  **7674.75** (risk 9.5). First target the session open 7701.25 — **hit 22:50, +17.00 pts = $170**.
  Extreme 7708.25 @22:55 — **+24.00 pts = $240, R 2.53**; never stopped.
  → **SEEN-BUT-BLOCKED** · 17:40:03 S4 FAMIR LONG **@7684.25 — the identical price** →
  `daytype_playbook` ("FAMIR SKIP on Normal"); 17:45:05 S2 REACTIVE_LONG @7685.50 → `awaiting_release`.
* **21:55 LONG @7684.50** — the 21:35/21:40 flush stopped at 7678.00, a higher low vs 7674.75, and
  delta turned +726/+398. Stop below **7678.00** (risk 6.5). First target 7696.25 — **hit 22:40,
  +11.75 pts = $117.50**. Extreme 7708.25 — **+23.75 pts = $237.50, R 3.65**.
  → **SEEN-BUT-BLOCKED** · S4 FAMIR LONG blocked by `daytype_playbook` ("FAMIR SKIP on Normal") at
  21:45:02, 21:50:04, 21:55:02 and 22:00:06 — four times on the same idea, @7681.75 → 7685.25.
* **22:40 LONG @7698.25** — breaks the five-hour balance high on delta +1,196, CCI 152, cumulative
  delta back to flat from −3,000. Stop below **7689.75** (risk 8.5). First target IB high 7704.25 —
  **hit 22:50, +6.00 pts = $60**. Extreme 7708.25 — **+10.00 pts = $100, R 1.18**.
  → **SEEN-BUT-BLOCKED** · 22:35:03/22:35:09 S4 ZLR LONG @7692.25 → `eod_entry_cutoff`.

RTH blocker histogram 08-31 (n=517): **awaiting_release 294** · **duplicate_fire 140** · `(passed)` 49 ·
cluster_guard 12 · daytype_playbook 7 · direction_compass 6 · location_gate 3. (The 517 is the
`S2_DELTA_DBL` storm — 61 shadow trades, all `STOP_HIT`, several per second.)

### 2026-08-14 — WORST · Variation, OPEN_DRIVE, IB 7813.75–7830.75 (w 17.0)
Prior CASH value 7808.25–7810.50 (a 2.25-pt balance). Open 7827.75 — ~17 pts above prior VAH.
RTH 7796.50 / 7830.75, close 7802.75. Only 34.25 pts of range — a genuinely thin day.

* **17:10 SHORT @7825.25** — at that close: four attempts at 7828.50–7830.75 over 40 minutes
  (16:45, 16:50, 17:00, 17:05) all rejected; the gap above a 2.25-pt prior value has produced no
  upside acceptance; 17:10 prints the first big sell (delta −1,391) and CCI drops 84 → 3.
  Failed auction above value → return to value. Stop above the last high **7830.75** (risk 5.5).
  First target prior VAH 7810.50 — **hit 17:30, +14.75 pts = $147.50**. Extreme 7796.50 @20:35 —
  **+28.75 pts = $287.50, R 5.23**; never stopped. **Best risk-adjusted moment in the sample.**
  → **SEEN-BUT-BLOCKED** · 17:00:03 S4 ZLR SHORT @7825.00 → `awaiting_release`; 17:00:10 same
  candidate → `lsma_flat`; 17:15:05 and 17:15:08 S4 ZLR SHORT @7825.25/7825.75 → `cont_trend_filter`
  ("ZLR (CONT) setup DOWN vs sustained NEUTRAL"). The system did not go short until 17:35 @7811.25 —
  i.e. exactly *at* the first target — and was stopped.
* **21:00 LONG @7802.50** — three consecutive positive-delta bars off the 20:35 low (+608/+554/+1,015),
  first BLUE of the afternoon, CCI −64 → +100, price reclaims the 20:20–20:45 shelf.
  Stop below the session low **7796.50** (risk 6.0). First target 7810.25 — **not reached**;
  extreme 7807.50 @21:50 — **+5.00 pts = $50, R 0.83**; never stopped. A small moment on a small day.
  → **SEEN-BUT-BLOCKED** · 20:55:03 S4 HTLB LONG @7799.75 → `direction_context`
  ("setup UP vs day-context DOWN — LSMA DOWN + CVD-slope +0 → DOWN").

Only two moments are listed for 08-14: the day had no third structure worth an entry, and inventing
one would be exactly the error §4 guards against.

RTH blocker histogram 08-14 (n=55): `(passed)` 16 · **lsma_flat 8** · **awaiting_release 7** ·
eod_entry_cutoff 6 · cont_trend_filter 5 · direction_context 4 · entry_not_confirmed 4.

---

## 2 · The 17 moments, compressed

`risk`, `→T1`, `→ext` in points; `$` at 2 contracts ($10/pt). Shorts: points = entry − exit.

| # | day | time | dir | entry | stop | risk | →T1 | →ext ($) | R | verdict | blocker |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 08-14 | 17:10 | SHORT | 7825.25 | 7830.75 | 5.50 | +14.75 | **+28.75 ($287.50)** | 5.23 | SEEN-BUT-BLOCKED | `awaiting_release` → `lsma_flat` → `cont_trend_filter` |
| 2 | 08-14 | 21:00 | LONG | 7802.50 | 7796.50 | 6.00 | n/r | +5.00 ($50) | 0.83 | SEEN-BUT-BLOCKED | `direction_context` |
| 3 | 08-27 | 16:40 | LONG | 7723.25 | 7702.75 | 20.50 | +15.00 | **+32.50 ($325)** | 1.59 | **NOT SEEN AT ALL** | — (live 15 min later, non-structural stop) |
| 4 | 08-27 | 17:45 | LONG | 7733.75 | 7724.50 | 9.25 | +10.50 | +22.00 ($220) | 2.38 | SEEN-BUT-BLOCKED | `daytype_playbook` + `structural_targets_wrong_side` |
| 5 | 08-27 | 20:45 | SHORT | 7745.75 | 7755.75 | 10.00 | +9.00 | +23.00 ($230) | 2.30 | SEEN-BUT-BLOCKED | `lsma_flat` ×2 |
| 6 | 08-28 | 17:30 | LONG | 7750.75 | 7738.00 | 12.75 | +9.75 | **+31.75 ($317.50)** | 2.49 | SEEN-BUT-BLOCKED | `lsma_flat` (same price) |
| 7 | 08-28 | 18:40 | SHORT | 7757.50 | 7775.50 | 18.00 | +31.00 | **+45.75 ($457.50)** | 2.54 | SEEN-BUT-BLOCKED | `awaiting_release` |
| 8 | 08-28 | 19:20 | SHORT | 7724.00 | 7741.50 | 17.50 | +12.25 | +12.25 ($122.50) | 0.70 | DETECTED-IN-SHADOW | `live_slot_occupied` |
| 9 | 08-31 | 17:35 | LONG | 7684.25 | 7674.75 | 9.50 | +17.00 | +24.00 ($240) | 2.53 | SEEN-BUT-BLOCKED | `daytype_playbook` (FAMIR SKIP) |
| 10 | 08-31 | 21:55 | LONG | 7684.50 | 7678.00 | 6.50 | +11.75 | +23.75 ($237.50) | 3.65 | SEEN-BUT-BLOCKED | `daytype_playbook` ×4 (FAMIR SKIP) |
| 11 | 08-31 | 22:40 | LONG | 7698.25 | 7689.75 | 8.50 | +6.00 | +10.00 ($100) | 1.18 | SEEN-BUT-BLOCKED | `eod_entry_cutoff` |
| 12 | 09-01 | 19:10 | SHORT | 7662.00 | 7673.75 | 11.75 | +23.50 | **+40.50 ($405)** | 3.45 | SEEN-BUT-BLOCKED | `awaiting_release` ×24 |
| 13 | 09-01 | 21:30 | SHORT | 7634.50 | 7645.25 | 10.75 | n/r | +13.00 ($130) | 1.21 | SEEN-BUT-BLOCKED | `extreme_chase_guard` + `awaiting_release` + `location_gate` |
| 14 | 09-01 | 21:55 | LONG | 7634.00 | 7621.50 | 12.50 | +9.00 | +13.25 ($132.50) | 1.06 | SEEN-BUT-BLOCKED | `awaiting_release` |
| 15 | 09-02 | 16:55 | LONG | 7656.75 | 7645.75 | 11.00 | +17.00 | **+34.50 ($345)** | 3.14 | SEEN-BUT-BLOCKED | `awaiting_release` ×4 |
| 16 | 09-02 | 17:15 | LONG | 7674.75 | 7662.75 | 12.00 | +7.75 | +16.50 ($165) | 1.38 | **TAKEN** (live, trade 953) | — |
| 17 | 09-02 | 20:45 | LONG | 7676.50 | 7670.00 | 6.50 | +9.50 | +11.00 ($110) | 1.69 | DETECTED-IN-SHADOW | shadow-only flag (CEILING_FLIP) |

Every stop was checked bar-by-bar; `→ext` is the extreme reached **before** the stop was touched.
Only three moments ever saw their stop at all: #4 (21:25) and #6 (18:55), both long after the first
structural target had been paid, and #13 (22:55), whose measured-move target was missed by 0.25 pt
(low 7621.50 vs 7621.25) so it is scored at its extreme only. `n/r` = target not reached.

---

## 3 · The split, and the blocker that costs the most

**17 moments across six sessions:**

| verdict | n | share |
|---|---|---|
| **SEEN-BUT-BLOCKED** | **13** | **76.5 %** |
| DETECTED-IN-SHADOW (never reached live) | 2 | 11.8 % |
| TAKEN (live) | 1 | 5.9 % |
| **NOT SEEN AT ALL** | **1** | **5.9 %** |

**The answer to the question: the detectors are not the problem.** 16 of 17 (94 %) of the days'
best moments were produced by S2 or S4 at the right bar, often at the exact price. Only one moment
(08-27 16:40 ORR long) had no candidate inside ±10 minutes — and even that one fired 15 minutes
later at the identical price, so the true "missing detector" count is somewhere between 0 and 1.
**Roughly 13 blocked : 1 unseen.** This is a gate problem, not a coverage problem.

**Dominant blocker.** Counting the distinct gates named on each of the 13 blocked moments:

| blocker | moments it blocked | which |
|---|---|---|
| **`awaiting_release`** | **8 of 13 (62 %)** | #1, #6, #7, #9, #12, #13, #14, #15 |
| `lsma_flat` | 3 | #1, #5, #6 |
| `daytype_playbook` | 3 | #4, #9, #10 |
| `cont_trend_filter` | 1 | #1 |
| `direction_context` | 1 | #2 |
| `structural_targets_wrong_side` | 1 | #4 |
| `eod_entry_cutoff` | 1 | #11 |
| `extreme_chase_guard` | 1 | #13 |
| `location_gate` | 1 | #13 |

`awaiting_release` is also the top RTH blocker on four of the six days by raw count
(08-31: 294 · 09-01: 41 · 09-02: 16 · 08-27: 9) and #2 on 08-28 (12).
Its reasons cluster into three phrasings — *"only N bars since the extreme"*, *"structure not
turning (1/2 higher lows)"*, *"left the zone without volume — not convincing"* — and all three
are the **same structural objection**: the gate wants the reversal to be already visible before it
will let you enter. On every one of the eight moments above, that objection was wrong: the entry
bar *was* the turn. The clearest single case is #12 — 24 blocks in five minutes on the trade that
would have paid $405, followed by a live entry 18 points worse that lost $156.25.

The runner-up pair is instructive because it is a different failure. `lsma_flat` (3 moments) and
`daytype_playbook` (3 moments) both blocked **reversal** entries specifically: `lsma_flat` by
definition rejects the bar where LSMA has not yet turned — which is every turn — and
`daytype_playbook`'s "FAMIR SKIP on Normal" / "ZLR SKIP on Neutral_*" skipped the two best longs
on 08-31 four separate times at four separate prices.

**One structural observation that is not a gate:** on the three moments the system *did* act on
near the right time (#3 live-15-min-late, #7 live-15-min-late, #5 live-15-min-late), it entered
7.5–18 points worse and used a stop far tighter than the structural one — 08-27 #3 used ~10 pts
where the structure asked for 20.5 and was stopped out of a +32.5-pt idea. Late entry plus a
non-structural stop converts a winning read into a loss even when the gate eventually opens.

---

## 4 · Guarding against hindsight

Every moment above is stated with the information available at that bar's close and nothing later:
prior-session value, the session open, the IB once locked, the bars and delta printed so far, and
the CCI/LSMA/trend_state values already written on those bars.

**9 candidates were examined and rejected because their case, or their stop, needed a later bar:**

1. 08-27 16:35 long @7713.75 (the exact low bar) — one 5-min rejection, price still below the open.
2. 08-31 17:25 long @7676.75 (the exact IB-low bar) — no turn evidence at that close; used 17:35.
3. 08-28 20:10 long @7722.50 (the exact low bar) — knife-catch, no higher low yet.
4. 08-14 20:35 long @7797.75 (the exact low bar) — same; used 21:00.
5. 09-01 21:45 long @7628.75 (the capitulation bar close) — same; used 21:55.
6. 08-28 17:10 short @7731.00 — reads as an open-drive failure, but the market rallied 51 pts first;
   only the knowledge of 7711.75 five hours later makes it look right.
7. 09-01 17:35 short @7670.00 — survives only if the stop is set >0.75 pt above 7673.00, which
   requires knowing the 18:50 high of 7673.75. Threshold-tuning with the future.
8. 08-31 20:50 long @7695.75 (balance breakout) — every structural stop (7685.50 or 7680.75) is
   taken by the 21:40 flush to 7678.00; including it would need a stop chosen with hindsight.
9. 09-02 17:50 short @7680.75 (IB-high look-above-and-fail) — ex-ante plausible, but fading a
   session with cumulative delta +5,060 above prior VAH is against the day's own order flow; and
   it loses. Listed here for completeness rather than silently dropped.

No threshold anywhere in this document was tuned to improve a day. Stops are placed at the last
structural reference (swing low/high, session extreme, IB edge) and stated before the outcome.

---

## 5 · What this implies (no change made — this is a read-only pass)

1. `awaiting_release` is the single highest-value gate to re-specify. It is not a risk gate;
   it is a confirmation gate whose confirmation arrives after the trade is gone. 8 of 13 blocked
   moments, carrying **$2,315** of entry-to-extreme value at 2 contracts on this sample alone
   ($287.50 + $317.50 + $457.50 + $240 + $405 + $130 + $132.50 + $345).
2. `lsma_flat` and `daytype_playbook` are structurally anti-reversal. Any day whose best trade is
   a turn (4 of these 6) will be blocked by them by construction.
3. Missing detectors are **not** the bottleneck. Building a new pattern would have added at most
   one moment out of seventeen.
4. The live path loses money even when the gate opens, because it opens late and then attaches a
   sub-structural stop. Entry timing and stop placement are a separate, additive fix.

Any change to any of these is a trading-risk-surface change → strategic stop + Michael sign-off.

---

*Sources: `v9_bars_5min_woodies`, `v9_bars_cumulative_delta`, `v9_tpo_sessions`,
`v9_day_type_history`, `v9_trades`, `v9_shadow_ledger`,
`~/SierraChart_Data/v9_export/decisions_archive/gateway_decisions.<date>.jsonl`.
DB accessed through `backend.v9.db.read.read_all` with `.env` loaded (`postgresql://localhost/mems26`).*
