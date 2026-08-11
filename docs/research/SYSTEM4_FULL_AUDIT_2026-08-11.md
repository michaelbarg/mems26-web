# SYSTEM-4 (Woodies CCI) — FULL AUDIT ACROSS EVERY TRADING DAY WE HAVE

**Date:** 2026-08-11 · **Agent:** `s4-audit-agent` · **Scope:** every session in `v9_bars_5min_woodies`
(48 usable sessions, 2026-06-05 → 2026-08-11) · **Question:** which S4 configuration makes money on
LIVE tomorrow?

**Script:** `scripts/s4_full_audit.py` (added by this audit; 12 sections, all read-only)
**Raw run:** `python3 scripts/s4_full_audit.py > /tmp/s4_audit_full.txt` (901 lines)

> **READ-ONLY DECLARATION.** No flag was enabled or disabled. No service was restarted. Nothing was
> written to `~/SierraChart_Data` or to the database. The only writes are this document, the script,
> and the `LIVE_CHANNEL.md` entry.

---

## 0. תקציר בעברית — מה עושים מחר

1. **התבנית שמרוויחה היא GB100 — לא ZLR.** שלושה מקורות בלתי-תלויים מסכימים: לייב (8 ניתובים,
   3 מילויים, **3 מנצחות 0 מפסידות, +$167.50**), צל (**+$530.20**, n=12, 82%), ורפליי 48 סשנים
   (**+$2,282 נטו**, 110 עסקאות, 61%). GB100 חיובי **בשני חצאי המדגם, בכל שלושת החודשים, בכל סטופ
   מ-4 עד 12 נק', ועד 4 טיקים החלקה**.
2. **ZLR — התבנית הכי רועשת שלנו — מפסידה בכל מקום.** לייב **−$270** (37, 39%), צל **−$849**
   (136, 51%), רפליי **−$134 נטו** (128, 50%). ב-1 טיק החלקה היא כבר **−$901**. **לא מצאתי שום
   פרוסה של ZLR ששורדת מחוץ למדגם.** כלל התזוזה שנראה מנצח (+$1,678 בחלון-הלוג) נותן **−$365
   בחלון שלפניו**. זו התאמת-יתר, לא כלל.
3. **הפלייבוק הפוך לראיות:** `config/daytype_playbook.yaml` נותן ל-ZLR **FULL** ול-GB100
   **REDUCED**. זו ההמלצה המרכזית: להחליף ביניהם.
4. **למה לא היו עסקאות ב-10 וב-11 באוגוסט:** אין שער אחד אשם — **מסירת-שליחים של 8–9 שערים**.
   וב-10.08 השערים **צדקו**: לקיחת כל החסימות = **−$452 נטו**. ב-11.08 = **+$151 נטו**.
5. **הבעיה הגדולה אינה מדיניות-השערים אלא הביצוע.** על אותם איתותים שהמערכת כן העבירה, המודל אומר
   **+$1,127.50** והמציאות נתנה **+$23.75**. בנוסף **18 מתוך 57 ניתובי-לייב (32%) מעולם לא הפכו
   לפוזיציה** (`ORDER_FAILED:-1`).

---

## 1. Method, and two data-integrity findings that changed the answer

### 1.1 Execution model (Michael's, as specified)
4 contracts on MES ($5/pt/contract). `C1 → T0 = +3.0 pt`, `C2 → T1 = 1R`, `C3 → T2 = 2R`,
`C4 → T3 = 4R`, where `R` = the stop distance. Break-even stop after T1 (1R) fills. Inside a bar the
**stop is checked before the targets** (conservative). 12-bar forward horizon; contracts still open at
the end exit at the last bar's close. Commission $1.50/contract round-turn is reported separately
("net" = gross − 4 × $1.50 per trade).

Two aggregations are always shown:
* **per-signal** — every signal taken, overlapping. An upper bound, not an account.
* **sequential** — one trade at a time per session. This is the number a real single-slot account earns,
  and it is the number every recommendation below is based on.

### 1.2 Finding A — a timezone double-cast silently shifts the RTH window by 11 hours
`v9_bars_5min_woodies.ts` is `timestamptz`. The **only** correct ET rendering is a *single*
`ts AT TIME ZONE 'America/New_York'`. My first probe used
`ts AT TIME ZONE 'UTC' AT TIME ZONE 'America/New_York'`, which round-trips through the session TZ
(Israel, +03) and lands **+11h from UTC**. It still returned exactly 81 bars per full session, so it
*looked* right — it was selecting the overnight Globex session. Every early number was wrong until
this was caught.

```
 raw= 2026-08-11 18:50:00+03:00 | ny1(correct)= 2026-08-11 11:50:00 | ny2(wrong)= 2026-08-11 22:50:00+03:00
```
`scripts/leg_exemption_replay.py` already uses the correct single cast. **Anyone writing a new replay
must copy that form.** This is a repeat of the class CLAUDE.md Rule 4 warns about (TZ ambiguity).

### 1.3 Finding B — `v9_bars_5min_woodies.zlr_detected` is NOT a faithful record of live ZLR
The live `WoodiesSystem` fires ZLR from **the DLL's flag on any mid-bar push** (Mechanism-C,
`backend/v9/systems/woodies/woodies_system.py:441-449` and the DLL-fallback block at `:487-520`),
but the bars table keeps only the **last** push of each bar. Verified against the decision log: most
logged `entry` values sit **inside the forming bar's range, not on a close**, and

* **2026-08-10: DB says 0 DLL-ZLR bars. The live log holds 17 unique ZLR signals.**

Consequence: the Python-detector replay (§6) **under-counts ZLR** and cannot be used as a census. It is
used only for breadth (48 sessions, including a pre-decision-log out-of-sample window). The decision log
is the only ground truth for "how many signals did S4 actually produce".

### 1.4 Data hygiene applied
* Fixture rows `entry == 7600.00` dropped (735 of 3,609 S4 rows) — these are pytest leaks, per the
  2026-08-11 20:05 forensic entry.
* **Stale re-broadcasts dropped** (72 signals): after a restart the gateway replays week-old setups
  (the leg-exemption audit found `signal age 566994s` = 6.5 days). Their `entry` belongs to another
  session; simulating one produced an MFE of **1,890 pt**, which is how they were found. Rule:
  `entry` must sit within ±2 pt of its signal bar's range.
* One signal per `(signal-bar, pattern, direction)` — the gateway re-evaluates the same setup on every
  mid-bar push, so raw rows over-count roughly 7×.

---

## 2. Session inventory — every session we have

48 sessions with ≥20 RTH bars, **2026-06-05 → 2026-08-11** (40 of them ≥70 bars = full sessions).
Day-type is the **live label the gates actually acted on** (`v9_day_type_history`).

| regime | sessions |
|---|---|
| ROTATION (`Variation` / `Normal` / `Normal_Variation`) | 36 |
| TREND (`Trend_Normal`) | 7 — 06-15, 06-16, 06-18, 06-23, 07-02, 07-09, 08-04 |
| NEUTRAL (`Neutral_Center` / `Neutral_Extreme` / `Nontrend`) | 3 — 07-29, 08-06, 08-10 |
| unlabelled | 2 — 06-17, 07-16 |

Full per-session table (bars / range / open / close / displacement / day-type / DLL-ZLR count) is in
§1 of `/tmp/s4_audit_full.txt` — reproduce with
`python3 scripts/s4_full_audit.py --only sessions`.

**The sample is 75% rotation.** Only 7 trend sessions exist in the entire history. Any claim about S4
"in a trend" rests on 7 days and must be read that way.

---

## 3. Signal + gate census (ground truth: `gateway_decisions.jsonl`)

The decision log only starts **2026-07-22**. It covers 19 dates (15 with RTH bars). Everything before
that has bars but no decisions.

* 5,938 log lines → 3,609 `system=4` rows → 735 fixture → **531 unique S4 signals**.
* Outcomes: **466 blocked · 41 shadow_only · 24 live**.

### 3.1 Unique signals per day × pattern

| date | day-type | ZLR | GHOST | GB100 | CONFL | FAMIR | HFE | HTLB | VEGAS | TOT |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 07-22 | Variation | 15 | | | 2 | | 2 | | | 19 |
| 07-23 | Variation | 36 | 5 | 3 | 5 | 2 | 5 | | | 56 |
| 07-24 | Variation | 31 | 4 | 1 | 4 | 2 | 4 | | 1 | 47 |
| 07-25 | Normal | 7 | | | 3 | | 3 | | | 13 |
| 07-27 | Variation | 20 | 3 | 2 | | | | | 1 | 26 |
| 07-28 | Variation | 25 | 6 | 1 | 6 | 1 | 6 | | | 45 |
| 07-29 | Neutral_Extreme | 25 | 5 | 1 | 2 | 2 | 1 | 1 | 1 | 46 |
| 07-30 | Variation | 25 | 4 | 5 | | | | 2 | | 38 |
| 07-31 | Variation | 20 | | 3 | | 4 | | 1 | | 30 |
| 08-03 | Variation | 30 | | 1 | 1 | | 2 | 1 | | 39 |
| 08-04 | Trend_Normal | 5 | | 1 | | | | 1 | | 7 |
| 08-05 | Variation | 21 | 9 | 1 | | 3 | | 1 | | 35 |
| 08-06 | Neutral_Center | 24 | | 3 | 2 | 4 | | 1 | | 34 |
| 08-07 | Variation | 25 | 5 | 2 | | | | 1 | | 33 |
| 08-10 | Neutral_Center | 17 | 6 | 5 | | 2 | | | | 30 |
| 08-11 | Variation | 13 | 2 | 1 | | 7 | | | 1 | 24 |
| **TOTAL** | | **343** | **49** | **30** | **27** | **27** | **24** | **9** | **4** | **531** |

**ZLR is 65% of all S4 signal volume.** That is the whole reason this audit matters.

### 3.2 Gate histogram for ZLR (first-match-wins, n=343)

| gate | n | % |
|---|--:|--:|
| `cont_trend_filter` | 65 | 19% |
| `awaiting_release` | 53 | 15% |
| **PASSED** | **45** | **13%** |
| `rr_entry_gate` | 45 | 13% |
| `eod_entry_cutoff` | 31 | 9% |
| `extreme_chase_guard` | 23 | 7% |
| `daytype_playbook` | 19 | 6% |
| `lsma_flat` | 18 | 5% |
| `session_gate_closed` | 10 | 3% |
| other (entry_not_confirmed, feed_watchdog, direction_context, pattern_stop_cooldown, s4_risk_cap, zone_limit, pattern_loss_breaker, duplicate_fire) | 34 | 10% |

87% of ZLR signals are blocked, by **no fewer than nine different gates**. There is no single
"the gate that stops ZLR".

---

## 4. What actually happened to real orders (`v9_trades`, `firing_system=4`)

### 4.1 LIVE — the money number

**57 routed · 35 with an entry · net −$288.75 over 13 sessions (2026-07-08 → 2026-08-07).**

| pattern | routed | net $ | W | L | win rate |
|---|--:|--:|--:|--:|--:|
| **ZLR** | 37 | **−270.00** | 9 | 14 | **39%** |
| GHOST | 5 | −177.50 | 0 | 3 | 0% |
| CONFLUENCE_RI_ZLR | 1 | −42.50 | 0 | 1 | 0% |
| FAMIR | 2 | 0.00 | 0 | 0 | — |
| HTLB | 4 | +33.75 | 2 | 1 | 67% |
| **GB100** | 8 | **+167.50** | **3** | **0** | **100%** |

Per day: 07-08 +$22.50 · 07-10 +$105 · 07-13 −$83.75 · 07-15 −$98.75 · 07-20 −$42.50 ·
07-21 −$178.75 · 07-22 −$36.25 · 07-23 −$138.75 · 07-24 +$62.50 · 07-27 −$90 · 08-03 +$107.50 ·
08-04 +$168.75 · 08-07 −$86.25.

### 4.2 The operational finding: a third of live S4 orders never became a position

| exit_reason | n | net $ |
|---|--:|--:|
| `STOP_HIT` | 20 | −816.25 |
| **`ORDER_FAILED:-1`** | **16** | **0.00** |
| `T2_HIT` | 8 | +472.50 |
| `PHANTOM_PENDING_FLAT` | 2 | 0.00 |
| `SIERRA_FLAT` | 2 | 0.00 |
| `ORDER_FAILED` / `CMD_NEVER_SENT_P0-1` | 2 | 0.00 |
| others (manual / STOP_FILL / phantom_reconcile / SIM_SWITCHOVER) | 5 | −7.50 |

**18 of 57 routes (32%) ended `CANCELLED/CANCELLED` with `entry_ts = NULL`.** They cost nothing
directly, but they mean (a) the live sample is a third smaller than it looks, and (b) the live path is
not reliable enough to draw strong conclusions from.

### 4.3 SHADOW — the same execution engine, 3× the sample

| pattern | n | net $ | win rate |
|---|--:|--:|--:|
| HFE (now disabled) | 27 | **−2,986.70** | 33% |
| **ZLR** | 136 | **−849.48** | 51% |
| FAMIR | 9 | −660.00 | 33% |
| GHOST | 9 | −431.60 | 33% |
| VEGAS | 3 | −276.50 | 33% |
| CONFLUENCE_RI_ZLR | 2 | +78.75 | 100% |
| **GB100** | 12 | **+530.20** | **82%** |
| **TLB** | 50 | **+792.52** | **70%** |
| **HTLB** | 9 | **+885.75** | **78%** |

Shadow and live agree on the sign for every pattern with n ≥ 4. This is an **independent** confirmation
of §6 — different engine, different exit logic, same ranking.

---

## 5. Counterfactual — what every blocked S4 signal would have done

313 of the 531 unique signals are simulatable (278 blocked + 35 passed). Drops: 105 signal-bar outside
RTH, 72 stale, 22 no bars for that date, 14 too early in the session, 5 too late.

| gate | n | per-signal $ | wr% | seq n | seq $ | seq net $ | MFE med | MAE med |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| `awaiting_release` | 78 | +2,952.50 | 62.8 | 21 | **+465.00** | +339.00 | 9.62 | 5.88 |
| `cont_trend_filter` | 45 | +2,662.50 | 71.1 | 19 | **+276.25** | +162.25 | 11.00 | 4.25 |
| `daytype_playbook` | 29 | −2,273.75 | 20.7 | 10 | **−670.00** | −730.00 | 4.25 | 8.25 |
| `eod_entry_cutoff` | 26 | +665.00 | 65.4 | 11 | +172.50 | +106.50 | 8.62 | 4.62 |
| `lsma_flat` | 25 | +712.50 | 52.0 | 15 | +220.00 | +130.00 | 8.00 | 7.00 |
| `rr_entry_gate` | 17 | +336.25 | 64.7 | 8 | **−428.75** | −476.75 | 9.00 | 3.75 |
| `extreme_chase_guard` | 16 | +60.00 | 50.0 | 7 | **−306.25** | −348.25 | 7.38 | 7.12 |
| `location_gate` | 13 | −51.25 | 53.8 | 8 | −145.00 | −193.00 | 5.25 | 6.00 |
| `direction_context` | 12 | +1,400.00 | 83.3 | 7 | **+603.75** | +561.75 | 12.88 | 2.62 |
| `session_gate_closed` | 7 | −142.50 | 42.9 | 7 | −142.50 | −184.50 | 0.50 | 3.25 |
| `pattern_stop_cooldown` | 5 | −237.50 | 20.0 | 3 | −25.00 | −43.00 | 5.50 | 6.75 |
| `s4_risk_cap` | 4 | −155.00 | 50.0 | 1 | +55.00 | +49.00 | 9.00 | 11.25 |
| **ALL BLOCKED** | **278** | +5,768.75 | 57.2 | **58** | **−318.75** | **−666.75** | | |

Positive = the gate **cost** money. Negative = the gate **saved** money.

**Headline: taking every blocked S4 signal, one at a time, would have LOST $318.75 gross / $666.75
net.** The gate stack in aggregate is not the problem — it is mildly net-positive. Individually:

* **Best gate: `daytype_playbook` (−$670).** It blocked 29 signals with a 20.7% win rate. Do not weaken it.
* **`rr_entry_gate` (−$429) and `extreme_chase_guard` (−$306) also earn their keep** across the sample.
* **Worst gates: `direction_context` (+$604), `awaiting_release` (+$465), `cont_trend_filter` (+$276).**
  These three block genuinely good setups. They are also the three the leg-exemption audit
  (2026-08-11 22:40) was circling.

### Per gate × regime (sequential $)

| gate | ROTATION | NEUTRAL |
|---|--:|--:|
| `awaiting_release` | +546 (n=15/47) | −81 (n=6/31) |
| `cont_trend_filter` | +199 (13/35) | +78 (6/10) |
| `daytype_playbook` | −165 (4/5) | **−505 (6/24)** |
| `eod_entry_cutoff` | +492 (9/19) | −320 (2/7) |
| `rr_entry_gate` | −269 (7/16) | −160 (1/1) |
| `extreme_chase_guard` | **−515 (5/10)** | +209 (2/6) |
| `direction_context` | +604 (7/12) | — |

No TREND row exists: **08-04 is the only trend-labelled day inside the decision-log window, and none of
its blocked signals were simulatable.** Every per-gate trend claim in the earlier reports rests on
sessions that were labelled `Variation`, not `Trend_*`.

Note `extreme_chase_guard` reverses sign by regime — it **saves** $209 on neutral days and **costs**
$515 on rotation days. That is the same asymmetry the leg-exemption audit found, from a different angle.

---

## 6. ZLR — when is it profitable? (the honest answer: it isn't, reliably)

### 6.1 On the live-signal population (14 sessions, n=220)

Sliced every way Michael asked for:

| slice | best bucket | worst bucket |
|---|---|---|
| **day-type** | Variation +$1,055 seq (n=38) · Trend_Normal +$520 (n=2) | **Neutral_Center −$450 (n=8)**, 33% wr |
| **distance from the extreme it runs into** | 3–6 pt: +$4,140 per-signal (75/sig) · 0–3 pt: +$1,669 | 6–10 pt: +$556 (10/sig) · ≥20 pt: +$421 (11/sig) |
| **CCI-14 at the signal bar** | 0–100 on the trade side: +$5,474 (n=104) | ≥ ±100 already extended: −$320 (n=2) |
| **time of day** | 11:00–12:00 +$3,520 (86/sig, 76% wr) | 09:30–10:00 −$191 (33% wr) |
| **LSMA slope vs direction** | with, flat (<0.25): +$2,350 (71/sig) | against, shallow: seq −$695 |
| **session displacement agrees ≥10 pt** | **+$1,887 seq / +$1,678 net, 71% wr (n=142)** | disagrees: **−$737 seq** (n=78) |

The displacement rule looked like the answer: `R8 = trade ZLR only in the direction of the session
displacement when |displacement| ≥ 10 pt` → **+$1,677.50 net over 35 trades at 71.4% win rate**.

### 6.2 …and it does not survive out of sample

The decision log starts 07-22, but the bars go back to 06-05. Replaying the detectors over the
**33 sessions that predate the decision log** is a true hold-out — those bars were found *after* the
rule was written:

| rule | window | trades | net $ | $/session |
|---|---|--:|--:|--:|
| every ZLR | **PRE-LOG (33 sessions, OOS)** | 96 | **−127.25** | −4.10 |
| every ZLR | log window (15 sessions) | 32 | −7.00 | −0.54 |
| ZLR, displacement ≥ 10 pt | **PRE-LOG (OOS)** | 72 | **−364.50** | −11.76 |
| ZLR, displacement ≥ 10 pt | log window | 22 | +134.25 | +10.33 |
| ZLR, displacement ≥ 15 pt | **PRE-LOG (OOS)** | 67 | **−543.25** | −17.52 |
| ZLR, displacement ≥ 20 pt | **PRE-LOG (OOS)** | 58 | **−2,419.25** | −78.04 |

**Every displacement threshold is negative out of sample and positive in sample.** That is the
signature of curve-fitting, not an edge.

### 6.3 The full both-halves sweep for ZLR (cut = 2026-07-13, 26 vs 22 sessions)

| filter | h1 net $ | h2 net $ | verdict |
|---|--:|--:|---|
| no filter | −593.50 | +459.25 | negative |
| regime ≠ NEUTRAL | −593.50 | +1,152.75 | in-sample only |
| displacement ≥ 10 | −352.00 | +121.75 | negative |
| distance from extreme ≥ 6 | −2,027.75 | +572.25 | negative |
| distance from extreme < 6 | +888.75 | −138.25 | in-sample only |
| LSMA with direction ≥ 0.25 | −444.50 | +93.75 | negative |
| LONG only | −794.50 | +232.50 | negative |
| SHORT only | −1,002.00 | +82.25 | negative |
| **before 12:00 ET** | **+153.25** | **+990.50** | **BOTH-POSITIVE** |

**Exactly one ZLR slice survives both halves: `before 12:00 ET` (35 trades, +$1,143.75 net).** And it
fails the month test — June is **−$236.25**. With 1 tick of slippage it drops to +$871; at 4 ticks,
+$516. n=35 across 48 sessions is under one trade per session.

### 6.4 The rule, stated honestly

> **There is no ZLR rule I can defend for live money.** The strongest slices in-sample (displacement,
> distance-from-extreme, LSMA) all invert out-of-sample. The only both-halves-positive slice
> (before 12:00 ET, n=35, +$1,144) is negative in one of three months and is one trade per 1.4 sessions.
>
> What *is* robust about ZLR is the negative: **unfiltered ZLR loses at every stop from 4 pt to 12 pt,
> at every slippage level, with a −$2,207 max drawdown**, and it loses in all three independent
> measurements (live −$270, shadow −$849, replay −$134). Its 65% share of S4 signal volume is why S4
> is flat.

---

## 7. Michael's question — why no S4 trade on 2026-08-10 and 2026-08-11?

**Short answer: no single gate. A relay of eight-to-nine gates, each catching a different cluster.
And on 08-10 they were right — taking every blocked signal would have lost $452 net.**

### 7.1 2026-08-10 — `Neutral_Center`, displacement **+2.25 pt**, range **33.25 pt** (the flattest session in the entire 48)

30 unique S4 signals, 17 of them ZLR. Every one blocked. The chain, in order:

| time ET | pattern/dir | gate | reason |
|---|---|---|---|
| 09:35–09:50 | GB100 SHORT + 3× ZLR SHORT | `cont_trend_filter` | "setup DOWN vs sustained UP" |
| 09:55–10:45 | 7× ZLR LONG | `extreme_chase_guard` | entry 0.75–5.50 pt from session high, threshold **6.0** |
| 11:00 | GB100 SHORT | `awaiting_release` | "still active in the zone (vol 0.96 > 0.75)" |
| 11:20–12:25 | 4× GHOST | `lsma_flat` | \|slope\| 0.08–0.24 < **0.25** |
| 11:50–12:30 | 4× ZLR SHORT | `awaiting_release` | "structure not turning (0–1 / 2 higher lows)" |
| 11:55 | GB100 LONG | `rr_entry_gate` | T1 2.75 < stop 5.50 × 0.65 → R:R 0.50 |
| 12:55–13:00 | 2× FAMIR LONG | `awaiting_release` | "left the zone without volume" |
| **13:00–14:45** | **4× ZLR SHORT + 2× GB100** | **`daytype_playbook`** | **"ZLR SKIP on Neutral_Center"** |
| 15:35–15:45 | 2× GHOST + ZLR LONG | `eod_entry_cutoff` | past the 45-min EOD cutoff |
| 16:00 | ZLR LONG | `session_gate_closed` | outside 08:30–15:00 CT |

The day-type settled on `Neutral_Center` around 13:00; from that moment `daytype_playbook` alone would
have stopped every ZLR (`ZLR: Neutral_Center: SKIP`). Before 13:00 the work was done by
`cont_trend_filter` (a flat tape flips "sustained" direction) and `extreme_chase_guard` (a 33-pt range
means every entry is near an extreme).

**Counterfactual: per-signal −$1,702.50 (28.6% win rate). Sequential −$416.25 gross / −$452.25 net.
ZLR alone: per-signal −$615.00, sequential −$510.00 / −$534.00 net.**
**The gates saved roughly half a thousand dollars. 08-10 is a gate success, not a gate failure.**

### 7.2 2026-08-11 — `Variation`, displacement **−39.25 pt**, range 53.25 pt

24 unique signals, 13 ZLR. Gate counts over raw rows: `awaiting_release` 10, `extreme_chase_guard` 9,
`lsma_flat` 4, `cont_trend_filter` 3, `daytype_playbook` 2, `session_gate_closed` 2,
`direction_context` 1, `location_gate` 1, `eod_entry_cutoff` 1.

The load-bearing cluster is **`extreme_chase_guard`, 11:55 → 12:20, five ZLR SHORTs** into a market
making new session lows:

| bar ET | entry | reason | MFE | MAE | sim $ |
|---|--:|---|--:|--:|--:|
| 11:55 | 7763.75 | dist 1.25 < 6.2 from session low 7762.50 | 8.25 | 6.25 | +125.00 |
| 12:05 | 7765.50 | dist 3.00 < 6.2 | 12.75 | 4.50 | +167.50 |
| 12:10 | 7766.00 | dist 3.50 < 6.2 | 17.75 | 4.00 | +222.50 |
| 12:15 | 7765.50 | dist 3.00 < 6.2 | 17.75 | 2.00 | +198.75 |
| 12:20 | 7766.75 | dist 4.25 < 6.2 | 19.00 | 0.00 | +197.50 |

Per-signal that is **+$911.25 — the biggest single-gate cost in the whole audit.** But all five sit
inside one 12-bar window, so a **single-slot account captures only +$125.00** of it. Three more ZLR
SHORTs (10:35 / 10:40 / 10:45, +$214 / +$195 / +$205 per-signal) were blocked by `cont_trend_filter`
and `awaiting_release`.

**Counterfactual for the whole day: per-signal +$686.25 (60.9% win rate). Sequential +$181.25 gross /
+$151.25 net. ZLR alone: per-signal +$1,277.50 at 76.9% win rate, but sequential −$15.00 / −$33.00
net over 3 trades.** The per-signal number is the one that feels like a disaster; the sequential number
is what an account would actually have made.

**Two details worth keeping:**
* 09:30 GB100 LONG was blocked by `lsma_flat` at slope **0.2467 vs a 0.2500 threshold** — missed by
  0.0033 pt/bar.
* `awaiting_release` fired on "still active in the zone (vol 0.85–2.02 > 0.75)" six times between
  10:05 and 10:45 — the volume side of the release gate, not the structure side.

---

## 8. Full-history replay + robustness — which pattern actually has an edge

993 signals re-detected across all 48 sessions (see §1.3 for why this under-counts ZLR).

| pattern | signals | trades | gross $ | **net $** | win rate |
|---|--:|--:|--:|--:|--:|
| **GB100** | 155 | 110 | +2,942.50 | **+2,282.50** | 60.9% |
| **HTLB** | 81 | 62 | +1,032.50 | **+660.50** | 53.2% |
| **GHOST** | 178 | 56 | +643.75 | **+307.75** | 60.7% |
| TT | 5 | 5 | +178.75 | +148.75 | 60% |
| TLB | 9 | 8 | +167.50 | +119.50 | 66.7% |
| **ZLR** | 435 | 128 | +633.75 | **−134.25** | 49.2% |
| **VEGAS** | 21 | 20 | −895.00 | **−1,015.00** | 40.0% |
| **FAMIR** | 109 | 47 | −1,325.00 | **−1,607.00** | 38.3% |

By regime: **TREND +$1,077.50** seq (150 signals / 25 trades) · ROTATION **−$833.75** (738 / 135) ·
NEUTRAL **−$550.00** (53 / 12).

### 8.1 Rules that survive BOTH chronological halves (cut 2026-07-13)

| pattern | filter | trades | net $ | h1 | h2 |
|---|---|--:|--:|--:|--:|
| **GB100** | **10:30–15:00 ET** | **95** | **+2,477.50** | +215.75 | +2,261.75 |
| GB100 | regime ≠ NEUTRAL | 100 | +2,335.00 | +195.75 | +2,139.25 |
| GB100 | **no filter at all** | 110 | +2,282.50 | +195.75 | +2,086.75 |
| GB100 | LSMA with dir ≥ 0.25 | 85 | +1,303.75 | +249.25 | +1,054.50 |
| GB100 | SHORT only | 64 | +1,151.00 | +243.25 | +907.75 |
| GB100 | LONG only | 56 | +689.00 | +219.00 | +470.00 |
| HTLB | displacement ≥ 10 | 39 | +1,281.00 | +183.00 | +1,098.00 |
| HTLB | no filter | 62 | +660.50 | +45.25 | +615.25 |
| GHOST | displacement ≥ 10 | 25 | +857.50 | +477.00 | +380.50 |
| ZLR | before 12:00 ET | 35 | +1,143.75 | +153.25 | +990.50 |

**GB100 is the only pattern that is positive in both halves with no filter at all, and stays positive
under every single filter tested — including LONG-only and SHORT-only.** That is what a real edge looks
like: it does not need to be sliced to work.

### 8.2 Robustness stress test

| candidate | trades | net $ | wr% | drop-best | top-3 share | max DD | $/session |
|---|--:|--:|--:|--:|--:|--:|--:|
| **GB100 + 10:30–15:00 ET** | 95 | **+2,477.50** | 62.1 | +2,188.50 | 35% | −892.75 | **+55.06** |
| GB100 + regime ≠ NEUTRAL | 100 | +2,335.00 | 61.0 | +2,046.00 | 37% | −824.00 | +55.60 |
| GB100 (no filter) | 110 | +2,282.50 | 60.9 | +1,993.50 | 38% | −824.00 | +50.72 |
| GB100 + HTLB, 10:30–15:00 | 106 | +2,424.00 | 60.4 | +2,135.00 | 36% | −808.50 | +52.70 |
| HTLB + displacement ≥ 10 | 39 | +1,281.00 | 64.1 | +992.00 | 61% | −512.25 | +44.17 |
| ZLR + before 12:00 ET | 35 | +1,143.75 | 62.9 | +854.75 | 68% | −832.25 | +33.64 |
| **ZLR (no filter)** | 128 | **−134.25** | 49.2 | −423.25 | — | **−2,207.00** | −3.05 |

**Slippage (net $, adverse fill vs the signal price)**

| candidate | 0 tick | 1 tick | 2 ticks | 4 ticks |
|---|--:|--:|--:|--:|
| **GB100 + 10:30–15:00 ET** | 2,477.50 | **2,285.00** | **2,143.75** | **2,011.25** |
| GB100 (no filter) | 2,282.50 | 1,833.75 | 1,586.25 | 1,393.75 |
| HTLB + displacement ≥ 10 | 1,281.00 | 1,218.50 | 906.00 | 786.00 |
| ZLR + before 12:00 ET | 1,143.75 | 871.25 | 788.75 | 516.25 |
| **ZLR (no filter)** | −134.25 | **−900.50** | **−1,345.50** | **−2,480.50** |

**Stop sensitivity (net $)**

| candidate | 4 pt | 5 pt | 6.5 pt | 8 pt | 10 pt | 12 pt |
|---|--:|--:|--:|--:|--:|--:|
| **GB100 + 10:30–15:00 ET** | 1,350.00 | 1,291.25 | 2,110.00 | 2,477.50 | **3,103.75** | 2,517.50 |
| GB100 (no filter) | 1,456.25 | 1,237.50 | 1,892.50 | 2,282.50 | 2,535.00 | 1,752.50 |
| **ZLR (no filter)** | −919.25 | −935.50 | −396.75 | −134.25 | −78.00 | −131.75 |

**Month walk-forward (net $)**

| candidate | 2026-06 | 2026-07 | 2026-08 |
|---|--:|--:|--:|
| **GB100 + 10:30–15:00 ET** | **+588.25** | **+1,149.00** | **+740.25** |
| GB100 + regime ≠ NEUTRAL | +380.00 | +1,040.75 | +914.25 |
| GB100 (no filter) | +380.00 | +1,365.25 | +537.25 |
| HTLB + displacement ≥ 10 | +35.75 | +1,018.50 | +226.75 |
| ZLR + before 12:00 ET | **−236.25** | +1,166.00 | +214.00 |
| ZLR (no filter) | **−1,610.00** | +919.50 | +556.25 |

**`GB100 + 10:30–15:00 ET` is positive in every half, every month, at every stop from 4 to 12 pt, at
every slippage level to 4 ticks, and survives dropping its single best trade. Nothing else in S4 does.**

---

## 9. Model vs reality — the gap that dwarfs every gate argument

Take only the signals the live gateway **passed** (not blocked) and compare the model to the account:

| date | passed signals | model seq net $ | LIVE trades | LIVE $ |
|---|--:|--:|--:|--:|
| 07-23 | 1 | −166.00 | 1 | −138.75 |
| 07-24 | 1 | −166.00 | 1 | +62.50 |
| 07-27 | 6 | +154.50 | 2 | −90.00 |
| 07-30 | 3 | +204.00 | 0 | 0.00 |
| 08-03 | 11 | +581.00 | 8 | +107.50 |
| 08-04 | 6 | +508.00 | 3 | +168.75 |
| 08-05 | 4 | +289.00 | 0 | 0.00 |
| 08-06 | 1 | −111.00 | 0 | 0.00 |
| 08-07 | 2 | −166.00 | 2 | −86.25 |
| **TOTAL** | **35** | **+1,127.50** | **17** | **+23.75** |

**Gap: +$1,103.75 on the same signals, on the same days.** This is not gate policy. It is:

* **Live ZLR shape: 26% win rate, average win $47.50, average loss −$49.82, payoff ratio 0.95.**
  Wins arrive as partial fills (T2 on one or two contracts); losses arrive with all four contracts at
  the stop. A 0.95 payoff at a 26% hit rate cannot be profitable at any gate setting.
* 20 `STOP_HIT` exits worth −$816.25 against 8 `T2_HIT` worth +$472.50.
* 18 of 57 routes that never became a position at all.

> **The single highest-value change to S4 is not a gate and not a pattern — it is the stop/target
> ladder and the order-placement reliability.** This is the same conclusion the trend-step audit reached
> from a different direction (`STEP_SCALED_LADDER_V1`, LIVE_CHANNEL 2026-08-11 23:55 §6). **Three
> independent analyses have now converged on the ladder.**

---

## 10. THE S4 CONFIGURATION FOR TOMORROW'S LIVE SESSION

### 10.1 What to change — one file, no new flags, no gate touched

`config/daytype_playbook.yaml` currently reads (verbatim):

```yaml
ZLR:   { group: CONT, cells: { Trend_Normal: FULL,    Trend_DD: FULL,    Normal: REDUCED, Variation: FULL,    Neutral_Center: SKIP, Neutral_Extreme: SKIP, ... } }
GB100: { group: CONT, cells: { Trend_Normal: REDUCED, Trend_DD: REDUCED, Normal: REDUCED, Variation: REDUCED, Neutral_Center: SKIP, Neutral_Extreme: SKIP, ... } }
FAMIR: { group: REV,  cells: { Trend_Normal: SKIP, Trend_DD: SKIP, Normal: FULL, Variation: REDUCED, Neutral_Center: FULL, Neutral_Extreme: FULL, ... } }
VEGAS: { group: REV,  cells: { Trend_Normal: SKIP, Trend_DD: SKIP, Normal: FULL, Variation: REDUCED, Neutral_Center: FULL, Neutral_Extreme: FULL, ... } }
```

**The table is backwards relative to every measurement in this audit: the pattern that loses in all
three sources gets `FULL`, the pattern that wins in all three gets `REDUCED`.**

| pattern | now | **proposed** | evidence |
|---|---|---|---|
| **GB100** | REDUCED on Trend_*/Normal/Variation | **FULL** on Trend_Normal / Trend_DD / Variation / Normal (keep SKIP on Neutral_*/Nontrend) | live +$167.50 3W-0L · shadow +$530.20 82% · replay +$2,282.50 both halves, all 3 months, all stops, to 4 ticks slippage |
| **ZLR** | FULL on Trend_*/Variation, REDUCED on Normal | **REDUCED** on Trend_Normal / Trend_DD / Variation; **SKIP** on Normal (keep SKIP on Neutral_*) | live −$270 39% · shadow −$849 51% · replay −$134, −$901 at 1 tick, negative at every stop, max DD −$2,207 |
| **TLB** | FULL on Trend_*/Variation | **unchanged (FULL)** | shadow +$792.52 over 50 at 70% |
| **HTLB** | FULL on Trend_*/Variation | **unchanged (FULL)** | live +$33.75 · shadow +$885.75 78% · replay +$660.50 both halves |
| **FAMIR** | FULL on Normal / Neutral_* | **SKIP everywhere** | replay −$1,607 (38% wr) · shadow −$660 (33%) · 0 live wins |
| **VEGAS** | FULL on Normal / Neutral_* | **SKIP everywhere** | replay −$1,015 (40%) · shadow −$276.50 (33%) |
| **GHOST** | FULL on Normal / Neutral_* | **REDUCED** on Normal / Neutral_* | live −$177.50 **0 wins in 3** · shadow −$431.60 (33%) · replay positive only with displacement ≥ 10 |
| **HFE** | disabled | **stays disabled** | shadow −$2,986.70 |

**Exact env / flag values: NO CHANGE. Every flag stays exactly as it is today.**

```
DAYTYPE_PLAYBOOK=1          keep — the single best-performing gate (−$670 saved)
EXTREME_CHASE_GUARD_V1=1    keep — net −$306 saved across the sample; do NOT open it
RELEASE_ENTRY_GATE_V1=1     keep
RR_ENTRY_GATE_V1=1          keep — net −$429 saved
LSMA_FLAT_GATE_V1=1         keep
CONT_TREND_FILTER=1         keep
DIRECTION_CONTEXT=1         keep
ZLR_SPEC_V2=1               keep
HFE_DISABLED=1              keep
LIVE_TRADING_V1=1 / LIVE_EXECUTION_V1=1   unchanged
```

**Permitted day-types:** trade S4 on `Trend_Normal`, `Trend_DD`, `Variation`, `Normal`. **Do not trade
S4 on `Neutral_Center`, `Neutral_Extreme`, `Nontrend`** — already enforced, and the data backs it hard
(NEUTRAL replay −$550; `daytype_playbook` saved −$505 on neutral days; 08-10 was `Neutral_Center` and
the blocks saved $452).

**Entry-distance rule:** **none for GB100.** I tested `distance from the session extreme ≥ 6 pt` and it
is *negative* for GB100 in half 1 (−$473.75) and for ZLR overall (−$1,455.50 across both halves). The
existing `extreme_chase_guard` (6.0–6.2 pt, ATR-scaled) already does this job and is net-positive.
**Do not add a second distance rule, and do not loosen the existing one.**

**Time window:** the best GB100 variant is `10:30–15:00 ET` (+$2,477.50 vs +$2,282.50 unfiltered, and
better at every slippage level). This is *already* nearly enforced by the existing
`session_gate_closed` (08:30–15:00 CT = 09:30–16:00 ET) plus `eod_entry_cutoff` (45 min). The only
missing piece is the 09:30–10:30 exclusion, worth ≈ +$195 over 48 sessions — **not worth a code change**.

### 10.2 Expected $ per day — measured, and then discounted honestly

* **Model, on the 48-session replay:** `GB100 + 10:30–15:00 ET` = **+$55.06 per session**
  (95 trades, +$2,477.50 net, 62.1% win rate, max DD −$892.75).
* **Reality check:** on the 9 days where signals passed the gateway, the same model said **+$1,127.50**
  and the account delivered **+$23.75** — **2%**.
* **Live GB100 to date:** 8 routes → 3 fills → 3 wins → **+$167.50 over ~5 weeks ≈ +$33/week.**

> **The number to plan on is the live one, not the model one.** My honest expectation for tomorrow is
> **+$0 to +$40 for the session, with a realistic worst case around −$150** (one full-R GB100 loss at
> 4 contracts). Anyone quoting "+$55/day" from this report is quoting the model, and the model has
> been wrong by 50× on this exact system.

### 10.3 Acceptance evidence

```bash
cd /Users/michael/Downloads/mems26_web_git
python3 scripts/s4_full_audit.py                      # all 12 sections
python3 scripts/s4_full_audit.py --only sweep         # the both-halves table (§8.1)
python3 scripts/s4_full_audit.py --only robust        # slippage / stop / months (§8.2)
python3 scripts/s4_full_audit.py --only chain --chain-dates 2026-08-10,2026-08-11   # §7
```

Load-bearing raw output:

```
   pattern                  n   per-sig $    wr%  seq n      seq $      net $
   ZLR                    435    -1906.25   49.9    128     633.75    -134.25
   GB100                  155     2078.75   56.8    110    2942.50    2282.50

   RULES THAT SURVIVE BOTH HALVES (the only ones worth shipping)
   pattern       filter                     trades  net $ total    h1 net$    h2 net$
   GB100         10:30-15:00 ET                 95      2477.50     215.75    2261.75
   GB100         no filter                     110      2282.50     195.75    2086.75

   candidate                            0 tick     1 tick    2 ticks    4 ticks
   GB100 + 10:30-15:00 ET              2477.50    2285.00    2143.75    2011.25
   ZLR (no filter)                     -134.25    -900.50   -1345.50   -2480.50

=== LIVE S4 by pattern ===
  ZLR    n=37 net=$-270.00  W=9  L=14  wr=39%
  GB100  n=8  net=$167.50   W=3  L=0   wr=100%
=== SHADOW S4 by pattern ===
  ZLR    n=136 net=$-849.48  wr=51%
  GB100  n=12  net=$530.20   wr=82%
  TLB    n=50  net=$792.52   wr=70%
  HTLB   n=9   net=$885.75   wr=78%
```

---

## 11. Brutal honesty — what this audit cannot support

1. **The decision log is 19 dates, not 48.** Everything in §3, §5, §7 and §9 rests on 15 sessions with
   RTH bars. The 48-session numbers (§6.2, §8) come from **my** detector replay, which is not the live
   signal stream (§1.3) and under-counts ZLR badly.
2. **7 trend sessions in the entire history**, and **zero** trend-labelled sessions inside the
   decision-log window with simulatable blocked signals. Every "S4 works in a trend" claim — including
   the +$1,077.50 TREND row in §8 — rests on 25 trades across 7 days.
3. **GB100's edge is concentrated in half 2** (+$196 in h1 vs +$2,087 in h2). It passes every test I
   ran, but 91% of the money is in the second half of the sample. n=110 trades is respectable; n=48
   sessions is not a lot of regimes.
4. **The replay's 8 pt stop is not the live stop.** Live S4 stops come out of `StopResolver`
   (`STOP_RESOLVER_V1=1`) and the per-pattern caps in `config/stop_anchors.yaml` (GB100 window 6,
   `max_risk_points: 15`). §8.2 shows GB100 is positive at every stop from 4 to 12 pt, which is why I
   am willing to recommend it anyway — but the exact $ will not reproduce.
5. **`daytype_playbook`, `rr_entry_gate` and `extreme_chase_guard` all read as net-savers across the
   whole sample and as net-costers on individual days.** 08-11 is the counterexample to
   `extreme_chase_guard`: +$911.25 per-signal cost on one day. One day is not a sample.
6. **This is an in-sample pattern-selection exercise on 48 sessions.** The both-halves + month +
   slippage + stop tests are the strongest hold-out available, but they are all drawn from the same
   10-week window on the same instrument. There is no genuinely fresh data.
7. **I did not re-verify the live day-type labels.** `v9_day_type_history` is taken as the truth about
   what the gates believed. `classify_replay` disagrees with it on at least one date
   (08-11: history `Variation` conf 0 vs replay `Normal_Variation`), and 08-11's playbook block quoted
   `FAMIR SKIP on Trend_Normal` while history says `Variation` — the anti-flap hold means gates can see
   a different label than the one recorded.

---

## 12. 🔴 Decisions for Michael

| # | decision | risk | needs a ruling? |
|---|---|---|---|
| **D1** | **`config/daytype_playbook.yaml`: GB100 REDUCED → FULL; ZLR FULL → REDUCED (SKIP on `Normal`)** | changes live sizing per pattern | **YES — one written ruling** |
| **D2** | **FAMIR + VEGAS → SKIP on every day-type** (replay −$1,607 / −$1,015; shadow −$660 / −$276; 0 live wins) | reduces the traded surface — risk-reducing | **YES**, but strictly narrowing |
| **D3** | **GHOST FULL → REDUCED on `Normal` / `Neutral_*`** (live 0 wins in 3, shadow 33%) | risk-reducing | **YES**, narrowing |
| **D4** | **Build `STEP_SCALED_LADDER_V1`** — the stop/target ladder is worth ~50× any gate change (§9). Third independent audit to land on it. | new behaviour, flag-OFF | **YES — and this is the one that matters** |
| **D5** | **Investigate `ORDER_FAILED:-1` — 18 of 57 live S4 routes (32%) never became a position.** Pure operations, no trading-risk change. | none | **no ruling needed** |
| **D6** | **Do NOT open `extreme_chase_guard`, `daytype_playbook`, or `rr_entry_gate`.** All three are net-positive across the sample (−$306 / −$670 / −$429 saved). 08-11 is a single-day counterexample. | — | **no — this is a "leave it alone"** |
| **D7** | **Do NOT ship any ZLR displacement/distance rule.** Every variant inverts out of sample (§6.2). | — | **no — this is a "do not ship"** |

---

*Generated by `s4-audit-agent`, 2026-08-11. Script: `scripts/s4_full_audit.py`. Full raw output:
`python3 scripts/s4_full_audit.py`. READ-ONLY: no flag changed, no restart, nothing written to
`~/SierraChart_Data` or the DB.*
