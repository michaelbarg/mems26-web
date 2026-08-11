# LEG-EXEMPTION — quantification across ALL gates (replay, 2026-08-11)

**Agent:** `leg-exemption-agent` (Cowork/MacBook) · **Mode:** STRICTLY READ-ONLY —
no flag changed, no restart, nothing written to `~/SierraChart_Data` or the DB.
**Question (Michael, tonight):** the LEG_RIDE exemption already covers
`cont_trend_filter` / `location_gate` / `extreme_chase_guard` / `lsma_flat`.
Should **`awaiting_release`** and **`zone_limit_late_entry`** also be leg-exempt?

**Answer in one line: NO to both — and the reason is not "risky", it is
"n=0". Neither gate has a single with-leg block to exempt on the trend days.
The money that got left on the table today needs a *displacement* qualifier
and a *step-scaled stop*, not a wider leg exemption.**

---

## 0. Method + reproduction

```
cd /Users/michael/Downloads/mems26_web_git
env BRIDGE_TOKEN=x DATABASE_URL=postgresql://localhost/mems26 \
  python3 scripts/leg_exemption_replay.py --zigzag-thr 6 \
  --detail-day 2026-08-11 --json-out /tmp/leg_z6.json
```

* Source of blocks: `~/SierraChart_Data/v9_export/gateway_decisions.jsonl`
  (5,936 rows). **Fixture rows (`entry == 7600`) dropped** — 114 of them across
  the log, 7 on 08-11 (the pytest contamination the live-forensic agent
  documented at 20:05).
* Source of price: **`v9_bars_5min_woodies`** (canonical Sierra), RTH
  09:30–16:00 ET only.
* Leg call: `backend/v9/systems/leg_state.detect_leg` on the **10 closed RTH
  bars up to the decision's bar** — byte-for-byte the window `_live_leg()`
  queries in `trading_gateway.py:117-123`.
* `.env` loaded with the same `parse_env` shape as `scripts/flag_guard.py`.
* Dedupe: one signal per `(date, gate, pattern, direction, bar)`. 2,010 raw
  blocked rows → **318 unique signals** over 10 sessions.
* Two aggregations, always both:
  * **per-signal** — sum over every unique signal (overlapping; an upper bound).
  * **sequential** — one trade at a time per day (a new signal is skipped while
    the previous simulated trade is still inside its 12-bar window). **The
    sequential number is the headline** — it is the only one a single account
    could actually have earned.
* Simulation, 4 contracts, $5/pt, **conservative intrabar order (stop is
  checked before targets inside the same bar)**; the entry bar's full range is
  charged against the trade. Runner exits at the 12th bar's close.
  * **CURRENT** = stop 8pt (the jsonl records no stop — structural fallback per
    the brief), C1 +3pt · C2 1R · C3 2R · C4 4R runner, BE after T1(1R).
  * **STEP** = stop `max(4pt, 0.6 × median step)`, targets `0.5 / 1.0 / 1.5 ×
    step`, C4 runner, BE after the 1.0× leg. `step` = causal median zigzag swing
    (reversal threshold 6pt → median step **10.38pt** on the trend days, which
    matches Michael's eyeballed "~11pt down-steps"; a 3pt threshold gives 6.69pt
    and is reported as a sensitivity).
* Cohorts: **TREND** = 08-03, 08-04, 08-11 · **ROTATION** = 08-06, 08-07, 08-10
  · **ZL_COHORT** = 07-23, 07-24, 07-28, 07-31 (added because the six August
  days contain **zero** real `zone_limit_late_entry` blocks — see §2).

**Known limits (stated up front):** the stop is a *fallback*, not the stop the
system would really have used; a 12-bar horizon truncates runners; the
conservative intrabar rule penalises the tighter STEP stop, so STEP's advantage
below is if anything understated. Every n<10 is flagged in §5.

---

## 1. `awaiting_release` — leg exemption pays **$0 on the trend days (n=0)** and **−$122.50 on rotation**

```
[TREND]    awaiting_release: n=8  with_leg=0 | CUR seq net=$0.00 (n=0)  | no-leg CUR per-signal=$22.50 (n=8)
[ROTATION] awaiting_release: n=35 with_leg=9 | CUR seq net=$-122.50 (n=5, w=2) | STEP seq net=$86.94
[ZL_COHORT]awaiting_release: n=24 with_leg=11| CUR seq net=$121.25 (n=3, w=2)  | STEP seq net=$29.32
```

**Not one of the 8 release-gate blocks on the three trend days was with-leg.**
On 08-11 the release gate blocked 11 raw / 8 unique signals; three were LONGs on
a down day (correctly held), and the three that *did* carry the day's money were
`leg=None`:

| 08-11 (UTC) | dir | pattern | leg | why no leg | disp | MFE | CUR sim |
|---|---|---|---|---|---|---|---|
| 14:25:06 | SHORT | ZLR | None | `structure 4/2 swings, net=no` | −11.50 | 12.25 | **+$142.50** |
| 14:40:38 | SHORT | ZLR | None | `CCI not holding the side (2 bars across zero)` | −12.25 | 16.75 | **+$211.25** |
| 14:45:02 | SHORT | ZLR | None | `CCI not holding the side (2 bars across zero)` | −12.00 | 16.75 | **+$195.00** |

A leg exemption would have unlocked **none** of them. What would have unlocked
them already exists: `release_gate.trend_bypass()` — and it missed by 3 points.
Displacement at those bars was −11.5 / −12.25 / −12.0 against a threshold of
`RELEASE_TREND_BYPASS_PTS=15`.

```
=== RELEASE-GATE TREND-BYPASS SENSITIVITY (awaiting_release only) ===
  thr= 15.0 [TREND   ] released=0  /8   CUR seq net=$     0.00 (n=0, w=0)  STEP seq net=$     0.00
  thr= 15.0 [ROTATION] released=0  /35  CUR seq net=$     0.00 (n=0, w=0)  STEP seq net=$     0.00
  thr= 12.0 [TREND   ] released=2  /8   CUR seq net=$   211.25 (n=1, w=1)  STEP seq net=$   -99.00
  thr= 12.0 [ROTATION] released=2  /35  CUR seq net=$   202.50 (n=2, w=2)  STEP seq net=$   215.62
  thr= 10.0 [TREND   ] released=3  /8   CUR seq net=$   142.50 (n=1, w=1)  STEP seq net=$   -80.00
  thr= 10.0 [ROTATION] released=6  /35  CUR seq net=$   138.75 (n=4, w=3)  STEP seq net=$   280.51
  thr=  8.0 [TREND   ] released=3  /8   CUR seq net=$   142.50 (n=1, w=1)  STEP seq net=$   -80.00
```

**12pt is the knee** — it is the only threshold that is positive in *both*
regimes on the CURRENT sizing (+$211.25 trend, +$202.50 rotation, 3 winners /
3 trades). Going to 10 adds three more rotation entries and *lowers* the trend
number. This is a **parameter change on an existing, already-ruled bypass**, not
a new exemption surface — and it is the single cheapest fix in this report.

> This supersedes item **B3** ("`awaiting_release` leg-aware") in the 20:05
> live-forensic ranking. The gate is not leg-blind; the *leg detector* is blind
> on this tape. B3 as written would have changed nothing.

**Verdict: `awaiting_release` must stay leg-strict.** The rotation cohort is the
proof it earns its keep: the 26 no-leg release blocks on rotation days would
have been **+$1,175 per-signal if taken** — i.e. the gate is *costing* money on
rotation days too, but not through the leg dimension, and its with-leg subset is
the *losing* half (−$122.50).

---

## 2. `zone_limit_late_entry` — **zero real blocks. Ever. In RTH.**

```
  2026-08-11 zone_limit_late_entry    real=0    fixture(7600)=7
```

None of the six study days has a single non-fixture `zone_limit_late_entry`
block. Widening the search to the **entire 5,936-row decision log**:

```
zone_limit real= 247 fixture= 114
real by date: {'2026-07-23': 9, '2026-07-24': 159, '2026-07-28': 78, '2026-07-31': 1}
by UTC hour:  07-23 h06=9 · 07-24 h10=120 h12=39 · 07-28 h06=78 · 07-31 h13=1
```

Every one of the 247 is **outside RTH** (06:00 / 10:00 / 12:00 / 13:00 UTC =
02:00 / 06:00 / 08:00 / 09:00 ET), and every one is the *age* branch, not the
drift branch:

```
2026-07-23T06:49:53Z CONFLUENCE_RI_ZLR SHORT 7589.5
  'signal age 566994s > max 180s (bar_ts=2026-07-16 17:20:00)'
```

566,994 seconds = **6.5 days**. These are backend-restart / hydration replays of
week-old signals. The gate has never once blocked a live in-session signal —
it exists to stop a stale signal firing at a price that no longer exists, and
that is exactly what it did.

**Verdict: `zone_limit_late_entry` stays strict, no exemption, no discussion.**
NET impact of exempting it on trend days = **$0 on n=0**; on rotation days
**$0 on n=0**. Exempting it would only re-open the 6.5-day-stale-signal path,
which is a pure risk add with a measured zero upside. *(If a leg exemption were
ever wired here it would also have to be leg-*and*-freshness aware, since
`_live_leg` reads "today's" bars — on a stale signal the leg it evaluates has
nothing to do with the signal.)*

---

## 3. Re-verification of the four gates that are already leg-exempt

```
[TREND]    extreme_chase_guard: n=10 with_leg=4 | CUR seq=$117.50 (n=1,w=1) per-signal=$365.00 | no-leg per-signal=$1022.50 (n=6) || WITH-DISP n=10 seq=$327.50 (n=2,w=2)
[ROTATION] extreme_chase_guard: n=3  with_leg=3 | CUR seq=$-105.00 (n=1,w=0) per-signal=$-315.00
[TREND]    lsma_flat:           n=10 with_leg=0 | CUR seq=$0.00              | no-leg per-signal=$257.50 (n=10) || WITH-DISP n=7 seq=$162.50 (n=3,w=2)
[ROTATION] lsma_flat:           n=8  with_leg=0 | CUR seq=$0.00              | no-leg per-signal=$-327.50 (n=8)
[TREND]    cont_trend_filter:   n=3  with_leg=0 | CUR seq=$0.00
[TREND]    location_gate:       n=2  with_leg=0 | CUR seq=$0.00
[ZL_COHORT]cont_trend_filter:   n=27 with_leg=4 | CUR seq=$445.00 (n=2,w=2)  | STEP seq=$580.00
[ZL_COHORT]location_gate:       n=12 with_leg=3 | CUR seq=$110.00 (n=2,w=2)  | STEP seq=$246.57
```

| gate | verdict | evidence |
|---|---|---|
| `cont_trend_filter` | **exemption was RIGHT — keep** | no with-leg signal on the six August days, but **+$445 sequential, 2/2 winners** on the ZL cohort where it did fire. Correct call, thin on the study window. |
| `location_gate` | **exemption was RIGHT — keep** | same shape: **+$110 sequential, 2/2 winners**, ZL cohort. |
| `extreme_chase_guard` | **RIGHT on trend, WRONG on rotation** | trend with-leg: **+$117.50 seq / +$365 per-signal, 4 of 4 profitable.** Rotation with-leg: **−$105 seq / −$315 per-signal, 0 of 3 profitable** (all three 08-10 ZLR longs into a Neutral/Variation chop). The `_live_leg` bypass at `trading_gateway.py:1616` is **not day-type gated**; `TREND_LEG_CHASE_EXEMPT_V1` (the tip-revocation escape) *is*. That asymmetry is the −$315. |
| `lsma_flat` | **exemption is inert — harmless, but it does nothing** | **0 of 18** blocked signals on the six days were with-leg (1 of 12 on the ZL cohort). Structurally near-impossible: `detect_leg` demands a *strictly monotone* LSMA over 4 transitions, `lsma_flat` fires when \|slope\| < 0.25 pts/bar. `LEG_EXEMPT_LSMA_FLAT_V1=1` has essentially never fired. The 08-11 `lsma_flat` money (**+$257.50 per-signal over 6 no-leg blocks**, e.g. 18:10 INITIATIVE_SHORT +$117.50) needs the **displacement** qualifier: with-disp n=7 → **+$162.50 sequential, 2/3 winners.** |

**The critical structural finding.** On 08-11, **only 4 of 35** unique blocked
signals were with-leg — and none of the three largest MFE signals was. The
detector's stated reasons on the misses are `CCI not holding the side (2 bars
across zero)`, `structure N/2 swings, net=no`, `LSMA not one-directional`. On a
Trend_DD stair-step the CCI *does* cross zero on every pullback, and the
`LEG_CCI_DIP_TOLERANCE = 1` allows exactly one. **The leg detector, not the gate
list, is the binding constraint.** Widening the exemption *list* while the
*detector* stays this strict buys almost nothing.

Compare, sequentially, across every gate at once:

```
=== QUALIFIER TOTALS (sequential, one trade at a time) ===
  [TREND    ] ALL blocks  pool=61  | CUR seq n=12  net=$   552.50 w=7   | STEP seq net=$   549.14 w=6
  [TREND    ] with-LEG    pool=10  | CUR seq n=5   net=$   233.75 w=3   | STEP seq net=$   382.00 w=3
  [TREND    ] with-DISP   pool=41  | CUR seq n=11  net=$  1012.50 w=9   | STEP seq net=$   950.50 w=8
  [ROTATION ] ALL blocks  pool=110 | CUR seq n=16  net=$ -1105.00 w=5   | STEP seq net=$  -786.74 w=3
  [ROTATION ] with-LEG    pool=24  | CUR seq n=11  net=$  -880.00 w=2   | STEP seq net=$  -707.68 w=1
  [ROTATION ] with-DISP   pool=44  | CUR seq n=11  net=$  -588.75 w=4   | STEP seq net=$  -270.42 w=2
  [ZL_COHORT] with-LEG    pool=31  | CUR seq n=9   net=$   930.00 w=8   | STEP seq net=$   994.88 w=7
```

* **with-LEG** on trend days: +$233.75 over 5 trades (3 winners).
* **with-DISP** (`|session displacement| ≥ 10pt` and the trade agrees) on trend
  days: **+$1,012.50 over 11 trades, 9 winners** — 4.3× the leg qualifier, and
  it *separates the regimes correctly*: −$588.75 on rotation days, where taking
  everything would have been −$1,105.
* Both qualifiers are strongly negative on rotation days. **Any exemption must
  be day-type/displacement gated. An unconditional leg exemption is a
  rotation-day tax.**

---

## 4. THE STOP PROBLEM — step-scaled sizing beats current sizing in every cohort

Michael's diagnosis was right and the data confirms it: with `step ≈ 10.4pt` on
the trend days and a structural R of 10–15pt, T1 = 1R sits **beyond the next
step** and nothing banks. Today's per-day sequential result on all blocks is
+$277.50 with 4 of 6 winners — but the winners are all C1-at-3pt scraps.

```
=== STOP/TARGET SIZING — CURRENT vs STEP (zigzag thr=6.0) ===
  CURRENT = stop 8pt, C1 +3pt / C2 1R / C3 2R / C4 4R runner, BE after 1R
  STEP    = stop max(4, 0.6*step), targets 0.5/1.0/1.5*step, C4 runner
  [TREND    ] with-leg n=10  step_med=10.38 | CUR seq=$  233.75 (n=5,w=3) | STEP seq=$  382.00 (n=5,w=3)
  [ROTATION ] with-leg n=24  step_med=11.00 | CUR seq=$ -880.00 (n=11,w=2)| STEP seq=$ -707.68 (n=11,w=1)
  [ZL_COHORT] with-leg n=31  step_med=15.12 | CUR seq=$  930.00 (n=9,w=8) | STEP seq=$  994.88 (n=9,w=7)
```

| cohort | CURRENT (seq) | STEP (seq) | delta |
|---|---|---|---|
| TREND, with-leg | +$233.75 | **+$382.00** | **+$148.25 (+63%)** |
| ROTATION, with-leg | −$880.00 | **−$707.68** | +$172.32 (still a loss) |
| ZL_COHORT, with-leg | +$930.00 | **+$994.88** | +$64.88 |
| ROTATION, all blocks | −$1,105.00 | **−$786.74** | +$318.26 |
| TREND, with-disp | +$1,012.50 | +$950.50 | −$62.00 |

Sensitivity to the step estimator (zigzag reversal threshold):

| zigzag thr | trend step_med | TREND with-leg CUR | TREND with-leg STEP |
|---|---|---|---|
| 3.0pt | 6.69 | +$233.75 | +$280.94 |
| 6.0pt | 10.38 | +$233.75 | **+$382.00** |

**STEP wins at both estimators and in 4 of the 5 slices, and it wins under a
simulation rule (stop-before-target inside the bar) that is deliberately unfair
to the tighter stop.** The one slice it loses (trend / with-disp) is the slice
with the widest entries, where the fixed 4R runner outruns a 3×step runner.

**Conclusion for the sizing question:** the stop is a *bigger* lever than any
exemption. On the trend days the exemption debate is worth $233 → $382; getting
the ladder onto the step is worth more than the whole `awaiting_release`
question, and it is regime-neutral (it improves rotation days too, where it
turns −$1,105 into −$787).

---

## 5. RANKED RECOMMENDATIONS

Ordered by ($ evidence × confidence) ÷ risk. Every one is a *proposal* — nothing
was enabled by this agent.

### 🥇 R1 — lower the release-gate trend bypass: `RELEASE_TREND_BYPASS_PTS` 15 → **12**
* **$:** +$211.25 (trend, n=1 trade / 2 signals released) **and** +$202.50
  (rotation, n=2 trades, 2 winners). Positive in both regimes; the only
  threshold in the sweep that is.
* **Change:** add `RELEASE_TREND_BYPASS_PTS=12` to `.env` (today the var is
  **absent** → the code default of 15 is live, `release_gate.py:209`). Backend
  restart required.
* **Risk:** parameter tightening of a bypass Michael already ruled on 07-29 —
  under the "code that implements an existing ruling" clause this is a
  parameter, not a new behavior. It can only *release* with-move entries; the
  counter-move path is untouched.
* ⚠️ **THIN — n=3 released signals total.** Recommend enabling and reviewing after
  5 sessions, not treating +$413 as a forecast.

### 🥈 R2 — step-scaled ladder (the stop problem) → build behind a flag, replay before enabling
* **$:** +$148.25 on trend with-leg (+63%), +$318 on the rotation all-blocks
  pool, +$65 on the ZL cohort. **Best regime-neutral lever in the report.**
* **Change:** new flag (proposed) `STEP_SCALED_LADDER_V1`, default OFF; stop =
  `max(4pt, 0.6 × median_step)`, targets `0.5 / 1.0 / 1.5 × step`, C4 runner,
  BE after the 1.0× leg. Config home: `config/stop_params.yaml` +
  `config/targets.yaml` (both are Michael-approval surfaces).
* **Risk:** touches every trade's risk surface → **strategic stop, needs a
  written ruling**, plus a full replay + sim day before live. This is the
  live-forensic **B1** item and it is confirmed here with numbers.

### 🥉 R3 — day-type-gate the chase guard's plain leg bypass
* **$:** stops the −$105 seq / −$315 per-signal (0 of 3 winners) that the
  unconditional `_live_leg` bypass at `trading_gateway.py:1616` cost on 08-10,
  while keeping the +$117.50 / +$365 (4 of 4 winners) it earned on 08-11.
* **Change:** apply the same `day_type.startswith(("Trend","Variation"))`
  condition that `TREND_LEG_CHASE_EXEMPT_V1` already uses, to the plain
  `_live_leg(direction)` bypass one block above it. Proposed flag
  `EXTREME_CHASE_LEG_BYPASS_TREND_ONLY_V1`, default OFF.
* ⚠️ **THIN — n=3 rotation signals.** But the sign is unambiguous (0 winners)
  and it is a *narrowing*, i.e. risk-reducing.

### 4 — `daytype_playbook`: the leg-exemption candidate that actually has evidence
* **Not part of tonight's question, surfaced by the sweep.** This gate has **no
  leg exemption today** (`trading_gateway.py:1169-1173`: opening-window override
  and a low-confidence degrade only).
* **$:** TREND with-leg **+$276.25 seq (n=3, 2 winners)** · ZL_COHORT with-leg
  **+$832.50 seq (n=4, 4 winners)** · ROTATION with-leg −$85.00 (n=3, 1 winner).
  Positive in 2 of 3 cohorts, +$1,023 combined, and its no-leg half is
  −$195 / −$1,305 per-signal — i.e. the leg dimension **separates** this gate's
  good blocks from its bad ones better than anywhere else in the data.
* **Change:** proposed `LEG_EXEMPT_DAYTYPE_PLAYBOOK_V1`, default OFF, gated on
  day_type ∈ {Trend*, Variation}. Needs one written ruling (new behavior).
* ⚠️ **THIN per cohort (n=4 / n=6 / n=5), n=15 combined.**

### 5 — leg detector calibration is the real ceiling (diagnosis, no change tonight)
* Only **4 of 35** 08-11 blocks were with-leg. Misses were rejected for
  `CCI not holding the side (2 bars across zero)` and `structure net=no` — on a
  stair-step down-leg the CCI crosses zero on every pullback and
  `LEG_CCI_DIP_TOLERANCE = 1` (`leg_state.py:40`, a module constant, not an env)
  allows exactly one.
* **Proposal:** make the three constants env-tunable, then replay
  `LEG_CCI_DIP_TOLERANCE ∈ {1,2}` before touching any gate list. **Do not tune
  and enable in one step** — a looser detector widens *four* live exemptions at
  once.

### ❌ R6 — `awaiting_release`: **DO NOT leg-exempt.** $0 on n=0 (trend), −$122.50 on n=5 (rotation). No env change.
### ❌ R7 — `zone_limit_late_entry`: **DO NOT leg-exempt.** 0 real RTH blocks in the entire decision log; all 247 real blocks are ≥6-day-stale restart replays. No env change.
### ⚪ R8 — `LEG_EXEMPT_LSMA_FLAT_V1`: leave as is, but know it is **inert** (0 of 18 with-leg). The `lsma_flat` money needs the displacement qualifier (+$162.50 seq on trend), not the leg one. No change tonight.
### ⚪ R9 — `cont_trend_filter` / `location_gate` exemptions: **confirmed correct**, keep (+$445 and +$110 sequential, 4 of 4 winners combined, ZL cohort). No change.

---

## 6. Evidence-strength ledger (Pre-LIVE Rule 5 — what is thin, stated plainly)

| claim | n (trades) | strength |
|---|---|---|
| `zone_limit_late_entry` has no real RTH block | 247 real blocks examined, 0 in RTH | **strong** (census of the whole log) |
| `awaiting_release` leg exemption ≈ $0 on trend days | 8 signals, 0 with-leg | **strong** for "no effect", **thin** for "$" |
| `awaiting_release` leg exemption loses on rotation | 5 trades | thin, but sign is consistent (2 of 5 winners) |
| bypass threshold 12 beats 15 | 3 trades | ⚠️ **thin** |
| chase exemption right on trend / wrong on rotation | 1 + 1 trades, 4 + 3 signals | ⚠️ **thin**, sign unambiguous (4/4 vs 0/3) |
| `lsma_flat` leg exemption is inert | 18 signals, 0 with-leg | **strong** (structural, not statistical) |
| STEP sizing beats CURRENT | 25 trades across 3 cohorts | **moderate** — wins in 4 of 5 slices |
| `daytype_playbook` leg exemption is positive | 10 trades (3+4+3) | ⚠️ **thin** |
| with-DISP beats with-LEG on trend days | 11 vs 5 trades | **moderate** (9 of 11 winners) |

**Not verified / out of scope:** the real per-trade stop the system would have
used (the jsonl carries none — an 8pt fallback was used); anything beyond the
12-bar horizon; slippage; commission (a $1.50/contract round turn = $6/trade
would move the sequential numbers by roughly −$30 to −$70 per cohort and does
not flip any sign except R1's rotation leg); the 08-03 pre-market block cluster
(105 of 106 `awaiting_release` rows that day were at 06:00 UTC and are excluded
as non-RTH).

**Artifacts:** `scripts/leg_exemption_replay.py` (this replay, read-only) ·
raw run output reproducible with the command in §0.
