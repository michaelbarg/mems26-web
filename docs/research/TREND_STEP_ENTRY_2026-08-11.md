# TREND_STEP_ENTRY_V1 — catching a stair-step trend from the FIRST step

**Agent:** `step-entry-agent` · **Written:** 2026-08-11 (post-session)
**Mode:** STRICTLY READ-ONLY — no flag enabled/disabled in the running backend, no restart,
no writes to `~/SierraChart_Data`, no DB writes. Only `v9_bars_5min_woodies` was read.
**Script:** `scripts/replay_trend_step_entry.py` (new, read-only)
**Michael's ask:** *"אם היינו תופסים את השורט בהתחלה היינו עושים כסף טוב."*

---

## 0. Bottom line — read the second row too

| Window | sessions | NET (gross) | after commission | n | win | avg/trade |
|--------|----------|-------------|------------------|---|-----|-----------|
| **Design window** 07-15 → 08-11 | 20 | **+$2,483.75** | +$2,303.75 | 30 | 50 % | +$76.79 |
| **TRUE out-of-sample** 06-05 → 07-14 | 29 | **+$345.00** | **+$129.00** | 36 | 36 % | **+$3.58** |
| **Combined** 06-05 → 08-11 | **48** | **+$2,915.00** | **+$2,525.00** | 65 | 43 % | **+$38.85** |

Commission = 4 contracts × $1.50 round-turn (same constant as `scripts/leg_exemption_replay.py`).

**The requested 15-session answer (07-15…08-11) is +$2,483.75. It is also the window the
parameters were chosen on, and it does not replicate.** After the design was frozen I found
29 more full RTH sessions in the DB (2026-06-05 → 07-14 — the table goes back further than
I first assumed) and ran them untouched. Out-of-sample the strategy is **+$3.58 per trade
after costs**, i.e. statistically indistinguishable from zero, and it dies under 2 ticks of
adverse fill (−$67.50).

| Focus day | Result |
|-----------|--------|
| **08-11** (the stair-step down day) | **+$255.00** — one SHORT, 11:25 ET @ 7769.50, full ladder `T0+T1+T2+T3`, MFE +30.25 / MAE −1.75 |
| **08-03 / 08-04** (trend up) | **+$400.00 / +$620.00** |
| **08-06 / 08-07 / 08-10** (rotation control) | −$153.75 / +$100.00 / $0.00 → **−$53.75** total |

**Head-to-head, all 48 sessions, identical 4-contract execution model:**

| Detector | NET | n | win | avg/trade |
|----------|-----|---|-----|-----------|
| `HIGHER_LOW_SECOND_TEST_V1` | **−$2,167.50** | 146 | 36 % | −$14.85 |
| `RE_PULLBACK_ENTRY_V1` | **−$457.45** | 54 | 41 % | −$8.47 |
| **`TREND_STEP_ENTRY_V1`** | **+$2,915.00** | 65 | 43 % | **+$44.85** |

### Verdict

**GO — to build the module + tests, flag-OFF, and run it SHADOW-only.**
**NO-GO — to a live enable, to any gateway/chase-guard change, and to treating
+$2,483.75 as the expected return.** The honest expectation from all 48 sessions is
**≈ +$39/trade after costs, with a −$1,068.75 max drawdown**, and the out-of-sample half of
that sample says ≈ $0. What is validated is the *anatomy* (§1, n = 1,297 steps, every
gradient replicates) and the *ranking* against the two prior attempts. What is **not**
validated is the calibration (§4).

Reproduce:
```
python3 scripts/replay_trend_step_entry.py --trades --validate --compare      # design window
python3 scripts/replay_trend_step_entry.py --since 2026-06-01 --until 2026-07-15 --validate --sweep
python3 scripts/replay_trend_step_entry.py --since 2026-06-01 --until 2026-08-12 --validate --compare
python3 scripts/replay_trend_step_entry.py --since 2026-06-01 --until 2026-08-12 --anatomy
```

---

## 1. Anatomy of a step — this part IS solid

Segmentation: offline ZigZag, 5.00 pt reversal threshold, RTH 09:30–16:15 ET.
Every `impulse → pause → next impulse` triple measured — **1,297 records over 48 sessions.**
"beat" = the next same-direction leg took out the impulse extreme (i.e. the staircase held).

### 1.1 Population

| Metric | p25 | median | p75 | p90 |
|--------|-----|--------|-----|-----|
| Impulse size (pt) | 8.75 | **13.25** | 20.50 | 30.25 |
| Pause length (bars) | 1 | **2** | 3 | 5 |
| Pause depth (% of impulse) | 64 % | **98 %** | 147 % | — |
| Continuation of the next leg (pt) | 8.50 | **12.75** | 19.75 | — |

The median step is **13 pt of impulse, a 2-bar pause, a 12.75 pt continuation.**
Unconditionally `P(beat) = 46 %` — a coin flip. The edge is entirely in *which* pause.

### 1.2 What separates a pause from a reversal

**Pause depth (retrace / impulse) — the dominant variable:**

| Retrace | n | P(beat) | median continuation |
|---------|---|---------|--------------------|
| 0–20 % | 12 | 92 % | 26.00 |
| 20–35 % | 52 | **73 %** | 11.75 |
| 35–50 % | 133 | **68 %** | 12.75 |
| 50–65 % | 137 | 55 % | 13.25 |
| 65–80 % | 141 | 60 % | 13.00 |
| 80–100 % | 176 | 61 % | 14.00 |
| **>100 %** | 646 | **31 %** | 12.25 |

A retrace past 100 % is not a pause — it is the other side taking control. Half the
population sits there, which is why the unconditional number is a coin flip.

**Pause length — the cleanest gradient in the whole dataset (monotone, n=1,297):**

| Pause bars | n | P(beat) |
|------------|---|---------|
| 1 | 514 | **63 %** |
| 2 | 317 | 50 % |
| 3 | 192 | 35 % |
| 4–5 | 173 | 27 % |
| ≥6 | 101 | **12 %** |

A step that pauses for half an hour is finished.

**Pause volume vs impulse volume:**

| pause / impulse volume | n | P(beat) |
|------------------------|---|---------|
| < 0.60 | 80 | 55 % |
| 0.60–0.85 | 395 | 54 % |
| 0.85–1.10 | 406 | 49 % |
| **> 1.10** | 415 | **37 %** |

A quiet pullback continues; a loud one is distribution.

**LSMA position at the pause end:** pause that did NOT push through the LSMA → 58 % beat;
pause that did → 41 %. Real but weak, and it costs trades in both windows, so it is a
default-off filter in V1.

**Impulse size is nearly uninformative** (44–51 % across every bucket) and **CCI at the pause
end is unusable** — on a stair-step, CCI crosses zero on every single pause. This is the same
root cause the `leg-exemption-agent` found in `LEG_CCI_DIP_TOLERANCE`
(LIVE_CHANNEL 2026-08-11 22:40 §4), reached here independently from bar geometry.

**All four gradients above are essentially identical on the 20-session design window and on
the 48-session superset.** The anatomy is the durable finding in this report.

### 1.3 The objectively repeatable entry window

> **Bar 1–3 of the pause, after 20–55 % of the impulse has been given back, while pause
> volume is at or below impulse volume.**

Before that window you are at the tip of the move — which is exactly what
`extreme_chase_guard` correctly refuses. After it, the step is dead.

### 1.4 The three focus days

**2026-08-11 — stair-step DOWN.** Every down-step with `pause ≤ 3 bars` and
`retrace 34–65 %` continued, without exception:

| Impulse | pt | pause bars | retrace | continued? |
|---------|----|-----------|---------|-----------|
| 10:50 → 11:15 | 18.75 | 1 | **34.7 %** | ✅ +11.50 |
| 11:20 → 11:35 | 11.50 | 8 | 65.2 % | ✅ +11.00 |
| 12:15 → 12:25 | 11.00 | 2 | **56.8 %** | ✅ +17.50 |
| 12:35 → 13:15 | 17.50 | 6 | 64.3 % | ✅ +19.75 |
| 13:45 → 14:25 | 19.75 | 2 | 43.0 % | ❌ (day ended) |

(The forensic's IL clock = ET + 7 h; these are the same four steps as
`LIVE_FORENSIC_2026-08-11.md` §2.1.)

**2026-08-03 / 08-04 — trend UP.** The same shape, mirrored: every up-leg pause with
retrace 20–57 % and pause ≤ 2 bars continued — 08-03 at 09:30/09:40/10:05/10:30/10:45,
08-04 at 09:30/09:55/10:20/11:05/11:30. The counter-legs (retrace 150–330 %) never did.
⚠️ **08-04 bars stop at 12:50 ET in the DB** — that session is only two-thirds present.

---

## 2. The detector — TREND_STEP_ENTRY_V1

Causal: at every closed 5-min bar `i` only `bars[0..i]` is read. Described for SHORT;
LONG is the exact mirror.

### 2.1 Step identification

Run a ZigZag (`ZZ_REV = 5.0 pt`) over `bars[0..i]`. Take the most recent swing **low** pivot
`ext` and the swing **high** `org` immediately before it. `impulse = org.price − ext.price`.

### 2.2 Entry trigger (all must hold on the closed bar `i`)

| # | Condition | Default |
|---|-----------|---------|
| 1 | `IMP_MIN ≤ impulse ≤ IMP_MAX` | 8.0 … 45.0 pt |
| 2 | impulse took `≤ IMP_BARS_MAX` bars | 10 |
| 3 | `PAUSE_MIN ≤ (i − ext.idx) ≤ PAUSE_MAX` | 1 … 3 bars |
| 4 | `RETR_MIN ≤ (pause_high − ext) / impulse ≤ RETR_MAX` | **0.20 … 0.55** |
| 5 | LSMA slope over the last 3 bars `< −LSMA_SLOPE_MIN` | 0.15 pt/bar |
| 6 | mean pause volume / mean impulse volume `≤ VOL_RATIO_MAX` | 1.10 |
| 7 | **the step extreme IS the session extreme** (`ext ≤ session_low + SESSION_EXT_TOL`) | 0.0 pt |
| 8 | bar time `≤ CUTOFF` | 15:00 ET |
| 9 | this `step_id` has not been traded yet; no position open | — |

**Entry = the close of bar `i`.** No break, no confirmation bar — the entry is *inside the
pause*, which is the whole point.

Condition 7 deserves emphasis: **it is the exact inverse of `extreme_chase_guard`.** On a
stair-step day the step that matters is the one that just made the session extreme;
proximity to the session low IS the setup, not the danger. The forensic reached the same
conclusion from the block log (§3.1); this derives it independently from bar geometry.
⚠️ But see §4.3 — this filter's measured benefit is **$/trade, not NET**, and it is
*negative* for NET out-of-sample.

### 2.3 Invalidation (no entry / abandon the step)

- retrace > `RETR_MAX` → the pause has become a reversal;
- pause longer than `PAUSE_MAX` bars → the step is dead;
- pause volume above impulse volume → distribution, not rest;
- price closes beyond `org` (the impulse origin) → the leg is gone;
- a new session extreme forms → that is a **new** step with its own single entry.

### 2.4 Stop — leg-relative, never a fixed R

```
stop = pause_extreme + max(2 ticks, STOP_BUF_FRAC × impulse)      # STOP_BUF_FRAC = 0.10
risk = clamp(stop − entry, STOP_MIN = 2.5 pt, STOP_MAX = 9.0 pt)
```

Measured over 65 trades: **mean R = 5.72 pt**, range 2.50 – 9.00. Compare with the live
`STOP_STRUCTURE_EXTREME` behaviour on 08-11, which produced **R = 9.75 – 15.00 pt on an
11-point step** and made T1 structurally unreachable (forensic §2.4(i)). Anchoring the stop
to the *pause* instead of to a 12-bar structure window is half of the fix.

### 2.5 Targets — sized to the measured step distribution

```
T0 = entry − 3.00 pt                 # C1, fixed (matches the live execution model)
T1 = entry − 0.45 × impulse          # C2
T2 = entry − 0.80 × impulse          # C3
T3 = entry − 1.30 × impulse          # C4
```
Ladder forced strictly monotone (≥ 0.5 pt apart). For the median 13 pt step that is
3.0 / 5.9 / 10.6 / 17.2 pt, against a measured median continuation of 12.75 pt from the
pause end. T3 is deliberately the tail target: 15 of 65 trades reached it and they carry
the entire P&L.

---

## 3. Backtest

Execution model: **4 contracts · $5/pt · C1→T0, C2→T1, C3→T2, C4→T3 · stop→BE after T1 ·
one entry per step · no re-entry on a stopped step · no overlapping positions · MTM at the
last RTH bar.** Conservative tie-break: within a bar the **stop fills before the target**.

### 3.1 Design window, per-day (07-15 → 08-11, the 15 trading sessions requested)

| Date | n | Net | Outcomes |
|------|---|-----|----------|
| 2026-07-15 | 1 | −$86.25 | `T0+STOP` |
| 2026-07-16 | 3 | +$223.75 | `T0+STOP`, `T0+T1+BE`, `T0+T1+T2+T3` |
| 2026-07-17 | 0 | $0.00 | — |
| 2026-07-20 | 2 | +$43.75 | `T0+STOP`, `T0+T1+T2+BE` |
| 2026-07-21 | 2 | −$8.75 | `STOP`, `T0+T1+BE` |
| 2026-07-22 | 1 | +$68.75 | `T0+T1+BE` |
| 2026-07-23 | 2 | +$16.25 | `T0+STOP`, `T0+T1+T2+BE` |
| 2026-07-24 | 1 | −$60.00 | `T0+STOP` |
| 2026-07-27 | 3 | +$242.50 | `T0+T1+T2+T3`, `T0+STOP`, `T0+STOP` |
| 2026-07-28 | 1 | −$50.00 | `STOP` |
| 2026-07-29 | 1 | **+$512.50** | `T0+T1+T2+T3` |
| 2026-07-30 | 2 | +$236.25 | `T0+STOP`, `T0+T1+T2+T3` |
| 2026-07-31 | 1 | −$90.00 | `STOP` |
| 2026-08-03 | 1 | **+$400.00** | `T0+T1+T2+T3` |
| 2026-08-04 | 2 | **+$620.00** | `T0+T1+T2+T3` ×2 |
| 2026-08-05 | 2 | +$213.75 | `T0+T1+T2+T3`, `STOP` |
| 2026-08-06 | 3 | **−$153.75** | `T0+STOP` ×3 |
| 2026-08-07 | 1 | +$100.00 | `T0+T1+BE` |
| 2026-08-10 | 0 | **$0.00** | — |
| 2026-08-11 | 1 | **+$255.00** | `T0+T1+T2+T3` |
| **TOTAL** | **30** | **+$2,483.75** | win 50 % |

### 3.2 Out-of-sample, per-day (06-05 → 07-14 — parameters never saw these bars)

| Date | n | Net | | Date | n | Net |
|------|---|-----|-|------|---|-----|
| 06-05 | 3 | **+$1,335.00** | | 07-01 | 1 | +$70.00 |
| 06-08 | 1 | −$63.75 | | 07-02 | 3 | +$326.25 |
| 06-09 | 1 | −$75.00 | | 07-03 | 2 | −$102.50 |
| 06-12 | 1 | −$180.00 | | 07-06 | 4 | **−$360.00** |
| 06-15 | 1 | +$126.25 | | 07-07 | 1 | −$120.00 |
| 06-16 | 1 | −$60.00 | | 07-08 | 2 | +$47.50 |
| 06-17 | 2 | −$285.00 | | 07-09 | 4 | −$111.25 |
| 06-22 | 1 | −$165.00 | | 07-10 | 2 | +$30.00 |
| 06-24 | 1 | −$75.00 | | 07-14 | 1 | −$97.50 |
| 06-29 | 1 | +$68.75 | | | | |
| 06-30 | 2 | +$122.50 | | **TOTAL** | **36** | **+$345.00** |

**Remove 06-05 and the out-of-sample window is −$990.** That is the honest statement.

### 3.3 The answers Michael asked for

- **08-11 (stair-step down): +$255.00.** One SHORT, **11:25 ET @ 7769.50**, stop 7776.00
  (R = 6.38 pt), impulse 18.75 pt, retrace 35 %, pause 2 bars. Full ladder, MFE +30.25 pt,
  **MAE −1.75 pt**. This is the **first step of the actual staircase** (the 10:50 → 11:15 leg).
  It is also the *same price* as the `REACTIVE_SHORT` the live system generated at 18:30 IL
  and then blocked with `extreme_chase_guard` (forensic §2.3: MFE +12.00 / MAE −0.50).
  Only one trade fires that day because the position stayed open through T3 until ~14:20 ET —
  it captured the whole staircase in one position.
- **08-03: +$400.00** (one long, 10:05, full ladder). **08-04: +$620.00** (two longs, 09:55
  and 11:30, both full ladder — on two-thirds of a session).
- **Rotation control: 08-06 −$153.75 · 08-07 +$100.00 · 08-10 $0.00 → −$53.75 over three
  sessions**, from only 4 signals. It barely trades there, which is the behaviour we want.

### 3.4 Trend vs rotation, all 48 sessions

Days labelled from the tape itself (`|close − open| / RTH range`), not from
`v9_day_type_history` (unreliable here — it labels 08-11 `Variation` with confidence 0).

| Day character | sessions | n | NET | win | per session |
|---------------|----------|---|-----|-----|-------------|
| TREND (ratio ≥ 0.55) | 19 | 34 | **+$3,515.00** | 53 % | **+$185.00** |
| SEMI (0.30–0.55) | 12 | 13 | −$360.00 | 31 % | −$30.00 |
| ROTATION (< 0.30) | 17 | 18 | −$240.00 | 33 % | **−$14.12** |

**This is the thesis, and it does replicate:** +$275/trend-session in the design window,
+$85/trend-session out-of-sample, +$185 combined; rotation costs −$38 / −$8 / −$14 per
session respectively. No day-type input is used anywhere in the detector — the geometry
filters do the regime selection by themselves.

### 3.5 Payoff structure (48 sessions)

| Outcome | n | Net |
|---------|---|-----|
| `T0+T1+T2+T3` | 15 | **+$5,013.75** |
| `T0+T1+T2+BE` | 4 | +$467.50 |
| `T0+T1+BE` | 9 | +$661.25 |
| `T0+STOP` | 19 | −$1,342.50 |
| `STOP` | 18 | −$1,885.00 |

Median trade **−$41.25**. Explicitly right-tailed: 15 full-ladder runners carry everything.
Anyone tempted to raise the win rate by cutting T3 destroys it (`T3_FRAC=1.0` → −$240 in-sample,
−$192 out-of-sample).

---

## 4. Is it real, or is it fitted? — the honest section

### 4.1 In-sample robustness (looks great)

| Check | Result |
|-------|--------|
| First half 07-15…07-28 / second half 07-29…08-11 | +$390.00 (n=16) / +$2,093.75 (n=14) |
| Drop the 1 / 3 / 5 best trades | +$1,971 / +$1,165 / **+$490** — still positive |
| Max drawdown | −$288.75 |
| Adverse slippage 1 / 2 / 4 ticks | +$2,430 / +$2,120 / **+$1,928.75** |
| One-knob sweep | **every** parameter profitable across its whole range (+$1,929 … +$2,784) |

### 4.2 Out-of-sample (does not hold up)

| Check | Result |
|-------|--------|
| NET / after commission | +$345.00 / **+$129.00** on 36 trades |
| Drop the 1 best trade | **−$215.00** |
| Max drawdown | **−$990.00** (3.4× the in-sample figure) |
| Profitable sessions | 8 of 21 |
| Adverse slippage 1 / 2 / 4 ticks | +$85.00 / **−$67.50** / **−$498.75** |
| Direction split | LONG −$1,245.00 (n=26, 27 %) · SHORT +$1,590.00 (n=10, 60 %) |

**Two ticks of adverse fill turns the out-of-sample edge negative.** The live measurement is
a median 5.0 s from bar close to gateway decision (forensic §4), so 1–2 ticks is the realistic
assumption, not a stress case.

### 4.3 Which parameter choices disagree between the two windows

| Knob | design window | out-of-sample | verdict |
|------|---------------|---------------|---------|
| `REQUIRE_STAIR=1` | +$885 (hurts) | **+$1,013.75 (helps)** | contradictory → noise |
| `CUTOFF=14:00` | +$2,483 (helps) | **−$286.25 (hurts)** | contradictory → noise |
| `SESSION_EXT_TOL` off | +$2,517 (~flat) | **+$841.25 (helps a lot)** | filter is not NET-accretive |
| `T3_FRAC=1.8` | −$113 | −$507 | agrees (bad) |
| `RETR_MIN=0.3` | −$294 | −$662 | agrees (bad) |
| `IMP_MIN=12` | flat | −$404 | agrees (bad) |
| `REQUIRE_LSMA_SIDE=1` | −$255 | −$331 | agrees (bad) |
| `REQUIRE_EXHAUST=1` | −$1,669 | −$271 | agrees (bad) |
| `BE_AFTER_T1=1` | +$250 | +$230 | agrees (good) |

Roughly half the knobs agree and half contradict. `RETR_MAX = 0.55`, `CUTOFF = 15:00` and
`SESSION_EXT_TOL = 0` were all picked on the design window and **none of the three is
supported out-of-sample.** The structural choices (enter in the pause, leg-relative
stop/ladder, BE after T1, no confirmation bar) **are** supported in both.

### 4.4 The other things I do not like

1. **65 trades over 48 sessions.** Two-thirds of the P&L is 15 trades.
2. **LONG is dead flat over the full sample** (−$107.50 on 39 trades) while SHORT is
   +$3,022.50 on 26. Over 48 sessions in a net-rising market, that asymmetry is not
   explainable from the anatomy, and I will not ship a short-only variant on it — that
   would be fitting a coin flip.
3. **08-04 is two-thirds of a session** (bars end 12:50 ET); 07-15/16/22 are truncated too.
4. **The "15 sessions" the task asked for are the design window itself**, so that number
   carries no evidential weight on its own. The 48-session figure is the one to quote.
5. No true walk-forward is possible — 48 sessions is the entire usable
   `v9_bars_5min_woodies` RTH history. The table does hold scattered rows back to 2024-06,
   but every pre-June-2026 date has 1–27 bars total and not one complete RTH session
   (verified: `SELECT date_trunc('month',ts …) GROUP BY 1` → 2024-06: 1 bar · 2025-05: 27 ·
   2026-05: 55 across 5 dates).

---

## 5. Versus the two previous failures — what is actually different

All three re-run on the identical 48 sessions with the identical 4-contract model
(`--compare`): HLST **−$2,167.50** (n=146) · RE_PULLBACK **−$457.45** (n=54) ·
TREND_STEP **+$2,915.00** (n=65). The ranking is stable on the design window alone too.

### 5.1 `HIGHER_LOW_SECOND_TEST_V1` — a reversal pattern wearing a trend costume

HLST waits for **push → first pullback → second, higher pullback low.** By construction it
requires the *second* test, so it can only fire once the step has already stalled twice —
i.e. in the 65–100 % retrace bucket (60 % beat) or past it (31 %). Its structural anchor
`L2` sits at the deepest point of the retracement, so its stop is on the wrong side of the
noise. It is structurally a bottom-fishing pattern. −$1,822 raw then, −$2,167.50 here.

### 5.2 `RE_PULLBACK_ENTRY_V1` — right idea, wrong anchor

C2 anchors everything to a **broken IB edge** — a *daily* level, while the staircase is a
*local* structure. On 08-11 the IB edges were 7767.50 / 7792.50 and the entire 12:00–15:55
staircase happened **below** the IB, so there was nothing to retest for four hours. It also
needs `ib_locked` from the Sierra TPO export, so it cannot fire before 10:30 at all. It is
not wrong — it is blind to steps 2..n.

### 5.3 What TREND_STEP does differently

1. **The reference frame is the step**, not the session and not the IB. Stop, T1, T2, T3 are
   all fractions of *this step's* impulse. A 13 pt step gets a ~4 pt stop and a 17 pt T3.
   Nothing is a fixed R and nothing is a daily level.
2. **It enters in the pause, deliberately next to the session extreme** — filter 7 requires
   what `extreme_chase_guard` forbids. This is the single largest behavioural difference from
   anything in the system today, and it is what Michael actually asked for.
3. **It has explicit, measured death conditions for the step** (retrace, pause length, pause
   volume), each a 20–30 point drop in P(beat) on n=1,297 — not invented rules.
4. **It requires no confirmation.** Both "wait for proof" variants collapse in *both* windows:
   requiring an exhaustion bar → +$815/n=8 in-sample, +$74/n=13 OOS; requiring a confirmed
   staircase → +$885 in-sample. Waiting is what makes you late, and late is precisely the
   failure mode of the 34 blocked signals on 08-11.

### 5.4 Where it is NOT new — stated plainly

The leg-relative stop/target ladder is the same `STEP_SCALED_LADDER_V1` the
`leg-exemption-agent` reached from the opposite direction (LIVE_CHANNEL 2026-08-11 22:40 §6:
median trend-day step 10.38 pt, `stop = max(4, 0.6 × step)`, targets 0.5/1.0/1.5 × step,
+63 % on trend days). Two independent analyses converged on it. **The ladder is not this
report's contribution — the entry is.** If only one thing ships, ship the ladder: it is
regime-neutral, it helps every existing pattern, and it does not depend on the calibration
this report failed to validate.

**And the part that IS the same idea repackaged:** like HLST and RE_PULLBACK, this is still
"buy the pullback in a trend". The three differ only in *where* the reference frame is
anchored (second test / IB edge / current step). TREND_STEP wins the head-to-head by a wide
margin and the anatomy explains why — but it is an improvement in framing, not a new
mechanism, and its out-of-sample result is thin enough that this must be said out loud.

---

## 6. Implementation plan (build it — flag-OFF, SHADOW-first)

### 6.1 Module

`backend/v9/systems/five_min/patterns/trend_step_entry.py`

```python
def detect_trend_step_entry(bars, *, session_bars=None) -> Tuple[Optional[Direction], float, Dict]
```
Pure, stateless, causal. `info` carries `kind="TREND_STEP_ENTRY"`,
`pattern_name="TREND_STEP_ENTRY_{LONG|SHORT}"`, `structural_anchor = pause_extreme`,
`impulse_pts`, `retrace_frac`, `pause_bars`, `step_id`, `entry_price`, `stop`,
`t1`, `t2`, `t3`, `stage=5`. Lift `zigzag()` and `detect_trend_step()` verbatim out of
`scripts/replay_trend_step_entry.py` — they are already written as pure functions.

### 6.2 Flag

`TREND_STEP_ENTRY_V1`, **default OFF in code**, registered in `docs/FLAG_REGISTRY.yaml` +
`config/RULED_FLAGS.yaml` in the same commit, then `python3 scripts/gen_flag_index.py`.
Parameters env-tunable with the `TSE_` prefix already used by the replay script, so a
recalibration never needs a code edit — which matters, because §4.3 says recalibration is
coming.

### 6.3 Wiring point

`backend/v9/systems/five_min/five_min_system.py`, **new `Pkg 5e`, immediately after `Pkg 5d`
(RE_PULLBACK, line ~1529)** and before the A2 dedup block at line 1562:

```python
# Pkg 5e · TREND_STEP_ENTRY_V1 (default OFF): enter INSIDE the pause of a
# stair-step impulse, at a leg-relative price. No IB / TPO dependency.
if not direction and os.getenv("TREND_STEP_ENTRY_V1", "0").lower() in ("1","true","yes"):
    try:
        from ...patterns.trend_step_entry import detect_trend_step_entry
        direction, conf, info = detect_trend_step_entry(_det_buf)
    except Exception as e:
        logger.warning("[FiveMin] TREND_STEP errored (fail-open): %s", e)
```

No TPO / IB / day-type dependency — unlike Pkg 5a/5c it needs no `chart_patterns_allowed()`
and unlike Pkg 5d it needs no `_load_sierra_tpo()`.
Set `_dedup_cooldown["TREND_STEP_ENTRY"] = 0`; the `step_id` rule replaces bar-cooldown dedup.

### 6.4 ⚠️ The stop/target override is a build-blocker

At `five_min_system.py:1586+` the shared path **discards the detector's `stop`** and
recomputes it from `structural_anchor` through the adaptive-stop engine / StopResolver. On
08-11 that produced R = 9.75–15.00 pt on an 11 pt step and made T1 unreachable (forensic
§2.4(i)). **Wiring TREND_STEP without fixing this ships a detector whose measured edge cannot
be realised.** Two acceptable routes:

- **(a) preferred** — add `TREND_STEP_ENTRY` to `config/stop_anchors.yaml` `anchors:` as
  `{system: S2, group: CONT, type: pause_extreme, window: <pause_bars>, max_risk_points: 9}`
  plus a step-scaled T-ladder, i.e. implement `STEP_SCALED_LADDER_V1` for this pattern first;
- **(b)** honour `info["stop"] / info["t1..t3"]` verbatim when
  `info["kind"] == "TREND_STEP_ENTRY"`, behind the same flag.

Enabling either is a **trading-risk-surface change** → strategic stop + Michael sign-off.
The build is not.

### 6.5 Gateway interaction

`extreme_chase_guard` (`trading_gateway.py:1596-1690`) will block **every** TREND_STEP entry
by construction — filter 7 *requires* the entry to sit at the session extreme.
`TREND_LEG_CHASE_EXEMPT_V1` already exists for exactly this and has **never executed in
production** (forensic §3.2).

**Recommendation: ship SHADOW-only.** No gateway edit, no risk-surface change, and a live
shadow period is the only genuine out-of-sample this design can get, since 48 sessions is
the entire bar history. Do **not** open the chase guard on the strength of §4.2.

### 6.6 Tests — `tests/v9/regression/test_trend_step_entry.py`

| # | Test | Expect |
|---|------|--------|
| 1 | flag unset → `(None, 0.0, {})` | default-OFF proven |
| 2 | synthetic 12 pt down-impulse + 1-bar 40 % pause | `SHORT`, entry = last close |
| 3 | same, retrace 70 % | `None` (RETR_MAX) |
| 4 | same, pause 5 bars | `None` (PAUSE_MAX) |
| 5 | same, pause volume 2× impulse | `None` (VOL_RATIO_MAX) |
| 6 | same, step low 6 pt above the session low | `None` (SESSION_EXT_TOL) |
| 7 | mirrored LONG fixture | `LONG` |
| 8 | `stop = pause_high + max(0.5, 0.10·imp)` clamped 2.5–9.0; ladder monotone | exact values |
| 9 | causality: mutate `bars[i+1:]`, re-run `detect(bars[:i+1])` | output identical |
| 10 | 16:00 ET bar | `None` (CUTOFF) |

### 6.7 Acceptance cases (replay + sim, before any live discussion)

| # | Case | Pass criterion |
|---|------|----------------|
| A1 | Replay **06-05…08-11** through the real `FiveMinSystem`, flag on | ≥ 60 fires, NET ≥ +$2,200 **gross** with the pattern's own stop/ladder |
| A2 | **08-11** | exactly one SHORT at **11:25 ET / 7769.50**, stop 7776.00, reaches T3 |
| A3 | **08-03 + 08-04** | ≥ 3 LONG fires, both days net-positive |
| A4 | **08-06 + 08-07 + 08-10** (rotation) | ≤ 6 fires total, combined net ≥ −$300 |
| A5 | **06-05…07-14 out-of-sample** | NET ≥ **$0 after commission** — a hard gate, currently +$129 |
| A6 | Slippage 2 ticks adverse, full 48 sessions | NET ≥ +$1,500 gross |
| A7 | Flag OFF | byte-identical decision log to the baseline replay |
| A8 | One live SIM week, SHADOW | fire count within ±40 % of replay; nothing outside 09:50–15:00 ET |

### 6.8 Order of work

1. module + tests (§6.1, §6.6) — no wiring, nothing in `.env`;
2. `STEP_SCALED_LADDER_V1` / anchor entry (§6.4) — **do not skip this one**;
3. wire Pkg 5e, flag OFF (§6.3);
4. replay acceptance A1–A7;
5. SHADOW week (A8);
6. **only then** bring the chase-guard exemption to Michael as a written ruling — and only
   if the shadow week is consistent with §3.4, not with §0.

---

## 7. What would make this work

- **More sessions — this is the binding constraint, not the design.** 48 RTH sessions is the
  entire usable `v9_bars_5min_woodies` history. `scid` replay backfill to ~150–250 sessions
  would let the calibration in §4.3 be chosen properly instead of guessed on 20 days. It is
  already the listed blocker for `EDGE_FADE`; this report is a second, independent reason to
  do it first.
- **Tick / footprint data inside the pause.** The 5-min volume ratio is already the third
  strongest filter (54 % → 37 %). Delta or absorption inside the pause bars should separate
  "quiet rest" from "quiet distribution" far better — but S3 is deferred until after LIVE,
  so this is a post-LIVE item.
- **A live shadow month**, which is the only genuine out-of-sample available before new
  history exists.
- **An explanation for the LONG/SHORT asymmetry** (§4.4 #2) before anyone acts on it.

---

## 8. Verdict

**GO to build — module, tests, `STEP_SCALED_LADDER_V1`, wired flag-OFF, SHADOW-only.**
**NO-GO to live enable and NO-GO to any chase-guard change on this evidence.**

The design answers Michael's question correctly on the day he asked about: on 08-11 it takes
the first step of the staircase, at 7769.50 — the exact price the live system generated and
then blocked — and banks +$255 on a −1.75 pt MAE. It beats both prior attempts by a wide
margin on all 48 sessions, and the step anatomy behind it (n = 1,297) replicates cleanly.

But the number to plan around is **+$38.85 per trade after commission across 48 sessions,
with a −$1,068.75 drawdown** — not the +$82.79 of the design window. And the true
out-of-sample half of that sample is **+$3.58 per trade, negative under 2 ticks of
slippage, and dependent on a single session (06-05).** That is a promising design that has
not yet been validated, and it must be treated as such.
