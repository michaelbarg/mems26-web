# FORENSIC — "why did neither machine trade the opening?" (2026-08-14)

**Machine:** MacBarg (mac-1, the LIVE trading machine) · **Window:** 16:30–17:35 IL = 13:30–14:35 UTC
**Sources:** `~/SierraChart_Data/v9_export/gateway_decisions.jsonl` · `/tmp/backend.err.log` ·
`v9_bars_5min_woodies` (postgresql://localhost/mems26) · live `step_scaled_ladder` module (imported, not re-implemented)
**Realized today:** 8 closed trades, **−$148.75**
**Code changed: NONE. Flags changed: NONE. Restarts: NONE.** This report proposes only.

---

## 0. Headline — the premise needs one correction, and it changes the fix

Michael's read was "we missed the opening drop." The tape says something more precise:

| | |
|---|---|
| RTH open (13:30 UTC bar open) | **7827.75** |
| First 45 min (13:30–14:05) range | **7819.25 – 7830.75 = 11.50 pt** |
| 30-min momentum (open → 13:55 close) | **−1.75 pt** |
| Day high | 7830.75 @ **14:05** |
| Break begins | **14:10–14:15** |
| Day low (by 16:25) | 7800.00 @ 15:50 |

**The first 45 minutes were genuine balance, not a missed drive.** There was no opening drive to
catch — the 30-min momentum was −1.75 pt inside an 11.5 pt range. The tradeable move started at
**14:10–14:15 UTC (17:10–17:15 IL)**, *after* the opening window's decision point.

So the miss is not "the opening." The miss is **the break of that balance at 17:15 IL**, and it has
a single owner: **`cont_trend_filter`**. The system fired at 17:35 — **20 minutes and 14 points late**.

The counterfactual confirms this: the gates that blocked the *actual* opening chop
(`lsma_flat`, `awaiting_release`) **saved $405**. Blocking them was correct.

---

## 1. Every decision in the window

Two populations. The second is **invisible in `gateway_decisions.jsonl`** — those candidates were
killed inside `five_min_system` before they ever reached the gateway, so any audit that reads only
the decisions file undercounts the opening by 5.

### A) Gateway decisions (`gateway_decisions.jsonl`)

| # | UTC | IL | Pattern | Dir | Entry | blocked_by | Reason |
|---|-----|----|---------|-----|-------|------------|--------|
| 1 | 13:30:04 | 16:30 | GB100 | SHORT | 7825.25 | `awaiting_release` | zone release — structure not turning (1/2 higher lows) |
| 2 | 13:58:36 | 16:58 | ZLR | SHORT | 7823.75 | `awaiting_release` | zone release — structure not turning (1/2 higher lows) |
| 3 | 14:00:03 | 17:00 | ZLR | SHORT | 7825.00 | `awaiting_release` | still active in the zone (vol 2.71 > 0.75) |
| 4 | 14:00:10 | 17:00 | ZLR | SHORT | 7825.00 | `lsma_flat` | \|LSMA slope −0.0267\| < 0.2500 pts/bar |
| 5 | 14:10:04 | 17:10 | TREND_STEP | LONG | 7827.75 | `lsma_flat` | \|LSMA slope 0.0700\| < 0.2500 pts/bar |
| 6 | 14:15:05 | 17:15 | ZLR | SHORT | 7825.75 | **`cont_trend_filter`** | ZLR (CONT) setup DOWN vs sustained NEUTRAL |
| 7 | 14:15:08 | 17:15 | ZLR | SHORT | 7825.25 | **`cont_trend_filter`** | ZLR (CONT) setup DOWN vs sustained NEUTRAL |
| 8 | 14:25:03 | 17:25 | FAMIR | LONG | 7818.00 | `direction_context` | setup UP vs day-context DOWN |
| — | 14:35:04 | 17:35 | TREND_STEP | SHORT | 7811.25 | *(FIRED — #667+#668)* | duplicate fire, −$78.75 + −$71.25 |

### B) Opening-path candidates killed inside `five_min_system` (never reached the gateway)

From `/tmp/backend.err.log`. **The opening engine classified the day correctly — `DRIVE SHORT` from
16:40 IL, ten minutes after the open.** Every one of its own triggers was then killed by its own guards.

| # | UTC | IL | Trigger | Dir | Killed by | Log line |
|---|-----|----|---------|-----|-----------|----------|
| 9 | 13:40 | 16:40 | DRIVE | SHORT | `OPENING_FIRST_TRADE_STRICT` | `held DRIVE SHORT — opening confidence 0.0 < 0.6` |
| 10 | 13:50 | 16:50 | DRIVE | SHORT | `OPENING_FIRST_TRADE_STRICT` | `held DRIVE SHORT — opening confidence 0.0 < 0.6` |
| 11 | 14:05 | 17:05 | ORR | LONG | `OPENING_DIR_FUSION` | `gate dropped ORR LONG (fusion=None)` |
| 12 | 14:20 | 17:20 | DRIVE | SHORT | `OPENING_DIR_FUSION` | `gate dropped DRIVE SHORT (fusion=None)` |
| 13 | 14:25 | 17:25 | DRIVE | SHORT | `OPENING_DIR_FUSION` | `gate dropped DRIVE SHORT (fusion=None)` |

**13 candidates in the first hour, not 7.**

---

## 2. Counterfactual per candidate

Model — the live ladder, using the **imported** `backend/v9/systems/five_min/step_scaled_ladder.py`
(`compute_median_session_step`, causal bars only, `ZZ_REV=5.0`):

* `stop = max(4.0, 0.6 × median_zigzag_leg)` → snapped to 0.25
* `T1 = max(0.5 × step, 1.0 × stop)` · `T2 = max(1.0 × step, T1)` · `T3 = max(1.5 × step, T2)`
* 4 contracts, **1 lot per OCO group** — C1→T1, C2→T2, C3→T3, C4 runner
  (verified in `~/SierraChart/ACS_Source/MES_AI_DataExport.cpp:2874-2935`)
* stop → BE after T1 · 12-bar (60-min) time stop · MES $5/pt
* Conservative: when stop and target both sit inside one bar, **the stop fills first**
* `*` = fewer than 5 bars / 3 zigzag legs available → ladder degenerates to the 4.0 stop floor

| # | IL | Pattern | Dir | Entry | Gate | step | stop | T1 | Result | **pts** | **$ (4c)** |
|---|----|---------|-----|-------|------|------|------|----|--------|---------|------------|
| 1 | 16:30 | GB100 | SHORT | 7825.25 | awaiting_release | 6.67* | 7829.25 | 7821.25 | T1 then stop | +4.00 | **+20.00** |
| 2 | 16:58 | ZLR | SHORT | 7823.75 | awaiting_release | 8.50 | 7828.75 | 7818.75 | stop 14:00 | −20.00 | **−100.00** |
| 3 | 17:00 | ZLR | SHORT | 7825.00 | awaiting_release | 9.00 | 7830.50 | 7819.50 | stop 14:05 | −22.00 | **−110.00** |
| 4 | 17:00 | ZLR | SHORT | 7825.00 | lsma_flat | 9.00 | 7830.50 | 7819.50 | stop 14:05 | −22.00 | **−110.00** |
| 5 | 17:10 | TREND_STEP | LONG | 7827.75 | lsma_flat | 8.75 | 7822.50 | 7833.00 | stop 14:15 | −21.00 | **−105.00** |
| 6 | 17:15 | ZLR | SHORT | 7825.75 | **cont_trend_filter** | 8.75 | 7831.00 | 7820.50 | **T1+T2+T3** | +46.25 | **+231.25** |
| 7 | 17:15 | ZLR | SHORT | 7825.25 | **cont_trend_filter** | 8.75 | 7830.50 | 7820.00 | **T1+T2+T3** | +45.75 | **+228.75** |
| 8 | 17:25 | FAMIR | LONG | 7818.00 | direction_context | 9.25 | 7812.50 | 7823.50 | stop 14:30 | −22.00 | **−110.00** |
| 9 | 16:40 | DRIVE | SHORT | 7826.25 | opening_strict | 6.67* | 7830.25 | 7822.25 | T1 then stop | +4.00 | **+20.00** |
| 10 | 16:50 | DRIVE | SHORT | 7827.00 | opening_strict | 8.75 | 7832.25 | 7821.75 | T1 then stop | +5.25 | **+26.25** |
| 11 | 17:05 | ORR | LONG | 7828.00 | opening_fusion | 9.00 | 7822.50 | 7833.50 | stop 14:15 | −22.00 | **−110.00** |
| 12 | 17:20 | DRIVE | SHORT | 7818.00 | opening_fusion | 8.75 | 7823.25 | 7812.75 | **T1+T2** | +33.50 | **+167.50** |
| 13 | 17:25 | DRIVE | SHORT | 7816.75 | opening_fusion | 8.75 | 7822.00 | 7811.50 | T1 then stop | +5.25 | **+26.25** |
| | | | | | | | | | **TOTAL** | **+15.00** | **+75.00** |

> **The whole first hour, fully unblocked, was worth +$75.** Not a fortune lost. The money is not
> spread across the hour — it is concentrated in candidates 6 and 7 at 17:15.

### Ranked gates by missed-$ (today)

| Rank | Gate | n | Missed pts | **Missed $** | W | L | Verdict |
|------|------|---|-----------|--------------|---|---|---------|
| 1 | **`cont_trend_filter`** | 2 | +92.00 | **+460.00** | 2 | 0 | **the whole miss** |
| 2 | `opening_dir_fusion` | 3 | +16.75 | +83.75 | 2 | 1 | cost money |
| 3 | `opening_first_trade_strict` | 2 | +9.25 | +46.25 | 2 | 0 | cost money |
| 4 | `direction_context` | 1 | −22.00 | −110.00 | 0 | 1 | **saved $110** |
| 5 | `awaiting_release` | 3 | −38.00 | −190.00 | 1 | 2 | **saved $190** |
| 6 | `lsma_flat` | 2 | −43.00 | −215.00 | 0 | 2 | **saved $215** |

---

## 3. The #1 gate — `cont_trend_filter`, why it fired, and whether it was right

**Code:** `backend/v9/gateway/trading_gateway.py:1402-1477` (inside the `DIRECTION_CONTEXT` block).
**Flags (live, `.env`):** `DIRECTION_CONTEXT=1`, `CONT_TREND_FILTER=1`, `LEG_RIDE_V1=1`,
`LEG_REPLACES_SUSTAINED_V1` **absent → OFF**.

### The input value vs the threshold

```
_sus = _dc.get("dir_sustained", "NEUTRAL")      # -> NEUTRAL
if _sus != _set_dir:                            # NEUTRAL != DOWN  -> block
```

ZLR resolves to family `CONT`, so it requires a **sustained** trend. `dir_sustained` was `NEUTRAL`.

**Was that input correct at 17:15, or stale?** — **It was CORRECT.** The preceding 45 minutes ranged
7819.25–7830.75 (11.5 pt) with −1.75 pt of net momentum. That is textbook balance. `dir_sustained`
was reading the market accurately. **This is not a stale-data bug.**

The problem is structural: **a continuation filter that requires a pre-existing sustained trend
mechanically blocks the initiation of every new trend.** The first entry of any new leg is, by
definition, taken when no sustained trend yet exists. The gate is therefore designed to be wrong
exactly once per trend — at the most valuable entry.

### Both escape hatches were shut — and one of them explains the 20-minute lag exactly

**Hatch 1 — displacement bypass** (`backend/v9/systems/release_gate.py:191-216`):

```python
thr  = float(os.getenv("RELEASE_TREND_BYPASS_PTS", "15"))   # 15 pt
disp = float(last_price) - float(session_open)
if abs(disp) < thr: return False
```

| | |
|---|---|
| RTH session open | 7827.75 |
| Entry at 17:15 | 7825.75 |
| **disp** | **−2.00 pt** — needs ≥ 15 → **shut** |
| Excursion from the 14:05 high (7830.75) | 5.00 pt — **not measured by this gate** |
| First bar reaching open − 15 = 7812.75 | **14:30** (low 7810.50) — verified by query |
| System actually fired | **14:35** — one bar later |

**This is the root of the 20-minute lag.** The bypass is anchored to the **session open**, not to the
**session extreme**. On a balance-then-break day the price at the break is ~0 pt from the open, so
the only escape hatch cannot open until the market has already travelled 15 pt — i.e. until the
move is largely over. The fire time was not a coincidence: it is arithmetically determined by this
threshold.

**Hatch 2 — LEG_RIDE** (`trading_gateway.py:105-132`, `LEG_RIDE_V1=1`): needs a formed leg
(`LSMA falling ×4` ≈ 20 min of established downtrend). Log evidence — the first
`LEG_RIDE: live DOWN leg ... agrees with SHORT` line today is at **18:40 IL**, 85 minutes after the
17:15 candidates. Also shut, for the same structural reason.

---

## 4. The opening-specific path — the detector worked, its guards did not

**The opening detector was not silent and it was not wrong.** It produced `DRIVE SHORT` — the correct
direction — from **16:40 IL**, ten minutes after the open. Three mechanisms killed it.

### 4a. `OPENING_FIRST_TRADE_STRICT_V1=1` — held on confidence 0.0

```
[FiveMin] OPENING_FIRST_TRADE_STRICT held DRIVE SHORT — opening confidence 0.0 < 0.6
```
at 16:40 and 16:50 IL. `OPENING_MIN_CONF=0.6`; `market_context.opening_conf` = 0.0
(`backend/v9/services/market_context.py:117`).

### 4b. `OPENING_CONF_ENGINE_FUSE_V1=1` — a catch-22, inert exactly when needed

This flag was built on 08-12 **specifically to fix 4a** (ruling: "engine score replaces detector score
when the detector is directional"). It cannot fire. `backend/v9/systems/opening_entry.py:405-411`:

```python
_DETECTOR_IS_DIRECTIONAL = (conf is not None and conf >= 0.5)
if (fuse_on and trigger_type in _ENGINE_CONF and _DETECTOR_IS_DIRECTIONAL):
    engine_conf = _ENGINE_CONF[trigger_type]          # DRIVE = 0.85
    if conf < engine_conf: conf = engine_conf
```

The fuse only engages when `conf >= 0.5` — but it is only *needed* when `conf` is 0.0. The guard
tests the very number the fuse exists to replace. **Result: on every day the detector returns 0.0,
the 08-12 fix is dead code.** It has never engaged (no `B1 CONF_FUSE` line anywhere in the log).

### 4c. `OPENING_DIR_FUSION_V1=1` — a gate that has **never once passed**

```
$ grep -ac "OPENING_DIR_FUSION] RESULT=" /tmp/backend.err.log
0
$ grep -a "OPENING_DIR_FUSION gate dropped" /tmp/backend.err.log | wc -l
8
```

**Zero passes, 8 drops, 100% veto rate.** This is not a filter; it is an off-switch for the opening path.

Two independent defects:

**(i) Wrong volume — a verified 40× under-read.** `backend/v9/services/trade_context.py:952`:

```python
opening_vol = sum(_f(_bg(b, "v", "volume")) or 0.0 for b in b6)
```

`_bg` looks for keys `"v"` and `"volume"`. The Sierra export bar dict carries **`vol`**:

```
$ python3 -c "...json.load(open('5min.json'))..." -> keys:
['ts','o','h','l','c','vol','poc_vol','vah','val','cumulative_delta']
has 'v'? False   has 'volume'? False   has 'vol'? True
```

So the sum silently collapses to `0.0` for export-sourced bars:

| | |
|---|---|
| Value fed to the fusion (log) | **2,212** |
| True first-6-RTH-bar volume (DB) | **89,246** |
| Trailing median (the code's own query) | **114,590.5** |

`2,212 < 114,590` is true by construction on every day forever. **This is a Rule-1 violation in
effect** — the gate reports a confident "auction/low-conviction" verdict from a number that is not
the opening volume.

**(ii) Even with the key fixed, today still skips — and that part is correct.** Re-running the
fusion's own rules on the true tape:

| Session | true opening_vol | median | ratio | 30-min delta | vol rule | mom rule (≥2.0) |
|---------|-----------------|--------|-------|--------------|----------|-----------------|
| 2026-08-13 | 117,574 | 114,359 | **1.028** | **+27.50 pt** | **PASS** | **PASS** |
| 2026-08-14 | 89,246 | 114,590 | 0.779 | −1.75 pt | SKIP | SKIP |

**On 08-13 the key bug alone cost the opening path.** On 08-14 the fusion's verdict ("auction /
low-conviction") was **substantively right** — the open genuinely was balanced.

Priced on the real tape, all 8 fusion drops (single-slot, 4 contracts):

| Session | Drops | Single-slot result |
|---------|-------|--------------------|
| 2026-08-13 | 5 × DRIVE LONG | +13.00 pt = **+$65.00** |
| 2026-08-14 | 1 × ORR LONG, 2 × DRIVE SHORT | +11.50 pt = **+$57.50** |
| | | **+$122.50 vetoed over 2 sessions** |

### 4d. Other opening flags — cleared

* **`opening_type_gate` = OFF** (`OPENING_TYPE_GATE=0`, ruled by Michael 08-13). Correctly not a factor.
* **`cold_start_guard`** — no blocks in the window.
* **`OPENING_OR_ATR_SCALE_V1=1`** — active, not a blocker (the OR cap was not the binding constraint).
* **`OPENING_ANCHOR_ET_V1=1`** — anchor resolved correctly; the 13:30 UTC open bar was recognised
  (the engine produced triggers from 13:40, proving collection worked).

---

## 5. 20-session base rate — and it inverts the obvious conclusion

**Sample:** all first-hour (09:30–10:35 ET) blocked candidates in `decisions_archive/` + today.
The `2026-08-11` archive file actually spans 07-22 → 08-11. **17 sessions** have both decisions and
bars (07-23, 07-24, 07-27..07-31, 08-03..08-07, 08-10..08-14). Sessions with decisions but no bars: none.
**102 blocked candidates, 70 taken after single-slot.**

Reported at **both** 1 contract (T1 only, as briefed) and 4 contracts (the actual live execution
model). The 1-contract view caps upside at T1 while charging the full stop, so it systematically
understates trend days — the 4-contract column is the decision-grade number.

| Gate | blocks | taken | sess | W | L | missed $ | saved $ | **NET $ (4c)** | NET $ (1c) |
|------|--------|-------|------|---|---|----------|---------|----------------|------------|
| `daytype_playbook` | 5 | 2 | 2 | 2 | 0 | 820.00 | 0.00 | **+820.00** | +131.25 |
| `extreme_chase_guard` | 13 | 6 | 5 | 4 | 2 | 841.25 | −160.00 | **+681.25** | +282.50 |
| `awaiting_release` | 32 | 24 | 11 | 10 | 14 | 2317.50 | −1975.00 | +342.50 | −13.75 |
| `news_blackout` | 1 | 1 | 1 | 1 | 0 | 275.00 | 0.00 | +275.00 | +20.00 |
| `direction_context` | 12 | 8 | 7 | 1 | 7 | 686.25 | −520.00 | +166.25 | +16.25 |
| `zone_limit_late_entry` | 1 | 1 | 1 | 1 | 0 | 103.75 | 0.00 | +103.75 | +20.00 |
| `entry_not_confirmed` | 1 | 1 | 1 | 1 | 0 | 53.75 | 0.00 | +53.75 | +20.00 |
| `duplicate_fire` | 1 | 1 | 1 | 0 | 1 | 0.00 | −80.00 | −80.00 | −20.00 |
| `location_gate` | 3 | 2 | 2 | 1 | 1 | 100.00 | −215.00 | −115.00 | −28.75 |
| `rr_hard_floor` | 4 | 2 | 1 | 1 | 1 | 57.50 | −175.00 | −117.50 | +71.25 |
| `lsma_flat` | 7 | 5 | 3 | 1 | 4 | 301.25 | −435.00 | −133.75 | −88.75 |
| `s4_risk_cap` | 3 | 1 | 1 | 0 | 1 | 0.00 | −215.00 | −215.00 | −53.75 |
| **`cont_trend_filter`** | **19** | **16** | **9** | **4** | **12** | **602.50** | **−1625.00** | **−1022.50** | −132.50 |
| **TOTAL** | 102 | 70 | | 27 | 43 | 6158.75 | −5400.00 | **+758.75** | +223.75 |

### The inversion

**`cont_trend_filter` — today's #1 villain — is the single most profitable gate in the stack.**
Over 17 sessions it blocked 19 first-hour candidates: 4 winners ($602.50 missed) and
**12 losers ($1,625.00 of losses prevented)** → **net +$1,022.50 saved**.

Per-session, fully relaxed (4c): 07-24 −$235 · 07-30 −$200 · 07-31 +$45 · **08-05 −$490** ·
08-06 +$46.25 · 08-07 +$40 · **08-10 −$320** · 08-11 −$140 · **08-14 +$231.25**.
Today is the *only* session where relaxing it would have paid meaningfully.

I tested the obvious repair — an **excursion-from-session-extreme** bypass to sit alongside the
15-pt-from-open one — at every sensible threshold. **All variants lose money:**

| Variant | released | W | L | pts | **NET $** |
|---------|----------|---|---|-----|-----------|
| today (block all) | 0 | 0 | 0 | 0.00 | **0.00** |
| FULL relax | 16 | 4 | 12 | −204.50 | −1022.50 |
| excursion ≥ 4 / 5 pt | 16 | 4 | 12 | −204.50 | −1022.50 |
| excursion ≥ 6 / 8 pt | 15 | 3 | 12 | −250.75 | −1253.75 |
| excursion ≥ 10 pt | 14 | 3 | 11 | −234.75 | −1173.75 |
| excursion ≥ max(4, 0.5 × step) | 16 | 4 | 12 | −204.50 | −1022.50 |
| excursion ≥ max(4, 0.75 × step) | 14 | 2 | 12 | −275.75 | −1378.75 |

Today's 5.0 pt excursion does not separate the winner from the 12 losers — they all clear 4–5 pt.
**There is no threshold on this axis that keeps today and rejects 08-05/08-10.**

---

## 6. PROPOSAL — three changes, and one deliberate refusal

> Nothing below has been enabled. `OPENING_FIRST_TRADE_STRICT_V1`, `OPENING_DIR_FUSION_V1`,
> `CONT_TREND_FILTER` and every other flag remain exactly as they were.

### P0 — DO NOT relax `cont_trend_filter`. ❌

The instinct is to open the gate that cost $460 today. **The 17-session evidence says that trade is
−$1,022.50.** Today is a tail, not a signal (4W/12L). Every bypass variant tested is net-negative.
Cost of acting on today alone: about **−$60/session**.

If Michael wants this revisited, the honest next step is a *pattern-quality* axis
(what separates the 08-14 ZLR from the 08-05/08-10 ZLRs), not a displacement threshold — that is a
research task, not a flag flip.

### P1 — Fix the fusion volume key. **Bug fix, no ruling needed.**

**File:** `backend/v9/services/trade_context.py:952`
**Change:** `_bg(b, "v", "volume")` → `_bg(b, "v", "volume", "vol")`

The gate is currently deciding on **2,212** when the canonical bars say **89,246** — a 40× under-read
caused purely by a key-name mismatch with the Sierra export (`vol`). This is a correctness fix under
Source-of-Truth Rule 1 (the gate is asserting a verdict from a number that isn't the measurement),
not a trading-risk change; it restores the behaviour the 07-24 study specified.

**Measured effect on the sample:** 08-13 flips SKIP → PASS (ratio 1.028, momentum +27.50 pt),
releasing 5 held DRIVE LONG triggers worth **+$65.00** single-slot. 08-14 is unchanged (still SKIP —
correctly). Expected effect ≈ **+$65 over the 2 sessions where the fusion ran**, and it turns a
0-pass gate into one that actually discriminates.

*Add a regression test asserting `opening_vol` equals the DB's first-6-bar sum for a known session
(Pre-LIVE: a test per bug fix).*

### P2 — Fix the `OPENING_CONF_ENGINE_FUSE_V1` catch-22. **Implements an existing ruling.**

**File:** `backend/v9/systems/opening_entry.py:407`
**Current:** `_DETECTOR_IS_DIRECTIONAL = (conf is not None and conf >= 0.5)`
**Proposed:** gate on the detector's **`opening_type`** being directional
(`OPEN_DRIVE` / `TEST_DRIVE` / `ORR` / `PULLBACK_CONT` / `EXTREME_REJECT`), **not** on the numeric
`conf` the fuse exists to replace. Auction days (`opening_type=AUCTION`) stay excluded exactly as
the 08-12 ruling requires — the exclusion moves from the confidence number to the type label, which
is what "כשהגלאי כיווני" actually means.

**Why it qualifies as ruled work:** Michael's 08-12 ruling already authorised the behaviour
("ציון-מנוע (DRIVE=0.85/ORR=0.65) מחליף ציון-גלאי כשהגלאי כיווני"). The flag is ON; the
implementation simply reads "directional" off the wrong field, so the ruled behaviour never
executes. Per CLAUDE.md § *Rulings are one-time and standing*, this is build → verify → enable
without a second approval, with the pointer recorded in `config/RULED_FLAGS.yaml`.

**Measured effect today:** releases candidates 9 and 10 (16:40, 16:50 DRIVE SHORT) →
**+$46.25** (2W/0L). Both banked T1 before stopping at breakeven — small, but positive and
correct-direction.

### P3 — Re-examine the two gates the base rate actually indicts. **Investigate, do not flip.**

Not `cont_trend_filter` — these:

| Gate | blocks | W | L | NET (4c) | Note |
|------|--------|---|---|----------|------|
| `daytype_playbook` | 5 | 2 | 0 | **+$820.00** | 0 losers blocked in 17 sessions |
| `extreme_chase_guard` | 13 | 4 | 2 | **+$681.25** | excursion bypass keeps all 4 winners at every threshold tested |

`extreme_chase_guard` is the one case where the excursion bypass *does* work — every threshold from
4 to 10 pt yields **+$681.25** (4W/2L), because its blocked winners are genuinely displaced entries.
**Small n (13 blocks / 5 sessions) — this needs a wider replay before any flag moves.**
Recommended: run `scripts/replay_*` over a 60-session window on these two gates and report back.

### Combined expected effect

| Change | Today | 17-session sample | Risk class |
|--------|-------|-------------------|------------|
| P0 (refuse to relax `cont_trend_filter`) | 0 | **+$1,022.50 preserved** | none |
| P1 (fusion volume key) | 0 | +$65.00 (08-13) | bug fix |
| P2 (conf-fuse catch-22) | **+$46.25** | releases held DRIVE triggers on every conf=0.0 day | ruled 08-12 |
| P3 (investigate 2 gates) | 0 | up to +$1,501 indicated, **unvalidated** | research |

P1+P2 together are worth about **+$111** across the two sessions where the opening path ran — modest,
but they convert a **100%-veto** opening path into one that can actually produce a first trade,
which is the thing Michael asked for on 07-31 and again on 08-12.

---

## 7. Answers to the five questions, in one line each

1. **Every decision extracted** — 13 candidates, not 7 (§1). Five were killed inside `five_min_system`
   and never appear in `gateway_decisions.jsonl`.
2. **Counterfactual** — the entire first hour unblocked is worth **+$75.00** at 4 contracts (§2);
   $460 of upside sits in two candidates at 17:15 and the rest of the hour is net-negative.
3. **Top gate** — `cont_trend_filter`. Its input (`dir_sustained=NEUTRAL`) was **correct, not stale**;
   its bypass is anchored to the session open (−2.00 pt vs a 15 pt threshold) and could not open until
   14:30, one bar before the system fired at 14:35 (§3).
4. **Opening path** — the detector **did** produce a classification, `DRIVE SHORT`, correct direction,
   from 16:40 IL. It was killed by a 100%-veto fusion (0 passes ever, verified) reading the wrong
   volume key, plus a conf-fuse that cannot engage at conf=0.0 (§4).
5. **Base rate** — over 17 sessions `cont_trend_filter` **saved $1,022.50**; the first-hour gate stack
   as a whole costs **+$758.75 (~$45/session)**; the real offenders are `daytype_playbook` and
   `extreme_chase_guard` (§5).

## 8. Reproduce

```bash
export PATH=/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH
grep -ac "OPENING_DIR_FUSION] RESULT=" /tmp/backend.err.log     # -> 0  (never passed)
grep -a  "OPENING_DIR_FUSION gate dropped" /tmp/backend.err.log | wc -l   # -> 8
grep -a  "OPENING_FIRST_TRADE_STRICT held" /tmp/backend.err.log
psql postgresql://localhost/mems26 -c "SELECT sum(volume) FROM (SELECT volume,
  row_number() OVER (ORDER BY ts) rn FROM v9_bars_5min_woodies WHERE symbol='MES'
  AND (ts AT TIME ZONE 'America/New_York')::date='2026-08-14'
  AND (ts AT TIME ZONE 'America/New_York')::time>='09:30') x WHERE rn<=6;"   # -> 89246
python3 -c "import json;d=json.load(open('/Users/michael/SierraChart_Data/v9_export/5min.json'));\
print([k for k in (d['bars'] if 'bars' in d else d)[0]])"                    # -> 'vol', no 'v'/'volume'
```

Analysis scripts (scratch, not committed): `/tmp/cf_opening_0814.py` ·
`/tmp/base_rate_opening.py` · `/tmp/base_rate_4c.py` · `/tmp/fusion_drops.py`

---
*cowork-dev · 2026-08-14 · no code, flags, or services were changed by this investigation.*
