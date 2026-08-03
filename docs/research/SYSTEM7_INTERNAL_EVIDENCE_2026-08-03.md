# System-7 Internal Evidence — what our own trades say should be built (2026-08-03)

**Mission (Michael's ruling 03.08):** before building System-7 (confluence-scoring judgment
layer, 1–3 contracts, add-on-strength), mine OUR OWN experience for what actually grows the
account day-over-day.

**Agent:** quantitative research agent (read-only; this file is the only write).
**Sources:** `v9_trades` (local Postgres, `mode='live'` closed since 2026-07-15, n=32; `mode='shadow'`
closed since 2026-07-15, n=90) · `v9_bars_5min_woodies` (RTH 16:30–23:00 IL) ·
`~/SierraChart_Data/v9_export/gateway_decisions.jsonl` (2,276 unique rows after dedup; starts 22.07,
contains known rebroadcast noise per DALTON §0) · `docs/reports/DALTON_GAP_AUDIT_2026-08-02.md` ·
`MAE_CALIBRATION_2026-08-02.md` · `WEEK_REVIEW_2026-07-27_31_REAL_ID.md` · `FIRE_MATRIX_ALL_DAYS.md` ·
`EDGE_FADE_TRUTH_REPLAY_2026-08-02.md` · `CLASSIFIER_TRUTH_AUDIT_2026-08-03.md`.

**תקציר בעברית:** על 32 עסקאות-לייב סגורות (15–31.07, סה"כ −$880) שלושה גורמים מפרידים
מנצחות ממפסידות: תבנית-מבנה (67% מול 11% הצלחה), מיקום-לא-רודף, וכיוון-עם-היום. ציון-קונפלואנס
≥2 מתוכם = ‏88% הצלחה (7W/1L/1BE, ‏+$242 כפי-שנוסחר) מול 14% ב-≤1 (‎−$1,122). **הגדלת-גודל בלי
סינון רק מגדילה את הדימום** (3 חוזים קבועים: ‎−$1,236); סינון score≥2 + ‏sizing ‏2–3 הופך את
התקופה ל-‏+$167..+$253. הבנייה: קודם שער-קונפלואנס, אחר-כך סולם-חוזים.

---

## Honesty header (Rule-5 + sample sizes)

- **n=32 closed live trades** total. Every sub-split below is single-digit-to-teens. These are
  directions of evidence, not statistics. Shadow (n=90) is used as a second, larger, imperfect
  sample (virtually-managed; MAE report caveat 3).
- **$ figures from `pnl_usd` are as-traded facts.** All counterfactual/sim figures are
  sample-arithmetic, **not forecasts**.
- **Alignment factor uses REALIZED day direction** (hindsight proxy). A live System-7 would use
  the fixed classifier + dir_bias; classifier truth-audit shows 11/13 = 85% direction/balance
  accuracy (CLASSIFIER_TRUTH_AUDIT_2026-08-03), so the proxy is approximately implementable —
  treat aligned-factor results as an **upper bound**.
- **Pattern-tier factor is partly in-sample** on the live 32; it is cross-checked against the
  independent larger MAE sample (n=112: ZLR 10/53 W, GB100 7/10 W) and shadow (n=90), which agree.
- **Location factor is fully ex-ante** (computed only from bars ≤ entry_ts).
- **Leg presence (`LEG_RIDE`) is NOT recorded** in `v9_trades.quality` for this window (walked all
  quality JSON keys for `*leg*`: NONE) — cannot be analyzed; moving on. Same for
  `session_at_entry` (NULL on all 33 live rows).
- `pnl_r` denominators are inconsistent across trades (initial vs trailed stop; e.g. #581
  +$143.75 but R=0.33 vs initial 43-pt stop) — ranking is done in $, R shown as-is.
- Days 22.07 and 24.07 are data-suspect (DALTON §0) but their fills are real → included in $ sums.
- `day_type_at_entry` labels before 31.07 came from the buggy classifier (fixed
  `S1_RECLASS_REQUIRES_IB_EXT_V1`); the realized-direction analysis side-steps that.

**Base query (all trade pulls below are variants of this):**

```sql
SELECT id, firing_system, direction, entry_ts, entry_price, stop, t1, t2, t3, exit_reason,
       pnl_usd, pnl_r, outcome, quality, day_type_at_entry, pattern_id_at_entry,
       t1_hit_ts IS NOT NULL AS t1h, t2_hit_ts IS NOT NULL AS t2h, t3_hit_ts IS NOT NULL AS t3h
FROM v9_trades
WHERE entry_ts >= '2026-07-15' AND state='CLOSED' AND outcome IS NOT NULL AND mode='live'
ORDER BY entry_ts;   -- n=32; mode='shadow' variant → n=90
```

**Ground-truth verification (Rule 2/5):** the as-traded sum reproduces the DALTON audit exactly:

```
actual (as-traded, mixed 1-4c): $-880.00        # matches DALTON "−$880 על 31 עסקאות" (32 incl. 2 BE-zero rows)
daily: 15.07 −98.75 · 17 −58.75 · 20 −125 · 21 −208.75 · 22 −36.25 · 23 −300 ·
       24 +122.50 · 27 −90 · 30 +66.25 · 31 −151.25   (16.07 & 29.07 = zero trades)
```

---

## 1 · Per-factor expectancy — which single factors separate winners from losers

Format: `(key, n, W, L, sum$, avgR, winrate%)`; winrate excludes BE from the denominator only
where W+L=0. LIVE = 32 closed live; SHADOW = 90 closed shadow, both since 07-15.

### 1a. Pattern (the strongest raw separator)

```
LIVE:                                          SHADOW:
ZLR                    10  2W  8L  -437.50 20% |  ZLR                45  8W 37L -1946.25 18%
OPENING_DRIVE           2  0W  2L  -262.50  0% |  REACTIVE_SHORT      6  1W  5L  -847.50 17%
INITIATIVE_SHORT        5  1W  4L  -195.00 20% |  INITIATIVE_LONG     4  1W  3L  -547.50 25%
REACTIVE_SHORT          2  0W  2L  -112.50  0% |  REACTIVE_LONG       7  1W  6L  -271.25 14%
GHOST                   2  0W  2L   -95.00  0% |  OPENING_DRIVE       2  0W  2L  -266.25  0%
HTLB                    1  0W  1L   -56.25  0% |  GHOST               3  1W  2L   -76.25 33%
CONFLUENCE_RI_ZLR       1  0W  1L   -42.50  0% |  INITIATIVE_SHORT    6  4W  2L   +71.25 67%
INITIATIVE_LONG         2  2W  0L   +22.50 100%|  GB100               7  5W  2L  +241.25 71%
BEAR_FLAG_SHORT         2  2W  0L   +80.00 100%|  DOUBLE_BOTTOM_EE    1  1W  0L  +306.25 100%
GB100                   3  2W  0L  +108.75 100%|  OPENING_ORR         1  1W  0L   +80.00 100%
DOUBLE_BOTTOM_EE_LONG   1  1W  0L  +110.00 100%|
```

**Structure-confirmation tier** (GB100, BEAR/BULL_FLAG, DOUBLE_BOTTOM/TOP_EE, INITIATIVE_*) vs
**momentum/derived tier** (ZLR, REACTIVE_*, GHOST, OPENING_DRIVE, HTLB, CONFLUENCE_RI_ZLR):

| Tier | LIVE n | W/L | sum$ | WR | SHADOW n | W/L | sum$ | avgR | WR |
|---|---|---|---|---|---|---|---|---|---|
| Structure | 13 | 8/4 | **+$126.25** | **67%** | 20 | 12/8 | −$138.75 | **+0.51** | **60%** |
| Momentum/derived | 19 | 2/16 | **−$1,006.25** | **11%** | 70 | 14/56 | −$3,657.50 | −0.47 | 20% |

Both samples agree; the MAE calibration's independent n=112 sample agrees (GB100 7/10 W vs
ZLR 10/53 W). **This is the single strongest factor we have.** ZLR alone is −$437.50 live
(n=10) and −$1,946.25 shadow (n=45) — it is the account's largest pattern-level leak.

### 1b. Direction and firing system (LIVE)

```
SHORT  22   5W 17L  -846.25  23%      S4  17  4W 12L  -522.50  25%
LONG   10   5W  3L   -33.75  62%      S2  15  6W  8L  -357.50  43%
```

The short-side bleed is mostly the chase/counter-value classes below, not "shorts are bad" per se.

### 1c. Direction-vs-day alignment (realized RTH direction, threshold |move| ≥ 0.3×range)

```
LIVE:  with 7: 3W/4L −$143.75 (43%) · against 4: 1W/2L −$100.00 · flat-day 21: 6W/14L −$636.25 (30%)
SHADOW: with 21: 11W/10L +$191.25 (52%, avgR −0.02) · against 17: 4W/13L −$730.00 (24%)
        flat-day 52: 11W/41L −$3,257.50 (21%)
```

On the bigger shadow sample, **with-day trades are the only bucket that isn't bleeding**
(52% WR vs 24% against). Live n=7/4 is too small alone but points the same way.

### 1d. Location at entry (ex-ante: position in the running day range at entry; rng≥8pts, ≥3 bars)

chase = entering in the last 30% of the running range **in the trade direction**
(SHORT at pos<0.30 of range, LONG at pos>0.70); edge = responsive extreme; mid = 30–70%.

```
LIVE:  chase 16: 4W/11L −$477.50 (27%) · edge 7: 1W/5L −$163.75 (17%) · mid 7: 5W/2L +$23.75 (71%)
       None (opening, <3 bars) 2: 0W/2L −$262.50 (both OPENING_DRIVE)
SHADOW: chase 41: −$1,202.50 (34%) · edge 18: −$615.00 (22%) · mid 28: −$1,496.25 (29%) · None 3: −$482.50 (0%)
```

Live `mid` (pullback-band entries) is the only positive location bucket (n=7). The five DALTON
"MFE≤1.25" chase trades (#420 #479 #481 #545 #584, −$526.25) all land in `chase` here — the
factor catches them ex-ante. Caveat: `edge` mixes good responsive fades with counter-value
fights (the 21.07 shorts), so location alone is not sufficient — it needs the day-type factor.

### 1e. Time of day (hour, IL)

```
LIVE:  16h 3: 0W −$307.50 · 17h 7: −$178.75 (29%) · 18h 7: −$295.00 (43%) · 19h 1: +$110.00
       20h 6: −$55.00 (40%) · 21h 6: −$156.25 (20%) · 22h 2: +$2.50
SHADOW: 16h 8: −$970.00 (25%) · 18h 13: −$1,110.00 (15%) · 21h 22: −$827.50 (18%)
        17h 11: −$57.50 (55%) · 19h 11: +$237.50 (45%) · 20h 19: −$662.50 (32%)
```

The 16:00 IL hour (16:30–17:00 opening) is 0-for-3 live and −$970 shadow (n=8). Late hours
(21–22 IL) are also net-negative in both samples.

### 1f. Day-type label at entry (LIVE; labels partly from the pre-fix classifier)

```
Variation 18: −$490.00 (35%) · None 3: 0W −$307.50 · Trend_DD 3: −$93.75 (0%)
Trend_Normal 5: −$76.25 (40%) · Normal 3: +$87.50 (67%)
```

**Every trade taken with `day_type=None` lost (n=3, −$307.50).** Trading before the day is
classified is a measurable leak on its own.

---

## 2 · Confluence evidence — does stacking factors justify 1–3 contract scaling?

**Score (0–3), one point each, all implementable at entry time:**
F1 = with-day direction (live: classifier+dir_bias; here: realized-direction proxy, upper bound) ·
F2 = structure-tier pattern · F3 = acceptable location (mid or responsive-edge, i.e. not chase, not None).

```
LIVE  score 0:  9: 1W/7L  −$538.75 (12%)      SHADOW score 0: 18: 1W/17L −$1,718.75 ( 6%, avgR −0.71)
      score 1: 14: 2W/12L −$583.75 (14%)             score 1: 59: 17W/42L −$1,987.50 (29%, avgR −0.35)
      score 2:  7: 6W/0L  +$301.25 (100%)            score 2: 11: 6W/5L    −$198.75 (55%, avgR +0.87)
      score 3:  2: 1W/1L   −$58.75 (50%)             score 3:  2: 2W/0L    +$108.75 (100%, avgR +0.61)

LIVE  score≥2:  9: 7W/1L(1BE) +$242.50 (88% WR)   vs score≤1: 23: 3W/19L −$1,122.50 (14% WR)
SHADOW score≥2: 13: 8W/5L −$90.00 (62%, avgR +0.83) vs score≤1: 77: 18W/59L −$3,706.25 (23%, avgR −0.44)
```

**Verdict: yes — the expectancy gap is large and consistent across both samples** (live
88% vs 14% WR; shadow avgR +0.83 vs −0.44). n=9 live / n=13 shadow in the high-confluence
bucket is small — stated plainly — but the **low-confluence bucket (n=23/77) is where ~100% of
the losses live**, and that is the actionable half: the evidence justifies scaling 1–3 primarily
as a **downward** instrument (starve score≤1), not as leverage on favorites.

---

## 3 · Sizing simulation on the actual live sequence (n=32, 15–31.07)

**Assumptions (stated per mission):**
1. Per-contract P&L = `pnl_usd / contracts_actual` (contracts from `quality.contracts`,
   fallback = count of `c*_stop_id` brackets; #400 recorded `contracts:0` with 3 brackets → 3).
   Exact for full losers (all contracts stop at the same price); conservative for partial winners.
2. "Ladder" variant reconstructs per-contract legs from recorded t1/t2/t3 prices + hit flags:
   C1→T1, C2→T2, C3→T3; un-hit legs = BE after T1 (the ruled BE-after-T1 management), full stop
   if no T1. Non-clean exits (`manual`, `phantom_reconcile`, `SIM_SWITCHOVER_CLOSE`,
   `SIERRA_FLAT`) fall back to linear scaling.
3. Confluence-scaled uses §2 scores: score 3 → 3c, score 2 → 2c, score ≤1 → 1c.
4. Equity throttle: 2c default; 1c on any day following a red day (by the sim's own daily P&L).
5. Commissions/slippage not modeled (identical across variants). In-sample; not a forecast.

| Sizing policy | linear | ladder-reconstructed |
|---|---|---|
| Actual (as-traded, mixed 1–4c) | **−$880.00** | — |
| (a) Fixed 2 | −$824.17 | −$751.25 |
| (b) Fixed 3 | **−$1,236.25** | **−$1,280.62** |
| (c) Confluence-scaled 1–3 (all 32 trades) | −$335.00 | −$314.38 |
| (d) Equity throttle (2c → 1c after red day) | −$664.27 | −$584.69 |
| (e) Confluence **gate**: score≥2 only (n=9), sized 2–3 | **+$167.19** | **+$233.44** |
| (e′) score≥2 only, fixed 2 | +$180.21 | +$253.12 |

**Findings:**
- **Fixed-3 is the worst policy tested** — more size on a negative-expectancy flow multiplies the
  leak (−$1,236..−$1,281 vs −$824..−$751 at fixed-2). The 02.08 ruling (2 contracts, T1+T2) is
  directionally supported by our own data.
- **Scaling without selection recovers ~$500** (c vs a) — real but still red.
- **Selection is worth ~3× more than sizing:** the same confluence score used as a **gate**
  flips the period to **+$167..+$253** (n=9 trades — small-sample caveat repeated).
- The equity throttle is the weakest lever (+$216 vs fixed-2 linear); harmless, optional.
- Supporting counterfactuals (as-traded sizes): skip only `chase & score<2` entries → −$272.50
  (saves $607.50, n_skipped=14); skip only hour-16 entries → −$572.50 (saves $307.50, n=3).

---

## 4 · The leaks, ranked by $ impact — and the System-7 rule that would have caught each

$ = measured live loss (from `v9_trades`/DALTON MFE table) unless marked *book-estimate*
(conservative playbook estimates from DALTON/WEEK_REVIEW, ≈).

| # | Leak | Measured $ | n | Evidence | System-7 rule that catches it |
|---|---|---|---|---|---|
| 1 | **Edge-chasing** (entry at leg/day extreme in trade direction; MFE≤2 after entry) | **−$631.25** live (my chase bucket: −$477.50) | 8 (5 flagship: #420 #479 #481 #545 #584) | DALTON §4 class-1; §1d above | Location factor: no entry in last-30% of running range in trade direction; pullback-band (30–70% retrace) only → score-gate blocks at score≤1 |
| 2 | **Counter-value selling on a value-migration day** (21.07: 5 shorts vs 48 bars holding above IB-high) | **−$208.75** | 6 | DALTON §2-21.07; §1c shadow `against` −$730 (n=17) | F1 with-day factor + day-type-as-process re-eval (evening re-classification); `RESPONSIVE_WITH_DAY_TREND_V1` extended to "holding above IB-high" |
| 3 | **Opening losses** (16:30–17:00 IL, incl. both OPENING_DRIVE and #575 40-pt-stop long) | **−$307.50** live hour-16 (shadow −$970, n=8) | 3 live | §1e; WEEK_REVIEW #575; opening caps built 31.07 | No full size before day classification: `day_type=None` → max 1c (all 3 None-trades lost); opening-window trades capped 1c until 17:00 |
| 4 | **ZLR over-trading** (31% of live trades, 20% WR) | **−$437.50** live, −$1,946.25 shadow | 10 live / 45 shadow / 53 MAE-sample | §1a; MAE report per-pattern table | Pattern-tier factor: momentum-tier alone = score≤1 → 1c probe or skip; ZLR requires confluence (≥2) to size up |
| 5 | **Winner give-back / runner cut** (125 MFE pts across 5 winners banked only $102.50) | ≈$400–500 *book* | 5 (#400 #515 #548 #573 #586) | DALTON §4 winner-cutting; §3 MFE table | T2/T3 measured-move clamp on with-trend days (clamp ruling 31.07); BE only after T1+3pts; System-7 sizes runners on score-3 setups |
| 6 | **Stop-in-noise** (stop <6pts on IB>27 days; direction was right, MFE≥10 after stop) | **−$183.75** direct + 83 MFE pts abandoned | 3 (#377 #381 #579; 12 narrow-stop total) | DALTON §4 class-3, rec-4 | Stop-floor: `stop_dist ≥ max(6, 0.15×IB_range)` + structure anchor — System-7 refuses sub-floor entries (RR must survive the floor) |
| 7 | **Zero-availability days** (16.07 clean trend / 25.07 feed-dead / 29.07 watchdog+release = 0 fires) | ≈$450/day *book* (≈$1,350) | 3 days | DALTON §4c gate table: feed_watchdog 239 + awaiting_release 151 unique journal rows | Morning green-gate: feed fresh (<120s), journal dedup writing, `day_type≠None` before first entry — availability is a bigger $ number than any calibration item |
| 8 | **Fade-execution missing on Normal/Neutral/IB-giant days** (system knew the label, no arm attacks edges) | ≈$1,550 *book* | 4 days (15/17/27/31.07) | DALTON §4a-1; WEEK_REVIEW; EDGE_FADE replay **NO-GO** (−20pt, 7 entries) | EDGE_FADE stays OFF (standing ruling) until scid-replay GO with day-type + edge-location gating — System-7's score machinery is exactly the gate it lacked |
| 9 | **Losses held to full stop** (losers' median MAE 11.2pt vs winners' 3.2pt) | ≈$700–1,100/sample *book* | 112 (36W/76L) | MAE_CALIBRATION (Sweeney) | MAE-scratch ≥ pattern threshold (default 8pt) pre-T1 — **already ruled + live 02.08** (`S6_MAE_SCRATCH_V1` 150/150); System-7 consumes its journal, doesn't rebuild it |

Cross-check per DALTON: chase (−$631) + counter-value (−$209) ≈ 93% of the −$880 period loss.

---

## 5 · What to build in System-7 — ranked recommendation table

"Expected $" = effect measured on THIS 15–31.07 sample (n=32 live unless noted). **Sample
arithmetic, not forecasts.** Rules 1–3 are one mechanism (the score) — build once.

| Rank | Rule | Evidence | n | Expected $ impact (on sample) |
|---|---|---|---|---|
| 1 | **Confluence score s = F1(with-day) + F2(structure-pattern) + F3(location); trade only s≥2** | 88% vs 14% WR live; 62% vs 23% shadow; avgR +0.83 vs −0.44 shadow | live 9 vs 23; shadow 13 vs 77 | **−$880 → +$167..+$253** (≈ +$1,050..$1,130 swing); the single biggest lever found |
| 2 | **Sizing ladder on the same score: s=3→3c, s=2→2c, s≤1→0–1c probe; fixed-3 forbidden** | Fixed-3 = −$1,236..−$1,281 (worst); conf-scaled −$335 vs fixed-2 −$824 | 32 | +$489 vs fixed-2 even WITHOUT the gate; sizing alone never goes green — gate first |
| 3 | **F3 anti-chase location rule as a hard veto** (no entry in last-30% of running range in trade direction; pullback-band entries only) | chase bucket 27% WR; the 5 MFE≤1.25 trades all flagged ex-ante | 16 (live chase) | skip chase&s<2 → −$272.50, i.e. **+$607.50** |
| 4 | **No-classification-no-size: `day_type=None` or first 30min → max 1c** | day_type=None: 0W/3L; hour-16: 0W/3L live, −$970 shadow (n=8) | 3+3 live, 8 shadow | +$307.50 live (hour-16 skip); overlaps partially with #3 |
| 5 | **Stop-floor `≥ max(6pt, 0.15×IB)` + structure anchor** (DALTON rec-4) | 3 right-direction trades stopped in noise, 83 MFE pts abandoned; 12 sub-floor stops in period | 12 | ≈ +$250 direct (DALTON acceptance test) + optionality on 83 pts |
| 6 | **Runner policy per score: s=3 keeps a measured-move runner (no clamp); BE after T1+3pt** | 125 MFE pts → $102.50 banked across 5 winners | 5 | ≈ +$400–500 *book*; pairs with clamp-T2/T3 ruling 31.07 |
| 7 | **Supervise the MAE-scratch + verify it stays ON** (already live 02.08) | winners MAE 3.2 vs losers 11.2 median (×3.5 separation) | 112 | ≈ +$700–1,100/sample *book* (MAE report NET) |
| 8 | **Availability green-gate as a System-7 precondition** (feed fresh, journal dedup, classifier alive) | 3 dead days; feed_watchdog 239 + awaiting_release 151 unique blocks | 3 days | ≈ +$1,350 *book* — operational, not algorithmic, but largest raw number |
| 9 | **Equity throttle (2c → 1c after red day)** — optional, last | −$880 → −$664 | 32 | +$216; weakest lever, harmless |

**Explicitly NOT supported by our data right now:** (a) fixed 3-contract sizing — worst policy
tested; (b) enabling EDGE_FADE as-is — replay NO-GO −20pt (standing ruling keeps it OFF until
scid-replay); (c) add-on-strength (adding contracts mid-trade) — **no evidence either way in
this window** (no add-on trades exist to measure; defer until score-gate data accumulates).

**Build order that follows from the evidence:** score machinery (1) → hard vetoes (3,4,5) →
sizing ladder (2) → runner policy (6) → supervision hooks (7,8) → throttle (9). Flag-OFF →
replay on the clean bars (30.07+, FIRE_MATRIX: 13/13 judgeable days) → Michael's ruling, per
the standing protocol.

---

## Appendix — raw outputs (Rule-5)

Realized day direction (from `v9_bars_5min_woodies`, RTH 16:30–23:00 IL, dir if |close−open| ≥ 0.3×range):

```
15:FLAT 16:DOWN 17:DOWN 20:DOWN 21:FLAT 22:UP 23:FLAT 24:FLAT 27:DOWN 28:UP 29:DOWN 30:UP 31:FLAT
(n_bars=3091 pulled 14.07–31.07; first_ts 2026-07-14 01:00+03, last_ts 2026-07-31 23:55+03)
```

Sizing-sim raw output (per-contract normalization + ladder reconstruction, n=32):

```
actual (as-traded, mixed 1-4c): $-880.00
fixed-2 linear: $-824.17    | fixed-2 ladder: $-751.25
fixed-3 linear: $-1236.25   | fixed-3 ladder: $-1280.62
conf-scaled 1-3 linear: $-335.00 | ladder: $-314.38
equity-throttle linear: $-664.27 | ladder: $-584.69
score>=2-only conf-sized 2-3: linear $167.19 | ladder $233.44
score>=2-only fixed-2:        linear $180.21 | ladder $253.12
skip chase&score<2: n=18 kept, total as-traded $-272.50
skip hour-16:       n=29 kept, total $-572.50
score>=2-only ids: [379, 396, 400, 466, 515, 548, 566, 573, 586]
```

Gateway journal (deduped on ts+pattern+entry+blocked_by; 2,276 unique rows, 22.07→03.08 —
rebroadcast noise removed per DALTON §0 finding):

```
rr_entry_gate 262 · feed_watchdog 239 · cont_trend_filter 186 · awaiting_release 151 ·
session_gate_closed 123 · zone_limit_late_entry 123 · daytype_playbook 111 · location_gate 83 ·
entry_not_confirmed 83 · eod_entry_cutoff 76 · direction_context 53 · opening_type_gate 39
```

Mode inventory: `v9_trades` has no `is_sim` column; live/shadow/demo separation is `mode`
(live n=80 total since 07-07; 33 rows ≥07-15 of which 32 closed, 1 CANCELLED `PHANTOM_FILLED_FLAT` #536).

Analysis scripts were run ad-hoc against `postgresql://localhost/mems26` via
`backend/v9/db/read.py` (`read_all`); full per-trade table with factors is reproducible from the
base query + the factor definitions in §1c–1d.
