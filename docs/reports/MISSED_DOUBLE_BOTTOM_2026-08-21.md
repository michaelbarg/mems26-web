# MISSED DOUBLE BOTTOM — 2026-08-21 (LIVE, market open)

**Verdict: it was NOT the day-type and NOT the detector geometry.
System 2 `process_bar` has been crashing with a `NameError` on EVERY bar since
16:50:02 IL. The double-bottom detector was never called.**

Author: cowork-dev · investigated 18:05–18:25 IL, market open, READ-ONLY.

---

## 0. TL;DR — the causal chain

| # | Layer | Verdict today |
|---|-------|---------------|
| 1 | **S2 `process_bar`** | 🔴 **CRASHED 19/19 bars** — `NameError: name '_atr' is not defined`. Aborts *before* the chart-pattern block. **This is the killer.** |
| 2 | Detector geometry (`double_bt.py`) | ✅ Would have confirmed. Offline replay on the real bars returns `LONG conf=0.80` at the 17:55 bar. |
| 3 | Auth Table `DOUBLE_BOTTOM_EE_LONG × Normal` | ✅ `("FULL", 3, 2, 2)` — **not** a SKIP cell. |
| 4 | `chart_patterns_allowed(Normal, "5a")` | ✅ True (`Normal ∈ _PKG5A_DAYTYPES`; also `S2_CHART_ALL_DAYTYPES=1`). |
| 5 | Direction compass | ✅ Would have passed — live `dir_bias=UP`, `day_bias=UP` (System0 SHADOW DIR 18:00:48). A LONG was *with* the bias. |
| 6 | `day_entry_budget` (Normal = 2) | 🟠 **Would have blocked it anyway** — both slots spent by 16:55 on two ZLR SHORTs (net **−$35**). Second line of defence, never reached. |

---

## 1. The double bottom, reconstructed from `v9_bars_5min_woodies`

RTH 2026-08-21, times in IL (UTC+3); Z = UTC.

| Role | Bar (IL) | Bar (Z) | O | H | L | C |
|------|----------|---------|---|---|---|---|
| **Trough 1** | 16:50 | 13:50 | 7685.00 | 7687.75 | **7676.50** | 7679.50 |
| Neckline bar | 17:05 | 14:05 | 7684.75 | **7691.00** | 7684.50 | 7688.00 |
| **Trough 2** | 17:40 | 14:40 | 7678.75 | 7684.00 | **7677.25** | 7681.50 |
| **Breakout** | 17:55 | 14:55 | 7685.75 | 7694.00 | 7684.75 | **7693.75** |
| Run high | 18:05 | 15:05 | 7698.00 | **7699.50** | 7693.25 | 7693.75 |
| Last read | 18:15 | 15:15 | 7692.50 | 7695.00 | 7691.00 | 7691.75 |

- Trough symmetry: |7676.50 − 7677.25| = **0.75 pt** (0.0098 % — vs `TROUGH_SYM_PCT = 3 %`, i.e. ±230 pt; the symmetry gate is effectively inert).
- Neckline = max intervening high = **7691.00**; pattern height = 7691.00 − 7676.50 = **14.50 pt**.
- Breakout rule `close > neckline + 1T` → 7693.75 > 7691.25 ✅ first met at the **17:55 close**.
- Measured-move target = 7691.00 + 14.50 = **7705.50** — never reached (high 7699.50).
- 7676.50 is also the session low and the Sierra **IB low** (`tpo_snapshotter` 18:00:04: `ib_low: 7676.5`).

### The "~20 points"
Second low → post-breakout high = 7677.25 → 7699.50 = **22.25 pt**.
That is the *eye* measurement, not what a neckline-breakout entry gets:

| Entry style | Entry | MFE (to 7699.50) | MTM @ 7691.75 |
|---|---|---|---|
| Neckline breakout (what the detector emits) | 7693.75 | **+5.75 pt** | **−2.00 pt** |
| Second-low retest, 1-bar pivot confirm (17:45 close) | 7685.75 | **+13.75 pt** | +6.00 pt |
| Buy the low tick (Michael's eyeball) | 7677.25 | **+22.25 pt** | +14.50 pt |

**4 contracts = $20/pt (MES $5/pt × 4).** Verified against live fills: #760 4.5 pt → $45 on 2 contracts.

---

## 2. Why no fire — the crash (primary, decisive)

```
2026-08-21 18:00:06 [INFO]  [mems26.systems.five_min] [S2-DL] REACTIVE ts=2026-08-21 14:55:00+00:00 ...
2026-08-21 18:00:06 [ERROR] [backend.v9.services.bar_router] BarRouter: handler FiveMinSystem.process_bar failed: name '_atr' is not defined
```

`/tmp/backend.err.log`, **19 occurrences, all today**, one per 5-min bar:

```
16:50:02 16:54:54 16:55:03 17:00:03 17:05:04 17:10:03 17:15:03 17:20:02 17:25:04
17:30:03 17:35:03 17:40:07 17:45:03 17:50:04 17:55:04 18:00:06 18:06:23 18:10:35 18:15:02
```

Still crashing at the time of writing (last crash 18:15:02, clock 18:18:39).

### The bug

`backend/v9/systems/five_min/five_min_system.py:1078` (and `:1081`), inside **`_detect_initiative`**:

```python
if _os.environ.get("S2_INITIATIVE_JOIN_ATR_CAP_V1", "").lower() in ("1", "true", "yes"):
    _join_atr_cap = 0.55 * (_atr or 5.0)          # ← NameError
```

`_atr` is a **local of `_detect_reactive`** (`five_min_system.py:818`: `_atr = self._current_atr_5m or 2.0`). It does not exist in `_detect_initiative`. The correct reference is `self._current_atr_5m`.

- Introduced by **`87227d0fc`** — *"feat: S2_INITIATIVE_JOIN_ATR_CAP_V1 — cap b3_join at 0.55×ATR (A2)"*, Michael Barg, **2026-08-20 23:55:38 +0300** (last night).
- The flag is live: `.env:246 S2_INITIATIVE_JOIN_ATR_CAP_V1=1` → the branch is entered → guaranteed raise.
- Zero occurrences before today ⇒ the bug went live with the first backend start after that commit.

### Blast radius
`_detect_initiative` is called at `five_min_system.py:1724`. The exception propagates out of
`process_bar`, so **everything after line 1724 never runs today**:
HLST · Pkg 5a (Inverse H&S, H&S top) · **Pkg 5b (Double Bottom, Double Top)** · Pkg 5c (Bull/Bear flag) ·
Pkg 5d (RE_PULLBACK) · dedup · FHB gate · quality tier · `emit_t1_setup` · gateway routing.

Corroboration: `/api/v9/gateway/decisions` holds **15 rows today, all `system: 4`** — **zero System-2
candidates reached the gateway**. `grep DOUBLE backend.err.log` — last hits are **2026-08-20**
(two `FIRE: DOUBLE_BOTTOM_EE LONG`, conf 0.96 and 1.00). Nothing on 08-21.

### Proof the detector itself was fine
Offline replay of the real `detect_double_bottom_ee` against `v9_bars_5min_woodies`, emulating the
live buffer (`_bar_buffer[-20:]`, `_det_buf = buffer[:-1]`, `atr_5m = atr_5min(buffer, 14)`):

```
det_last=17:45 n_det=19 atr=6.40 tol=4.80 pivots=[(4,7681.25),(7,7676.5)]              -> None
det_last=17:50 n_det=19 atr=6.76 tol=5.07 pivots=[(3,7681.25),(6,7676.5),(16,7677.25)] -> None
det_last=17:55 n_det=19 atr=6.97 tol=5.23 pivots=[(2,7681.25),(5,7676.5),(15,7677.25)] -> LONG 0.8 neckline=7689.5
det_last=18:00 n_det=19 atr=6.72 tol=5.04 pivots=[(4,7676.5),(14,7677.25)]             -> LONG 0.8 neckline=7691.0
```

`S2_ATR_RELATIVE = True` (`.env:20`), so `get_trough_tolerance = 0.75 × ATR14 = 5.23 pt`, and both
troughs clear the Eve width test (`TROUGH_MIN_WIDTH_BARS = 3`).
**Note the fragility:** with the flag OFF the tolerance is the fixed `TICK_SIZE × 2 = 0.50 pt`, which
gives w1 = 1 and w2 = 2 → **no fire**. The Eve variant filter only works because ATR-relative is on.

The panel's *"1 swing lows found"* at 17:45 is correct and expected: `PIVOT_LOOKBACK = 2` needs two
bars **after** the pivot, so the 17:40 trough only becomes a pivot once 17:45 and 17:50 have closed —
a built-in **10-minute confirmation lag**.

---

## 3. The day-type angle — did a Normal-day rule kill a good trade?

**Not the Auth Table.** `auth_table_v1.py:81` → `("DOUBLE_BOTTOM_EE_LONG", "Normal"): ("FULL", 3, 2, 2)`.
Best cell in the row apart from Nontrend. The day-type gate `chart_patterns_allowed` also passes
(`_PKG5A_DAYTYPES = ("Neutral_Extreme", "Neutral_Center", "Normal", "Variation")`).
Day-type became `Normal` at **17:00:03** — 55 minutes before the breakout, so the earlier
`UNKNOWN` window is irrelevant here.

**The entry budget, yes — but only as the second blocker.** `config/daytype_entry_budget.yaml` →
`Normal: max_entries: 2` ("selective — 2 high-quality entries, no churn"), `DAYTYPE_ENTRY_BUDGET_V1=1`
(`.env:248`). The gate counts `mode IN ('live','demo')` non-scale-in entries **first-come, no ranking**
(`trading_gateway.py:1753-1782`).

Both slots were consumed within **5 minutes of each other, at the session low**:

| # | Mode | Pattern | Dir | Entry | @ (IL) | Exit | Reason | P&L | R | MFE | MAE |
|---|------|---------|-----|-------|--------|------|--------|-----|---|-----|-----|
| 760 | live | ZLR | SHORT | 7684.50 | 16:50:12 | 7680.00 | T2_FILL | **+$45.00** | 0.90 | 8.00 pt | 15.00 pt |
| 762 | live | ZLR | SHORT | 7678.25 | 16:54:59 | 7686.25 | STOP_FILL | **−$80.00** | −1.03 | **1.00 pt** | **21.25 pt** |

Net live today: **−$35.00** on 2 contracts.

**#762 is the damning one: it shorted at 7678.25 — 1.75 pt above the session low 7676.50 — i.e. the
system sold the first trough of the very double bottom it later failed to buy.** MFE 1.00 pt against
MAE 21.25 pt. It then blocked 7 further candidates:

```
by_gate: {cold_start_guard: 2, awaiting_release: 1, cont_trend_filter: 1,
          day_entry_budget: 7, daytype_playbook: 2}   (13 blocked / 2 fired / 15 candidates)
```

So the honest answer to Michael's question: **a Normal-day rule did not kill this trade — a crash did.
But the Normal-day budget was standing right behind it, and it had already spent both slots on a
+0.9R scratch and a −1.03R loss taken into the low.**

---

## 4. Fix proposal (design only — no code written)

### F1 — `_atr` NameError · **P0, ship now, no ruling needed**
`five_min_system.py:1078,1081` → replace `_atr` with `self._current_atr_5m` (keep the `or 5.0` /
`or 0` fallbacks). It is a straight typo-class bug in `87227d0fc`, not a behaviour change: the
*intended* behaviour was already ruled (S2_INITIATIVE_JOIN_ATR_CAP_V1, Michael 2026-08-20).
Add a regression test that calls `_detect_initiative` with the flag ON.
**Value today (4c):** unblocks the DBT signal — **+$115 at MFE / −$40 mark-to-market**. The real value
is that S2 has been 100 % blind for 19 bars of a live session; today's move was small, tomorrow's may
not be.

### F2 — BarRouter must escalate a repeating handler crash · **no ruling needed**
Today a `[ERROR]` line repeated 19 times and nothing paged. Proposal: N consecutive failures of the
same handler → `phone_alert` + a `system_health` degradation flag surfaced in the mobile snapshot.
A silently-dead S2 must never again look identical to a quiet S2.
**Value today:** $0 directly; it converts a 90-minute blind window into a 10-minute one.

### F3 — second-low retest entry for DOUBLE_BOTTOM_EE · **needs a Michael ruling** (new entry trigger)
The pattern's edge sits at the **second trough**, not at the neckline. Today the neckline entry gave
+5.75 pt MFE; a retest entry gave +13.75 pt. Proposal: arm when trough 2 is confirmed within
`k × ATR14` of trough 1 (today 0.75 pt = **0.11 × ATR 6.97**; suggest `k = 0.35`, ≈ 2.4 pt today) and
enter on the first close above the confirm-bar high, stop below trough 2, neckline as T1.
Also worth folding in: `TROUGH_SYM_PCT = 0.03` is 230 pt at 7680 — it is not a constraint, it is
decoration. Replace it with the ATR-relative `k`.
**Value today (4c):** entry 7685.75 vs 7693.75 → **+$160 extra at MFE (+$275 vs +$115)**; MTM
**+$120 vs −$40**.

### F4 — quality-ranked entry budget · **needs a Michael ruling** (trading-risk surface)
`day_entry_budget` is first-come. Today it spent Normal's 2 slots on two ZLR counter-trend SHORTs at
the low (net −$35) and then blocked 7 candidates. Options, cheapest first:
(a) **re-earn a slot** — a full −1R loss inside the first 30 min of the session returns its slot
(would have restored one slot at 17:05 when #762 stopped out);
(b) **reserve by tier** — 1 of Normal's 2 slots reserved for an Auth-Table `FULL` + tier `HIGH`
pattern; ZLR/GB100 draw only from the unreserved slot;
(c) **rank, don't queue** — hold candidates to the bar close and take the highest-RR one.
(a) is the smallest change and is the one that fits today's tape.
**Value today (4c):** with F1 + F3 + F4(a) the DBT would have been the day's third entry —
**+$275 at MFE**, turning a −$35 day into roughly +$85…+$240 depending on the exit rule.
Without F4 the trade is blocked at the gateway even after F1 ships.

### F5 — `SEARCH_WINDOW` is unreachable · **no ruling needed, latent**
`double_bt.py:31 SEARCH_WINDOW = 30`, but `_bar_buffer` is hard-capped at **20**
(`five_min_system.py:458, 1333, 1349`) and `_det_buf = _bar_buffer[:-1]` → the detector never sees
more than **19 bars (95 min)**. Every "10–30 bar" Bulkowski pattern longer than 95 minutes is
silently invisible. Raise the buffer cap to ≥ 32.
**Value today:** $0 — both troughs were 10 bars apart, inside the window. Latent bug only.

Minor, no action proposed: `_swing_lows` uses `<=`, so an exact tie disqualifies a pivot — today the
17:20 and 17:30 lows were both 7679.75 and cancelled each other. Not decisive here.

---

## 5. Evidence index

- Bars: `psql postgresql://localhost/mems26` → `v9_bars_5min_woodies`, `ts >= '2026-08-21 13:30:00+00'`
  (19 RTH bars; `v9_bars_5min` is byte-identical today — checked, no contamination).
- Crash: `/tmp/backend.err.log` → `grep "name '_atr' is not defined"` (19 hits, all 2026-08-21).
- Decisions: `curl http://localhost:8000/api/v9/gateway/decisions?limit=300` → 15 rows, all `system: 4`.
- Trades: `v9_trades` where `entry_ts >= '2026-08-21'` → #759/#761 shadow, #760/#762 live.
- Code: `backend/v9/systems/five_min/five_min_system.py:818, 1078, 1081, 1724, 1749-1757`;
  `backend/v9/systems/five_min/patterns/double_bt.py:30-48, 66-78, 96-111, 167-230`;
  `backend/v9/systems/five_min/auth_table_v1.py:76-82`;
  `backend/v9/gateway/trading_gateway.py:1749-1784`; `config/daytype_entry_budget.yaml`.
- Commit: `git blame -L 1074,1082 backend/v9/systems/five_min/five_min_system.py` → `87227d0fc`.
