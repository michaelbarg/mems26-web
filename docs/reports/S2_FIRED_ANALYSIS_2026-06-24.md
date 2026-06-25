# S2 (five_min) Fired-Pattern Analysis — Why the Shadow Trades Lost

**Scope:** All 78 S2 shadow trades (`firing_system=2`, `mode=shadow`, 2026-06-05 → 06-24).
**Source:** `outputs/s2_trades_dump.csv` (DB table `v9_trades`). Code grounded in
`backend/v9/systems/five_min/five_min_system.py` + `patterns/flags.py`.
**Net result:** **−$2,126.88** over 78 trades.

> Method note: `pattern_id_at_entry` was blank/`ZLR`/`VEGAS` for 5 rows; pattern was
> recovered from the `quality` JSON `pattern_name`. This reconciles the baseline
> (raw `pattern_id`) to the true detector pattern. Net P&L is identical (−$2,126.88).
> **Every one of the 78 trades exited via `STOP_HIT`/`manual` — none of the loss rows
> ever hit T1 first.** So losses are an *entry/direction* problem, not exit management.

---

## 0. The headline finding (read this first)

**S2's entire bleed is a LONG problem. The SHORT book is ~breakeven.**

| Side | n | Wins | Win% | Net P&L |
|---|---|---|---|---|
| **ALL LONGS** | 26 | 9 | **35%** | **−$2,174** |
| **ALL SHORTS** | 52 | 30 | **58%** | **+$47** |

The three "losers" Michael flagged (REACTIVE_LONG, BULL_FLAG_LONG, and the loss
*tail* of REACTIVE_SHORT) are all explained by two root causes:

1. **REACTIVE is a counter-trend fade with no day-type × location gate** (see §4). It
   fires on every 5-min bar in `DAY_TYPE_MODE` with *zero* trend/LSMA/location veto.
2. **No fire-dedup on REACTIVE/INITIATIVE** → overtrading clusters (06-22 alone:
   10 REACTIVE_SHORT, −$889).

---

## 1. Per-pattern scorecard (normalized)

| Pattern | n | W | L | Win% | Net $ | Avg $ | Avg R | Exit |
|---|---|---|---|---|---|---|---|---|
| **REACTIVE_LONG** | 19 | 6 | 13 | 32% | **−$1,634** | −$86 | −0.58 | 19× STOP_HIT |
| **REACTIVE_SHORT** | 34 | 18 | 16 | 53% | **−$862** | −$25 | −0.19 | 34× STOP_HIT |
| **BULL_FLAG_LONG** | 3 | 0 | 3 | 0% | **−$596** | −$199 | −1.00 | 3× STOP_HIT |
| INITIATIVE_LONG | 4 | 3 | 1 | 75% | +$56 | +$14 | +1.36 | 4× STOP_HIT |
| INITIATIVE_SHORT | 14 | 9 | 5 | 64% | +$175 | +$13 | +0.13 | 14× STOP_HIT |
| BEAR_FLAG_SHORT | 4 | 3 | 0 | 75% | +$734 | +$184 | +1.09 | 3× STOP_HIT, 1× manual |

The three losers contribute **−$3,092**; the three winners only **+$965**.

---

## 2. REACTIVE_LONG — the #1 bleeder (−$1,634)

### Finding A — it loses almost entirely on **Variation** days and **late** (≥19:00 IL)

| Slice | n | W | Net $ |
|---|---|---|---|
| day_type = **Variation** | 9 | **1** | **−$1,380** |
| day_type = Trend_Normal | 9 | 5 | −$164 |
| day_type = Normal | 1 | 0 | −$90 |
| entry hour **≥ 19:00 IL** | 9 | **0** | **−$1,414** |
| entry hour 17:00–18:59 | 10 | 6 | +$80 |

Variation days and the post-19:00 window each independently account for ~85% of the loss.

### Finding B — the "winners" are scratch trades; the losers are real counter-trend fades

Looking at every REACTIVE_LONG row by **risk = |entry − stop|** (raw rows from the CSV):

```
06-11 19:15 Variation    risk=22.5pt  -$338  LOSS
06-12 20:05 Variation    risk=17.8pt  -$266  LOSS
06-12 20:20 Variation    risk=14.2pt  -$214  LOSS
06-15 18:55 Trend_Normal risk=12.5pt  -$188  LOSS
06-18 17:50 Trend_Normal risk=11.0pt  -$165  LOSS
06-24 18:50 Variation    risk= 9.8pt  -$146  LOSS
...
06-18 17:25 Trend_Normal risk= 0.2pt  +$48   WIN   <- stop already at BE
06-18 17:35 Trend_Normal risk= 0.2pt  +$50   WIN   <- stop already at BE
06-18 17:40 Trend_Normal risk= 0.2pt  +$46   WIN   <- stop already at BE
06-24 18:20 Variation    risk= 0.2pt  +$11   WIN   <- stop already at BE
06-15 18:05 Trend_Normal risk= 4.5pt  +$146  WIN
```

**Pattern:** the 6 winners cluster at risk ≤ 4.5pt (4 of them ~0.2pt — entry essentially
*at* a trailed/breakeven stop, so they scratch +$11–$48). Every loss carries 5–22.5pt of
real risk and stops out for −$60 to −$338. REACTIVE_LONG is **buying into seller-weakness
fades that get run over**; when the trade actually has open risk, it loses.

### Proposed fix
Add a day-type × time gate on REACTIVE_LONG: **block when `day_type ∈ {Variation, Normal}`
OR entry hour ≥ 19:00 IL.** (Ground: `current_day_type` already available at the fire site,
`five_min_system.py:1247`; bar `ts` available in `_det_buf[-1]`.) Longer term, gate REACTIVE
*direction* against the day-type bias (don't fade-long on a down/neutral day) — see §4.

### Counterfactual
| Filter | Blocks | of which L / W | New S2 Net |
|---|---|---|---|
| Block RL on Variation | 9 | 8L / 1W | **−$747** (+$1,380) |
| Block RL hour ≥ 19:00 | 9 | 9L / 0W | **−$713** (+$1,414) |
| **Block RL on (Variation OR ≥19:00)** | **12** | **11L / 1W** | **−$473 (+$1,654)** |

The combined RL filter removes 11 losers at the cost of 1 winner (+$11). Best single-pattern lever.

---

## 3. BULL_FLAG_LONG — small count, 100% loss (−$596)

### Finding
3 fires, **0 wins**, all stopped within ≤10 min (whipsaw). Avg −$199, avg R = −1.0.
Newest two (06-24, Variation) lost −$236 and −$232 — the flag "broke out" then immediately
reversed. With n=3 there is no winning sub-cluster to protect.

```
06-18 22:55 Trend_Normal  -$128  LOSS
06-24 18:00 Variation     -$236  LOSS
06-24 18:30 Variation     -$232  LOSS
```

### Proposed fix
BULL_FLAG_LONG has **never** produced a shadow win. Its mirror BEAR_FLAG_SHORT is +$734 (3/3
wins) — so the *flag machinery* works short but not long over this sample. Disable/suspend
BULL_FLAG_LONG pending recalibration of the long pole/flag geometry (`patterns/flags.py`
`POLE_MIN_HEIGHT_TICKS`/`FLAG_MAX_RETRACE_PCT`, currently ATR-relative `_POLE_MIN_ATR_K=5.5`).
It is already day-type-gated via `chart_patterns_allowed(..., "5c")` (`_PKG5C_DAYTYPES`), so a
clean suspend is to drop LONG flags from that allow-list (or add a `BULL_FLAG_LONG` block flag).

### Counterfactual
Block all BULL_FLAG_LONG → removes 3 losers, **+$596** (no winners sacrificed). New S2 net −$1,531.

---

## 4. REACTIVE_SHORT — net negative but the *book is salvageable* (−$862)

### Finding A — loses on Trend_Normal and mid-session; **wins on Variation and late**

| Slice | n | W | Net $ |
|---|---|---|---|
| day_type = **Trend_Normal** | 11 | 4 | **−$660** |
| day_type = Normal | 6 | 4 | −$331 |
| day_type = Variation | 15 | 8 | **+$44** |
| hour **17:00–18:59** | 12 | 4 | **−$1,100** |
| hour 20:00 | 3 | 3 | +$520 |

### Finding B — overtrading. No dedup → repeat fires same day

06-22 fired **10** REACTIVE_SHORT entries (several 5 min apart): −$889. 06-18/06-19 added
−$356 / −$248. The 4th-and-later entry of a day is, on net, where the losses concentrate
*relative to count*, but the cleaner structural fix is the dedup gap (§6).

### Proposed fix
1. Block REACTIVE_SHORT during **17:00–18:59 IL** (early US session, where it's 4W/8L = −$1,100).
2. Add fire-dedup to REACTIVE (see §6) to kill the 06-22-style clusters.
Do **not** block REACTIVE_SHORT wholesale — it's the largest winning sub-book (18 wins,
+$1,523 gross) and is net-positive on Variation days.

### Counterfactual
| Filter | Blocks | L / W | New S2 Net |
|---|---|---|---|
| Block RS 17:00–18:59 | 12 | 8L / 4W | **−$1,026** (+$1,100) |
| Block RS on Trend_Normal | 11 | 7L / 4W | −$1,467 (+$660) |
| Cap RS at 3 entries/day | 11 | 4L / 7W | −$1,786 (+$341) — weak; sacrifices 7 winners |

The time-window filter is far better than the per-day cap (the cap throws away too many winners).

---

## 5. Direction × day-type mismatch vs Michael's rule

Michael's rule: *patterns fire per day-type + location; selectivity comes from
day-type × location plus an LSMA + CVD veto.*

**Code reality (verified):** in `five_min_system.process_bar`, `_detect_reactive` and
`_detect_initiative` run **unconditionally** on every completed 5-min bar in `DAY_TYPE_MODE`
(`five_min_system.py:1021–1023`). There is:
- **No day-type gate** on REACTIVE/INITIATIVE (the `chart_patterns_allowed` allow-list at
  `:1037`/`:1049` gates *only* H&S/Double/Flag chart patterns — `_PKG5A_DAYTYPES`,
  `_PKG5C_DAYTYPES`).
- **No location-vs-POC gate.** `location = self._compute_location_vs_poc(bar)` is computed at
  `:1167` but only feeds **sizing** (`calculate_size`, `:823`), never a fire veto.
- **No LSMA / CVD veto anywhere** in the fire path (grep: no `lsma`/`cvd` in the detector).
- The only direction-vs-flow filter (COT/AMT) is **disabled by default** (S2 ⟂ S3, per
  CLAUDE.md; `_require_cot_amt` defaults False at `:605`/`:747`).

So REACTIVE_LONG fades sellers (bets price *up*) regardless of whether the day is a down/neutral
day or whether price is at a sensible location — exactly the counter-trend mismatch the row-level
evidence in §2B shows. **The selectivity layer Michael's rule calls for is not wired for
REACTIVE/INITIATIVE.** This is the architectural root cause behind the LONG bleed.

---

## 6. Structural gap — REACTIVE/INITIATIVE have no fire-dedup

`five_min_system.py:220` — `_DEDUP_COOLDOWN = {"DOUBLE_TOP_AA":30, "DOUBLE_BOTTOM_EE":30,
"INVERSE_HNS":30, "HNS_TOP":30, "BULL_FLAG":20, "BEAR_FLAG":20}`. The lookup at `:1059`
`self._dedup_cooldown.get(_kind, 0)` returns **0** for kind `REACTIVE`/`OFA` → **no cooldown**.
That is why 06-22 produced 10 REACTIVE_SHORT fires in one session. Adding a cooldown
(e.g. 3–6 bars) for `REACTIVE`/`OFA` is the smallest structural fix for the overtrading cluster.

---

## 7. Highest-leverage recommendation

A single, conservative filter package flips S2 from −$2,127 to **positive** while sacrificing
only **one** winning trade (+$11):

> **Block REACTIVE_LONG when `day_type ∈ {Variation, Normal}` OR entry hour ≥ 19:00 IL,
> AND suspend BULL_FLAG_LONG.**

| Package | Blocks | L / W | New S2 Net | Delta |
|---|---|---|---|---|
| RL(Variation\|≥19h) + suspend BULL_FLAG_LONG | 15 | **14L / 1W** | **+$123** | **+$2,250** |
| (add) cap/dedup REACTIVE_SHORT clusters | — | — | further upside | — |

For comparison, the blunt "block all S2 longs except INITIATIVE_LONG" yields +$103 — i.e. the
*targeted* filter is actually **better** than blanket-blocking longs, because it keeps the
profitable late-session and Trend_Normal REACTIVE_LONG scratch-wins.

### Why this is safe under Pre-LIVE discipline
- Every claim is a row-count from `v9_trades` or a line in `five_min_system.py` (cited).
- It removes a **loss cluster** (14 of 15 blocked are losers), not winners.
- It is consistent with Michael's day-type × location selectivity rule — it *adds* the missing
  day-type gate to REACTIVE_LONG that the code currently lacks (§5).
- **Caveat / not-done:** this is a *shadow backtest counterfactual* on n=78. It does not prove the
  filter forward. The clean next step is to wire the gate behind a default-OFF flag, run it in
  SHADOW, and verify the four UAT axes before any LIVE consideration. It also does not address
  *why* the long detectors mis-fire (geometry recalibration of BULL_FLAG_LONG, and a real
  trend/LSMA veto for REACTIVE) — those remain open.

---

## Appendix — key code references
- `_detect_reactive` — `backend/v9/systems/five_min/five_min_system.py:580`
- `_detect_initiative` — `:722`
- Fire path (no day-type gate on REACTIVE/INIT) — `:1021–1023`
- Day-type gate (chart patterns only) — `chart_patterns_allowed` `:98`; allow-lists `:56–57`
- location computed but only feeds sizing — `:1167` → `calculate_size` `:823`
- Fire-dedup table (REACTIVE/OFA absent → cooldown 0) — `:220`
- BULL/BEAR flag detector + geometry constants — `patterns/flags.py:32–46`
