# RELEASE_ENTRY_GATE_V1 — why it was on, what it did, and what should replace it

**Date:** 2026-09-08 (written while the session is still open — see §0 caveat) · **Author:** cowork-dev
**Scope:** read-only. No code, service, flag, `.env`, order or DLL touched. This file is the only thing written.
**Question (Michael, 08.09):** *"is there a reason it was on — check the history; and if it does not work well,
examine alternatives for improving it and which components would help it more."*

---

## 0 · Caveats that bound every number below

* **MES = $5/point.** Every `$` figure is **2 contracts = $10/point** unless the line says otherwise.
  2 is the uniform basis chosen so blocked candidates and live trades are comparable; it is not the ruled size.
* **Shorts:** points = entry − exit. Asserted in code on every row (`relgate_score.py`): every STOP row is
  negative and every T1 row positive, checked separately for the 61 shorts and the 65 longs. Zero violations.
* **First-blocker trap.** `trading_gateway.py:2678` sets `blocked_by="awaiting_release"` and **returns**.
  ~20 gates downstream never saw these candidates. Nothing here says "it would have entered" — only
  *"this gate stopped it here, and the bars afterwards did X"*.
* **Today is incomplete.** `v9_bars_5min_woodies` for 09-08 ends at the bar opening **10:25 ET**; live #1231
  is still open. Today's rows are intraday, and §5 is re-run with today excluded.
* **Shadow is not used as truth anywhere in §2–§4.** It appears only in §5, to audit the ruling's own evidence.

---

## 1 · PART 1 — the paper trail

### 1.1 The ruling and its stated purpose

Michael, 2026-07-28, quoted verbatim at `backend/v9/systems/release_gate.py:3-4`:

> *"אתמול הכניסה של הסים לעסקת לונג הייתה טובה אבל מוקדמת … אפשר היה לזהות ולבצע כניסה בשלב אחר
> שהמחיר הפסיק להיות תקוע באותו אזור"*

Enabled the same morning in commit **`a27e2a8e` (2026-07-28 09:50 +0300)**, "LIVE: hold entries until the zone
releases, and size to the account (Michael 07-28)", which also quotes his framing for the day —
*"אני רוצה שהיום הלייב ימקסם מיקום ועסקה"* — and describes the mechanism as
"each can only restrict, never add … It fails closed, because a gate that fails open recreates precisely the
early entry it exists to prevent."

### 1.2 What loss it was built to prevent

**Not a live trade. A SIM long on 07-27**, named in the module docstring (`release_gate.py:6-17`):

> the extreme at 19:15 (low 7416.25), four higher lows on drying volume, the release at 19:50 closing 7433.
> *"The system entered at 19:24 — inside the sticky zone, 26 minutes early, with a 9pt stop, and was stopped
> out before the move it had correctly predicted."*

A second, structural rationale is attached to the same specimen (`:29-33`): entering on the release puts the
stop *under the real extreme* — "7433 with a stop below 7416 — a 17pt stop, exactly the GB100 profile that
survived, instead of ZLR's 9pt that did not. **Waiting for the release and sizing the stop correctly are the
same act.**" Hold that sentence; §6 shows two components now do the second half directly.

### 1.3 What measurement justified it — and this is the finding

**None that measured what it would block.** The 07-28 commit replays **one session** (07-27) and reports only
what the gate would *approve*: "five long approvals across the whole day, none stopped out, the first at 19:50
@7433 … reaching +1.34R". The counterfactual on the held signals was not computed.

The author said so, in writing, seven hours later — commit **`f04feaa5` (2026-07-28 16:25)**, prompted by
Michael's own demand *"אם הוא ימנע עסקה לבדוק אותו"*:

> *"He is right to demand accountability from **a gate I enabled on live off a single day of evidence**. A gate
> that only ever blocks looks identical whether it is saving money or quietly destroying an edge, and 'it
> prevented a bad trade' is unfalsifiable unless the counterfactual is measured."*

That commit built `scripts/release_gate_review.py` (SAVED US / COST US / UNDECIDED per hold, with the explicit
line `🔴 IT COST MORE THAN IT SAVED — recalibrate or turn it off`). **The script has never been modified since
and no report in `docs/reports/` publishes its output** — it is referenced only by two 07-29 handoff docs
(`TASKS_2026-07-29_PREOPEN.md`, `CC_WORKORDER_2026-07-29_NIGHT.md`) and `scripts/_INDEX.md`.

**But the gate was not unmeasured for long, and this is worse than "never measured":**
`docs/research/SYSTEM4_FULL_AUDIT_2026-08-11.md:222,243` measured it on 08-11 —

| gate | n | per-signal $ | wr% | seq $ |
|---|--:|--:|--:|--:|
| `awaiting_release` | 78 | +2,952.50 | 62.8 | **+465.00** |

> *"**Worst gates:** `direction_context` (+$604), **`awaiting_release` (+$465)**, `cont_trend_filter` (+$276).
> These three block genuinely good setups."* (positive = the gate **cost** money)

and per regime: **ROTATION +$546 (n=15/47) · NEUTRAL −$81 (n=6/31)** — i.e. the rotation model cost money
*in rotation*, the regime it was designed for. **It stayed ON for another 28 days after that reading.**

### 1.4 Every later change to its parameters

Reconstructed from **241 `.env` snapshots** under `~/mems26_snapshots/` plus `git log`. The enable moment is
bracketed exactly: `20260728T064914Z_pre-release-gate-enable` has no `RELEASE_*` var; the next snapshot
`20260728T095346Z_pre-dll-deploy` has the full set.

| when | change | reason given at the time |
|---|---|---|
| **07-28** | `RELEASE_ENTRY_GATE_V1=1` with `MIN_HIGHER_LOWS=2 · VOL_WINDOW=3 · VOL_RATIO=0.75 · ZONE_POINTS=8 · MAX_BARS=24 · STOP_BUFFER=1` | the 07-27 single-session replay (§1.3) |
| **07-29** (`029581d7`) | **code**, not params: `trend_bypass()` + the V-reversal path | *"60 gateway decisions since open, ZERO passed, on an 80pt trend-down + 62pt V-reversal … 29 validated winners blocked; **awaiting_release alone cost 16 vs 8 saved**."* Root: "this gate models a ROTATION … A trending session has no zone to release FROM" |
| **08-12** | `RELEASE_TREND_BYPASS_PTS` **15 → 12** (first seen in `20260812T050942Z_enable-step-ladder-0812`) | RULED_FLAGS: 11.08, three with-trend shorts missed the threshold by 3 pts, +$540 one-slot; +$202 in rotation replay. **n=3** |
| **08-14** | `RELEASE_LEG_EXEMPT_V1=1` (first seen in `20260814T065133Z`) | RULED_FLAGS: on 13.08 the gate held 4 of 10 candidates incl. the 16:34 long and the reversal shorts; replay 40 sessions → 5 exemptions, 5/5 winners, +$100 one-slot, 43 blocks preserved |
| **09-07** (`316056b0`) | `DELTA_BREAKOUT_RELEASE_V1=shadow` — second release path, logs only, `release_gate.py:126-139` never returns a release in shadow | ignition gated on `t1_before_stop ≥ 60%` at `n ≥ 10` |
| **09-08 17:20** | `RELEASE_ENTRY_GATE_V1=0` (`6b02ace8`, snapshot `20260908T141909Z`) | today's tape (§5) |

**The headline of this table: not one of the six structural parameters was ever re-calibrated.**
`MIN_HIGHER_LOWS=2`, `VOL_RATIO=0.75`, `ZONE_POINTS=8`, `MAX_BARS=24`, `VOL_WINDOW=3`, `STOP_BUFFER=1` are
byte-identical in all 42 snapshots from 07-28 to 09-08. Every change in 42 days was an **escape hatch bolted
onto the outside** — a bypass, an exemption, a second release path — never a correction of the model itself.

---

## 2 · PART 2 — what it actually did (measured, not inferred)

### 2.1 Population and what is excluded

Source: `~/SierraChart_Data/v9_export/decisions_archive/gateway_decisions.*.jsonl` (21 files) **+ today's live
`gateway_decisions.jsonl`** — 22 files, records spanning **2026-07-28 → 2026-09-08**.

```
raw blocked_by="awaiting_release"                    1,156
  inside RTH (ET 09:30–15:59) with bars                905
    carrying mfe_track{stop,t1}                        716   → 12 sessions, 08-24 … 09-08
  EXCLUDED: in-RTH, no mfe_track                       189   → 18 sessions, 07-28 … 08-21
deduped (candidate_id, else day+system+pattern+dir+signal-bar)  126
```

**189 candidates across 18 sessions carry no tracking and are excluded, not scored with a synthesised stop**
(Rule 1 — honest missing). The gate's first 18 sessions are therefore unmeasurable at this resolution.

Forward scoring: bars = `v9_bars_5min_woodies`, RTH only, walk starts at the first bar **opening strictly
after** the block; stop-first / T1-first / still-open at 15:55; same-bar stop+T1 → **STOP** (conservative).

**Method calibration (this is what makes the rest usable).** Against 39 live trades with a closed exit, the
5-min walk verdict vs `v9_trades.t1_hit_ts` (did T1 actually trade?): 19 T1→T1 · 16 STOP→NO_T1 · 2 wrong each
way = **90% agreement; walk precision 0.538 vs reality 0.538, delta 0.000.** The walk is unbiased on this
sample. *(A first attempt calibrated against `exit_reason` and appeared to show a 100% optimistic bias — that
test is invalid: `STOP_HIT` also fires on a stop trailed past entry, and 3 live rows carry `STOP_HIT` with a
positive P&L. Reported here so the discarded result is not re-derived later.)*

### 2.2 Blocks by reason, per session (deduped)

| day | n | Σ$ | structure not turning | still active in zone | left w/o volume | has not left | bars since extreme |
|---|--:|--:|--:|--:|--:|--:|--:|
| 08-24 | 13 | +308 | 8 | 1 | 2 | 0 | 2 |
| 08-25 | 6 | +445 | 3 | 3 | 0 | 0 | 0 |
| 08-26 | 5 | +270 | 1 | 2 | 2 | 0 | 0 |
| 08-27 | 7 | −79 | 5 | 0 | 1 | 1 | 0 |
| 08-28 | 10 | −201 | 2 | 1 | 2 | 0 | 5 |
| 08-31 | 20 | +108 | 6 | 5 | 8 | 0 | 1 |
| 09-01 | 17 | −103 | 10 | 0 | 4 | 0 | 3 |
| 09-02 | 11 | **+1,077** | 4 | 2 | 2 | 2 | 1 |
| 09-03 | 15 | +158 | 10 | 1 | 3 | 1 | 0 |
| 09-04 | 12 | −202 | 4 | 1 | 1 | 2 | 4 |
| 09-07 | 4 | −112 | 2 | 1 | 0 | 1 | 0 |
| 09-08 | 6 | +127 | 2 | 0 | 0 | 0 | 4 |
| **TOTAL** | **126** | **+1,794.50** | **57** | **17** | **25** | **7** | **20** |

Raw (pre-dedup) counts: structure not turning 378 · still active 271 · not enough bars 185 · bars since the
extreme 159 · left without volume 130 · has not left 33.

**The refusal string carries no forward information.** Precision by reason: `bars since the extreme` 0.650
(n=20) · `structure not turning` 0.509 (57) · `left without volume` 0.480 (25) · `has not left` 0.429 (7) ·
`still active` 0.412 (17). A 24-point spread on cells of 7–57, straddling the base rate in both directions.

### 2.3 Base rate

**T1-first 64 · STOP-first 42 · still open 20 → precision 0.508, n = 126.**
**Σ realised = +$1,794.50** at 2 contracts · Σ max-favourable-excursion = $11,232.50.
Under the *saved-vs-blocked* framing the 08.09 ruling used: saved **$4,701.00** (42 stop-first) / blocked
**$6,283.00** (64 T1-first) = **ratio 0.75**, with $212.50 still open — consistent with the published 0.83
at a different N. Net cost of holding, on the bars alone: **−$1,794.50 over 12 sessions ≈ $150/session at 2
contracts.** Read as money-at-stake behind the first block; not as forgone trades.

### 2.4 Distance from the session extreme — **the inversion hypothesis is half right**

Distance measured at the moment of the block, against the running session extreme in the relevant direction
(SHORT: session high − entry; LONG: entry − session low).

| band (pts) | n | T1 | ST | OP | precision | Σ$ | Σ MFE$ |
|---|--:|--:|--:|--:|--:|--:|--:|
| 0–2 | **0** | 0 | 0 | 0 | — | 0.00 | 0.00 |
| 2–5 | 7 | 3 | 0 | 4 | 0.429 | +10.40 | 247.50 |
| 5–10 | 43 | 23 | 17 | 3 | 0.535 | +410.10 | 3,622.50 |
| 10–20 | 59 | 29 | 19 | 11 | 0.492 | +1,278.20 | 5,822.50 |
| ≥20 | 8 | 5 | 1 | 2 | 0.625 | +256.20 | 740.00 |
| *missing (no closed prior bar)* | 9 | | | | | | |

**On the outcome axis this is a null result.** Precision is flat, non-monotone, and the widest cell (10–20)
sits *below* the base rate. Distance from the extreme does not predict what the bars did next. Excluding
today's still-open session the shape is unchanged (2–5: 0.429 · 5–10: 0.535 · 10–20: 0.474 · ≥20: 0.625).

**On the selection axis the hypothesis is confirmed**, and sharply:

| | blocked (n=126) | live-passed, same 12 sessions (n=41) |
|---|--:|--:|
| median distance from the session extreme | **11.00 pt** | **21.75 pt** |
| mean | 11.64 | 25.23 |
| candidates within 5 pt of the extreme | 7 / 126 | **0 / 41** |
| precision, identical forward walk | 0.508 | **0.512** |
| Σ$ (2 ct) | +1,794.50 | +77.50 |
| Σ$ per candidate | +14.24 | +1.89 |

**So: the shape is inverted, and the money is not.** The gate does hold the entries near the edge and pass
the ones roughly twice as far away — *no live trade in twelve sessions entered within 5 points of the session
extreme* — but the two populations score the same (0.508 vs 0.512) on the identical measurement. The
per-candidate gap ($14.24 vs $1.89) points the way Michael expects, but on n=41 with this variance it is not
a separation. **§6 shows the gate is only half the cause of the inversion.**

### 2.5 Distance from IB / prior-day VA — **this axis does separate**

Nearest of: IB high/low (after 10:30 ET), prior-day VAH / VAL / POC. Session extremes deliberately excluded
so this is a *level* test, not a repeat of §2.4.

| band (pts) | n | T1 | ST | OP | precision | Σ$ |
|---|--:|--:|--:|--:|--:|--:|
| **≤2** | **17** | 3 | 7 | 7 | **0.176** | **−453.10** |
| 2–5 | 25 | 15 | 7 | 3 | 0.600 | +783.90 |
| 5–10 | 26 | 15 | 4 | 7 | 0.577 | +651.30 |
| ≥10 | 58 | 31 | 24 | 3 | 0.534 | +812.40 |

Today excluded: ≤2 pt → n=15, precision **0.200**, **−$228.10**. Same sign, same magnitude.

This is not a new discovery — it replicates predicate **c**, pre-registered in writing in
`docs/reports/RELEASE_EXEMPTION_2026-09-08.md` §3 *before* any outcome was joined (0.300 / −$371.70 on n=20,
with a reference set that also included the session extremes). Two independent reference definitions, two
populations, same conclusion: **an entry glued to a named level is the one that does not pay.** That is a
*location* statement, and it is an argument for holding those entries — the opposite of loosening.

### 2.6 Two more axes, for completeness

| signal-bar range ÷ session median bar | n | precision | Σ$ | | stop distance ÷ session median bar | n | precision | Σ$ |
|---|--:|--:|--:|---|---|--:|--:|--:|
| <0.8 | 47 | 0.532 | +1,139.10 | | <0.75 | 4 | 0.500 | +24.60 |
| 0.8–1.0 | 18 | **0.333** | **−552.60** | | 0.75–1.0 | 7 | 0.571 | −46.30 |
| 1.0–1.25 | 13 | 0.615 | +454.90 | | 1.0–1.5 | 17 | **0.765** | +191.60 |
| ≥1.25 | 9 | 0.667 | +371.90 | | ≥1.5 | 68 | 0.441 | +1,083.00 |
| *missing (<6 prior bars)* | 39 | | | | *missing* | 30 | | |

### 2.7 Live trades that passed, realised

n=41 over the same 12 sessions. Book columns, **not** the walk: `pnl_r` median **0.27**, mean **0.04**,
23 wins / 14 losses → **win rate 0.622** (n=37) · `pnl_usd` **+$165.00** (n=34) · `pnl_sierra`
**−$46.25** (n=18). Median initial risk 7.25 pt; median signal-bar range ratio 0.796.

---

## 3 · PART 3 — the alternatives, each defined mechanically

Every rule is a **permit** predicate, measured **twice** on the same populations: (i) what it releases from
the 126 the gate held, and (ii) what it removes from the 41 live trades that passed.

### (i) on the 126 blocked candidates — base rate 0.508, Σ +$1,794.50

| rule | n permitted | T1 | ST | OP | precision | Σ$ released | Σ MFE$ |
|---|--:|--:|--:|--:|--:|--:|--:|
| **a** release gate as-is (baseline) | 0 | — | — | — | — | 0.00 | 0.00 |
| **b** no gate at all (running now) | 126 | 64 | 42 | 20 | 0.508 | +1,794.50 | 11,232.50 |
| **c** TIME: no repeat on the same pattern+direction within 6 bars | 89 | 40 | 32 | 17 | **0.449** | +595.10 | 7,560.00 |
| **d1** VOL: entry-bar range ≥ 1.0 × session median bar | 22 | 14 | 4 | 4 | **0.636** | +826.80 | 2,242.50 |
| **d2** VOL: stop distance ≥ 1.0 × session median bar | 85 | 43 | 24 | 18 | 0.506 | +1,274.60 | 6,920.00 |
| **e** ENTRY-BAR: stop beyond the last **closed** bar's extreme | 116 | 59 | 37 | 20 | 0.509 | +1,832.40 | 10,265.00 |
| **f** LEVEL: entry > 2.0 pt from any IB / prior-VA edge | 108 | 60 | 35 | 13 | **0.556** | **+2,226.20** | 9,847.50 |

### (ii) on the 41 live trades that passed — what each rule would have removed

| rule | trades removed | Σ pnl_usd removed | Σ pnl_sierra removed | Σ R removed |
|---|--:|--:|--:|--:|
| a | 0 | 0.00 | 0.00 | 0.00 |
| b | 0 | 0.00 | 0.00 | 0.00 |
| c | 9 | **+82.50** | −32.50 | +0.49 |
| d1 | **30 of 41** | −60.00 | +45.00 | −0.90 |
| d2 | 15 | −80.00 | −45.00 | −1.57 |
| e | 10 | −26.25 | **−262.50** | +0.46 |
| f | 11 | **+298.75** | +30.00 | +1.29 |

*(a rule that removes a positive Σ is destroying money; a rule that removes a negative Σ is saving it)*

### (f) — my own, stated before it was measured, and its provenance

I did not invent (f) after seeing §2.5. It is predicate **c** of the 12:05 study, fixed in writing that
morning before outcomes were joined; what I changed is the reference set (IB + prior-VA only, dropping the
session extremes so it is not a restatement of §2.4) and I then measured it on a 2-session-larger population.
That is a replication, not a discovery — and it is the **only** rule here that beats the base rate at n ≥ 10.

Full accounting: permitted (>2 pt from a level) n=108, precision **0.556**, **+$2,226.20**; still held
(≤2 pt) n=18, precision **0.222**, **−$431.70**. **But its two halves disagree**: on the live side it would
have removed 11 trades worth **+$298.75** of `pnl_usd`. It helps on the blocked set and hurts on the live set,
at n=17 and n=11. That is not a licence.

### (e) — the rule as literally stated cannot be run before the bar closes

Michael's example is exact: live **#1224** SHORT 7694.00 with its stop at 7699.25, inside the 09:55 bar whose
high reached **7701.25** — the stop sat **2.00 pt inside its own entry bar's high** and was taken. But the
entry was at that bar's *open*; the 7701.25 high printed **after** the fill. At decision time the bar had no
high yet. The implementable version must use the **last closed** bar, and on that version:

* on the blocked set it is inert — **116 of 126** already satisfy it (precision 0.509 = the base rate),
  median margin **7.00 pt** outside; exactly **1** blocked candidate has its stop inside the prior bar.
* on the live set it is not inert — **10 of 41** violate it: precision 0.400 vs 0.548, walk −$58.70 vs
  +$136.20, and **`pnl_sierra` −$262.50 (n=5) vs +$216.25 (n=13)**. The ten are #818 #822 #831 #838 #840
  #841 #853 #873 #950 #963.

**So (e) is not a release-gate replacement at all — it is a stop-placement rule, and it is the single most
interesting number in this report on the live side.** n=10, and the broker-priced subset is n=5. It belongs
in shadow, not in a flag.

### Variants tried, reported so no one re-tunes them silently

d1 at 0.80/1.00/1.25/1.50 × median → n=40/22/9/4, precision 0.500/0.636/0.667/0.750, Σ$ +274.20/+826.80/
+371.90/+186.10 · d2 at 0.75/1.0/1.5/2.0 → 92/85/68/45, 0.511/0.506/0.441/0.378 · f at 1/2/3/4 pt →
114/108/99/92, 0.544/0.556/0.535/0.543 · c at 3/6/12 bars → 93/90/85, 0.462/0.456/0.435 (every setting
**below** the base rate) · *entry within 10 pt of the extreme* → n=52, 0.519 · *entry bar closes beyond the
prior bar's extreme* → n=52, 0.481 · *f ∧ d1* → n=19, 0.632, +$566.80.
**Nothing was selected on these.** Only (f) at its pre-registered 2.0 pt clears n ≥ 10 with precision above
base — and §3(ii) shows its live half contradicts it.

---

## 4 · PART 3b — which existing components already do this job better

The release gate sits at `trading_gateway.py:2678`. Order matters: a component **downstream** of that line
never saw a single one of the 126.

| component | state | does it cover the release gate's job? | evidence |
|---|---|---|---|
| **`entry_not_confirmed`** (`S4_ENTRY_CONFIRM_V1=1`, `:3551-3573`) | ON, **downstream** | **Yes — the same job, in one bar instead of five.** Requires the last closed bar to close in the trade direction, tolerance `max(0.10×ATR14, 0.5 pt)`. That is the release gate's condition 3 (RELEASE) without conditions 1 and 2. | `ASYMMETRY_17D` §2: **n=15, 13 stop-first / 2 T1, saved $1,323.75 vs blocked ≤$243.75 → ratio 5.43** — the best gate in the entire stack, against `awaiting_release`'s 0.83. It is downstream of the release gate, so it has been starved of exactly the candidates it is best at judging. |
| **`ENTRY_LOCATION_QUALITY_V1=1`** (`:1905-1957`, blocking since 09-03) | ON, upstream | **Owns the axis that actually separates.** `pos > 0.66` in the leg without a pullback = chaser (`PULLBACK_MIN_PTS=3.0`), plus VAH/VAL and stop/ATR. §2.5's ≤2-pt-from-a-level cell is a location statement, and this is the component that owns location. | `ASYMMETRY_17D` §2: n=60, ratio 0.54 — currently blocks more than it saves. It has the right axis and the wrong calibration; §2.5 is a candidate cell to add **in shadow**. |
| **`extreme_chase_guard`** (`EXTREME_CHASE_GUARD_V1=1`, `:2495-2523`) | ON, upstream | **It is the release gate's mirror image on the same axis, and together they are the inversion.** Chase-guard blocks entries *too close* to the session extreme (min distance + a pullback in the last 3 bars); the release gate blocks entries *until structure turns*. One closes the near-the-extreme window, the other closes the still-in-the-zone window; the surviving window is **the middle**. | This, not the release gate alone, is why **0 of 41** live entries in 12 sessions sit within 5 pt of the session extreme (§2.4). On 08-11 chase-guard measured **−$306.25 (n=16)** — it saved money. Turning the release gate off leaves the other half of the pincer fully armed. |
| **`STOP_RESOLVER_V1=1`** (`:2778-2917`) | ON | **Fully covers the release gate's second stated rationale.** `release_gate.py:29-33` argues the release matters because it "puts the structural stop under the real extreme". The resolver does that directly — floor 0.5×ATR, cap 1.2×ATR (CONT) / 1.5×ATR (REV), walking a per-pattern rung ladder — without delaying the entry by 26 minutes. | `FLAG_INDEX.md:226`. The docstring's own claim "waiting for the release and sizing the stop correctly are the same act" is false once a resolver exists: they are two acts, and only one of them costs you the entry. |
| **`STEP_SCALED_LADDER_V1=1`** | ON | Same half: `stop = max(4, 0.6 × median step)`, targets 0.5/1.0/1.5 × step. Covers stop **sizing**, not entry **timing**. | `FLAG_INDEX.md:193`; ruled 08-12, re-aligned 08-13 to zig-zag leg amplitude. |
| **`_live_leg`/`RELEASE_LEG_EXEMPT_V1=1`** (`:2629`) | ON | **Already exhausted.** With-leg candidates are exempted *before* the gate can block them. | `RELEASE_EXEMPTION_2026-09-08` §4: predicate b0 (leg agrees with direction) selects **0 of 116** blocked candidates — structurally empty, not a null. A stricter leg rule is strictly emptier. |

---

## 5 · Today's tape — auditing the ruling's own evidence

The gate blocked **six** candidates today, all before 09:41 ET. Scored on the system's own `mfe_track`
structural stop and first target, uniform 2 contracts:

| ET | dir | pattern | entry | forward | Σ$ @2ct | dist. from level |
|---|---|---|--:|---|--:|--:|
| 09:30 | SHORT | DALTON_EDGE_SHORT | 7711.25 | T1 | **+65.00** | 2.75 |
| 09:30 | LONG | **ZLR** | 7714.25 | **STOP** | **−150.00** | 0.25 |
| 09:30 | LONG | **FAILED_RE_IB** | 7713.75 | **STOP** | **−75.00** | 0.25 |
| 09:30 | SHORT | CEILING_FLIP_SHORT | 7711.25 | T1 | +52.10 | 2.75 |
| 09:35 | SHORT | GB100 | 7707.75 | T1 | +115.00 | 6.25 |
| 09:40 | SHORT | FAILED_BREAK_SHORT | 7702.25 | T1 | +120.00 | 11.75 |
| | | | | **NET** | **+127.10** | |

**The ruling quoted three of these six.** At 09:30 the gate blocked **both directions at the same instant** —
two shorts at 7711.25 and two longs at 7714.25/7713.75 — and the two longs are the day's two losers.
Cross-checked against the system's own shadow twins (mixed contract sizes 5/2/5/5/2/3): the three cited
(#1214 +$220 · #1218 +$141.25 · #1221 +$92.50) sum to **+$453.75**; **all six** sum to **+$316.90**; and
**today's entire shadow book through 10:31 ET is −$54.35** across 21 rows. The direction of the ruling
survives; its magnitude is between one-third and two-thirds smaller once the same-moment losers are counted.

**What each alternative would have done to today's six** — and why most of them cannot answer:

| rule | releases | Σ$ of what it releases | would remove from today's 2 live |
|---|--:|--:|--:|
| a as-is | 0 / 6 | 0.00 | 2 of 2 |
| b no gate | 6 / 6 | +127.10 | 0 |
| c time (6 bars) | 6 / 6 | +127.10 | 0 |
| d1 vol (entry bar) | 0 / 6 | 0.00 | 2 of 2 |
| d2 vol (stop) | 1 / 6 | −150.00 | 1 of 2 |
| e entry-bar (last closed) | 2 / 6 | +235.00 | 0 |
| **f level (>2 pt)** | **4 / 6** | **+352.10** | 0 |

**d1, d2 and e are blind to four of the six**: those blocks fired on the **first RTH bar**, where there is no
closed prior bar and no session median. Only (f) — which needs no bar history, just IB/VA geometry — has an
opinion on all six, and it releases the four winners and holds the two losers. **n=6. That is an anecdote,
and it is the same anecdote that produced the ruling; it is not evidence.**

The prompt's shadow warning is verified exactly: shadow **#1223** and live **#1224** are the same signal, same
entry 7694.00, same t1 7688.75, **different stop** — shadow 7693.75 (0.25 pt from entry) booked **+$27.50** on
a "STOP_HIT"; live's real 5.25-pt stop was taken for **−$50.00**. Same signal, opposite sign, from the stop
alone. Shadow P&L is not usable as truth, and §2–§4 do not use it.

---

## 6 · Verdict and recommendation

**Was there a reason it was on?** Yes, a stated one, and it was honest about what it was: a fail-closed
restrict-only gate built in one morning from **one** session's replay, by an author who wrote down the same
day that this was insufficient and built the review tool to fix it. What was never done is the thing that
tool existed for. And the gate *was* independently measured on **2026-08-11** — n=78, named among the three
"worst gates", costing +$465 sequential and +$546 in rotation, the very regime it models — and it stayed on
for 28 more days. **The failure was not the enable. It was 28 days of not acting on a measurement we had.**

**Does it work well?** No, and not in the way it was accused of either.
* It is a **coin flip on outcome**: 0.508 over 126 candidates against **0.512** for the 41 trades it let
  through, on the identical forward walk. Its own five refusal strings run 0.412–0.650 and straddle the base
  rate — the reason it gives you carries no information about what happens next.
* It **is** structurally inverted **in location**: it holds entries a median 11.00 pt from the session extreme
  and passes entries a median 21.75 pt away, and no live trade in twelve sessions entered within 5 pt of the
  extreme. But distance from the extreme does not predict outcome in this data (0.429 / 0.535 / 0.492 / 0.625,
  and *zero* blocks inside 2 pt), so **the inversion is real as a shape and unproven as a cost.** And the
  release gate is only half of it — `extreme_chase_guard` closes the other side of the same pincer and is
  still armed.

**Recommendation: keep it off. Do not replace it with any of a–f.**

The number: **0.508 blocked vs 0.512 permitted, n = 126 against n = 41, over 12 sessions on one measurement
whose calibration error against real fills is 0.000.** A gate that selects at the base rate is not a gate; it
is a delay. Removing it returns the **+$1,794.50** (2 ct, 12 sessions, ratio 0.75) that sat behind its blocks
to the twenty gates downstream — including `entry_not_confirmed`, which does the same job one bar later at
**ratio 5.43** and has been starved of these candidates by ordering alone.

**On "replace it with X": the data cannot license X today.** No alternative clears *n ≥ 10 **and** precision
above base **and** positive on **both** halves*. (f) is the only one that beats the base rate on the blocked
set (0.556, +$2,226.20) and it removes +$298.75 of live winners. (d1) has the best precision (0.636) and
removes 30 of 41 live trades. (c) is below the base rate at every setting tried. (e) is inert where the gate
acted and interesting only where it did not.

**Three follow-ups, in priority order, none of them a flag today:**
1. **(e) as a stop rule, in shadow.** The 10 live trades whose stop sat inside the prior closed bar ran
   0.400 vs 0.548 and **−$262.50 vs +$216.25** on broker-priced rows. n=10 / n=5 — the smallest interesting
   number in this report, and it is about stop placement, which is where `STOP_RESOLVER_V1` already lives.
2. **(f) as a cell inside `ENTRY_LOCATION_QUALITY_V1`, in shadow** — not as a new gate. Twice
   pre-registered, twice replicated (0.176 here on n=17, 0.300 on n=20 in the 12:05 study), and it is a
   location statement, which is that component's job. Its live half disagrees; 20 sessions of shadow will
   say which half is the sample.
3. **Re-measure `awaiting_release` in a week, as the ruling says** — and this time via
   `scripts/release_gate_review.py`, which has been sitting unused since the day it was written for exactly
   this purpose.

**What must not be concluded.** The chain returns at the first blocker. Every `Σ$` above is what the bars did
after the block, at 2 contracts and one slot per candidate — never "it would have entered". 189 in-RTH blocks
across the gate's first 18 sessions carry no tracking and are excluded entirely, so nothing here describes
2026-07-28 → 2026-08-21.

---

### Reproduce

```bash
cd ~/Downloads/mems26_web_git && set -a && . ./.env && set +a
python3 <outputs>/relgate_score.py    # §2.2–2.6 base rate + all band tables (needs /tmp/relgate/data.pkl)
python3 <outputs>/relgate_alts.py     # §2.7 live set + §3 the seven rules, both halves
python3 <outputs>/relgate_today.py    # §3 variants + §5 today's six, entry by entry
python3 <outputs>/relgate_calib2.py   # §2.1 walk-vs-t1_hit_ts calibration (and the discarded test)
python3 <outputs>/relgate_final.py    # §2.3 saved/blocked + §2.4 head-to-head + §5 rule-by-rule
```

Sources: `~/SierraChart_Data/v9_export/decisions_archive/gateway_decisions.*.jsonl` + today's live
`gateway_decisions.jsonl` · `v9_bars_5min_woodies` · `v9_tpo_sessions WHERE session_type='CASH'` ·
`v9_trades` (`mode`, `t1_hit_ts`, `quality->metadata->stop_initial`) · 241 `.env` snapshots under
`~/mems26_snapshots/` · `git log -S RELEASE_ENTRY_GATE_V1`.
Population build: `/tmp/relgate/build.py`. Scripts are ephemeral; every query and predicate they run is
written out above.
