# STAIR PATTERN GAP — "התבנית החסרה של המדרגות"

**Date:** 2026-08-18 · **Machine:** mac-1 · **Mode:** STRICTLY READ-ONLY
(no flag changed, no restart, no DB write, no `~/SierraChart_Data` write, no code edit).
**Sources:** `v9_bars_5min_woodies`, `v9_trades`, `/tmp/backend.err.log`, `.env`.
**Scratch scripts (outside the repo):** `outputs/stair_census.py`, `outputs/stair_variants.py`,
`outputs/stair_oos.py`, `outputs/stair_f_detail.py`.

---

## 0. Answer: it is **(c)**, with a live-path (b) on top

Michael is not asking for a detector that does not exist. `TREND_STEP_ENTRY_V1=1` is live
(`.env:505`) and it does fire. He is pointing at a **different staircase**: the detector by
construction only accepts the step that **made the session extreme**. A staircase that walks
*inside* the day's range — the second-order staircase, the afternoon staircase, the one that
climbs back toward an earlier extreme — is **excluded by design**, and that is the single
largest class of misses (18 of 48 missed legs, 33 of 48 missed legs are not at the extreme).

Secondary, and real: the routed candidates on 08-14 all lost (**−$930 on 9 rows**) because of
three live-path divergences from the ruled replay model (§4). One of them (forming-bar entry)
was already root-fixed on 08-16; two are still open.

---

## 1. Baseline verification (Rule 2 — verified before comparing)

```
$ cd /Users/michael/Downloads/mems26_web_git
$ python3 scripts/replay_trend_step_entry.py --validate
...
=== VALIDATION ===
  first half 2026-07-15..2026-07-28  NET=   +$390.00 n= 16 win= 44%
  second half 2026-07-29..2026-08-12 NET= +$1,988.75 n= 15 win= 53%

  NET=+$2,378.75  n=31
  best=+$512.50  worst=-$135.00  median=-$33.75
  profitable sessions: 12/19
  max drawdown (trade sequence): -$288.75
```

**The 2026-08-14 ruling's `+$2,378.75 / n=31 / win 48%` reproduces exactly** (15 winners /
31 = 48 %). Every number below is measured against this, same window, same 4-contract model.

---

## 2. Question 1 — how many real staircases in the last 10 sessions?

**Criterion (in code, `outputs/stair_census.py::find_staircases`), from
`v9_bars_5min_woodies` RTH bars only:**

> A STAIRCASE = **≥ 2 consecutive same-direction impulse legs** of the offline zigzag
> (`ZZ_REV = 5.0 pt`), where
> (a) each leg is **≥ 6.0 pt**,
> (b) each successive extreme **extends** the previous one (lower low / higher high),
> (c) the counter-leg between them gives back **< 100 %** of the prior impulse
>     (a ≥100 % giveback is a reversal, not a stair),
> (d) total displacement **≥ 12.0 pt**.

```
$ python3 outputs/stair_census.py
sessions analysed: 10  (2026-08-04 .. 2026-08-17)

===== TOTALS (10 sessions) =====
staircases (>=2 extending legs) : 27
  of which >=1 leg caught       : 12
individual staircase legs       : 68
  legs caught by detector       : 20

first-failing condition census (per missed leg, at pause bar 1):
  SESSION_EXT            18
  RETR                    9
  CUTOFF                  9
  IMP_RANGE               4
  IMP_BARS                4
  i<4                     3
  VOL_RATIO               1

misses that are NOT at the session extreme (structurally excluded): 33
misses at the session extreme: 15
```

**27 staircases · 12 with at least one leg caught · 68 legs · 20 legs caught.**
15 staircases are completely invisible to the detector.

## 3. Question 2 — what the misses have in common

| Rank | Blocking condition | missed legs | What it excludes |
|---|---|---|---|
| 1 | **`SESSION_EXT_TOL = 0`** (the step must BE the session extreme) | **18** | Staircases **inside the range** and every **second-order** staircase. |
| 2 | `RETR_MAX = 0.55` | 9 | Deep-pause steps (0.59–1.4 giveback). |
| 3 | `CUTOFF = 15:00` | 9 | The **entire** late-day staircase: 08-05 15:20, 08-06 14:40, 08-07 14:40, 08-11 15:05, 08-13 14:20, 08-17 14:50. |
| 4 | `IMP_MIN = 8.0` | 4 | The tail leg of a dying staircase (5.0–7.8 pt). |
| 5 | `IMP_BARS_MAX = 10` | 4 | The slow grind leg (11–17 bars). |
| 6 | `i < 4` | 3 | The 09:30–09:45 opening leg. |
| 7 | `VOL_RATIO_MAX` | 1 | — |

**The dominant shared property of the misses: the step is not at the session extreme
(33 of 48 missed legs).** Concrete examples straight out of the census:

```
── 2026-08-13 [SEMI]
    LONG  12:15→13:20 legs=2 total=19.50pt  ends_at_session_extreme=False
        leg 12:15→12:30 11.75pt  ❌ SESSION_EXT(-27.00) | SESSION_EXT(-27.00) | IMP_RANGE(5.0)
        leg 12:35→13:20 13.25pt  ❌ SESSION_EXT(-19.25) | SESSION_EXT(-19.25) | SESSION_EXT(-19.25)
── 2026-08-12 [TREND]
    LONG  11:40→14:40 legs=3 total=20.75pt  ends_at_session_extreme=False
        leg 11:40→12:25 11.00pt  ❌ SESSION_EXT(-22.75) | SESSION_EXT(-22.75) | IMP_RANGE(7.5)
        leg 12:35→13:05 11.50pt  ❌ SESSION_EXT(-16.50) | SESSION_EXT(-16.50) | SESSION_EXT(-16.50)
── 2026-08-10 [ROTA]
    LONG  12:30→13:15 legs=2 total=15.75pt  ends_at_session_extreme=False
        leg 12:30→12:35 13.50pt  ❌ SESSION_EXT(-19.75) | ...
        leg 12:45→13:15 14.00pt  ❌ SESSION_EXT(-17.50) | SESSION_EXT(-17.50) | SESSION_EXT(-17.50)
```

**The 2026-08-13 LONG staircase 12:15→13:20 is literally the one Michael complained about**
(`detector.py:4` — *"13.08: 7798→7814 in two up-steps"*). It is 27 pt below the session high,
so `SESSION_EXT_TOL = 0` rejects it three bars running. The complaint that created the detector
is still not answered by the detector.

---

## 4. Live path — what actually happened since the flag went on (the (b) part)

```
$ grep "TrendStep] CANDIDATE" /tmp/backend.err.log | awk '{print $1}' | sort | uniq -c
  13 2026-08-14
   1 2026-08-17
$ grep "TrendStep] ROUTED" /tmp/backend.err.log | awk '{print $1}' | sort | uniq -c
   7 2026-08-14
$ grep -o "gateway blocked: [a-z_]*" /tmp/backend.err.log | sort | uniq -c
   1 gateway blocked: awaiting_release
   3 gateway blocked: entry_not_confirmed
   2 gateway blocked: lsma_flat
   1 gateway blocked: pattern_stop_cooldown
```

Only **two** RTH sessions exist since the flag went live (08-14 Fri, 08-17 Mon; 08-18 has 15
bars, latest `2026-08-18 08:10+03` = 01:10 ET — RTH has not opened). It is **not** silent:
08-14 produced 13 candidates → 7 routed. 08-17 produced 1, blocked by `awaiting_release`.

**Every routed trade lost:**

```
$ psql postgresql://localhost/mems26 -c "SELECT id,mode,entry_ts AT TIME ZONE 'America/New_York' et,
    direction,entry_price,stop,exit_price,exit_reason,pnl_usd FROM v9_trades
    WHERE pattern_id_at_entry ILIKE '%TREND_STEP%' ORDER BY id;"
 667 | shadow | 2026-08-14 10:35 | SHORT | 7811.25 | 7816.5  | 7816.5  | STOP_HIT  |  -78.75
 668 | live   | 2026-08-14 10:35 | SHORT | 7811.25 | 7816.5  | 7816    | STOP_FILL |  -71.25
 674 | shadow | 2026-08-14 11:25 | SHORT | 7802.25 | 7809.25 | 7809.25 | STOP_HIT  |  -105
 675 | shadow | 2026-08-14 11:30 | SHORT | 7805    | 7812.5  | 7812.5  | STOP_HIT  |  -150
 676 | shadow | 2026-08-14 11:35 | SHORT | 7804    | 7811.5  | 7811.5  | STOP_HIT  |  -150
 678 | shadow | 2026-08-14 11:40 | SHORT | 7803.25 | 7810.75 | 7810.75 | STOP_HIT  |  -150
 681 | shadow | 2026-08-14 13:00 | SHORT | 7799.25 | 7804.25 | 7804.25 | STOP_HIT  |  -75
 682 | live   | 2026-08-14 13:00 | SHORT | 7799.25 | 7804.25 | 7804.25 | STOP_FILL |  -75
 683 | shadow | 2026-08-14 13:10 | SHORT | 7801.25 | 7806.25 | 7806.25 | STOP_HIT  |  -75
count=9  sum=-930
```

Three divergences from the ruled replay model explain it — none is a detector-geometry fault:

1. **Forming-bar entry (already root-fixed 2026-08-16).** Trade 667/668 entered at
   **7811.25**; the replay's same 10:35 signal enters at **7816.50** (5.25 pt better) and runs
   `T0+T1+T2+MTM1 = +$218.75`. Exactly the 5.25 pt described in `detector.py:220-235`.
   The 08-14 evidence therefore **predates** the fix and says nothing about the current code.
2. **No `step_id` dedup in the live path — STILL OPEN.** `backend/main.py:877-907` dedups only
   on `bar_ts`; `build_setup()` (`detector.py:276-293`) does not even return `step_id`. Result:
   11:25 / 11:30 / 11:35 / 11:40 are **four separate entries on the same step** (674/675/676/678,
   −$555 combined). The replay takes one (`run()` `used_steps` + `busy_until`). The research
   spec required it (`TREND_STEP_ENTRY_2026-08-11.md` §6.3). Measured:
   ```
   WITH step dedup + no-overlap (replay/ruling) NET= +$2,378.75 n= 31 win= 48%
   NO dedup  (= the live path today)            NET= +$2,735.00 n= 69 win= 42%
   ```
   Not a P&L disaster in the replay, but **2.2× the trades and 2.2× the risk concentrated on
   one step** — the ruled number was measured with dedup, so the live path is off-model.
3. **The stop is not the detector's stop — STILL OPEN** (the §6.4 build-blocker, materialised):
   ```
   2026-08-14 18:25:03 [INFO] [StepLadder] SHORT entry=7802.25 median_step=11.75 → stop=7809.25 (7.0pt) t1=7795.25 ...
   2026-08-14 18:25:03 [WARNING] [Gateway] TARGET_REALISM_V1: t1 7795.25 → 7800.00
   ```
   F3 scales the stop to the **session median step** (7.0 pt), not to **this step's pause
   extreme** (replay R = 2.50–3.02 pt on the same signals), and `TARGET_REALISM_V1` then pulls
   T1 to 2.25 pt against a 7.0 pt stop (**T1 R:R = 0.32**). 9/9 stopped, 0/9 reached T1.

---

## 5. Question 3 — the smallest correct change, measured

### The change (one condition, `backend/v9/systems/trend_step/detector.py:153-162`)

The anti-rotation gate becomes an **OR**, using the staircase test that is **already in the
file** (`detector.py:146-151`, currently dead because `REQUIRE_STAIR=0`) as an *alternative*
to the session-extreme test rather than an additional AND:

```
accept if   step extreme IS the session extreme      (today's rule, unchanged)
        OR  the step extends a CONFIRMED staircase   (lower low AND lower high vs the
                                                      previous swing pair — piv[k-2]/piv[k-3])
```

Nothing else moves: same zigzag, same impulse/pause/retrace/LSMA/volume tests, same ladder.
It keeps the intent (never enter a rotation) while admitting the in-range staircase, which is
exactly the shape Michael is pointing at.

### Replay, same window / same execution model as the 2026-08-14 ruling

```
$ python3 outputs/stair_variants.py
window 2026-07-15..2026-08-12  sessions=21

A  BASELINE (ruling 2026-08-14)              NET= +$2,378.75 n= 31 win= 48% | after comm +$2,192.75
                                             H1 07-15..07-28 NET=  +$390.00 n=16 win= 44%
                                             H2 07-29..08-12 NET=+$1,988.75 n=15 win= 53%
F  session_extreme OR confirmed-staircase    NET= +$2,801.25 n= 43 win= 47% | after comm +$2,543.25
                                             H1 07-15..07-28 NET=  +$493.75 n=23 win= 43%
                                             H2 07-29..08-12 NET=+$2,307.50 n=20 win= 50%
     of which NEW (in-range staircase) trades: n=12 NET=+$422.50
```

**+$2,378.75 → +$2,801.25 (+$422.50, +17.8 %), n 31 → 43, win 48 % → 47 %.
Both chronological halves improve** (+$390 → +$493.75 and +$1,988.75 → +$2,307.50) — the
gain is not one half carrying the other. All 12 new trades are the previously-excluded
in-range-staircase class and together they are +$422.50, i.e. the whole delta.

### Every other knob I measured is worse (same window)

| Variant | NET | n | vs baseline |
|---|---|---|---|
| **A baseline** | **+$2,378.75** | 31 | — |
| B `SESSION_EXT_TOL=2.0` | +$2,088.75 | 36 | −$290 |
| B `SESSION_EXT_TOL=4.0` | +$1,921.25 | 38 | −$458 |
| B `SESSION_EXT_TOL=8.0` | +$1,907.50 | 42 | −$471 |
| B `SESSION_EXT_TOL=-1` (gate off) | +$2,410.00 | 60 | +$31 on **2× the trades** |
| C `CUTOFF=15:30` / `16:00` | +$2,228.75 | 33 | −$150 |
| D `RETR_MAX=0.65` | +$2,301.25 | 33 | −$78 |
| D `RETR_MAX=0.75` | +$2,132.50 | 37 | −$246 |
| E `IMP_MIN=6.0` | +$2,378.75 | 31 | $0 |
| E2 `IMP_BARS_MAX=14` | +$2,258.75 | 33 | −$120 |
| **F ext-OR-stair** | **+$2,801.25** | 43 | **+$422.50** |
| F2 = F + `MAX_PER_DAY=6` | +$2,711.25 | 44 | +$333 (worse than F) |

Loosening the gate by *tolerance* is strictly worse — it admits rotation. Loosening it by
*structure* is what works. That is the finding.

### Robustness (`outputs/stair_oos.py`)

| Window | Baseline | Variant F |
|---|---|---|
| TRUE out-of-sample 06-05…07-14 (29 sess) | +$345.00 / n=36 / 36 % | **+$763.75 / n=63 / 38 %** |
| All 49 sessions 06-05…08-12 | +$2,810.00 / n=66 / 42 % | **+$3,535.00 / n=103 / 42 %** |
| All 49, **2 ticks adverse slip** | +$2,031.25 | **+$2,628.75** |
| All 49, after commission | +$2,414.00 | **+$2,917.00** |
| Forward 08-13…08-17 (post-ruling, **THIN n=5**) | +$163.75 / n=2 | **+$297.50 / n=5** |

F improves in **every** window, including the out-of-sample one the original report failed
(§4.2 of `TREND_STEP_ENTRY_2026-08-11.md`), and it survives 2 ticks of adverse fill on the
full sample. The forward window is **n=5 — thin, no weight**.

**The direct hit:** on **2026-08-13**, the day of Michael's original complaint, the baseline
takes **zero** trades. Variant F takes three, all in-range staircases, **+$133.75**:

```
2026-08-13 11:40 SHORT entry=7803.75 stop=7809.75 R=5.95 imp=17.00 retr=0.47 stair=True at_ext=False T0+STOP      -$75.00
2026-08-13 12:35 LONG  entry=7807.25 stop=7804.75 R=2.50 imp=11.75 retr=0.47 stair=True at_ext=False T0+T1+T2+T3 +$165.00
2026-08-13 14:55 LONG  entry=7822.00 stop=7819.25 R=2.77 imp=12.75 retr=0.26 stair=True at_ext=False T0+T1+BE     +$43.75
```

The 12:35 LONG is the `7798→7814` up-staircase from `detector.py:4`.

### Coverage delta on the 10-session census

```
  BASELINE   staircases 12/27   legs 20/68
  VARIANT F  staircases 15/27   legs 24/68
```

+3 staircases, +4 legs. The rest of the residual is `CUTOFF=15:00` (6 whole late-day
staircases) and `RETR_MAX`, both of which measure **negative** in §5 — leave them alone.

---

## 6. What I am NOT proposing

No flag is proposed for enabling here, and nothing was changed. Per §5 this is a **measured
proposal only**; wiring it is a trading-risk-surface change → strategic stop + Michael's
sign-off. The two open live-path defects in §4 (missing `step_id` dedup; F3/TARGET_REALISM
overriding the detector's pause-anchored stop so T1 sits at R:R 0.32) are **independent of
the detector geometry and should be closed first** — the +$2,801.25 is not reachable live
while the executed stop is 2.3× the modelled one.

**Roadmap/STATUS_BOARD were deliberately NOT updated** (this session is read-only, one file);
the finding needs a STATUS_BOARD line + TASK_LOG rows when it is picked up.
