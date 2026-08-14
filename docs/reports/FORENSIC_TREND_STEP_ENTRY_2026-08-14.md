# FORENSIC — TREND_STEP entry, trade #668 (2026-08-14)

**Question (Michael):** *"למה זה ירה בנקודה כל כך נמוכה?"* — the one LIVE trade of the day
shorted at 7811.25, i.e. **0.75 pt above the session low**, at the very bottom of a 19-pt drop,
instead of earlier/higher.

**Verdict (one line):** the entry price is a **live-port bug, not a parameter problem**.
`detector.live_bars()` returns the **currently-forming 5-min bar** as `bars[-1]`, so the detector
evaluated a **4-second-old partial bar** instead of the closed bar. The researched detector, run
on the same tape with closed bars, would have shorted at **7816.50** — **5.25 pt higher**.
`SESSION_EXT_TOL=0.0` is **NOT** the flaw: relaxing it to 1.0 / 2.0 / 4.0 changes nothing on
2026-08-14, and on the replay window every relaxation is strictly **worse**.

All evidence below was produced on **mac-1 (the LIVE machine)** against local Postgres
`postgresql://localhost/mems26`, `/tmp/backend.err.log`, and
`~/SierraChart_Data/v9_export/gateway_decisions.jsonl`. **No flag, `.env`, service or DB row was
changed.** Read-only throughout.

---

## 1. The trade

| Field | #667 (shadow) | #668 (LIVE) |
|---|---|---|
| Direction / pattern | SHORT TREND_STEP (sys 4) | SHORT TREND_STEP (sys 4) |
| Entry | 7811.25 @ 17:35:04.384 IL | 7811.25 @ 17:35:05.558 IL |
| Stop / T1 / T2 / T3 | 7816.50 / 7807.75 / 7802.50 / 7798.00 | same |
| Exit | 7816.50 STOP_HIT @ 17:40:00 | 7816.00 STOP_FILL @ 17:37:05 |
| P&L | −$78.75 (−0.75R) | **−$71.25 (−0.68R)** |
| Day type at entry / EOD | Trend_Normal / Variation | Trend_Normal / Variation |

Source: `v9_trades` rows 667/668. `PM_668.md` records **range position 0.035** — the entry sat at
3.5 % of the day's range, i.e. on the floor.

RTH open 7827.75 · session high at fire 7830.75 · **session low at fire 7810.50** ·
entry 7811.25 = session low **+0.75 pt**.

---

## 2. Bar sequence 16:30–17:45 IL (`v9_bars_5min_woodies`, 2026-08-14)

| IL | ET | open | high | low | close | vol | lsma | cci_14 | sess low | sess high |
|---|---|---|---|---|---|---|---|---|---|---|
| 16:30 | 09:30 | 7827.75 | 7828.00 | 7821.50 | 7824.25 | 18437 | 7827.57 | −209.0 | 7821.50 | 7828.00 |
| 16:35 | 09:35 | 7824.25 | 7825.25 | 7819.25 | 7822.50 | 14023 | 7826.71 | −235.1 | 7819.25 | 7828.00 |
| 16:40 | 09:40 | 7822.75 | 7827.50 | 7820.50 | 7826.25 | 15477 | 7826.45 | −109.9 | 7819.25 | 7828.00 |
| 16:45 | 09:45 | 7826.50 | 7828.50 | 7821.25 | 7822.00 | 16557 | 7825.63 | −112.4 | 7819.25 | 7828.50 |
| 16:50 | 09:50 | 7821.75 | 7828.50 | 7820.25 | 7827.00 | 17227 | 7825.72 | −58.4 | 7819.25 | 7828.50 |
| 16:55 | 09:55 | 7827.25 | 7827.25 | 7823.25 | 7826.00 | 7525 | 7825.56 | −42.4 | 7819.25 | 7828.50 |
| 17:00 | 10:00 | 7825.75 | 7829.75 | 7823.25 | 7828.00 | 7514 | 7825.81 | +14.8 | 7819.25 | 7829.75 |
| 17:05 | 10:05 | 7828.25 | **7830.75** | 7827.25 | 7828.00 | 11188 | 7826.04 | +83.9 | 7819.25 | 7830.75 |
| 17:10 | 10:10 | 7828.00 | 7829.50 | 7824.25 | 7825.25 | 10979 | 7825.88 | +2.7 | 7819.25 | 7830.75 |
| 17:15 | 10:15 | 7825.25 | 7826.00 | 7820.00 | 7820.75 | 14450 | 7824.86 | −138.2 | 7819.25 | 7830.75 |
| 17:20 | 10:20 | 7820.75 | 7821.75 | 7816.25 | 7818.00 | 17009 | 7823.40 | −207.3 | 7816.25 | 7830.75 |
| 17:25 | 10:25 | 7817.75 | 7818.75 | 7813.75 | 7816.75 | 12493 | 7821.77 | −201.8 | 7813.75 | 7830.75 |
| 17:30 | 10:30 | 7816.75 | 7817.50 | **7810.50** | 7811.00 | 15139 | 7819.60 | −201.1 | **7810.50** | 7830.75 |
| 17:35 | 10:35 | 7811.00 | 7817.00 | 7810.75 | 7816.50 | 12370 | 7818.63 | −132.5 | 7810.50 | 7830.75 |
| 17:40 | 10:40 | 7816.50 | 7816.50 | 7812.25 | 7813.75 | 8245 | 7817.20 | −111.8 | 7810.50 | 7830.75 |
| 17:45 | 10:45 | 7813.75 | 7813.75 | 7813.50 | 7813.75 | 30* | 7815.95 | −96.8 | 7810.50 | 7830.75 |

\* the 17:45 row was still forming when queried.

**Where 7811.25 sits:** the impulse leg is 7830.75 (17:05 high) → 7810.50 (17:30 low) = **20.25 pt
in 5 bars**. The live entry 7811.25 is **0.75 pt off the leg's low**, i.e. it captured **3.7 %** of
the 20.25-pt move as adverse cushion. The 17:30 bar that made the low closed at 7811.00 — the
system sold the closing tick of the impulse bar itself.

---

## 3. Per-bar gating table — why no candidate before 17:35

Instrumented run of the **live** detector (`backend/v9/systems/trend_step/detector.py`, shipped
params) over every bar of the session; the column is the **first** check that failed.

| IL | SHORT verdict | detail |
|---|---|---|
| 16:30–16:45 | `i<4` | warm-up (`i < 4` guard) |
| 16:50 | `SESSION_EXT` | step_low 7820.25 > sess_low 7819.25 + 0.0 (d = +1.00) |
| 16:55 | `SESSION_EXT` | step_low 7820.25 > sess_low 7819.25 (d = +1.00) |
| 17:00 | `SESSION_EXT` | step_low 7820.25 > sess_low 7819.25 (d = +1.00) |
| 17:05 | `SESSION_EXT` | step_low 7820.25 > sess_low 7819.25 (d = +1.00) |
| 17:10 | `IMP_SIZE` | imp = 6.50 pt, below `IMP_MIN` 8.0 |
| 17:15 | `SESSION_EXT` | step_low 7820.00 > sess_low 7819.25 (d = +0.75) |
| 17:20 | `PAUSE_BARS` | pause = **0** (this bar IS the running extreme) |
| 17:25 | `PAUSE_BARS` | pause = **0** |
| 17:30 | `PAUSE_BARS` | pause = **0** |
| **17:35** | **FIRE** | imp 20.25/5b · pause 1 · retr 35 % · LSMA slope −1.59 · ext 7810.50 · **entry 7816.50** |
| 17:40 | FIRE (same step) | pause 2 · entry 7813.75 |
| 17:45 | FIRE (same step) | pause 3 · entry 7813.75 |

LONG side, same window: `RETRACE` (89 %/62 %/102 %/138 %), `IMP_SIZE` (6.50–7.00 pt) or
`PAUSE_BARS` on every bar; the only LONG candidate produced live was at 17:10 and the gateway
blocked it (`lsma_flat`, §7).

**Structural reading — this is the honest answer to "why not earlier":**
during an impulse **every bar makes a new session extreme**, so `pause_bars = i − ext_i = 0` and
`PAUSE_MIN=1` rejects it (17:20 / 17:25 / 17:30). The detector is *designed* to be unable to fire
while the leg is extending — it can only fire on the **first bar that fails to extend**, i.e. the
first bounce bar. Whatever distance from the extreme you get comes **entirely from the retracement
of that bounce bar**. On 08-14 the bounce bar (17:35) retraced 6.50 pt off the low and closed at
7816.50 — a perfectly good short price. **The live system did not wait for it.**

---

## 4. ROOT CAUSE — the detector evaluated a forming (partial) bar

`live_bars()` (detector.py:220-244) selects *all* of today's rows from
`v9_bars_5min_woodies` with no "closed" predicate, and `detect_trend_step(bars)` defaults to
`i = len(bars) - 1`. The woodies table **does** carry the currently-forming bar. Direct
observation on mac-1:

```
wall clock IL: 17:46:31            (= 10:46:31 ET)
live_bars() n= 16
   10:35 ET  o=7811.00 h=7817.00 l=7810.75 c=7816.50 v=12370
   10:40 ET  o=7816.50 h=7816.50 l=7812.25 c=7813.75 v=8245
   10:45 ET  o=7813.75 h=7816.00 l=7812.50 c=7815.75 v=2546   <-- LAST, still forming
```

The last element is the 10:45 ET bar, which does not close until 10:50 ET. Both the module
docstring ("bar `i` … already closed") and `main.py:872` ("on each closed 5-min bar") state the
opposite of what the code does.

**Evidence chain for trade #668 — the numbers only reconcile with a forming bar:**

| observation | forming 17:35 bar (i = 17:35, 4 s old) | closed 17:30 bar (i = 17:30) |
|---|---|---|
| logged entry 7811.25 | partial close at +4 s = **7811.25** ✅ | closed c = 7811.00 ❌ |
| logged `impulse 20.2pt in 5 bars` | 7830.75 − 7810.50 = **20.25**, 17:05→17:30 = 5 bars ✅ | ✅ (same leg) |
| logged `pause 1 bars` | 17:35 − 17:30 = **1** ✅ | 0 → `PAUSE_MIN` reject ❌ |
| logged `retrace 35%` | (7817.50 − 7810.50)/20.25 = **34.6 %** ✅ | n/a |
| `SESSION_EXT_TOL=0` | ext 7810.50 == sess low 7810.50 ✅ | ext would be 7813.75 > 7810.50 ❌ |
| logged `LSMA slope −1.85` | partial LSMA ≈ 7817.85 → −1.85 ✅ | −1.75 ❌ |

The closed-bar evaluation at that instant is **impossible** (it fails both `PAUSE_BARS` and
`SESSION_EXT`). The candidate can only have come from the forming bar.

**Consequence, exactly quantified:**

| | entry | dist. from session low | source |
|---|---|---|---|
| shipped design (replay, closed bars) | **7816.50** | +6.00 pt | offline re-run, §3 |
| what actually fired (forming bar) | **7811.25** | +0.75 pt | `v9_trades` 668 |
| **delta** | **5.25 pt worse on a SHORT** | | |

The bug is also **non-deterministic** — a race with the bridge's push cadence. At 17:40:05 the
17:40 row had not been written yet, so that evaluation *did* use the closed 17:35 bar
(candidate `SHORT @7817.00`, correct behaviour). At 17:35:04 the 17:35 row already existed, so it
used a 4-second-old partial. Same code, two different semantics, ~5 s apart.

### 4b. The same bug also broke the bracket (second-order)

`TARGET_REALISM_V1` clamps T1 to `session extreme ± avg breakout step`; on 08-14 that ceiling was
**7807.75** (= session low 7810.50 − 2.75). The chain:

* entry 7811.25 → step-ladder T1 (min_rr floor 1.00 × 5.25) = **7806.00** → *below* the ceiling →
  clamped to **7807.75** → T1 distance collapses 5.25 → **3.50** → live bracket **R:R 0.67**.
* entry 7816.50 (correct) → T1 = **7811.25** → *above* the ceiling 7807.75 → **no clamp** →
  bracket stays at **R:R 1.00**.

So the 5.25-pt entry error is the sole cause of the sub-1 R:R bracket as well.

---

## 5. THE KEY QUESTION — does `SESSION_EXT_TOL=0.0` force entries at the extreme?

### 5a. On 2026-08-14: no. Relaxing it changes nothing.

Re-ran the per-bar gating with `SESSION_EXT_TOL` ∈ {0.0, 1.0, 2.0, 4.0}:

| TOL | first SHORT fire | entry | earlier bars |
|---|---|---|---|
| 0.0 (shipped) | 17:35 | 7816.50 | 16:50–17:15 fail `SESSION_EXT` / `IMP_SIZE` |
| 1.0 | **17:35** | **7816.50** | 16:50 → `PAUSE_BARS 0`; 16:55/17:00/17:05 → `RETRACE 100/115/127 %`; 17:15 → `PAUSE_BARS 0` |
| 2.0 | **17:35** | **7816.50** | identical to TOL=1.0 |
| 4.0 | **17:35** | **7816.50** | identical to TOL=1.0 |

Loosening the anti-rotation gate does **not** unlock an earlier or higher entry on this session —
the earlier bars fail on *pause geometry* and *retracement*, not on the session-extreme test.

### 5b. On the replay window 2026-07-15 … 2026-08-12 (n = 31, shipped params)

Distance from the session extreme **at the moment of entry**, per trade
(`scripts/replay_trend_step_entry.py`, `--since 2026-07-15 --until 2026-08-12`):

```
n=31   min=1.50  p25=3.50  median=6.00  mean=6.05  p75=6.75  max=14.75
```

**P&L split by distance from the extreme** (4 contracts, $5/pt, pre-commission):

| bucket | n | NET | win | avg/trade | mean MFE | mean MAE |
|---|---|---|---|---|---|---|
| **dist < 2.00 pt** ("at the extreme") | 2 | **+$475.00** | **100 %** | +$237.50 | 26.38 | −1.88 |
| **dist ≥ 2.00 pt** ("mid-move") | 29 | +$1,903.75 | 45 % | +$65.65 | 16.14 | −5.47 |

Finer:

| bucket | n | NET | win | avg/trade |
|---|---|---|---|---|
| 0–1 pt | **0** | — | — | — |
| 1–2 pt | 2 | +$475.00 | 100 % | +$237.50 |
| 2–3 pt | 4 | +$1,155.00 | 100 % | +$288.75 |
| 3–5 pt | 4 | +$520.00 | 50 % | +$130.00 |
| ≥5 pt | 21 | +$228.75 | 33 % | +$10.89 |

Cumulative "keep only entries within X pt of the extreme":

| max dist | n | NET | win | avg |
|---|---|---|---|---|
| ≤ 2 pt | 4 | +$1,242.50 | 100 % | +$310.62 |
| ≤ 3 pt | 6 | +$1,630.00 | 100 % | +$271.67 |
| **≤ 4 pt** | **9** | **+$2,236.25** | **89 %** | **+$248.47** |
| ≤ 6 pt | 16 | +$1,681.25 | 50 % | +$105.08 |
| no cap (all) | 31 | +$2,378.75 | 48 % | +$76.73 |

**`SESSION_EXT_TOL` sweep** (one knob, everything else shipped):

| TOL | n | NET | win | avg/trade | median dist | mean dist |
|---|---|---|---|---|---|---|
| −1.0 (gate OFF) | 60 | +$2,410.00 | 45 % | +$40.17 | 6.75 | 15.46 |
| **0.0 (shipped)** | **31** | **+$2,378.75** | **48 %** | **+$76.73** | 6.00 | 6.05 |
| 0.5 | 33 | +$2,208.75 | 45 % | +$66.93 | 5.75 | 5.90 |
| 1.0 / 1.5 / 2.0 | 36 | +$2,088.75 | 44 % | +$58.02 | 5.75 | 5.83 |
| 3.0 / 4.0 | 38 | +$1,921.25 | 42 % | +$50.56 | 5.75 | 5.84 |
| 6.0 | 40 | +$1,987.50 | 42 % | +$49.69 | 5.88 | 6.32 |
| 8.0 | 42 | +$1,907.50 | 40 % | +$45.42 | 6.12 | 6.57 |
| 12.0 | 44 | +$1,917.50 | 41 % | +$43.58 | 6.25 | 6.82 |

### 5c. Verdict on `SESSION_EXT_TOL=0.0`

**It is not the flaw — and the hypothesis behind the question is inverted by the data.**

1. **It does not force entries onto the extreme.** With TOL=0 the *median* entry sits **6.00 pt**
   from the session extreme and the **minimum over 31 trades is 1.50 pt**. Trade #668 entered at
   **0.75 pt** — **closer to the extreme than any trade in the entire design population**. #668 is
   out-of-distribution, which is the signature of a bug, not of a parameter.
2. **Raising TOL is monotonically worse.** Every relaxation lowers both NET/trade (+$76.73 →
   +$43.58) and win rate (48 % → 40–45 %), while barely moving the median distance (6.00 → 6.25).
   The extra trades it admits are rotation noise, exactly what the gate was built to reject.
3. **Proximity to the extreme is where the edge lives, not where it dies.** 89 % win and
   **94 % of the entire NET** (+$2,236 of +$2,379) comes from the 9 trades entered **within 4 pt**
   of the extreme; the 21 trades entered >5 pt away are effectively flat (+$10.89/trade, 33 %) and
   would be **net negative after commission** (4c × $1.50 RT = $6.00/trade).

So "sell close to the low" is the *intended and profitable* behaviour — **provided the entry is
the close of a real pause bar**. What went wrong on 08-14 is that the pause bar was replaced by a
4-second-old partial bar.

### 5d. The cost of that 5.25 pt, measured

`SLIP_TICKS` degrades the entry adversely by N ticks on the **same 31 signals** — a direct proxy
for "how much does entering worse than the pause-bar close cost?":

| adverse offset | n | NET | win | avg/trade |
|---|---|---|---|---|
| 0.00 pt (design) | 31 | **+$2,378.75** | 48 % | +$76.73 |
| 0.25 pt | 31 | +$2,320.00 | 48 % | +$74.84 |
| 0.50 pt | 31 | +$2,005.00 | 48 % | +$64.68 |
| 1.00 pt | 31 | +$1,803.75 | 48 % | +$58.19 |
| 2.00 pt | 31 | +$1,252.50 | 45 % | +$40.40 |
| 3.00 pt | 31 | +$323.75 | 39 % | +$10.44 |
| **5.25 pt** (= the #668 error) | 31 | **−$696.25** | **32 %** | **−$22.46** |

**The forming-bar bug turns a +$2,379 strategy into a −$696 strategy on identical signals.** This
is the single most important number in this report.

---

## 6. Where the stop and T1 came from, and the R:R gate

From `/tmp/backend.err.log`, 17:35:04 (verbatim):

```
[Gateway] #68 structural targets: SHORT Trend_Normal → C1=7797.25 C2=7783.25 C3=7769.25 (was t1=None t2=None)
[StepLadder] SHORT entry=7811.25 median_step=8.75 (zz_rev=5.0, min_rr=1.00) → stop=7816.50 (5.2pt) t1=7806.00 t2=7802.50 t3=7798.00
[Gateway] F3 STEP_SCALED_LADDER: SHORT median=8.75 → stop=7816.50 t1=7806.00 t2=7802.50 t3=7798.00
[Gateway] TARGET_REALISM_V1: t1 7806.00 → 7807.75 (SHORT ceiling from session extreme + avg breakout step)
[Gateway] LIVE trade TM id=668: SHORT TREND_STEP system=4 t1=7807.75 t2=7802.50 t3=7798.00 account=37138283
```

* **Stop 7816.50 came from the F3 step-scaled ladder**, not the detector. The detector returns
  `stop=None, t1..t3=None` by design (detector.py:268-269). `stop_dist = max(4.0, 0.6 × 8.75) =
  5.25` (`step_scaled_ladder.py:196`). ✅ Correct per H6/F3.
* **T1 was 7806.00** (R:R exactly 1.00, produced by the ladder's structural `min_rr` floor,
  `min_rr = _effective_rr_min() = 1.0` because the label was **Trend_Normal** — `RR_MIN_ROTATION=0.65`
  relief applies only to rotation labels). ✅ Correct.
* **`TARGET_REALISM_V1` then moved T1 to 7807.75**, collapsing the distance 5.25 → 3.50 and the
  bracket to **R:R 0.67**.

**Should `rr_entry_gate` have blocked it? No — by standing ruling, not by accident.**
`trading_gateway.py:2595` reads `_rr_t1 = setup.get("t1_pre_realism", setup.get("t1"))`, and
`:2524-2528` documents Michael's **07-15 ruling (decision 2/6)**: *"the R:R gate judges the ORIGINAL
structural intent, not the realism-capped order price — two conservatisms must not double-count."*
The gate therefore evaluated 5.25/5.25 = **1.00 ≥ 1.00** and passed. The
`gateway_decisions.jsonl` row for #668 confirms `blocked_by: null, outcome: "live"`.

**This is not a regression and must not be "fixed" by re-enabling double-counting.** It is,
however, a real observation: `step_scaled_ladder`'s docstring promises *"a ladder bracket can never
fail the R:R gate it was built to pass"*, and `TARGET_REALISM_V1` silently voids that guarantee on
the order that actually reaches Sierra. On 08-14 the fix is upstream: with the correct entry
(7816.50) the realism ceiling never binds and R:R stays 1.00 (§4b).

*Minor open item (not material to this forensic):* `pnl_usd = −$71.25` with `exit_price 7816.00`
implies ~3.56 pt average adverse across the 4 mapped per-contract brackets (c1–c4, 9 Sierra order
ids), not a clean 4 × 4.75 pt. Worth one line in the exit-accounting review; it does not change any
conclusion here.

---

## 7. `[TrendStep]` census — every candidate the detector produced today

`grep "TrendStep" /tmp/backend.err.log` (20 hits; 14 are the pre-fix `'BarEvent' object has no
attribute 'get'` startup errors, resolved before RTH):

| time IL | event | outcome |
|---|---|---|
| 17:10:04 | `CANDIDATE LONG @7827.75 — stair LONG: impulse 10.5pt in 3 bars, pause 1 bars, retrace 33%, LSMA slope +0.23` | **blocked** `lsma_flat` (\|slope 0.0700\| < 0.2500 pts/bar, scope=ALL) |
| 17:35:04 | `CANDIDATE SHORT @7811.25 — stair SHORT: impulse 20.2pt in 5 bars, pause 1 bars, retrace 35%, LSMA slope -1.85` | **ROUTED → live #668** (shadow #667) |
| 17:40:05 | `CANDIDATE SHORT @7817.00 — stair SHORT: impulse 20.2pt in 5 bars, pause 1 bars, retrace 35%, LSMA slope -1.56` | **blocked** `entry_not_confirmed` (no bearish confirm bar: c=7817.0 ≥ o=7811.0 + tol 0.579) |

Notes:
* The 17:40:05 candidate is the **same step** re-detected off the correctly-closed 17:35 bar at
  entry 7817.00 — i.e. the system's own second look produced a price **5.75 pt better** than the
  one it traded, and then correctly declined it for lack of a bearish confirm bar.
* The 17:10 LONG shows the detector's `LSMA_SLOPE_MIN=0.15` and the gateway's `lsma_flat` gate
  (0.25) disagree by design; the gateway is the stricter of the two. No action.
* `[TrendStep] ROUTED: SHORT @7811.25 → 667` logs the **shadow** trade id; the live trade is
  **668** (`main.py:903-905` prints `_res.get("trade_id")`). Cosmetic, but it makes log→DB
  correlation misleading. One-line fix.

Flags in force (`.env`, verified): `TREND_STEP_ENTRY_V1=1`, `STEP_SCALED_LADDER_V1=1`,
`TARGET_REALISM_V1=1`, `RR_MIN_ROTATION=0.65`, `FIXED_CONTRACTS_4=1`. No `TSE_*` override is set —
the detector ran on **shipped defaults**.

---

## 8. CONCRETE PROPOSAL (numbers, not opinion)

### P1 — ROOT FIX (required): evaluate the **last closed** bar. No new parameter.

`_trend_step_on_bar` already receives the closed bar's `ts` and already dedupes on it
(`main.py:884-890`). Pass it through and have `build_setup()` / `live_bars()` select
`i = index(ts_of_the_closed_bar)`, or equivalently drop any trailing row whose 5-min window has not
elapsed (`AND ts <= now() - interval '5 minutes'` in the query). Passing the event ts is preferred —
it removes the race entirely rather than trading one timing assumption for another.

*Expected effect, measured:*
* 2026-08-14: entry **7816.50** instead of 7811.25 (+5.25 pt on a SHORT); stop would be 7821.75 and
  the trade would **not** have been stopped through 10:45 ET (subsequent highs 7817.00 / 7816.50 /
  7813.75), versus the actual stop-out 2 minutes after entry. T1 would be 7811.25 with **R:R 1.00**
  (no `TARGET_REALISM_V1` clamp — §4b).
* Replay window: restores the **+$2,378.75 / n=31 / 48 %** profile from the **−$696.25 / 32 %**
  the 5.25-pt error implies (§5d).
* Add a regression test: `live_bars()[-1]` must never be a bar whose close time is in the future.

### P2 — GUARD (recommended, free): reject entries too close to the session extreme.

A pure **out-of-distribution** guard, not an edge filter. Over the 31 design trades the **minimum**
observed distance is **1.50 pt**, so a threshold of **1.25 pt** is provably free:

| min-dist threshold | n | NET | win | trades dropped |
|---|---|---|---|---|
| 0.0 / 0.5 / 1.0 / 1.5 | 31 | +$2,378.75 | 48 % | **0** |
| 2.0 | 29 | +$1,903.75 | 45 % | 2 (worth +$475) |
| 3.0 | 25 | +$748.75 | 36 % | 6 (worth +$1,630) |

→ **Propose `TSE_MIN_DIST_FROM_EXT = 1.25` pt** (reject if
`|entry − session_extreme| < 1.25`). Cost on the design window: **zero** (n 31 → 31, NET unchanged).
It would have blocked trade #668 (0.75 pt). Anything ≥ 2.0 destroys the edge — **do not** go higher.

### P3 — DO NOT change these (the data says the current values are right):

| knob | shipped | why not to touch it |
|---|---|---|
| `SESSION_EXT_TOL` | **0.0** | best avg/trade (+$76.73) **and** best win rate (48 %) of every value tested; 1.0–12.0 all strictly worse; on 08-14 relaxing it changes nothing (§5a) |
| `RETR_MIN` | **0.20** | 0.30 → +$2,085 · 0.35 → +$1,983 · 0.40 → +$1,389 · 0.45 → +$186. Monotonically worse |
| `PAUSE_MIN` | **1** | 2 → n=11, +$531, 36 % · 3 → n=6, −$270, 33 %. "Wait one more bar" destroys it (29 of 31 winners are `pause_bars=1`) |
| `rr_entry_gate` / `t1_pre_realism` | as-is | standing ruling 07-15 decision 2/6 — do **not** re-add double-counting |

### P4 — Observability (one line each)

* `main.py:903-905` — log the **live** trade id, not the shadow id.
* `detector.py` docstring + `main.py:872` comment say "closed bar"; make the code match (P1) or the
  comment match. Right now the documented contract and the runtime behaviour differ.
* `backend/v9/systems/five_min/trend_step_entry.py` is an **orphan duplicate** of the live detector
  (no importer anywhere in `backend/`). Delete or clearly mark it — two copies of a trading
  detector is a maintenance trap.

---

## 9. Answer to Michael, in one paragraph

המערכת לא "בחרה" למכור בתחתית. הגלאי מתוכנן לירות על **בר-העצירה הראשון אחרי הדחיפה** — וב-08-14
בר-העצירה (17:35) נסגר ב-**7816.50**, 6 נקודות מעל השפל. הבאג: `live_bars()` מחזיר גם את הנר
**שעדיין נבנה**, ולכן ב-17:35:04 הגלאי קרא נר בן 4 שניות וסגירתו הייתה 7811.25 — כלומר הוא נכנס על
סגירת נר-הדחיפה עצמו, 0.75 נק' מהשפל. אותה טעות גם כיווצה את T1 (דרך `TARGET_REALISM_V1`) ל-R:R 0.67
במקום 1.00. `SESSION_EXT_TOL=0` **אינו** האשם: הרפליי מראה שהמרחק החציוני מהקיצון הוא 6.00 נק'
והמינימום ההיסטורי 1.50 — העסקה הזו (0.75) מחוץ להתפלגות כולה. הרפיית הפרמטר רק מזיקה
(+$76.73 → +$43.58 לעסקה). התיקון הוא לקרוא **נר סגור בלבד**; 5.25 הנקודות האלה שוות
**+$2,378.75 מול −$696.25** על אותם 31 איתותים.

---

*Read-only forensic. No flag, `.env`, LaunchAgent, service or DB row was modified; nothing was
restarted. All queries ran on mac-1 (the LIVE machine) via Desktop Commander.
Author: cowork-dev · 2026-08-14*
