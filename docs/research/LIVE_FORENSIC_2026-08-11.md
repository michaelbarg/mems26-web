# LIVE FORENSIC — 2026-08-11 (mid-session, market still open)

**Agent:** `live-forensic-agent` · **Written:** 2026-08-11 20:05 IL, market open until 23:00 IL
**Mode:** STRICTLY READ-ONLY — no flag changes, no restarts, no writes to `~/SierraChart_Data`, no DB writes.
**Machine:** MacBook (LIVE), branch `stabilize/mems26-local-truth-2026-05-16`, backend PID 15747 (started 19:47:33).
**Michael's directive:** *"היום זה יום מגמתי — רק אם המגמה נשברת אפשר עסקה נגדית; כרגע אנחנו בראש של שורט."*

---

## 0. Bottom line (read this first)

| # | Question | Answer |
|---|----------|--------|
| 1 | Why did 7 PASSED decisions produce no trade? | **They were never real.** All 7 are **pytest artifacts** written into the live decisions log by a test run at 19:26. Entry = `7600.00` (a fixture constant), not the live market (~7763). **Real PASSED decisions today: ZERO.** All 34 real decisions were blocked. |
| 2 | The 4 down-steps | 4 clean impulse+pause steps (−19.75 / −18.75 / −11.5 / −11.0 pt). **Signals DID arrive during the pauses, at good prices.** Detection is not the problem — the gates are. |
| 3 | Why do signals arrive late? | **They don't.** Median bar-close → gateway decision = **5.0 s** (n=14, min 1 s). `zone_limit_late_entry` never fired on a real signal — all 7 were the same pytest pollution. |
| 4 | Is the trend still intact RIGHT NOW? | **YES — DOWN leg ALIVE, age 5, no break.** LSMA falling −0.44 pt/bar, CCI14 −164.7, six consecutive lower highs, fresh session low 7755.5 on the 19:55 bar. **Counter-trade (LONG) is forbidden.** |
| 5 | Top fix | The `TREND_LEG_CHASE_EXEMPT_V1` fix is **correct and targets the right bug**, but it only went live at the **19:47:33 restart** — it covered **0 of today's 14 chase blocks**. |

---

## 1. THE "7 PASSED" DECISIONS — they are test pollution, not trades

### 1.1 What the log actually contains

Today's `gateway_decisions.jsonl` holds **50 decisions**: 43 `blocked`, 7 `shadow_only`.
All 7 `shadow_only` rows — plus 7 `zone_limit_late_entry` and 2 `cold_start_guard` rows —
carry **`entry = 7600.00`** and land inside a **27-second burst at 19:26:05 → 19:26:32**.

Live MES was trading **7762–7766** at that moment. 7600.00 is not a market price.

### 1.2 Proof it came from pytest, not the backend

| Evidence | Result |
|----------|--------|
| `grep -c "7600" /tmp/backend.err.log` | **0** — the backend never saw these setups |
| Backend log 19:26:00–19:27:00 | only routine `[System0] SHADOW DIR` lines; no gateway activity |
| `cold_start_guard` reason | `bars_processed_today=0 < 3 (five_min buffer=0) — system not hydrated` → a **freshly constructed `TradingGateway()`**, i.e. a test process, not the 6-hour-old live one |
| Fixture match | `tests/v9/regression/test_zone_limit_entry.py` uses `entry_price = 7600.00`, LONG/SHORT, and monkeypatches live price to **7603.00 / 7597.00** |

The logged reasons are a **line-by-line replay of that test file**:

```
19:26:32 ZLR LONG  7600.0  zone_limit_late_entry  adverse drift 3.00pt > max 2.00pt (entry=7600.00 live=7603.00)
19:26:32 ZLR SHORT 7600.0  zone_limit_late_entry  adverse drift 3.00pt > max 2.00pt (entry=7600.00 live=7597.00)
19:26:32 ZLR LONG  7600.0  zone_limit_late_entry  signal age 600s > max 180s
19:26:32 ZLR LONG  7600.0  zone_limit_late_entry  signal age  30s > max  10s
19:26:32 CONFLUENCE_RI_ZLR LONG 7600.0 zone_limit_late_entry adverse drift 3.25pt > max 2.00pt
```

versus the test source:

```python
_price(monkeypatch, 7603.00)   # test_on_long_chased_3pt_blocked
_price(monkeypatch, 7597.00)   # test_on_short_chased_3pt_blocked_mirror
s["bar_ts"] = time.time() - 600  # test_stale_signal_age_blocked_when_ts_present
monkeypatch.setenv("ZONE_LIMIT_MAX_AGE_SEC", "10")  # test_params_env_tunable
_price(monkeypatch, 7603.25)   # test_confluence_pattern_not_exempt
```

Exact match, including the 3.25pt CONFLUENCE case and the 10 s age override.

### 1.3 What `shadow_only` means

`trading_gateway.py:631` → `outcome = "shadow_only" if result.get("shadow") else "none"`.
The test does `monkeypatch.setattr(gw, "_execute_shadow", lambda *a, **k: {"trade_id": "t"})`,
so every test that expects a PASS returns a truthy shadow → recorded as `shadow_only`.
**`shadow_only` is not "passed and then dropped" — it is "reached shadow execution".**

### 1.4 Blast radius

- `v9_trades` today: **0 rows** — the test run created **no** trade records. No DB pollution.
- No live orders: `_execute_shadow` was monkeypatched; `_execute_live` was never on the path.
- Damage is limited to **corrupted forensics**: 16 of 50 rows (32 %) in the live decisions
  log for a live trading day are synthetic, which is exactly what sent this investigation
  chasing a non-existent latency problem.

### 1.5 The real bug to fix

`tests/v9/regression/test_zone_limit_entry.py` (and any test that constructs a real
`TradingGateway()`) writes to the **production** `~/SierraChart_Data/v9_export/gateway_decisions.jsonl`
because the decisions-writer path is a module constant that no fixture redirects.

**Fix:** in `tests/conftest.py`, redirect the decisions-log path to `tmp_path` for the whole
suite (and/or refuse to write when `PYTEST_CURRENT_TEST` is set). Additionally: **never run
pytest on the LIVE machine during RTH.**

### 1.6 The honest answer to "why did none become a trade"

There was **no pre-fire validator failure, no margin rejection, no dedup, no slot exhaustion,
and no shadow-mode misconfiguration.** There was simply **nothing to execute** — every one of
the 34 real decisions today was blocked at the gateway. The corrected blocker table:

| Gate | Real blocks | Share |
|------|------------|-------|
| `extreme_chase_guard` | **14** | 41 % |
| `awaiting_release` | 10 | 29 % |
| `lsma_flat` | 4 | 12 % |
| `cont_trend_filter` | 3 | 9 % |
| `direction_context` | 2 | 6 % |
| `location_gate` | 1 | 3 % |
| *(pytest artifacts removed)* | ~~16~~ | — |

---

## 2. THE DOWN-STEPS — signals arrived in the pause; the gates refused them

### 2.1 Day skeleton (v9_bars_5min_woodies, RTH from 16:30 IL)

Open 7791.50 → last 7756.25. Alternating swings ≥ 4 pt:

| Step | Impulse | Drop | Pause that followed |
|------|---------|------|---------------------|
| **1** | 16:30 7791.50 → 16:45 **7771.75** | −19.75 | 16:45 → 17:50, retrace to **7787.00 / 7786.25** (~65 min balance) |
| **2** | 17:50 7786.25 → 18:15 **7767.50** | −18.75 | 18:15 → 18:20, bounce to 7774.00 |
| **3** | 18:20 7774.00 → 18:35 **7762.50** | −11.50 | 18:35 → 19:15, balance to **7770.00** (~40 min) |
| **4** | 19:15 7770.00 → 19:25 **7759.00** | −11.00 | 19:25 → 19:35, bounce to 7765.25 |
| *(5, live)* | 19:35 7765.25 → 19:45 7758.00 → 19:55 **7755.50** | −9.75 | in progress |

### 2.2 Was there a signal DURING the pause? Yes — every time.

| Pause | Signals inside the pause | Price | Gate that killed them |
|-------|--------------------------|-------|----------------------|
| after step 1 | 6 SHORT signals 17:25–17:45 | 7779.25–7780.25 | `awaiting_release` ×5, `cont_trend_filter` ×1 |
| after step 2 | INITIATIVE_SHORT 18:15, REACTIVE_SHORT 18:30 | 7772.00 / 7769.50 | `extreme_chase_guard` |
| after step 3 | 7 ZLR/REACTIVE SHORTs 18:55–19:20 | 7763.50–7766.75 | `extreme_chase_guard` |
| after step 4 | REACTIVE_SHORT 19:25, GHOST 19:40 | 7761.00 / 7762.25 | `extreme_chase_guard`, `location_gate` |

**The detectors were on time and on price, in the pause, on the correct side of the trend,
before the break.** Not one of them was late. Every single one was blocked.

### 2.3 What each blocked short was worth (MFE/MAE vs the tape, to 19:55)

| IL | Pattern | Entry | Gate | MFE | MAE |
|----|---------|-------|------|-----|-----|
| 17:25:06 | ZLR | 7779.75 | awaiting_release | **+22.25** | 6.50 |
| 17:45:02 | ZLR | 7779.25 | awaiting_release | **+21.75** | 7.00 |
| 17:38:04 | ZLR | 7779.75 | cont_trend_filter | +22.25 | 6.50 |
| 18:15:50 | INITIATIVE_SHORT | 7772.00 | extreme_chase_guard | **+14.50** | **2.00** |
| 18:30:03 | REACTIVE_SHORT | 7769.50 | extreme_chase_guard | **+12.00** | **0.50** |
| 18:35:02 | BEAR_FLAG_SHORT | 7764.75 | extreme_chase_guard | +7.25 | 5.25 |
| 18:55:01 | ZLR | 7763.75 | extreme_chase_guard | +6.25 | 6.25 |
| 19:05:04 | ZLR | 7765.50 | extreme_chase_guard | +8.00 | 4.50 |
| 19:15:04 | ZLR | 7765.50 | extreme_chase_guard | +8.00 | **2.00** |
| 19:20:05 | ZLR | 7766.75 | extreme_chase_guard | +9.25 | **−1.50** |
| 19:25:03 | REACTIVE_SHORT | 7761.00 | extreme_chase_guard | +3.50 | 4.25 |
| 19:40:45 | GHOST | 7762.25 | location_gate | +4.75 | **−0.75** |

Sum of MFE across all 21 blocked-short rows: **252.50 pt**. The two cleanest — **18:15 (+14.50 / −2.00)**
and **18:30 (+12.00 / −0.50)** — never traded a single tick against the entry beyond 2 pt.

### 2.4 Money left on the table (bar-by-bar simulation, 4 contracts, 2@T1 + 2@T2, $5/pt, stop wins on ambiguous bars)

**(i) With the stop/T1/T2 the backend actually computed** (taken verbatim from
`STOP_STRUCTURE_EXTREME` / `T1_STRUCTURE_END` / `RUNNER_T2` log lines):

| Entry | Stop | R | T1 | T2 | Result at 20:00 |
|-------|------|---|----|----|-----------------|
| 18:55 7763.75 | 7778.75 | 15.00 | 7741.25 | 7733.75 | open +8.00 → **+$160** |
| 19:05 7765.50 | 7779.25 | 13.75 | 7744.88 | 7738.00 | open +9.75 → **+$195** |
| 19:15 7765.50 | 7778.00 | 12.50 | 7746.75 | 7740.50 | open +9.75 → **+$195** |
| 19:20 7766.75 | 7776.50 | 9.75 | 7752.12 | 7747.25 | open +11.00 → **+$220** |

⚠️ **None of them banked anything.** `STOP_STRUCTURE_EXTREME` widens the stop back to the
*previous pause high* (12 bars), producing R = 10–15 pt. T1 = 1R therefore lands at 7741–7752,
while the session low is 7755.50. **On an 11-point stair-step, a 15-point R makes T1 structurally
unreachable.** This is a second, independent defect: even with the gates open, today's
configuration books **zero** and leaves everything as open MTM.

**(ii) With a leg-relative stop** (current-step swing high + 2 pt, T1 = 1R, T2 = 2R):

| Entry | Stop | R | Result |
|-------|------|---|--------|
| 17:25 7779.75 | 7789.00 | 9.25 | T1+T2 both hit by 19:25 → **+$277.50 banked** |
| 17:45 7779.25 | 7788.25 | 9.00 | T1+T2 → **+$270.00 banked** |
| 18:15 7772.00 | 7776.00 | 4.00 | T1+T2 by 18:30 → **+$120.00 banked** |
| 18:30 7769.50 | 7776.00 | 6.50 | T1+T2 by 19:55 → **+$195.00 banked** |
| 18:35 7764.75 | 7774.50 | 9.75 | open +9.00 → +$180 |
| 18:55 7763.75 | 7770.00 | 6.25 | **STOPPED −$125** |
| 19:05 7765.50 | 7771.50 | 6.00 | T1 + open → +$157.50 |
| 19:15 7765.50 | 7772.00 | 6.50 | T1 + open → +$162.50 |
| 19:20 7766.75 | 7772.00 | 5.25 | T1+T2 by 19:55 → **+$157.50 banked** |
| 19:25 7761.00 | 7767.25 | 6.25 | open +5.25 → +$105 |

Total across all 10 (unrealistic — they overlap): **+$1,500**.
**Realistic, first-trade-strict, one entry per step:** 17:25 (+$277.50) + 18:30 (+$195) +
19:20 (+$157.50) ≈ **+$630 banked on 3 trades, 0 losers.**

> **Honest caveat on the 17:25 block.** At 17:25 the LSMA was genuinely flat (7780.63 → 7780.06
> over 5 bars, ≈ −0.02 pt/bar) and price was mid-balance. `awaiting_release` holding that entry
> was **defensible ex-ante** — it only looks wrong with hindsight. Do not "fix" the release gate
> on the strength of this one. The defensible complaint is §3 below: the 18:15-onward blocks,
> where the leg was **provably live** and the system said so in its own log.

---

## 3. THE ROOT CAUSE — the chase-guard bypass fired, then revoked itself 14 times

This is the finding that matters most for tomorrow.

### 3.1 The sequence inside `extreme_chase_guard` (`trading_gateway.py:1596-1690`)

1. **A bypass was granted.** In every one of the 14 blocks, permission had already been given:
   - `_live_leg(direction)` → `_ecg_bypass = True` — logged **9 times**:
     ```
     18:30:03 [Gateway] LEG_RIDE: live DOWN leg (age 5) agrees with SHORT — day-level gates exempt
     18:35:02 [Gateway] LEG_RIDE: live DOWN leg (age 5) ...
     18:55:01/02/06, 19:25:03 [Gateway] LEG_RIDE: live DOWN leg (age 5) ...
     ```
   - or `release_gate.trend_bypass()` → logged **8 times** as `TREND BYPASS: SHORT with-move on displaced session`.
2. **The K3d tip-revocation took it back — 14 times, 100 % of the time:**
   ```
   18:15:50 BYPASS REVOKED: SHORT entry 7772.00 only 1.0pt from session low 7771.00
   18:30:03 BYPASS REVOKED: SHORT entry 7769.50 only 2.0pt from session low 7767.50
   18:35:02 BYPASS REVOKED: SHORT entry 7764.75 only 1.5pt from session low 7763.25
   18:55:01/02/06, 19:05:04/09, 19:11:49, 19:15:04/06, 19:20:05/23, 19:25:03 — same
   ```
3. Block issued: `dist < 6.2 pt`.

**The system correctly identified a live DOWN leg, correctly granted the with-trend exemption,
and then a guard written on 08-09 for rotation days cancelled it — on a Trend_DD day, in the
trade's own direction.** On a trend day the extreme extends bar after bar; proximity to the
session low *is* the entry, not the danger.

### 3.2 The fix is already written — but it was live for 0 of today's blocks

`TREND_LEG_CHASE_EXEMPT_V1` skips the revocation when day-type is `Trend*`/`Variation*` **and**
`_live_leg(direction)` agrees. Timeline:

| Time | Event |
|------|-------|
| 18:15 – 19:25 | **all 14 chase blocks happen** |
| 19:27:13 | commit `4412c393` — `TREND_LEG_CHASE_EXEMPT_V1` written |
| 19:28:49 | `trading_gateway.py` last modified |
| 19:29:10 | commit `199dcb67` — Variation label added |
| 19:47:33 | `.env` written (`EXCESS_COUNTER_ENTRY_V1=1`) + **backend restart, PID 15747** |
| 19:47:51 | commit `a19f6a08` |

`grep -c "TREND-LEG EXEMPT" /tmp/backend.err.log` → **0**. The exemption has **never executed
in production**. Since the 19:47:33 restart there have been **zero gateway decisions**, so both
new flags are **completely unproven live**.

### 3.3 Second-order note

`_live_leg()` runs a DB query and is called **twice** per chase evaluation (line 1608 and again
at line 1648). Two identical `v9_bars_5min_woodies` round-trips per decision. Harmless today
(latency is fine) but worth memoising within a single `route_setup` call.

---

## 4. LATENCY — measured, and it is NOT the problem

### (a) Feed: nominal 5-min close → backend `Bar closed` log

`n=15 · min 0.0 s · median 1.0 s · mean 2.9 s · max 20.0 s`
Worst two: bar 18:15 logged at 18:15:20 (+20 s), bar 18:20 at 18:20:10 (+10 s). All others ≤ 3 s.

### (b+c) Nominal bar close → `[Gateway] BLOCKED` decision written

`n=14 · median 5.0 s · mean 16.2 s · max 109 s`

```
18:15:50  + 50.0s   INITIATIVE_SHORT   extreme_chase_guard
18:30:03  +  3.0s   REACTIVE_SHORT     extreme_chase_guard
18:35:02  +  2.0s   BEAR_FLAG_SHORT    extreme_chase_guard
18:55:01  +  1.0s   ZLR                extreme_chase_guard
18:55:06  +  6.0s   ZLR                extreme_chase_guard
19:05:04  +  4.0s / 19:05:09 + 9.0s    ZLR
19:11:49  +109.0s   ZLR                (mid-bar re-fire, not a bar-close event)
19:15:04  +  4.0s / 19:15:06 + 6.0s    ZLR
19:20:05  +  5.0s / 19:20:23 +23.0s    ZLR
19:25:03  +  3.0s   REACTIVE_SHORT     extreme_chase_guard
```

**Median 5.0 s end-to-end.** `ZONE_LIMIT_MAX_AGE_SEC` is 180 s and `ZONE_LIMIT_MAX_DRIFT_PT`
is 2.0 pt — nothing today came close to either. **`zone_limit_late_entry` blocked zero real
signals; all 7 were the pytest burst (§1).**

### The SLOW-handler warnings are real but were not the binding constraint

789 SLOW-handler warnings today:

| Handler | n | avg | max |
|---------|---|-----|-----|
| `TPOSystem.process_bar` | 433 | 606 ms | **27,691 ms** |
| `BarLevelDetector.on_bar` | 273 | 345 ms | 4,128 ms |
| `WoodiesSystem.process_bar` | 33 | 441 ms | 1,278 ms |
| `FiveMinSystem.process_bar` | 17 | 2,138 ms | **30,040 ms** |

Two handlers stalled for ~30 s at their worst. That almost certainly explains the +50 s and
+20 s outliers, and it is a genuine LIVE risk (a 30 s stall inside an 11 pt step is a whole
leg). But it is a **latent** risk, not today's cause: no signal today was rejected for age or
drift. **Fix it, but do not let it displace §3 in priority.**

---

## 5. IS THE TREND STILL INTACT RIGHT NOW? — YES

Run at 20:00 IL against the exact query `_live_leg()` uses:

```
detect_leg(last 10 bars) -> leg=DOWN  age=5
  "DOWN leg: LSMA falling x4, 4 net swings holding it, close on-side"
detect_leg(last 12 bars) -> leg=DOWN  age=5   (identical)
```

| Signal | Value | Verdict |
|--------|-------|---------|
| LEG state | **DOWN, age 5** | alive |
| LSMA slope (last 4 transitions) | −0.62, −0.66, −0.15, −0.34 | falling, monotone |
| LSMA net over 5 bars | −1.77 pt (−0.443 pt/bar) | falling |
| CCI-14 (19:55) | **−164.7** | deeply negative, no zero-line reclaim |
| TCCI (19:55) | −129.8 | negative |
| Highs, last 6 bars | 7764.50 → 7765.25 → 7764.00 → 7761.50 → 7761.00 → **7759.25** | lower highs |
| Lows, last 6 bars | 7760.00 → 7760.50 → 7761.00 → 7758.00 → 7758.25 → **7755.50** | fresh session low |
| Last close vs LSMA | 7756.25 vs 7757.73 | below the line, on-side |
| Session | high 7770.00 · low **7755.50** · last **7756.25** | at the low |

**No break. Not even a warning sign.** The 19:55 bar made a new session low and closed near it.
Per Michael's rule — *counter-trade ONLY on a confirmed break* — **a LONG is forbidden right now.**
A break would require, at minimum: two consecutive closes above the LSMA, CCI-14 reclaiming zero,
and a higher high above 7770.00.

⚠️ **Live warning for the remaining session.** Two of the last four LSMA transitions
(−0.15 and −0.34 pt/bar) sit at or below the `lsma_flat` threshold of **0.25 pt/bar**. A fresh
with-trend short in the next few bars is at real risk of being blocked by `lsma_flat` even though
the leg is provably alive — the same class of bug as §3, in a different gate. It already cost 4
blocks today.

---

## 6. RANKED FIXES BY EXPECTED $

### (a) Can be fixed tonight after close — no replay needed

| # | Fix | Evidence | Expected $ |
|---|-----|----------|-----------|
| **A1** | **Verify `TREND_LEG_CHASE_EXEMPT_V1` actually executes.** The code is live but has never run (`TREND-LEG EXEMPT` count = 0) and no decision has passed through since the 19:47 restart. Write a regression test that replays today's 18:30 bar window and asserts the exemption fires and the block does **not** occur. | §3.2 | **Unlocks 14 blocks / +$630 realistic on a day like today.** Highest value by far. |
| **A2** | **Stop pytest writing to the live decisions log.** Redirect the decisions-writer path to `tmp_path` in `tests/conftest.py`, and/or no-op the writer when `PYTEST_CURRENT_TEST` is set. Add a house rule: no pytest on the LIVE machine during RTH. | §1 | $0 direct, but it destroyed 32 % of today's forensics and sent this investigation down a false path. Cheap, do it first. |
| **A3** | **Extend the LEG exemption to `lsma_flat`.** A live leg with a −0.44 pt/bar LSMA is not flat; the 0.25 threshold is a rotation-day heuristic. Same one-line pattern as `TREND_LEG_CHASE_EXEMPT_V1`. | §5 warning, 4 blocks today | Moderate; and it is an **active risk in the next hour**. |
| **A4** | **Memoise `_live_leg()` per `route_setup` call.** Currently 2 identical DB queries per chase evaluation. | §3.3 | $0, pure hygiene. |
| **A5** | **Investigate the 30 s handler stalls** (`FiveMinSystem` max 30,040 ms, `TPOSystem` max 27,691 ms). Profile tonight; do not ship a change blind. | §4 | Latent tail risk, not today's loss. |

### (b) Needs replay first — do NOT enable live without it

| # | Fix | Why replay is mandatory | Expected $ |
|---|-----|------------------------|-----------|
| **B1** | **Leg-relative stop/target ladder on trend days.** `STOP_STRUCTURE_EXTREME` reaches back 12 bars to the previous pause high, producing R = 10–15 pt against an 11 pt step, so **T1 = 1R is unreachable and nothing is ever banked** (§2.4(i): four entries, all open, zero booked). Proposal: on a live leg, anchor the stop to the **current step's** swing high + buffer. | Changes stop distance on every trade → changes every historical outcome. Trading-risk-surface change: replay + Michael sign-off. | **The difference between +$770 unbanked MTM and ~+$630 banked.** Second-highest value. |
| **B2** | **`cont_trend_filter` `dir_sustained` lag.** At 17:38 it blocked a SHORT with *"setup DOWN vs sustained UP"* — on a day that had already fallen 20 pt from the open. Third documented occurrence. | Touches direction logic for both sides. | ~+$270 on today's tape (the 17:38 signal ran +22 pt). |
| **B3** | **`awaiting_release` needs a leg-aware path**, not just the ±15 pt `RELEASE_TREND_BYPASS_PTS` displacement test. At 17:25 displacement was only 6.75 pt so no bypass fired, and 5 shorts were held. | **Caveat:** at 17:25 the LSMA was genuinely flat and the hold was defensible (§2.4). This may be a *correct* block that only looks wrong in hindsight. Replay before touching. | Uncertain — could be **negative**. Lowest confidence of the three. |
| **B4** | **`EXCESS_COUNTER_ENTRY_V1`** was enabled at 19:47 and has produced zero live decisions. Given §5 (leg alive, no break), it must not fire a LONG today. Verify in replay that it stays silent while a leg is alive. | New counter-entry behaviour on a live account. | Risk-reduction, not revenue. |

### Priority order

**A2 → A1 → A3 → B1 → B2 → A5 → B3 → B4.**

`A1 + B1` together are the whole day: the gates open, and the ladder becomes reachable.
Everything else is second order.

---

## 7. Verification commands (Rule 5 — raw output, not assertion)

```bash
# 1 — the 7 "passed" are all entry=7600 in one 27s burst
python3 -c "import json;rows=[json.loads(l) for l in open('/Users/michael/SierraChart_Data/v9_export/gateway_decisions.jsonl') if l.strip()];\
print([(r['ts'],r['entry']) for r in rows if r['outcome']=='shadow_only' and r['ts'].startswith('2026-08-11')])"

# 2 — the backend never saw 7600
grep -c "7600" /tmp/backend.err.log          # -> 0

# 3 — the exemption has never executed
grep -c "TREND-LEG EXEMPT" /tmp/backend.err.log   # -> 0
grep -c "BYPASS REVOKED"  /tmp/backend.err.log    # -> 14

# 4 — the leg is alive right now
env DATABASE_URL=postgresql://localhost/mems26 LEG_RIDE_V1=1 python3 -c "
import sys;sys.path.insert(0,'.')
from backend.v9.db.read import read_all
from backend.v9.systems.leg_state import detect_leg
q=\"SELECT high,low,close,lsma_value,cci_14 FROM v9_bars_5min_woodies WHERE (ts AT TIME ZONE 'America/New_York')::date=(now() AT TIME ZONE 'America/New_York')::date AND (ts AT TIME ZONE 'America/New_York')::time>='09:30' ORDER BY ts DESC LIMIT 10\"
print(detect_leg(list(reversed(read_all(q,{})))))"
# -> ('DOWN', 5, 'DOWN leg: LSMA falling x4, 4 net swings holding it, close on-side')

# 5 — zero trades today
env DATABASE_URL=postgresql://localhost/mems26 python3 -c "
import sys;sys.path.insert(0,'.')
from backend.v9.db.read import read_all
print(read_all(\"SELECT count(*) c FROM v9_trades WHERE (entry_ts AT TIME ZONE 'Asia/Jerusalem')::date=DATE '2026-08-11'\"))"
# -> [{'c': 0}]
```

---

## 8. NOT DONE / open

- The session is **still open** (until 23:00 IL). All MFE/MAE and P&L figures are cut at the
  **19:55 bar** and will change.
- Both new flags (`TREND_LEG_CHASE_EXEMPT_V1`, `EXCESS_COUNTER_ENTRY_V1`) are **live but unproven** —
  zero gateway decisions since the 19:47:33 restart. First decision tonight is the real test;
  watch for a `TREND-LEG EXEMPT` line.
- The 30 s `FiveMinSystem` / 27 s `TPOSystem` stalls were **measured but not root-caused**.
- No replay was run (read-only mandate). B1–B4 all require one before any enable.
- Nothing was changed. No flags, no restarts, no DB writes, no writes to `~/SierraChart_Data`.

— `live-forensic-agent`, 2026-08-11 20:05 IL
