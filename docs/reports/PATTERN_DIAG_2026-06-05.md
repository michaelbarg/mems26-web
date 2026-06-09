# Pattern Firing Diagnostics — 2026-06-05 (RTH 08:30–15:00 CT)

Source: live API via Chrome fetch → `http://localhost:8000`. Read/document only — no
code/logic changes. Sierra `~/SierraChart_Data/v9_export/` cross-checks flagged for CC.

---

## 09:12 CT — snapshot

**System state:** S2 five_min running (mode=FIRST_HOUR_TACTICAL, opening_type=OPEN_REJECTION_REVERSE, buffer=166) ·
S3 footprint running but **0 bars processed today** · S4 woodies running+hydrated (signal=HFE LONG) ·
gateway: no active blocks (cooldown/cluster/SSV all inactive, chop_state=EXPANDING) ·
live_enabled_systems=[] (demo_enabled=[2,4]) · **trades_today=0**, daily_pnl=0.

### S4 — woodies (`/api/v9/woodies/current`)

| pattern | armed | evaluated | fired | reject_reason / not_armed_reason |
|---------|-------|-----------|-------|----------------------------------|
| HFE | ✅ (active_patterns=[HFE], LONG, conf 0.7) | ✅ | ❌ | **A5 FAIL `calculate_size=reject`** — sizing rejected; ready_to_route=false |
| ZLR | ❌ | — | ❌ | not_armed: current signal=HFE only; ZLR not in active_patterns |
| TLB | ❌ | — | ❌ | not_armed: not in active_patterns |
| TT | ❌ | — | ❌ | not_armed: not in active_patterns |
| GB100 | ❌ | — | ❌ | not_armed: not in active_patterns |
| HTLB | ❌ | — | ❌ | not_armed: not in active_patterns |
| FAMIR | ❌ | — | ❌ | not_armed: not in active_patterns |

**decision_tree (pre_fire):** A1 PASS (trend_state=RED) · A2 PASS (11 studies present) ·
A3 PASS (patterns=['HFE']) · A4 PASS (touch-point advisory **context degraded**:
day_type/tpo/veto/killzone/layer0 all `missing`) · **A5 FAIL (`calculate_size=reject`)** ·
A6 PASS (code=STRATEGIC spec=INITIATIVE) · A7 SKIP (gateway/pre_fire run at route_setup).
failed_stages=[A5]. ready_to_route=false. classification=STRATEGIC.

**Raw inputs that cut the decision (⚠ Sierra cross-check required — SoT for CCI/study fields):**
cci_14=**-192.9** · cci_6_tcci=**-99.7** · czi=-125 · swi=-63.62 · ema_34=7551.1 ·
lsma=7532.2 · trend_state=RED · predictor_next_cci=-124.37.
HFE setup: entry=7519.25, stop=7516.75, targets=[7522.25, 7525.25].
→ **CC: cross-check cci_14/tcci/OHLC for this bar against `~/SierraChart_Data/v9_export/`.**

### S3 — footprint (`/api/v9/footprint/current`)

| pattern | armed | evaluated | fired | not_armed_reason |
|---------|-------|-----------|-------|------------------|
| ABSORPTION | ❌ | ❌ | ❌ | footprint **0 bars processed today** (buffer_size=0; all flow fields null) |
| STACKED_IMBALANCE | ❌ | ❌ | ❌ | same — no footprint bars ingested |
| SWEEP_RETURN | ❌ | ❌ | ❌ | same — no footprint bars ingested |
| EXHAUSTION | ❌ | ❌ | ❌ | same — no footprint bars ingested |

last_classification=NO_SETUP · delta/cumulative_delta/dominance/aggressive_flow/cot/amt all null.
**⚠ FINDING:** S3 stream reports running+hydrated yet `bars_processed_today=0` at 09:12 CT (≈42 min
into RTH). No S3 pattern can arm until footprint bars flow. Flag for CC (Sierra footprint export path).

### S2 — five_min (`/api/v9/five_min/current` + `/stats`)

| pattern | armed | evaluated | fired | reject_reason / not_armed_reason |
|---------|-------|-----------|-------|----------------------------------|
| REACTIVE_LONG | ❌ | ✅ (detector on 166 bars) | ❌ | patterns_detected=0; no pattern matched this window |
| REACTIVE_SHORT | ❌ | ✅ | ❌ | patterns_detected=0 |
| INITIATIVE_LONG | ❌ | ✅ | ❌ | patterns_detected=0 |
| INITIATIVE_SHORT | ❌ | ✅ | ❌ | patterns_detected=0 |
| INV_HNS | ❌ | ✅ | ❌ | patterns_detected=0 |
| HNS_TOP | ❌ | ✅ | ❌ | patterns_detected=0 |
| DOUBLE_BOTTOM_EE | ❌ | ✅ | ❌ | patterns_detected=0 |
| DOUBLE_TOP_AA | ❌ | ✅ | ❌ | patterns_detected=0 |
| BULL_FLAG | ❌ | ✅ | ❌ | patterns_detected=0 |
| BEAR_FLAG | ❌ | ✅ | ❌ | patterns_detected=0 |

mode=FIRST_HOUR_TACTICAL · opening_type=OPEN_REJECTION_REVERSE · buffer_size=166 ·
patterns_detected=0 · setups_published=0 · last_pattern=null.

### Gateways (S6 / risk) — `/api/v9/gateway/status`

No active blocks: cooldown inactive (0 consecutive stops) · cluster_guard inactive (0 attempts/60s) ·
SSV inactive (suffering_side=NONE) · chop_state=EXPANDING (not chop-blocked). shadow_active_count=0.
live_slot/demo_slot=null. **Nothing was blocked by a gate this window** — the only armed signal (S4 HFE)
was stopped earlier, at A5 sizing, before reaching the gateway.

### Trades — `/api/v9/trades/recent`

Empty array — **0 trades today**. Consistent with: S4 HFE blocked at A5 sizing, S3 no bars, S2 no patterns.

### Window summary
- Only **1 armed signal**: S4 **HFE LONG**, blocked at **A5 `calculate_size=reject`** (sizing). Not a gate
  reject — sizing computed 0/invalid. Whether justified needs the size-calc inputs (account/risk/contract
  config) cross-checked; raw CCI inputs flagged for Sierra SoT check above.
- **S3 entirely dark**: 0 footprint bars at 09:12 CT — anomaly, no S3 pattern can arm.
- **S2 quiet**: detector live on 166 bars, 0 patterns detected (legitimate — no setup yet this window).

### NOT-DONE / gaps
- **FHB state not exposed** by `/api/v9/five_min/current` (no ACCUMULATING/EARLY field) — could not record S2
  per-pattern `armed` via FHB state as spec §2 asks; used patterns_detected/detector-running as proxy.
- **A5 `calculate_size=reject` has empty `details{}`** — the exact sizing input that returned reject is not
  surfaced by the endpoint; needs DB/log read by CC to attribute (account equity / risk-per-trade / contract).
- **Sierra cross-checks pending (CC):** cci_14=-192.9, tcci=-99.7, OHLC for the HFE bar vs `~/SierraChart_Data/v9_export/`.
- **S3 zero-bars root cause** not diagnosed here (read-only) — flag for CC (footprint export → bridge → DB path).

---

## 09:42 CT — snapshot (deep, all sections + cross-endpoint audit)

**Clock:** 14:42 UTC = 09:42 CT (72 min into RTH). Live API via Chrome fetch → `http://localhost:8000`.
This snapshot adds the **`/api/v9/build/pattern-status`** panel (per-pattern reject reasons) and the
**Build Status UI** (`localhost:3000`) — surfacing 3 cross-endpoint contradictions not visible at 09:12.
Screenshot of the Build Status · Live Debug table captured inline (Chrome screenshot `ss_53415gh17`;
**save_to_disk unsupported this session** — image is in the run log, not persisted to a file path).

**System state:** S2 five_min running, mode **changed FIRST_HOUR_TACTICAL → DAY_TYPE_MODE** (buffer 179–181) ·
S3 footprint running but **still 0 bars** (3rd confirmation) · S4 woodies running+hydrated (signal=HFE LONG,
unchanged from 09:12) · gateway: no active blocks · trades_today=0 / daily_pnl=0 · demo=[2,4] live=[].

### ⚠ NEW — three cross-endpoint contradictions (Source-of-Truth violations)

| # | field | engine endpoint says | build/pattern-status + UI say | verdict |
|---|-------|----------------------|-------------------------------|---------|
| C-1 | **trend_state** | `woodies/current`=**RED** → A1 **PASS**, HFE armed, fails at **A5** | `build/pattern-status` S4=**GRAY** → **A1 veto ALL 9** patterns; readiness `s4_trend_not_stuck_gray=GRAY` | board shows **wrong block reason** for woodies (A1 GRAY veto) vs engine reality (A5 sizing). cci_14=-192.9 ⇒ RED is the plausible one. **CC: cross-check WSI trend_state vs Sierra CCI/TCCI.** |
| C-2 | **day_type** | `day_type/state`=**UNKNOWN**, stage A1, `bar_count=0`, ib_locked=false, all ib/globex/rth fields null | `build/pattern-status` readiness=**Normal CLASSIFIED**; S2 gate `nt_day_type=Normal` (src=db); UI "Normal CLASSIFIED 48%", IBH 7552.75/IBL 7505.75 47pt, OPEN_REJECTION_REVERSE EXTREME | day_type **is** classified (Normal, real IB) and consumed by S2/UI/build — but `day_type/state` endpoint reports a **dead instance** (bar_count=0) AND woodies **A4 still sees day_type:missing**. ⇒ **propagation/endpoint bug, not a classification failure.** Refines I-1. |
| C-3 | **bridge/streams** | S2 `five_min` has fresh bars (lag 87–209s, buffer 181); S1 fresh (last 17:40 IL) | Build Status UI: Bridge **OFFLINE/BLOCKED**, all 8 stream gates **`no_data` / Present ✗** while **Freshness "fresh <1s"** in the *same row*; readiness "dead: …,5min_bars" | classic **B-11 / I-5** confirmed live + visually. Board lies (rowid→ts_col). |

### S4 — woodies (`/api/v9/woodies/current`)

| pattern | armed | evaluated | fired | reject_reason |
|---------|-------|-----------|-------|---------------|
| HFE | ✅ (active_patterns=[HFE] LONG conf 0.7 group REVERSAL) | ✅ | ❌ | **A5 FAIL `calculate_size=reject`** (details{} **empty** — I-12 persists). last_reasoning_notes: `HFE LONG size=reject: CCI=-192.9, trend=RED, conf=0.70, group=REVERSAL` |
| ZLR·TLB·TT·GB100·HTLB·FAMIR | ❌ | — | ❌ | not_armed: not in active_patterns (engine view) |

**decision_tree (engine):** A1 PASS(RED) · A2 PASS(11 studies) · A3 PASS([HFE]) · A4 PASS(**context degraded**:
day_type/tpo/veto/killzone/layer0 all `missing`) · **A5 FAIL** · A6 PASS(code=STRATEGIC spec=INITIATIVE) ·
A7 SKIP. failed_stages=[A5]. ready_to_route=false.
**Raw inputs (⚠ Sierra SoT cross-check — CC):** cci_14=**-192.9**, tcci=-99.7, czi=-125, swi=-63.62,
ema_34=7551.1, lsma=7532.2, trend_state=RED, predictor_next_cci=-124.37. HFE entry=7519.25 stop=7516.75 T=[7522.25,7525.25].

> **⚠ build_status disagrees with the engine here:** its S4 panel blocks **all 9** woodies patterns at
> "Stage A1 veto: trend_state=GRAY" — see C-1. The board's reason is wrong; the true block is A5.

**5-questions:** 1) data? ✅ all studies present. 2) sane? CCI/levels sane; **but trend_state RED↔GRAY split (C-1) is not sane**.
3) blocked? engine=A5 sizing; board=A1 GRAY (contradiction). 4) should block? A5 reject ≈ saved ~1R (counterfactual)
→ plausibly justified, but **fired without day_type context (A4 degraded)** so sizing calibration unverified.
5) missing? day_type/tpo/killzone/layer0 not reaching woodies A4 context (C-2); A5 `details{}` empty (I-12).

### S2 — five_min (`/api/v9/five_min/*` + `build/pattern-status` sys 1)

`five_min/current` only exposes `patterns_detected=0` (no per-pattern reason). **`build/pattern-status` does** —
and the real reason is **not "no setup"**:

| pattern | state | reason (build/pattern-status) |
|---------|-------|-------------------------------|
| REACTIVE_LONG / REACTIVE_SHORT | blocked | **Missing: `data.choppiness_ok`** |
| INVERSE_HNS_LONG / HNS_TOP_SHORT | blocked | **Missing: `data.choppiness_ok`** |
| DOUBLE_BOTTOM_EE_LONG / DOUBLE_TOP_AA_SHORT | blocked | **Missing: `data.choppiness_ok`** |
| BULL_FLAG_LONG / BEAR_FLAG_SHORT | blocked | **Missing: `data.choppiness_ok`** |
| INITIATIVE_LONG / INITIATIVE_SHORT | blocked | **Auth Table SKIP for INITIATIVE × Normal** |

mode=DAY_TYPE_MODE · buffer 181 fresh (lag~104s) · global_gate nt_day_type=Normal(db) · 0 fired / 0 armed / 10 blocked.

**5-questions:** 1) data? bars flow (buffer 181 fresh). 2) sane? mode/opening_type sane. 3) blocked? **8/10 by a
missing input `data.choppiness_ok`** (not a no-setup condition — refines 09:12); 2/10 by Auth-Table skip of
INITIATIVE on Normal days. 4) should block? Auth-skip is a config decision (likely justified for Normal). **The
`choppiness_ok`-missing block is NOT justified — it's a missing/un-wired input gating 8 patterns.** 5) missing?
**`data.choppiness_ok`** is the missing wired field for all reactive/HNS/double/flag patterns. NEW — refines I-4.

### S3 — footprint (`/api/v9/footprint/current` + sys 3)

| pattern | reason |
|---------|--------|
| ABSORPTION · STACKED_IMBALANCE · SWEEP_RETURN · EXHAUSTION | **Insufficient buffer (0 bars, need ≥ 5)** |

`bars_processed_today=0`, buffer=0, all flow null, build_status freshness **fresh=false / last_bar_ts=null**.
**5-questions:** 1) data? ❌ none. 2) sane? n/a. 3) blocked? footprint stream dark (0 bars). 4) should block? yes —
can't detect on 0 bars. 5) missing? **whole footprint export→bridge→DB path** (I-11, now 3rd+ confirmation, and
corroborated by build_status `fresh=false`). **CC: diagnose footprint ingest.**

### S1 — day_type (`/api/v9/day_type/state` vs sys 4 vs UI) — see C-2

- `day_type/state`: stage A1, day_type **UNKNOWN**, bar_count **0**, ib_locked false, session_high 0, all levels null.
- `build/pattern-status` sys 4: running, fresh (last 17:40 IL), "**IB locked**, opening_type=OPEN_REJECTION_REVERSE, awaiting probability".
- UI: "**Normal · CLASSIFIED · 48%**", IBH 7552.75 / IBL 7505.75 (47pt), OPEN_REJECTION_REVERSE EXTREME.
**5-questions:** 1) data? split (UI/db yes, state-endpoint no). 2) sane? UI day_type Normal + real IB = sane; the
UNKNOWN endpoint is **not** sane vs a 72-min RTH session. 3) blocked? n/a (classifier). 4) should block? n/a.
5) missing? **propagation** — classification exists but (a) `day_type/state` shows a dead instance, (b) woodies A4
never receives it. Refines I-1 (it is NOT a true classification failure today).

### Gateways / Trades
gateway: no blocks (cooldown/cluster/SSV inactive, chop=EXPANDING). trades_today=**0**, daily_pnl=0. Nothing
gate-blocked this window; the only engine-armed signal (S4 HFE) died at A5 sizing before reaching the gateway.

### UI extras (Dashboard) — flag for CC
- **Y IB = `dll_missing`** (yesterday IB field omitted by Sierra DLL) → Sierra SoT gap. **CC: confirm DLL export.**
- Day 23/30 · 0 trades · WR 0% · SHADOW 0t $0.

### NOT-DONE / for CC (Sierra v9_export cross-checks)
- **C-1** trend_state RED(engine)↔GRAY(board): cross-check WSI/CCI-14/TCCI for this bar vs `~/SierraChart_Data/v9_export/`.
- **C-2** day_type propagation: why `day_type/state` reads bar_count=0 while db/UI=Normal; why woodies A4 never gets it.
- **C-3 / B-11**: bridge_inspector rowid→ts_col — board OFFLINE/dead while streams fresh <1s.
- **S2 `data.choppiness_ok`**: locate producer; 8 S2 patterns gated on a missing input.
- **I-11** footprint 0-bars: export→bridge→DB path.
- **I-12** A5 `details{}` empty: surface the sizing input (equity/risk/contract) that returns reject.
- HFE A5 cci_14=-192.9 / tcci=-99.7 / OHLC vs Sierra export. **Y IB `dll_missing`** Sierra DLL field.

---

## 10:09 CT — snapshot (deep, all sections; two 09:42 contradictions no longer reproduce)

**Clock:** 15:09:12 UTC = 10:09 CT (99 min into RTH). Live API via Chrome fetch → `http://localhost:8000`;
Build Status UI at `localhost:3000`. `build/pattern-status` ts=`2026-06-05T15:09:12Z`, RTH open, −289m to close.

**⚠ Likely backend restart since 09:42.** Buffers reset hard: `five_min` buffer **181 → 4**, `woodies`
`bar_count=2`/buffer 50 (was effectively full at 09:42). Bars are flowing **fresh** again (five_min lag
112–252s, last_bar 18:05 IL), so this is a re-hydration, not a feed loss. **The restart coincides with two
09:42 cross-endpoint contradictions disappearing (C-1 trend GRAY, I-16 choppiness_ok) — see below. CC: confirm
whether a restart/deploy happened ~10:00 CT and whether the C-1/I-16 fixes are durable or will recur on the
next stale-state build.**

**System state:** S2 five_min running (mode=DAY_TYPE_MODE, opening_type=OPEN_REJECTION_REVERSE, buffer 4,
**8 armed / 2 blocked / 0 fired**) · S3 footprint running+hydrated but **still 0 bars** (4th confirmation) ·
S4 woodies running+hydrated, **signal now NEUTRAL / NO_SETUP — HFE disarmed** (was armed 09:12+09:42),
trend_state=RED, all 9 patterns "armed · not yet detected" on the board · gateway: no blocks (cooldown/cluster/SSV
inactive, chop=EXPANDING) · trades_today=**0**, daily_pnl=0 · demo=[2,4] live=[].

### ✅ Two 09:42 contradictions resolved at 10:09 (verify durability — CC)

| # | 09:42 state | 10:09 state | verdict |
|---|-------------|-------------|---------|
| **C-1 / I-15** trend_state | board S4=**GRAY**, "A1 veto ALL 9"; engine=RED | board readiness `s4_trend_not_stuck_gray` **✓ trend_state=RED**; all 9 woodies "armed · trend RED · not yet detected"; engine trend_state=RED | **board now agrees with engine (RED).** GRAY veto gone. cci_14=-93.73 ⇒ RED plausible. Likely cleared by restart. **CC: still cross-check WSI/CCI vs Sierra export; confirm fix is durable.** |
| **I-16** S2 `data.choppiness_ok` | 8/10 S2 patterns blocked "**Missing: data.choppiness_ok**" | same 8 patterns now **armed** with real detection-stage reasons (b2_volume_drop, hns_structure, swing_highs, eve_variant, neckline_breakout, flag_length, pole_found) | **choppiness_ok now PRESENT — input is wired.** Flipped missing→present despite *fewer* bars (buffer 4 vs 181) ⇒ **not a bar-count effect; wiring/state changed (restart?).** CC confirm producer + durability. |

### ⛔ Three suspects still reproduce at 10:09 (unchanged)

| # | field | engine | board / UI | verdict |
|---|-------|--------|------------|---------|
| **C-3 / B-11 / I-5** bridge/streams | five_min + woodies fresh (lag 112–252s, real `last_bar_ts`) | Build Status: Bridge **OFFLINE / run off**; **all 8 stream gates** `no_data` / Present **✗** while Freshness **"fresh <1s"** in the *same row*; readiness BLOCKED "dead: …,**5min_bars**" | **board still lies** (rowid→ts_col). `5min_bars` flagged dead while S2 has fresh bars + 8 armed patterns. Confirmed visually again (screenshot below). 🔴 |
| **C-2 / I-1** day_type/state | `day_type/state` = **UNKNOWN**, stage A1, `bar_count=0`, ib_locked=false, all ib/globex/rth null | board readiness `s1_day_type_classified` **✓ day_type=Normal**; UI "Normal CLASSIFIED 48%", IBH 7552.75 / IBL 7505.75 (47pt) | classification exists + consumed by board/UI, but **`day_type/state` endpoint still a dead instance** (bar_count=0). Propagation/endpoint bug persists. 🔴 |
| **I-11** footprint 0-bars | `footprint/current` `bars_processed_today=0`, buffer=0, all flow null | board: 4 footprint patterns "Insufficient buffer (0 bars, need ≥ 5)"; freshness `fresh=false / last_bar_ts=null`; streams cumulative_delta/volume_profile/tick_reversal/imbalance all `no_data` | **footprint export→bridge→DB still dark — 4th confirmation** (09:12/09:24/09:42/10:09). Part of the readiness "dead" list (cumulative_delta/volume_profile/tick_reversal/imbalance) is **genuinely** dead — distinct from the false `5min_bars` entry. 🔴 |

### S4 — woodies (`/api/v9/woodies/current` + `build/pattern-status` sys woodies)

| pattern | armed (engine) | armed (board) | fired | reason |
|---------|----------------|---------------|-------|--------|
| HFE | ❌ (signal NEUTRAL, active_patterns=[]) | ✅ "armed · trend RED · not yet detected" | ❌ | **HFE disarmed since 09:42** — engine NO_SETUP this bar; board shows it armed-but-undetected |
| ZLR · TLB · TT · GB100 · HTLB · FaMir · Vegas · Ghost | ❌ (no active patterns) | ✅ "armed · trend RED · not yet detected" | ❌ | data ready, RED trend; detector found no setup this bar |

**decision_tree (engine, NO_SETUP bar):** A1 **SKIP** (no patterns) · A2 PASS (11 studies) · A3 SKIP (no patterns
this bar) · A4 SKIP (no setup needs touch-points) · **A5 PASS — `advisory:calculate_size=reject`** (now correctly
advisory, status PASS — *not* FAIL) · A6 SKIP (NO_SETUP) · A7 SKIP. failed_stages=**[]**, ready_to_route=false.
**Note (re I-2):** with no armed pattern, A5 renders as advisory PASS — confirming A5 should never be a hard block;
the 09:12/09:42 "A5 FAIL" only appeared while HFE was armed. last_direction_change=BEARISH (TCCI crossed below CCI14).
**Raw studies (⚠ Sierra SoT cross-check — CC):** cci_14=**-93.73**, cci_6_tcci=**-147.97**, ema_34=7533.42,
lsma_value=7512.98, swi_value=-67.3, czi_value=-73, trend_state=RED, predictor_next_cci=-174.48.

**5-questions:** 1) data? ✅ 11 studies present. 2) sane? cci_14 -93.73 / RED consistent; **board↔engine now agree
on RED (C-1 cleared)** — sane. 3) blocked? nothing armed → no block; engine NO_SETUP this bar. 4) should block? n/a
(no setup to block; A5 advisory only — correct). 5) missing? day_type still not reaching woodies A4 historically
(but A4 SKIP this bar); footprint context dark.

### S2 — five_min (`/api/v9/five_min/*` + `build/pattern-status` sys five_min)

| pattern | status | reason (board) |
|---------|--------|----------------|
| REACTIVE_LONG | 🟡 armed | Awaiting `b2_volume_drop` — b2_vol=120079 · b1_vol=15601 · ratio=7.70 ✗ |
| REACTIVE_SHORT | 🟡 armed | Awaiting `b1_buyers` — b1 close=7519.50 open=7523.00 dir=bear vol=15601 |
| INVERSE_HNS_LONG | 🟡 armed | Awaiting `hns_structure` — no valid triplet (head lowest, shoulders symmetric) |
| HNS_TOP_SHORT | 🟡 armed | Awaiting `swing_highs_found` — 2 swing highs in last 20 bars ✗ |
| DOUBLE_BOTTOM_EE_LONG | 🟡 armed | Awaiting `eve_variant` — T1 width=1 · T2 width=1 ✗ |
| DOUBLE_TOP_AA_SHORT | 🟡 armed | Awaiting `neckline_breakout` — close=7515.00 · neckline=7512.75 · gap=-2.50pt ✗ |
| BULL_FLAG_LONG | 🟡 armed | Awaiting `flag_length` — flag=12 bars (out of range 3–8) ✗ |
| BEAR_FLAG_SHORT | 🟡 armed | Awaiting `pole_found` — no valid pole (need ≥5 bearish, ≥4.00pt) |
| INITIATIVE_LONG | ❌ blocked | **Auth Table SKIP for INITIATIVE_LONG × Normal** (+ detection.b1_expansion) |
| INITIATIVE_SHORT | ❌ blocked | **Auth Table SKIP for INITIATIVE_SHORT × Normal** (+ detection.b1_expansion) |

mode=DAY_TYPE_MODE · buffer 4 (fresh, lag 112–252s) · patterns_detected=0 · setups_published=0 · 0 fired.

**5-questions:** 1) data? ✅ bars flow fresh; **choppiness_ok now present** (was the missing gate at 09:42). 2) sane?
detection reasons reference real OHLC/volume in market range — sane. 3) blocked? **only 2/10 blocked** (INITIATIVE,
Auth-Table); the other 8 are **armed and legitimately awaiting their detection condition** (not a missing-input
block anymore). 4) should block? INITIATIVE Auth-skip on Normal is a config decision (plausibly justified); the 8
armed patterns are correctly gated by genuine detection logic. 5) missing? nothing un-wired this window for S2 —
**I-16 no longer reproduces.** (Still flag: confirm choppiness_ok producer + durability after restart.)

### S3 — footprint (`/api/v9/footprint/current` + sys footprint)

| pattern | reason |
|---------|--------|
| ABSORPTION · STACKED_IMBALANCE · SWEEP_RETURN · EXHAUSTION | **Insufficient buffer (0 bars, need ≥ 5)** |

`bars_processed_today=0`, buffer=0, delta/dominance/aggressive_flow all null, cumulative_delta=0; board freshness
`fresh=false / last_bar_ts=null`. **5-questions:** 1) data? ❌ none. 2) sane? n/a. 3) blocked? footprint stream dark.
4) should block? yes — can't detect on 0 bars. 5) missing? **whole footprint export→bridge→DB path** (I-11, 4th
confirmation). The restart did **not** revive footprint — so footprint darkness is independent of the S2/S4 buffer
reset. **CC: diagnose footprint ingest.**

### S1 / day_type, Gateways, Trades

- `day_type/state`: stage A1, day_type **UNKNOWN**, confidence 0, lock_state PENDING, `bar_count=0`, ib_locked false,
  all ib/globex/rth levels null — **dead instance persists** (C-2/I-1). Board + UI both read **Normal CLASSIFIED 48%**.
- gateway: no blocks (cooldown 0 stops, cluster 0/60s, SSV NONE, chop=EXPANDING). trades_today=**0**, daily_pnl=0.
  Nothing gate-blocked; no engine-armed signal reached the gateway (woodies NO_SETUP, S2 awaiting detection).
- Dashboard extras: Day 23/30 · 0 trades · WR 0% · SHADOW 0t $0 · **Y IB still `dll_missing`** (Sierra DLL field gap).

### Screenshot — Build Status · Live Debug

Captured the Build Status table (Chrome screenshot `ss_6571kck6m`; **save_to_disk not persisted this session** —
image is inline in the run log, same limitation as 09:42). It visually shows: top banner **BLOCKED** "dead:
cumulative_delta,volume_profile,tick_reversal,imbalance,5min_bars" + Hebrew "אין חיבור לגשר"; readiness chips
**s1_day_type_classified ✓ · s4_trend_not_stuck_gray ✓ · in_rth ✓**; Bridge **OFFLINE / run off**; STREAM GATES (8)
each **no_data / Present ✗ with Freshness "fresh <1s"** in the same row (the B-11 lie); S2 header **8 armed / 2
blocked / DAY_TYPE_MODE**. (Dashboard view `ss_7486hta08`: Woodies NEUT, 5-Min IDLE, Normal CLASSIFIED 48%.)

### NOT-DONE / for CC (Sierra v9_export cross-checks)
- **Confirm restart ~10:00 CT** and whether **C-1 (trend GRAY)** + **I-16 (choppiness_ok)** fixes are *durable* or an
  artifact of a fresh build that will recur once state goes stale. Locate the `choppiness_ok` producer.
- **C-3 / B-11**: bridge_inspector rowid→ts_col — board OFFLINE + `5min_bars` dead while S2 bars fresh & 8 armed.
- **C-2 / I-1**: why `day_type/state` reads bar_count=0/UNKNOWN while board+UI consume Normal.
- **I-11**: footprint export→bridge→DB (restart did not revive it; 4th confirmation).
- **S4 studies**: cci_14=-93.73 / cci_6_tcci=-147.97 / OHLC for this bar vs `~/SierraChart_Data/v9_export/`.
- **Y IB `dll_missing`** Sierra DLL field still omitted.

---

## 10:44 CT — Snapshot (deep) · Cowork diagnostic

**Clock:** 10:44 CT (15:44 UTC) — **inside RTH** (08:30–15:00 CT). Build ts `2026-06-05T15:44:02Z`.
**Board verdict:** **READY · all checks passed** — `bridge_streams_fresh ✓ · s1_day_type_classified ✓ (Normal) ·
s4_trend_not_stuck_gray ✓ (RED) · in_rth ✓`. errors=[]. **The 10:09 "BLOCKED / OFFLINE / אין חיבור לגשר" board-lie
is GONE** (B-11/I-5 not reproducing this snapshot — see I-5 below).

### Raw values (this snapshot)
- **woodies/current:** running·hydrated, `cci_14=-149.43`, `cci_6_tcci=-167.36`, `ema_34=7524.86`, `lsma=7505.3`,
  `swi=21.06`, `czi=-123`, **trend_state=RED**, `predictor_next_cci=-172.06`, signal=NEUTRAL, buffer=50,
  active_patterns=**[]**, classification=**NO_SETUP**. dtree: A1 SKIP(no patterns) · A2 PASS(11 studies) · A3 SKIP ·
  A4 SKIP(no setup needs touch-points) · **A5 PASS "advisory:calculate_size=reject"** · A6 SKIP(NO_SETUP) · A7 SKIP.
- **five_min/current:** running·hydrated, mode=DAY_TYPE_MODE, buffer=6→9 (grew over snapshot),
  opening_type=**OPEN_REJECTION_REVERSE**, last_pattern=**DOUBLE_TOP_AA_SHORT**, last_confluence=**99**,
  last_reasoning=`DOUBLE_TOP_AA SHORT size=reject: 3-bar pattern, COT=-16897 vs AMT=-13339, location=far`.
- **five_min/stats:** patterns_detected=0, setups_published=0, buffer=6.
- **footprint/current:** running·hydrated, NO_SETUP, **bars_processed_today=0, buffer_size=0**, all flow fields null.
- **trades/recent:** **[]** (0 trades). **gateway:** demo_enabled=[2,4], live=[], daily_pnl=0, trades_today=0,
  cooldown inactive(0 stops) · cluster inactive(0/60s) · SSV NONE · chop_state=FOUND. **No gateway block active.**
- **day_type/state:** stage=B2, **day_type=Normal, conf=0.48**, lock=PENDING, **opening_type=UNKNOWN**, ib_width=WIDE,
  behavior=DEVELOPING, range=NORMAL.

### 5-question table — patterns

| System · Pattern | 1 data? | 2 sane? | 3 what blocked | 4 should block? | 5 missing |
|---|---|---|---|---|---|
| **S2 Reactive L/S** | ✓ | ✓ (chop=75, fhb COMPLETE bar13) | **Missing: data.choppiness_ok** (gate flag) | **partly — see I-16** | boolean `data.choppiness_ok` (score chop=75 exists, flag absent) |
| **S2 Initiative L/S** | ✓ | ✓ | **Auth Table SKIP × Normal** | **yes — by spec** | nothing (auth-table by design) |
| **S2 Inv H&S / H&S Top** | ✓ | ✓ | choppiness_ok + only 2 swing pts found | yes (no valid structure) | choppiness_ok flag; more swings |
| **S2 Dbl Bottom EE / Dbl Top AA** | ✓ | ✓ (trough/peak pair valid) | choppiness_ok; "awaiting trigger" | partly (I-16) | choppiness_ok flag |
| **S2 Bull/Bear Flag** | ✓ | ✓ | choppiness_ok; no valid pole(Bull) | partly (I-16) | choppiness_ok flag |
| **S3 Absorption/Stacked/Sweep/Exhaustion** | ❌ | n/a | **Insufficient buffer (0 bars, need ≥5)** | yes (can't detect on 0) | **whole footprint export→bridge→DB (I-11)** |
| **S4 ZLR/TLB/TT/GB100/Vegas/HnS/FailedZLR/HTLB/HFE** | ✓ (9 armed) | ✓ (trend RED, cci_14=-149) | none — "not yet detected" | no | nothing — armed, awaiting detection |

### 5-question — suspects (Issues Register)
- **I-1 / C-2 (day_type instance):** PARTIAL FIX. `day_type/state` now returns **Normal/0.48/B2** (was UNKNOWN/0/bar_count=0
  at 10:09) — but **`opening_type=UNKNOWN`** there while five_min + board + UI all hold **OPEN_REJECTION_REVERSE**, and S2
  component `day_type_known=Variation`. ⇒ day_type **does** flow to S2 now (paralysis claim refuted); only the
  state-endpoint's `opening_type` (and naming Normal↔Variation) still diverges from the live instance. **CC: reconcile the
  state-endpoint instance's opening_type + Normal/Variation label.**
- **I-2 (A5 advisory):** ✓ CONFIRMED not-a-blocker — dtree shows `A5 PASS "advisory:calculate_size=reject"` (passes, advisory).
- **I-3 (ZLR):** armed (trend RED), "ZLR not yet detected" — **no anti-pattern/gate block**, simply no pattern this bar. No counterfactual.
- **I-4 (S2 arming):** ✓ healthy — FHB=**COMPLETE bar 13**, detector progressing; min_bars buffer≥7 ✓.
- **I-5 / B-11 (board-lie):** **NOT reproducing** — board READY, `bridge_streams_fresh ✓`, Bridge row "No blockers · all
  patterns clear". The 10:09 OFFLINE/dead-streams banner is absent. **Residual (NEW, → C-4 below):** freshness labels still
  inconsistent.
- **I-11 (footprint dark):** **STILL DEAD — 5th confirmation.** 0 bars / buffer 0 / all 4 S3 "Insufficient buffer". Bridge
  gate `footprint` shows **Present ✓** ("lag ?") ⇒ the export file is written but **ingest→buffer is broken downstream**.
  Independent of S2/S4 (those have bars). **CC: footprint export→bridge→DB.**
- **I-13 (A5 sizing misses):** woodies NO_SETUP this bar (cci_14=-149 deep), A5 advisory reject. Separately S2 detected
  **DOUBLE_TOP_AA SHORT @ confluence 99** but `size=reject` (COT=-16897 vs AMT=-13339, location=far). High-confluence
  pattern killed by sizing — **counterfactual needs bars (CC/EOD)**; flag for calibration.
- **I-14 (opening entry didn't fire):** opening_type classified OPEN_REJECTION_REVERSE; the reversal did **not** route to a
  fired entry because INITIATIVE_L/S are **Auth-Table SKIP × Normal (by spec)**. day_type now flows; block is legitimate.
  Open Q for CC: is open-rejection-reverse *supposed* to route via INITIATIVE (auth-skipped) or a separate path?
- **I-15 / C-1 (trend GRAY conflict):** **NOT reproducing** — board `s4_trend_not_stuck_gray ✓ trend_state=RED` AND engine
  trend_state=RED. They agree; GRAY veto gone. cci_14=-149 ⇒ RED sane.
- **I-16 (choppiness_ok):** **REPRODUCING + intermittent.** At 15:39 UTC: **8 S2 armed / 2 blocked**. At 15:44 UTC: **all
  10 blocked** on `Missing: data.choppiness_ok`. Component carries `choppiness_ok = chop=75` (a **score** is present) yet the
  headline gate flag `data.choppiness_ok` (boolean) is treated **missing** ⇒ the wiring gap is real (score≠gate-flag), and the
  flip armed→blocked is bar-boundary driven. **Refutes the 10:09 "not reproducing" note.** **CC: wire the boolean
  `data.choppiness_ok` from the chop score (=75) producer; fix the "Missing" mislabel; decide if chop=75 should legitimately
  gate (then label "chop too high" not "missing").**
- **I-17 (restart/buffer volatility):** buffer 6→9 within the snapshot, then state flipped armed→blocked ⇒ S2 gate state is
  **volatile on bar boundaries**, consistent with the hypothesis. Footprint (I-11) stayed dead ⇒ independent.

### NEW finding — **C-4: freshness gates mix TZ (IL-local vs UTC) + stale-but-Present**
Bridge STREAM GATES (8) raw values:
`woodies_5min [FRESH] 0s · 2026-06-05 18:35:00` · `footprint … 18:39:31` · `5min_bars … 18:35:00` (these three carry
**Israel-local timestamps, UTC+3, no TZ marker** — board can't compute lag → UI shows **"lag ?"**); vs
`cumulative_delta 2026-06-05T15:34:59` / `volume_profile …T15:39:33` (**proper UTC** → "stale 3m" / "fresh 3s").
`imbalance 2026-06-05T15:10:07` shows **Present ✓ / "stale 33m"** despite `required < 90s` (should be DEAD). `tpo_bars`
DEAD `2023-11-25` (S5/TPO unwired). ⇒ **CLAUDE.md Rule 4 violation (TZ ambiguity in spec inputs)** + a Present/required
mismatch on `imbalance`. **CC: normalize all bridge-gate timestamps to UTC at the boundary; enforce required-lag on
Present.** (Lower severity than B-11 but same family.)

### Screenshot — Build Status · Live Debug
Captured the Build Status table via Chrome computer-screenshot — **`ss_1002g70j7`** (Build Status · Live Debug, S2 detail)
and **`ss_31036aye2`** (Dashboard: Variation CLASSIFIED 48%, OPEN_REJECTION_REVERSE WIDE, IB 7552.75/7505.75 47pt WIDE,
**Y IB `dll_missing`**, 23 FOUND, 0 trades, WR 0%, Day 23/30). **`save_to_disk` not persisted this session** — images are
inline in the run log only (same tooling limitation noted 09:42 & 10:09; relevant to I-9).

### NOT-DONE / for CC (Sierra v9_export cross-checks)
- **S4 studies — Sierra=SoT:** cross-check `cci_14=-149.43 / cci_6_tcci=-167.36 / ema_34=7524.86 / lsma=7505.3 /
  swi=21.06 / czi=-123` and this bar's OHLC against `~/SierraChart_Data/v9_export/`. Any Sierra↔backend gap = finding.
- **I-16 choppiness_ok producer** — locate it; wire the boolean gate from the chop score (=75). Durability across bars.
- **I-11 footprint** ingest path (file Present ✓ but 0 bars) — 5th confirmation, still independent of restart.
- **I-1/C-2** state-endpoint instance: opening_type=UNKNOWN + Normal/Variation label vs live OPEN_REJECTION_REVERSE.
- **C-4 (new)** TZ-normalize bridge gates; enforce required-lag on Present (imbalance stale-33m/Present-✓).
- **Y IB `dll_missing`** — yesterday's IB still omitted by the Sierra DLL.
- **No counterfactual** computed (read-only, no bar-replay this snapshot): DOUBLE_TOP_AA conf=99 size=reject → for EOD.

## 11:08 CT — Snapshot (deep) · Cowork diagnostic (scheduled, unattended)

**System state:** S2 five_min running+hydrated (mode=**DAY_TYPE_MODE**, opening_type=OPEN_REJECTION_REVERSE,
buffer=21) · S3 footprint running+hydrated but **0 bars processed today** (buffer=0, all flow null) ·
S4 woodies running+hydrated (signal=NEUTRAL, **NO active patterns**, trend_state=RED) · gateway: no active
blocks (cooldown/cluster/SSV all inactive, **chop_state=FOUND**) · live_enabled=[] (demo_enabled=[2,4]) ·
**trades_today=0**, daily_pnl=0. day_type/state: **Variation 0.48 / stage B2 / lock PENDING / IB WIDE**.

### S4 — woodies (`/api/v9/woodies/current`)

Raw: `cci_14=-130.07 · cci_6_tcci=-172.96 · ema_34=7513.75 · lsma=7485.18 · swi=-17.09 · czi=-144 ·
trend_state=RED · predictor_next_cci=-154.96 · signal=NEUTRAL · active_patterns=[] · classification=NO_SETUP · buffer=50`.

| pattern | armed | evaluated | fired | reject / not_armed reason |
|---------|-------|-----------|-------|---------------------------|
| ZLR/TLB/TT/GB100/HFE/HTLB/FAMIR | ❌ | — | ❌ | **NO_SETUP** — none in active_patterns this bar (signal=NEUTRAL) |

**decision_tree (pre_fire):** A1 SKIP(no patterns) · A2 PASS(11 studies) · A3 SKIP(no patterns this bar) ·
A4 SKIP(no setup needs touch-points) · **A5 PASS — `advisory:calculate_size=reject`** (advisory only, no pattern to gate) ·
A6 SKIP(NO_SETUP) · A7 SKIP(gateway runs at route_setup).
*5-Q:* (1) data=yes; (2) sane — CCI -130, trend RED, studies 11/11 present, price-band OK; (3) blocked=nothing,
genuinely no setup (NEUTRAL signal, empty active_patterns); (4) should-block=N/A; (5) missing=A4 touch-point context
still shows day_type/tpo as advisory inputs but woodies has no pattern so no impact this bar.

### S3 — footprint (`/api/v9/footprint/current`) — **I-11 confirmed (6th)**
Raw: `running=true, hydrated=true, bars_processed_today=0, buffer_size=0, aggressive_flow=null, delta=null,
cumulative_delta=0, dominance=null, cot=0, amt=null, combined_class=null, last_fire=null`.
*5-Q:* (1) data=**NO** (0 bars all day); (2) n/a; (3) blocked=ingest path — file Present at bridge gate but
buffer never fills; (4) n/a; (5) missing=**the footprint export→bridge→DB→buffer ingest is broken downstream of
the file write.** ABSORPTION/STACKED_IMBALANCE/SWEEP_RETURN/EXHAUSTION all **un-armable** (need ≥5 bars, have 0).
Independent of the ~10:00 restart that re-hydrated S2/S4. **CC: diagnose footprint ingest.**

### S2 — five_min (`/api/v9/five_min/current` + `/stats`)
Raw: `mode=DAY_TYPE_MODE, buffer=21, opening_type=OPEN_REJECTION_REVERSE, last_pattern=DOUBLE_TOP_AA_SHORT,
last_confluence=88, last_classification=DOUBLE_TOP_AA,
last_reasoning_notes="DOUBLE_TOP_AA SHORT size=reject: 3-bar pattern, COT=-19652 vs AMT=-16065, location=far"`.
stats: `patterns_detected=0, setups_published=0`.

| pattern | armed | fired | reason |
|---------|-------|-------|--------|
| DOUBLE_TOP_AA_SHORT | ✅ detected (conf 88) | ❌ | **size=reject** — 3-bar pattern, COT=-19652 vs AMT=-16065, **location=far** |
| REACTIVE/INITIATIVE/INV_HNS/HNS_TOP/DOUBLE_BOTTOM_EE/BULL_FLAG/BEAR_FLAG | — | ❌ | not detected this bar (stats patterns_detected=0) |

*5-Q (DOUBLE_TOP_AA):* (1) data=yes (pattern formed, conf 88); (2) sane — short bias matches RED trend +
OPEN_REJECTION_REVERSE; (3) blocked=**sizing reject** (location=far from value, COT/AMT divergence); (4) should-block —
*plausibly justified* (entry "far" = poor R), but this is the **S2-side analogue of I-13** (sizing rejecting a
high-confluence pattern) → counterfactual needed at EOD to judge if the reject saved or cost; (5) missing=`details{}`
of the sizing reject not exposed on endpoint (same gap as I-12 on S4).

### Gateway / day_type / trades
- gateway: `chop_state=FOUND`, cooldown/cluster/SSV inactive, `trades_today=0`, `daily_pnl=0`, live=[], demo=[2,4].
- day_type/state: `stage=B2, day_type=Variation, confidence=0.48, lock_state=PENDING, opening_type=UNKNOWN,
  ib_width=WIDE, behavior=DEVELOPING, range_category=NORMAL`.
- trades/recent?limit=50: **0 rows** (consistent with trades_today=0).

### Cross-endpoint audit (findings)
- **I-1 / C-2 — day_type CLASSIFIED, NOT UNKNOWN.** state endpoint = Variation 0.48 / B2 (no longer UNKNOWN/bar_count=0).
  **Residual:** `opening_type=UNKNOWN` in state endpoint while five_min **and** UI = `OPEN_REJECTION_REVERSE`. The
  partial instance-mismatch persists → the "S2 paralysed by UNKNOWN day_type" claim remains **disproven**.
- **I-15 / C-1 — trend_state agreement, durable.** woodies engine=RED, UI Woodies CCI TrendDown 1.00 (=RED), no GRAY
  veto. Stable across 10:09 / 10:44 / 11:08 ⇒ **durable**, not a fresh-build artifact. Still pending Sierra CCI cross-check.
- **B-11 — NOT reproducing.** Dashboard board = 🟢 **LIVE**, IB/value/ranges all populated. Consistent with 10:44.
- **I-13 (A5 sizing) — no woodies setup this bar**, so A5 reject is advisory-with-nothing-to-gate. The live sizing-reject
  this snapshot is on the **S2 side** (DOUBLE_TOP_AA conf 88 → reject) — see S2 5-Q above.

### NEW finding — **C-5: `/api/v9/build/pattern-status` hangs (no response)**
Fetched 3× with 5–6s AbortController timeouts; **every call hit the 45s CDP ceiling without resolving** (abort did not
fire — request never returned). Other endpoints (woodies/footprint/five_min/gateway/day_type/trades) all responded
<1s in the same session. Previous snapshots (09:42–10:44) read pattern-status fine ⇒ **regression or load-induced
stall.** Risk: build/pattern-status is the heaviest read and the backend is single-worker uvicorn — a hang here can
choke health/polling. **CC: profile the pattern-status route; confirm it isn't blocking the event loop.** Because of
this hang, **I-16 (`data.choppiness_ok` gate) could not be re-verified this snapshot.** (Note: gateway chop_state=FOUND,
UI chop score = **25** — earlier I-16 referenced chop=75; chop value has moved, gate-flag wiring still unverified.)

### Build Status snapshot (Chrome page text — OS screenshot unavailable)
`request_access` for an OS-level screenshot **timed out (180s)** — this is an **unattended scheduled run**, no user
present to approve the access dialog (relevant to I-9). Captured the Build Status via Chrome `get_page_text` instead:
> Board 🟢 LIVE/SHADOW · MES · **VAR 48% M** · 5 Min / Tick Rev · **7,481.25** (B7480.75/A7481.00 Sz12856, 0.6s ago) ·
> $0/$200 · WR 0% · 0 trades · chop **25 FOUND** · SS:NONE · TODAY POC 7515.00 (VAH7535.25/VAL7498.00) ·
> YEST POC 7576.75 · **IB TODAY H7552.75/L7505.75 47.0pt WIDE** · **Y IB `dll_missing`** · YEST RANGE 69.8pt ·
> TODAY RANGE 78.5pt · **OPEN REJECTION REVERSE / Variation / MIDDAY** · Woodies CCI **-113.84 TrendDown 1.00**.

*(Minor: UI Woodies CCI=-113.84 vs endpoint cci_14=-130.07 — bar-refresh timing skew, not a contradiction; both RED.)*

### NOT-DONE / for CC (Sierra v9_export cross-checks)
- **S4 studies — Sierra=SoT:** cross-check `cci_14=-130.07 / cci_6_tcci=-172.96 / ema_34=7513.75 / lsma=7485.18 /
  swi=-17.09 / czi=-144` + this bar OHLC against `~/SierraChart_Data/v9_export/`. Any gap = finding.
- **C-5 (NEW)** profile `/api/v9/build/pattern-status` hang — event-loop block on single-worker uvicorn.
- **I-11 footprint** ingest (file Present, 0 bars) — 6th confirmation, independent of restart.
- **I-1/C-2** state-endpoint `opening_type=UNKNOWN` vs live OPEN_REJECTION_REVERSE — residual instance mismatch.
- **I-16** choppiness_ok gate-flag wiring (chop score now 25) — **unverified this snapshot** (pattern-status hung).
- **Y IB `dll_missing`** — yesterday's IB still omitted by the Sierra DLL.
- **No counterfactual** (read-only, no bar-replay): S2 DOUBLE_TOP_AA conf=88 size=reject(location=far) → for EOD.

---

## 11:38 CT — Snapshot (deep, all sections + 5-Q per pattern) · Cowork diagnostic (scheduled, unattended)

**System state:** S2 five_min running+hydrated (mode=**DAY_TYPE_MODE**, opening_type=OPEN_REJECTION_REVERSE,
buffer=12, FHB=**COMPLETE bar=13**, all 10 patterns **armed**) · S3 footprint running+hydrated but **0 bars
processed today** (buffer=0, cumulative_delta=0, all flow null; 4 patterns blocked) · S4 woodies running+hydrated
(signal=**NEUTRAL**, **NO active_patterns**, trend_state=RED, buffer=50) · gateway: no active blocks
(cooldown/cluster/SSV all inactive, **chop_state=FOUND**) · live_enabled=[] (demo_enabled=[2,4]) ·
**trades_today=0**, daily_pnl=0, trades/recent=**0 rows**. day_type/state: **Variation 0.48 / stage B2 / lock
PENDING / IB WIDE / opening_type=UNKNOWN / session_min=0**.

Endpoint latencies (same session): woodies 27ms · footprint 6ms · five_min 39ms · five_min/stats 4ms ·
gateway 4ms · day_type 36ms · trades <10ms · **build/pattern-status 138ms then 60ms** (see C-5 — not reproducing).

### S2 — five_min (`/api/v9/build/pattern-status` sys-1; `/api/v9/five_min/*`)

All 10 patterns **armed** and awaiting genuine detection conditions — **no `Missing: data.choppiness_ok`
this snapshot** (gate present: component `choppiness_ok = chop=69`, present:true). FHB=COMPLETE,
auth_table_cell=**FULL 3/2/2**, day_type_known=Variation, min_bars buffer=20≥7 ✓.

| pattern | armed | reject/awaiting (exact detection gate) | 1.נתון? | 2.הגיוני? | 3.מה חסם? | 4.צריך לחסום? | 5.מה חסר? |
|---------|-------|-----------------------------------------|---------|-----------|-----------|---------------|-----------|
| REACTIVE_LONG | ✅ | `b2_volume_drop` b2_vol=20134/b1_vol=186757 ratio=0.11 ✗ | yes | yes | detection.b2_volume_drop | justified (no setup) | — |
| REACTIVE_SHORT | ✅ | `b1_buyers` b1 close=7472.00 open=7475.75 dir=bear | yes | yes | detection.b1_buyers | justified | — |
| INITIATIVE_LONG | ✅ | `b1_expansion` b1 range=8.25 need [4.5,6.0] ✗ | yes | yes | detection.b1_expansion | justified (range too wide) | — |
| INITIATIVE_SHORT | ✅ | `b1_expansion` range=8.25 need [4.5,6.0] ✗ | yes | yes | detection.b1_expansion | justified | — |
| INVERSE_HNS_LONG | ✅ | `swing_lows_found` 1 in last 20 bars ✗ | yes | yes | detection.swing_lows_found | justified | — |
| HNS_TOP_SHORT | ✅ | `swing_highs_found` 1 in last 20 bars ✗ | yes | yes | detection.swing_highs_found | justified | — |
| DOUBLE_BOTTOM_EE_LONG | ✅ | `swing_lows_found` 1 found ✗ | yes | yes | detection.swing_lows_found | justified | — |
| DOUBLE_TOP_AA_SHORT | ✅ | `swing_highs_found` 1 found ✗ | yes | yes | detection.swing_highs_found | justified | — |
| BULL_FLAG_LONG | ✅ | `pole_found` no valid pole (need ≥5 bull bars, ≥4.00pt) | yes | yes | detection.pole_found | justified | — |
| BEAR_FLAG_SHORT | ✅ | `flag_length` flag=10 bars (range 3–8) ✗ | yes | yes | detection.flag_length | justified | — |

**Reading:** S2 is **healthy** this snapshot — every pattern armed, every block is a real per-pattern detection
criterion (volume-drop ratio, b1 expansion band, swing count, pole/flag geometry), **not** a missing input.
→ **I-16 NOT reproducing** (choppiness_ok present=true, chop=69). → INITIATIVE no longer Auth-Table SKIP×Normal;
now `auth_table_cell=FULL 3/2/2` ⇒ **I-14 auth-block cleared this snapshot** (still no opening entry fired, but
not because of auth). patterns_detected=0, setups_published=0.

### S3 — footprint (`/api/v9/footprint/current`; pattern-status sys-3)

| pattern | armed | reason | 1.נתון? | 2.הגיוני? | 3.מה חסם? | 4.צריך לחסום? | 5.מה חסר? |
|---------|-------|--------|---------|-----------|-----------|---------------|-----------|
| ABSORPTION | ❌ blocked | Insufficient buffer (0 bars, need ≥5) | **NO** | n/a | ingest dead (0 bars) | n/a — can't arm | **footprint feed** |
| STACKED_IMBALANCE | ❌ blocked | Insufficient buffer (0 bars, need ≥5) | **NO** | n/a | ingest dead | n/a | footprint feed |
| SWEEP_RETURN | ❌ blocked | Insufficient buffer (0 bars, need ≥5) | **NO** | n/a | ingest dead | n/a | footprint feed |
| EXHAUSTION | ❌ blocked | Insufficient buffer (0 bars, need ≥5) | **NO** | n/a | ingest dead | n/a | footprint feed |

**I-11 — 7th confirmation.** `bars_processed_today=0`, buffer=0, cumulative_delta=0, all flow null. None of the 4
S3 patterns can arm. **Escalation this snapshot:** the dead footprint family now blocks the **whole board** —
readiness `bridge_streams_fresh` = **passed:false / severity:block / "dead: tick_reversal"** ⇒ board verdict
**BLOCKED** (see below). At 10:44 footprint was equally dead but board read READY; now the same death is gating.
read-only here → **CC: footprint export→bridge→DB ingest, and why `tick_reversal` flips to dead-severity.**

### S4 — woodies (`/api/v9/woodies/current`; pattern-status sys-2)

Engine signal=**NEUTRAL**, active_patterns=**[]**, classification=NO_SETUP. decision_tree pre_fire:
A1 SKIP (no patterns) · A2 PASS (11 studies) · A3 SKIP (no patterns this bar) · A4 SKIP (no setup needs
touch-points) · A5 **PASS** (advisory:calculate_size=reject) · A6 SKIP (NO_SETUP) · A7 SKIP. No failed stages.
In pattern-status sys-2 **all 9 patterns armed**: "Data ready, trend RED · <X> not yet detected" (ZLR, TLB, TT,
GB100, Vegas, Ghost, FaMir, HTLB, HFE) — **no GRAY veto**.

| pattern | armed | reject/not_armed | 1.נתון? | 2.הגיוני? | 3.מה חסם? | 4.צריך לחסום? | 5.מה חסר? |
|---------|-------|------------------|---------|-----------|-----------|---------------|-----------|
| ZLR | ✅ armed (board) | "trend RED · not yet detected"; engine active_patterns=[] | yes | yes | A3: no pattern this bar | justified (no setup) | — (I-3: still no ZLR-armed day) |
| HFE | ✅ armed (board) | not in active_patterns this bar | yes | yes | A3: not detected | justified | — |
| TLB/TT/GB100/HTLB/FaMir/Vegas/Ghost | ✅ armed (board) | not detected this bar | yes | yes | A3: not detected | justified | — |

**Raw S4 inputs (⚠ Sierra cross-check = SoT):** cci_14=**-126.44** · cci_6_tcci=**-121** · ema_34=**7501.32** ·
lsma=**7465.63** · swi=**-11.56** · czi=**-140** · trend_state=**RED** · predictor_next_cci=**-123.26**.
→ **CC: cross-check cci_14/tcci/OHLC for this bar vs `~/SierraChart_Data/v9_export/`.**
**I-15/C-1 — stable RED, 4th consecutive (10:09/10:44/11:08/11:38), durable, no GRAY.**
**I-13/A5** — A5 advisory `calculate_size=reject` but **no woodies setup this bar** ⇒ nothing to gate; no sizing
finding to calibrate this snapshot (engine NO_SETUP).

### Gateway / board readiness

gateway: chop_state=FOUND; cooldown/cluster/SSV all inactive; demo_enabled=[2,4], live_enabled=[].
**readiness.verdict = BLOCKED**, reason **"dead: tick_reversal"**:
- `bridge_streams_fresh` **passed:false · block · "dead: tick_reversal"** ← the only failing check; halts the board.
- `s1_day_type_classified` passed:true · "day_type=**Normal**" ← ⚠ disagrees with state/UI/S2 (=**Variation**).
- `s4_trend_not_stuck_gray` passed:true · "trend_state=RED".
- `in_rth` passed:true · "RTH 09:30-16:00 ET".

### Cross-endpoint audit (findings this snapshot)

- **I-11 escalates — footprint death now BLOCKS the board.** `tick_reversal` dead ⇒ `bridge_streams_fresh` fails
  (block severity) ⇒ verdict BLOCKED. Same 0-bar footprint as prior snapshots, but now board-gating. **Finding.**
- **I-1 / C-2 — day_type label split persists, and now 3-way.** state endpoint=**Variation** (B2, 0.48, lock
  PENDING) · UI=**Variation CLASSIFIED 48%** · S2 component day_type_known=**Variation** · but readiness check
  `s1_day_type_classified`="day_type=**Normal**". The Normal↔Variation instance mismatch is unresolved; **+ new:**
  state endpoint `opening_type=**UNKNOWN**` and `session_min=**0**` at 11:38 CT (≈188 min into RTH) while
  five_min+UI=OPEN_REJECTION_REVERSE / MIDDAY 1:22 ⇒ the state-endpoint instance is **not tracking session
  progression** (session_min stuck at 0) — strengthens the dead/stale-instance hypothesis.
- **I-16 — NOT reproducing.** choppiness_ok present=true (chop=69); all 10 S2 armed. (UI chop strip shows "10
  FOUND" while S2 component=chop=69 and earlier gateway=FOUND ⇒ chop value differs across surfaces — bar/refresh
  skew, flagged but low-severity; the boolean gate-flag IS wired this snapshot.) Confirms I-17 volatility: I-16
  is a bar-boundary flip, not a permanent missing input.
- **I-15 / C-1 — durable RED.** 4 consecutive snapshots agree (engine RED + UI TrendDown 1.00 + board not-GRAY).
- **C-5 — NOT reproducing.** build/pattern-status returned 138ms then 60ms (200). The 11:08 45s-hang did not
  recur ⇒ **load-induced / intermittent stall, not a hard regression.** Keep watching.
- **B-11 — NOT reproducing.** Bridge sys-0 mode=LIVE; board 🟢 LIVE; IB/value/ranges populated.
- **Prices sane:** last 7458.00 (B7457.75/A7458.00, 0.2s ago); TODAY 7457.25–7552.75 (95.5pt); ema 7501.32 /
  lsma 7465.63 — all in-band MES values. (Q2 הגיוני ✓ across price/CCI/day_type.)

### NEW finding — **C-6: `bridge.data_freshness.lag_seconds = -10467s` with `fresh=true`**

Bridge aggregate freshness: `last_bar_ts=null`, `lag_seconds=**-10467.4**` (≈ −2.9h, **negative**),
`fresh=true`, `threshold_seconds=90`. A negative lag of ~2.9–3h is the **TZ-mix signature** (IL-local UTC+3 ts
compared against UTC `now` ⇒ I-18/C-4 / CLAUDE.md Rule 4), and `fresh=true` despite |lag| ≫ 90s means the
freshness predicate **does not enforce the threshold on a negative/garbage lag**. Distinct from the per-stream
`tick_reversal` death that actually gates the board. **CC: TZ-normalize the bridge aggregate `last_bar_ts` to UTC
at the boundary and enforce `|lag| ≤ threshold` (reject negative lag) before setting `fresh=true`.**

### Build Status table (Chrome `get_page_text` — OS screenshot unavailable)

OS-level screenshot (`computer action=screenshot`) requires `request_access`, which needs interactive user
approval; this is an **unattended scheduled run** (no user present — relevant to I-9), so the dialog cannot be
satisfied. Captured the Build Status board via Chrome `get_page_text` (frontend `localhost:3000`) instead:

> Board 🟢 **LIVE/SHADOW** · MES · **VAR 48% M** · — CLOSED · 5 Min / Tick Rev · **7,458.00**
> (B7457.75/A7458.00 S0.25 Sz6476, 0.2s ago) · $0/$200 · WR 0% · SHADOW 0t · 0 trades · VF 0 · ZLx 0 · POC no ·
> IBx 6 · R/A 1.11 · P-V 1.6 · chop **10 FOUND** · SS:NONE · News — · TODAY POC 7515.00 (VAH7542.00/VAL7491.25) ·
> YEST POC 7576.75 (VAH7601.25/VAL7552.25) · **IB TODAY H7552.75/L7505.75 47.00pt WIDE** · **Y IB `dll_missing`** ·
> YEST RANGE 69.75pt · TODAY RANGE H7552.75/L7457.25 95.50pt · **OPEN REJECTION REVERSE / Variation / MIDDAY 1:22** ·
> Woodies CCI **-136.31 TrendDown 1.00** (=RED). Systems strip: FIRING — **2 IDLE 5-Min · 3 — Footprint · 4 NEUT
> Woodies** ; OBSERVING — **1 VAR Day Type · 5 = TPO · 6 MID Killzone**. Day Type panel: **Variation CLASSIFIED,
> Prob 48% / Dir MEDIUM / Trade HIGH**, IBH7552.75/IBL7505.75 47.0pt 🔒, Opening OPEN_REJECTION_REVERSE WIDE.

*(Minor: UI Woodies CCI=-136.31 vs woodies endpoint cci_14=-126.44 — bar-refresh skew, both RED.)*

### NOT-DONE / for CC (Sierra v9_export cross-checks)

- **S4 studies — Sierra=SoT:** cross-check `cci_14=-126.44 / cci_6_tcci=-121 / ema_34=7501.32 / lsma=7465.63 /
  swi=-11.56 / czi=-140` + this bar OHLC against `~/SierraChart_Data/v9_export/`. Any gap = finding.
- **I-11** footprint ingest (file Present in prior snaps, 0 bars) — **7th confirmation**; now also a board-block
  via `tick_reversal` dead. Independent of the restart that re-hydrated S2/S4.
- **C-6 (NEW)** bridge `lag_seconds=-10467` + `fresh=true` — TZ-normalize + enforce threshold on negative lag.
- **I-1/C-2** day_type 3-way split (Variation everywhere vs readiness="Normal") + state `opening_type=UNKNOWN` +
  `session_min=0` (stuck) — dead/stale state instance.
- **C-5** build/pattern-status — confirm the 11:08 hang root (event-loop block under load on single-worker uvicorn);
  not reproducing at 11:38.
- **Y IB `dll_missing`** — yesterday's IB still omitted by the Sierra DLL.
- **No counterfactual** (read-only, no bar-replay): no S2/S3/S4 setup fired this snapshot; nothing to replay for EOD.

## 12:14 CT — Snapshot (deep, all sections + 5-Q per pattern) · Cowork diagnostic (scheduled, unattended)

**Clock:** 12:14 CT (17:14 UTC), Fri 2026-06-05. **In RTH** (08:30–15:00 CT), ~166m to close.
Backend `ts=2026-06-05T17:10:14Z`. All 7 read endpoints 200 in <40ms; `build/pattern-status` 200 in **477ms**
(no C-5 hang). Verdict: **BLOCKED — `dead: tick_reversal`**.

### 🔴 HEADLINE FINDING — 5-min / study Sierra export is STALLED (~39 min); tick/price layer stays live
The Build Status board states it directly on the S2 source row: **"מקור · stream freshness — תקוע · lag 39m · סף
660s · last_bar 12:35 PM"** with fix-hint **"יצוא Sierra תקוע — runbook docs/runbooks/SIERRA_DLL_OPS.md · log
/tmp/bridge.err.log"**. The whole study layer is flagged stale ~39m:
- **S2 · 5-Min Patterns** → `stale 39m` (last 5-min bar ~11:35 CT; export stuck)
- **S4 · Woodies CCI** → `stale 39m` (DATA_FRESHNESS panel: `stale 39m · סף 660s`)
- **S3 · Footprint** → `stale ?` + BLOCKED (0 bars — see I-11)
- **S1 · Day Type** → `stale ?`
- **Bridge · Streams** → `fresh <1s` ✅ — the **tick/price + CVD + volume_profile** layer is LIVE
  (Dashboard price 7456.75 "1s ago"; gates `cumulative_delta`=17:10:00Z, `volume_profile`=17:10:09Z — real UTC, fresh).

So this is a **partial feed stall on the 5-min/study export channel only** (woodies_5min, 5min_bars/min-patterns,
footprint, day_type), while the tick/price/CVD channel is unaffected. This fully explains:
- engine `woodies.cci_14 = -126.44` **identical to the 11:38 snapshot** (32 min earlier) — the CCI feed is **frozen**
  at the ~11:35 CT bar, not genuinely flat.
- every S2/S4 pattern sitting "armed but not detecting" — they are re-evaluating a **frozen 11:35 bar**.
- verdict BLOCKED chaining Day Type×stale → S3 BLOCKED → Footprint×stale → Woodies CCI×stale 39m → Min Patterns×stale 39m.
**Read-only here. CC: diagnose the Sierra-export→bridge→DB path for the 5-min/study streams (why woodies_5min /
5min_bars / footprint export stopped advancing ~11:35 CT while tick/CVD kept flowing). Cross-check
`~/SierraChart_Data/v9_export/` file mtimes + last bar ts. This is the root behind I-11 / I-15 frozen-CCI / the
"armed-but-idle" board.** Likely 🔴.

### ⚠️ Internal contradiction (same endpoint) — bridge global_gates say FRESH 0s, per-system panels say stale 39m
Within one `/build/pattern-status` response: `systems[0].global_gates` reports
`woodies_5min = "[FRESH] 0s ago · 2026-06-05 19:35:00"` and `footprint = "[FRESH] 0s ago · 2026-06-05 20:10:13"`
(present:true), **but** the S2/S4 system panels on the same payload report `stale 39m`. The "FRESH 0s" is the
**TZ-mix negative-lag mask** (C-6/I-18): those two gate ts are **IL-local (UTC+3)** stamped `+00:00`
(20:10:13 = IL-now; 19:35 = IL ~39m ago) → `now_utc − ts` is **negative** → clamped to "0s ago / FRESH". Meanwhile
`cumulative_delta`/`volume_profile`/`tick_reversal` carry **real UTC** ts. The UI board correctly surfaces stale 39m;
the bridge global_gates JSON is the lying surface. **This is the concrete harm of C-6/I-20 + I-18/C-4: the masked
freshness hides a real 39-min export stall.**

### Raw values (this snapshot)
- **woodies/current:** running·hydrated, `cci_14=-126.44` (FROZEN, =11:38), `tcci=-121`, `ema_34=7501.32`,
  `lsma=7465.63`, `swi=-11.56`, `czi=-140`, `trend_state=RED`, `predictor=-123.26`, `signal=NEUTRAL`,
  `active_patterns=[]`, `classification=NO_SETUP`, buffer=50. dtree: A1 SKIP(no patterns)·A2 PASS(11 studies)·
  A3 SKIP·A4 SKIP·**A5 PASS(advisory:calculate_size=reject)**·A6 SKIP(NO_SETUP)·A7 SKIP.
- **footprint/current:** running·hydrated, `bars_processed_today=0`, `buffer_size=0`, aggressive_flow/delta/dominance/
  amt/initiative_type/combined_class **all null**, cumulative_delta=0, last_fire=null. (I-11, 8th confirm.)
- **five_min/current:** running·hydrated, mode=DAY_TYPE_MODE, **buffer=12**, opening_type=OPEN_REJECTION_REVERSE,
  last_pattern/classification=null. **stats:** patterns_detected=0, setups_published=0.
- **day_type/state:** `Variation` · stage B2 · conf **0.48** · lock PENDING · **opening_type=UNKNOWN** ·
  ib_width=WIDE · behavior=DEVELOPING · **session_min=0** (stuck; ~224m into RTH) · vote_history=[] · profile_shape=null.
- **gateway/status:** chop_state=**FOUND**, daily_pnl=0, trades_today=0, shadow_active=0, demo_systems=[2,4],
  live_systems=[], cooldown inactive (0 stops), cluster_guard inactive, ssv inactive.
- **trades/recent:** **0** trades.
- **Prices sane (Q2 ✓):** last 7456.75 (B7456.50/A7457.00, 1s ago); TODAY range 7448.75–7552.75 (104.0pt);
  ema 7501.32 / lsma 7465.63 — all in-band MES. CCI −126.44 in-band but **frozen** (see headline).

### S2 (five_min) — 5-Q per pattern · all 10 ARMED, choppiness_ok PRESENT (I-16 not reproducing)
Buffer=12, FHB advanced, `data.choppiness_ok` wired (S2 derived gate present). Every block is a **real per-pattern
detection await on the frozen 11:35 bar** — not a missing input. (1)יש נתון ✓ (2)הגיוני ✓ but **stale** (3)מה חסם:
real detection threshold per row (4)צריך לחסום: yes, legitimate per spec (5)מה חסר: **fresh 5-min bars** (export stall).
- REACTIVE_LONG — Awaiting `b2_volume_drop`: b2_vol=20134·b1_vol=186757·ratio=0.11 ✗
- REACTIVE_SHORT — Awaiting `b1_buyers`: b1 close=7472.00 open=7475.75 dir=bear
- INITIATIVE_LONG/SHORT — Awaiting `b1_expansion`: b1 range=8.25 · need [4.5,6.0] ✗ (auth-block cleared per 11:38; blocks on real detection)
- INVERSE_HNS_LONG / HNS_TOP_SHORT — Awaiting swing lows/highs: only 1 found in last 20 bars ✗
- DOUBLE_BOTTOM_EE_LONG / DOUBLE_TOP_AA_SHORT — Awaiting swing lows/highs: 1 found ✗
- BULL_FLAG_LONG — Awaiting `pole_found`: no valid pole (need ≥5 bullish bars, ≥4.00pt height)
- BEAR_FLAG_SHORT — Awaiting `flag_length`: flag=10 bars (out of range 3–8) ✗

### S3 (footprint) — 5-Q · all 4 BLOCKED "Insufficient buffer (0 bars, need ≥5)"
(1)יש נתון: **לא** — 0 bars, buffer 0, all flow null. (2)הגיוני: n/a. (3)מה חסם: empty buffer + `tick_reversal`
stream DEAD 78m (last 15:51:19Z=10:51 CT) → readiness `bridge_streams_fresh` fails (block) → board BLOCKED.
(4)צריך לחסום: blocking is correct *given* no data, but the **data-absence itself is the bug**. (5)מה חסר:
footprint ingest→buffer pipeline. Footprint export gate shows present (ts being written) yet 0 bars ingested ⇒
**downstream ingest broken** (I-11, 8th confirm). ABSORPTION·STACKED_IMBALANCE·SWEEP_RETURN·EXHAUSTION all un-armable.

### S4 (woodies) — 5-Q · all 9 ARMED, trend RED, none detected; CCI feed FROZEN
(1)יש נתון ✓ (2)הגיוני: value in-band but **FROZEN** (cci_14=-126.44 = 11:38) ⇒ **stale = a finding** per headline.
(3)מה חסם: no pattern detected on the frozen bar (`active_patterns=[]`); A1 SKIP "no patterns". (4)צריך לחסום:
n/a (no setup). (5)מה חסר: **fresh CCI/5-min export** (stalled 39m). ZLR·TLB·TT·GB100·Vegas·Ghost·FaMir·HTLB·HFE
all "Data ready, trend RED · … not yet detected". **A5 PASS advisory `calculate_size=reject`** with no setup to block
(I-2 holds: A5 advisory, not a real blocker; I-13: no sizing finding to calibrate — engine NO_SETUP).
- **UI vs API CCI divergence:** Dashboard Woodies CCI panel reads ≈**-147.23 / -141.9** while woodies endpoint
  `cci_14=-126.44`. ~21pt gap — UI panel and engine read different CCI sources/bars. Flag for CC alongside the
  stall (is the UI panel on a fresher Sierra study read than the engine's frozen woodies_5min ingest?).

### S1 / Day Type — 5-Q · 3-way label split persists + session_min stuck
(1)יש נתון ✓ (2)הגיוני: partially — Variation/0.48/B2 plausible, but **opening_type=UNKNOWN** in state while
five_min+UI=OPEN_REJECTION_REVERSE, and **session_min=0** at ~224m into RTH = **not tracking session** (dead/stale
state instance). (3)מה חסם classification: not blocked (classified). (4)/(5) מה חסר: one consistent day_type
instance. **3-way split this snapshot:** state endpoint + Dashboard + S2-derived-gate = **Variation**; readiness
`s1_day_type_classified` + Build-Status header + Day Type panel = **Normal**. (I-1/C-2, unresolved.)

### Gates / context
- **S6 Killzone:** "לא מחווט כלל — חסר killzone_inspector" (not wired — known gate gap).
- **S5 TPO:** "לא מחווט כלל — חסר tpo_inspector" (not wired — known).
- **Gateway vetoes:** none active (cooldown/cluster/ssv all clear); chop_state=FOUND; 0 trades.
- **Y IB `dll_missing`** — yesterday IB still omitted by Sierra DLL (known).

### Screenshots (Chrome MCP — disk-save unavailable this session)
OS `computer action=screenshot save_to_disk=true` needs `request_access` (interactive) — unattended run, can't
satisfy (relevant to I-9). Captured via Chrome MCP instead; the tool reports **screenshots are not persisted to disk
in this session**, so only inline IDs exist: Dashboard board = `ss_7608oiin2`; Build Status decision-tree =
`ss_403604ljy`. Build Status text captured verbatim above (decision chain: ✓Bridge·Streams → Min Patterns×stale 39m-5
→ Woodies CCI×stale 39m → ?Footprint×stale → S3 BLOCKED → ?Day Type×stale → verdict BLOCKED).

### Suspect status this snapshot
- **I-1/C-2** day_type 3-way split + opening_type=UNKNOWN + session_min=0 stuck — **persists** (🔴).
- **I-2** A5 advisory display — holds (A5 PASS advisory, not blocking). **I-12** A5 `details{}` empty — persists.
- **I-3** ZLR — armed "trend RED · not yet detected", engine active_patterns=[]; no setup, **no counterfactual**.
  Plus now on a **frozen bar** (stall) ⇒ cannot arm a fresh ZLR until export resumes.
- **I-4/I-16** choppiness_ok — **NOT reproducing** (present; all 10 S2 armed). Bar-boundary volatility (I-17).
- **I-5 (B-11)** — **NOT reproducing** (bridge mode LIVE, no OFFLINE banner; tick/price fresh).
- **I-11** footprint 0 bars — **persists, 8th confirm**; file present but ingest→buffer broken; tick_reversal dead 78m gates board.
- **I-14** opening run — INITIATIVE armed, auth-block cleared; blocks on real `b1_expansion`. opening→entry chain still
  undiagnosed; moot while export stalled.
- **I-15/C-1** trend split — durable RED (snap 5). **But CCI frozen** (stall) ⇒ "durable RED" is on a frozen bar; Sierra
  cross-check now mandatory.
- **I-18/C-4 + I-20/C-6** TZ-mix + negative-lag `fresh=true` — **confirmed again, now with demonstrated harm**: masks the
  39-min 5-min/study export stall as "FRESH 0s". `data_freshness.lag_seconds=-8685.6`, `fresh=true`, threshold 90.
- **I-19/C-5** pattern-status hang — **NOT reproducing** (477ms). Intermittent/load-induced.

### NOT-DONE / for CC (Sierra v9_export cross-checks — read-only here)
- **🔴 NEW — 5-min/study export stall:** confirm via `~/SierraChart_Data/v9_export/` file mtimes + last-bar ts why
  `woodies_5min` / `5min_bars` / `footprint` stopped advancing ~11:35 CT while tick/CVD/volume_profile stayed live.
  This is the root behind frozen CCI + armed-but-idle board.
- **I-11** footprint ingest (present, 0 bars) — 8th confirm; now also part of the stall + tick_reversal dead board-block.
- **I-15 / S4 studies** cross-check `cci_14=-126.44 / tcci=-121 / ema_34=7501.32 / lsma=7465.63 / swi=-11.56 / czi=-140`
  + UI-panel CCI ≈-147 against Sierra export — resolve the ~21pt UI↔engine divergence and confirm which is the frozen one.
- **I-18/C-6** TZ-normalize bridge `last_bar_ts` to UTC + enforce `|lag|≤threshold` (reject negative lag) before `fresh=true`.
- **No counterfactual** (read-only, no bar-replay): no S2/S3/S4 setup fired; nothing to replay for EOD.

## 12:38 CT — Snapshot (deep, all sections + 5-Q per pattern) · Cowork diagnostic (scheduled, unattended)

**Clock:** 12:38 CT (17:39 UTC), Fri 2026-06-05. **In RTH** (08:30–15:00 CT), ~141m to close
(`rtb_session.minutes_to_close=141`). Backend `pattern-status ts=2026-06-05T17:39:31Z`. All 7 read endpoints
200 in <50ms; **`build/pattern-status` 200 in 49ms** (no C-5 hang). Verdict: **BLOCKED — `dead: tick_reversal`**.

### 🔴 HEADLINE — 5-min/study Sierra export stall now ~64 min (worsened from 39m @12:14); tick/price still live
The `build/pattern-status` per-system `data_freshness` now reports it numerically:
- **five_min:** `last_bar_ts=2026-06-05 19:35:00+03:00` (IL-local = **16:35 UTC = 11:35 CT**), `lag_seconds=3944.5`
  (~65.7m), `threshold_seconds=660` → **`fresh=true`** ❌ (lag 3944s ≫ 660s threshold, yet flagged fresh).
- **woodies:** identical — `last_bar_ts=…19:35:00+03:00`, `lag_seconds=3944.5`, `fresh=true`, threshold 660.
- **footprint:** `last_bar_ts=null`, `lag_seconds=null`, `fresh=false`, threshold 360 (dead — I-11).
- **bridge:** `last_bar_ts=null`, `lag_seconds=-6855.5` (negative ~-114m), **`fresh=true`**, threshold 90 (I-20 classic).

The last 5-min/study bar is **still 11:35 CT** — same bar as the 11:38 and 12:14 snapshots. The export channel
(woodies_5min, 5min_bars/min-patterns, footprint, day_type) has not advanced for **~64 min**, while the tick/price
layer is live (Dashboard price **7473.75 "0.9s ago"**, B7473.50/A7473.75, Sz6328). Direct consequences:
- engine `woodies.cci_14 = -126.44` — **identical for the 3rd consecutive snapshot** (11:38 → 12:14 → 12:38, ~60m
  span). The CCI feed is **frozen** at the 11:35 bar, not genuinely flat.
- five_min detection inputs are the **same frozen values** as 12:14 (b1_range=8.25, b1_vol=186757, b2_vol=20134).
- verdict BLOCKED chaining the dead `tick_reversal` stream + stalled study layer.
**Sharper than 12:14:** here the five_min/woodies lag is **positive** (+3944s) and STILL `fresh=true` — so the
broken predicate fails to enforce the threshold on *positive* lag too, not only the negative-lag (bridge) case.
**Read-only here. CC: diagnose Sierra-export→bridge→DB for the 5-min/study channel — why woodies_5min / 5min_bars /
footprint stopped advancing 11:35 CT while tick/CVD kept flowing. Cross-check `~/SierraChart_Data/v9_export/` file
mtimes + last-bar ts + `/tmp/bridge.err.log`.** This is the root behind I-11 / I-15 frozen-CCI / armed-but-idle board.

### Raw values (this snapshot)
- **woodies/current:** running·hydrated, `cci_14=-126.44` (**FROZEN, =11:38 & =12:14**), `tcci=-121`,
  `ema_34=7501.32`, `lsma=7465.63`, `swi=-11.56`, `czi=-140`, `trend_state=RED`, `predictor=-123.26`,
  `signal=NEUTRAL`, `active_patterns=[]`, `classification=NO_SETUP`, buffer=50. dtree: A1 SKIP(no patterns)·
  A2 PASS(11 studies)·A3 SKIP(no patterns this bar)·A4 SKIP(no setup needs touch-points)·
  **A5 PASS(advisory:calculate_size=reject)**·A6 SKIP(NO_SETUP)·A7 SKIP(no fire_setup — gateway/pre_fire at route_setup).
- **footprint/current:** running·hydrated, `bars_processed_today=0`, `buffer_size=0`, cumulative_delta=0, flow null.
  (I-11, **9th confirm**.)
- **five_min/current:** running·hydrated, mode=DAY_TYPE_MODE, **buffer=12**, opening_type=OPEN_REJECTION_REVERSE,
  last_pattern/classification/reasoning=null. **stats:** patterns_detected=0, setups_published=0.
- **day_type/state:** `Variation` · stage B2 · conf **0.48** · lock PENDING · **opening_type=UNKNOWN** · ib_width=WIDE ·
  behavior=DEVELOPING · range_category=NORMAL · **session_min=0** (stuck; ~249m into RTH) · vote_history=[] ·
  profile_shape=null.
- **gateway/status:** daily_pnl=0, trades_today=0, shadow_active=0, demo_systems=[2,4], live_systems=[],
  cooldown inactive (0 stops), cluster_guard inactive, ssv inactive — **no active vetoes**.
- **trades/recent:** **0** trades.
- **Prices sane (Q2 ✓):** last 7473.75 (0.9s ago); TODAY range 7448.75–7552.75 (104.0pt); IB 7505.75–7552.75
  (47pt WIDE); ema 7501.32 / lsma 7465.63 — all in-band MES. CCI −126.44 in-band but **frozen** (see headline).

### S2 (five_min) — 5-Q per pattern · build-status `armed=0/10`, blocks are real detection-awaits on the FROZEN bar
This snapshot all 10 S2 rows read **armed=false** (differs from 12:14's armed=true) — but every block reason is a
**real per-pattern detection await on the frozen 11:35 bar**, NOT `Missing: data.choppiness_ok`. So **I-16 still NOT
reproducing** (choppiness_ok wired); the armed=true↔false flip across snapshots is bar-boundary volatility (I-17)
now compounded by the export stall. (1)יש נתון ✓ (2)הגיוני ✓ but **stale/frozen** (3)מה חסם: real detection
threshold per row (4)צריך לחסום: yes, legitimate per spec (5)מה חסר: **fresh 5-min bars** (export stall).
- REACTIVE_LONG — Awaiting `b2_volume_drop`: b2_vol=20134 · b1_vol=186757 · ratio=0.11 ✗ (=12:14, frozen)
- REACTIVE_SHORT — Awaiting `b1_buyers`: b1 close=7472.00 open=7475.75 dir=bear, vol=186757 (frozen)
- INITIATIVE_LONG/SHORT — Awaiting `b1_expansion`: b1 range=8.25 · need [4.5,6.0] ✗ (frozen; auth-block stays cleared)
- INVERSE_HNS_LONG / HNS_TOP_SHORT / DOUBLE_BOTTOM_EE / DOUBLE_TOP_AA — Awaiting swing highs/lows on frozen window
- BULL_FLAG_LONG / BEAR_FLAG_SHORT — Awaiting pole/flag-length on frozen window

### S3 (footprint) — 5-Q · all 4 BLOCKED "Insufficient buffer (0 bars, need ≥ 5)" (I-11, 9th confirm)
(1)יש נתון: **לא** — 0 bars, buffer 0, flow null. (2)הגיוני: n/a. (3)מה חסם: empty buffer + `tick_reversal` stream
DEAD → readiness `bridge_streams_fresh` fails → board **BLOCKED**. (4)צריך לחסום: blocking correct *given* no data,
but the **data-absence is the bug**. (5)מה חסר: footprint ingest→buffer pipeline. Export gate present (file written)
yet 0 bars ingested ⇒ **downstream ingest broken**, now also part of the 5-min/study stall.
ABSORPTION·STACKED_IMBALANCE·SWEEP_RETURN·EXHAUSTION all un-armable.

### S4 (woodies) — 5-Q · all 9 rows "Data ready, trend RED · … not yet detected"; CCI FROZEN (3rd snap)
(1)יש נתון ✓ (2)הגיוני: in-band but **FROZEN** (cci_14=-126.44 = 11:38 = 12:14) ⇒ **stale = finding**. (3)מה חסם:
no pattern on the frozen bar (`active_patterns=[]`; A1 SKIP "no patterns"). (4)צריך לחסום: n/a. (5)מה חסר: **fresh
CCI/5-min export** (stalled ~64m). ZLR·TLB·TT·GB100·Vegas·CCI-H&S·FailedZLR(±200)·HTLB·HFE all "Data ready, trend
RED · not yet detected". **A5 PASS advisory `calculate_size=reject`** with no setup to block (I-2 holds; I-13 no
sizing finding to calibrate — engine NO_SETUP). UI↔engine CCI divergence (~-147 panel vs -126.44 endpoint) still
open for CC — confirm which is the frozen read.

### S1 / Day Type — 5-Q · 3-way label split persists + session_min still stuck at 0
(1)יש נתון ✓ (2)הגיוני: partially — Variation/0.48/B2 plausible, but **opening_type=UNKNOWN** in state while
five_min+UI=OPEN_REJECTION_REVERSE, and **session_min=0** at ~249m into RTH = **not tracking session**. (3) not
blocked (classified). (4)/(5) מה חסר: one consistent day_type instance. **3-way split this snapshot:** state endpoint
+ Dashboard badge ("Variation 48%") + S2-derived gate = **Variation**; readiness `day_type` check = **Normal**.
(I-1/C-2, unresolved.)

### Gates / context
- **S6 Killzone / S5 TPO:** not wired (known gate gaps).
- **Gateway vetoes:** none active (cooldown/cluster/ssv clear); 0 trades.
- **Y IB `dll_missing`** — yesterday IB still omitted by Sierra DLL (known).

### Screenshot (Chrome MCP — disk-save unavailable this session)
OS `computer action=screenshot save_to_disk=true` reports **screenshots are not persisted to disk in this session**
(unattended run — relevant to I-9). Inline ID only: Dashboard board = **`ss_6951hiktd`** (shows Variation 48%,
firing decisions 5-Min IDLE / Footprint — / Woodies NEUT, price 7473.75 "0.9s ago", 0 trades, Woodies-CCI panel).
Build Status decision chain captured via `build/pattern-status` API above: ✓day_type Normal · ✓trend RED · ✓RTH ·
✗**dead tick_reversal** → verdict **BLOCKED**.

### Suspect status this snapshot
- **I-1/C-2** day_type 3-way split + opening_type=UNKNOWN + session_min=0 stuck — **persists** (🔴).
- **I-2** A5 advisory display — holds (A5 PASS advisory). **I-12** A5 `details{}` empty — persists.
- **I-3** ZLR — "Data ready, trend RED · ZLR not yet detected", active_patterns=[]; no setup, **no counterfactual**;
  on a **frozen bar** ⇒ cannot arm a fresh ZLR until export resumes.
- **I-4/I-16** choppiness_ok — **NOT reproducing** (blocks are real detection-awaits, not "Missing").
- **I-5 (B-11)** — **NOT reproducing** (bridge mode live, tick/price fresh).
- **I-11** footprint 0 bars — **persists, 9th confirm**; file present, ingest→buffer broken; tick_reversal dead gates board.
- **I-14** opening run — INITIATIVE auth-block cleared; blocks on real `b1_expansion` (frozen). opening→entry chain
  undiagnosed; moot while export stalled.
- **I-15/C-1** trend split — durable RED (snap 6) **but on a FROZEN CCI bar** (3rd identical -126.44); Sierra
  cross-check mandatory.
- **I-17** bar-boundary armed flip — S2 armed=true(@12:14)→false(@12:38) with same frozen inputs ⇒ supports volatility
  hypothesis, now confounded by the stall.
- **I-18/C-4 + I-20/C-6** TZ-mix + threshold-not-enforced `fresh=true` — **confirmed again, demonstrated harm**:
  masks the ~64-min stall. five_min/woodies `lag=+3944.5s` fresh=true (threshold 660); bridge `lag=-6855.5s` fresh=true
  (threshold 90). **Now proven on positive lag too**, not only negative.
- **I-19/C-5** pattern-status hang — **NOT reproducing** (49ms).
- **I-21** 5-min/study export stall — **worsened to ~64m** (was 39m @12:14); root behind I-11/I-15/idle board.

### NOT-DONE / for CC (Sierra v9_export cross-checks — read-only here)
- **🔴 5-min/study export stall (I-21):** ~64m and growing — confirm via `~/SierraChart_Data/v9_export/` file mtimes +
  last-bar ts why woodies_5min / 5min_bars / footprint stopped advancing 11:35 CT while tick/CVD/volume_profile stayed
  live. Root behind frozen CCI + armed-but-idle board.
- **I-11** footprint ingest (present, 0 bars) — 9th confirm.
- **I-15 / S4 studies** cross-check `cci_14=-126.44 / tcci=-121 / ema_34=7501.32 / lsma=7465.63 / swi=-11.56 / czi=-140`
  + UI-panel CCI ≈-147 vs endpoint -126.44 against Sierra export — resolve ~21pt UI↔engine gap; confirm frozen source.
- **I-20/C-6 + I-18/C-4** TZ-normalize `last_bar_ts` to UTC + enforce `|lag|≤threshold` (reject both negative AND
  over-threshold positive lag) before `fresh=true`. This snapshot shows the predicate fails on positive lag too.
- **No counterfactual** (read-only, no bar-replay): no S2/S3/S4 setup fired; nothing to replay.

---

## 13:10 CT snapshot — 5-min/study export stall now ~95 min · footprint isolated as INGEST break (not export)

**Clock:** 13:10 CT (18:10 UTC), Fri 2026-06-05. **In RTH** (08:30–15:00 CT), ~110m to close.
Backend `pattern-status ts=2026-06-05T18:09:36Z`. All 7 read endpoints 200 in <15ms;
**`build/pattern-status` 200 in 62ms** (no C-5 hang). Verdict: **BLOCKED — `dead: tick_reversal`**.

### 🔴 HEADLINE — export stall ~95 min (worsened from 64m @12:38); + new split: footprint file is FRESH, ingest broken
`build/pattern-status` per-system `data_freshness`:
- **five_min:** `last_bar_ts=2026-06-05 19:35:00+03:00` (IL-local = **16:35 UTC = 11:35 CT**), `lag_seconds=5747.3`
  (~95.8m), `threshold_seconds=660` → **`fresh=true`** ❌ (I-20: positive lag 5747s ≫ 660 not enforced).
- **woodies:** identical — `last_bar_ts=…19:35:00+03:00`, `lag_seconds=5676.7→5747`, `fresh=true`, threshold 660.
- **footprint:** `last_bar_ts=null`, `lag_seconds=null`, `fresh=false`, threshold 360.
- **bridge:** `last_bar_ts=null`, `lag_seconds=-5123` (negative ~-85m), **`fresh=true`**, threshold 90 (I-20 classic).

The last 5-min/study bar is **still 11:35 CT** — same frozen bar as 11:38 / 12:14 / 12:38. engine
`woodies.cci_14 = -126.44` — **identical for the 4th consecutive snapshot** (11:38 → 12:14 → 12:38 → 13:09,
~95m span). CCI feed frozen, not flat.

**🔬 NEW — separate footprint (I-11) from the export stall (I-21):** the bridge `global_gates` expose the file
mtimes directly —
- `woodies_5min` gate value = `[FRESH] 0s ago · 2026-06-05 19:35:00` → file **frozen at 11:35 CT** = genuine
  **EXPORT stall** (Sierra stopped writing the 5-min/study file).
- `footprint` gate value = `[FRESH] 0s ago · 2026-06-05 21:10:44` (IL-local = **18:10:44 UTC = now**) → file is
  **actively written THIS minute**, yet `footprint.bars_processed_today=0 / buffer=0`. ⇒ footprint is an
  **INGEST/parse break** (file fresh, 0 bars reach the buffer), **NOT** the export stall.
This refines 12:38 (which lumped footprint into the stall): **two distinct roots** — woodies_5min/5min_bars/five_min
file *stopped advancing* (export); footprint file *is current but not ingested* (downstream parse). **CC: treat as
two separate diagnoses.**

### Raw values (this snapshot)
- **woodies/current:** running·hydrated, `cci_14=-126.44` (**FROZEN ×4**), `tcci=-121`, `ema_34=7501.32`,
  `lsma=7465.63`, `swi=-11.56`, `czi=-140`, `trend_state=RED`, `predictor=-123.26`, `signal=NEUTRAL`,
  `active_patterns=[]`, `classification=NO_SETUP`, buffer=50. dtree: A1 SKIP·A2 PASS(11 studies)·A3 SKIP·A4 SKIP·
  **A5 PASS(advisory:calculate_size=reject, `details{}`=EMPTY — I-12)**·A6 SKIP·A7 SKIP. `last_reasoning_notes=null`
  this snapshot (NO_SETUP ⇒ no sizing context — I-13 moot here).
- **footprint/current:** running·hydrated, `bars_processed_today=0`, `buffer_size=0`, cumulative_delta=0, flow null.
  (I-11, **10th confirm** — now with proof the export FILE is fresh.)
- **five_min/current:** running·hydrated, mode=DAY_TYPE_MODE, **buffer=12**, opening_type=OPEN_REJECTION_REVERSE,
  last_pattern/classification=null. **stats:** patterns_detected=0, setups_published=0.
- **day_type/state:** `Variation` · stage B2 · conf **0.48** · lock PENDING · **opening_type=UNKNOWN** · ib_width=WIDE ·
  behavior=DEVELOPING · range_category=NORMAL · **session_min=0** (stuck; ~280m into RTH) · vote_history=[].
- **gateway/status:** daily_pnl=0, trades_today=0, cooldown inactive (0 stops), cluster inactive — **no active vetoes**.
- **trades/recent:** **0** trades.
- **Prices sane (Q2 ✓):** TODAY range 7448.75–7552.75 (104.0pt); IB WIDE 47pt; ema 7501.32 / lsma 7465.63 — in-band
  MES. CCI −126.44 in-band but **frozen**.

### S2 (five_min) — 5-Q · build-status `armed=10/10` this snapshot (flip from 0/10 @12:38)
All 10 S2 rows read **armed** — opposite of 12:38 (armed=0) — but every block reason is a **real per-pattern
detection await on the FROZEN 11:35 bar** with the **same frozen inputs** as 12:14/12:38 (b1_range=8.25,
b2_vol=20134, b1_vol=186757). So **I-16 still NOT reproducing** (choppiness_ok wired), and the armed=0↔10 flip across
30-min snapshots on identical frozen inputs = **I-17 bar-boundary volatility**, now confounded by the export stall.
(1)יש נתון ✓ (2)הגיוני ✓ אבל **קפוא** (3)מה חסם: real detection threshold per row (4)צריך לחסום: כן, לגיטימי
(5)מה חסר: **ברי-5דק' טריים** (export stall).
- Reactive Long — Awaiting `b2_volume_drop`: b2_vol 20134 · b1_vol 186757 · ratio 0.11 ✗ (frozen)
- Reactive Short — Awaiting `b1_buyers`: b1 close 7472.00 open 7475.75 dir bear (frozen)
- Initiative Long/Short — Awaiting `b1_expansion`: b1 range 8.25 · need [4.5,6.0] ✗ (frozen; auth-block stays cleared)
- Inverse H&S Long / H&S Top Short — Awaiting swing lows/highs (1 found in last 20 bars ✗, frozen window)
- Double Bottom EE / Double Top AA — Awaiting swing lows/highs (1 found ✗)
- Bull Flag Long — Awaiting `pole_found` (no valid pole ≥5 bullish / ≥4.00pt); Bear Flag Short — flag 10 bars (range 3–8) ✗

### S3 (footprint) — 5-Q · all 4 BLOCKED "Insufficient buffer (0 bars, need ≥ 5)" (I-11, 10th confirm)
(1)יש נתון: **לא** — 0 bars, buffer 0, flow null. (2)n/a. (3)מה חסם: empty buffer + `tick_reversal` DEAD →
readiness `bridge_streams_fresh` fails → board **BLOCKED**. (4)blocking correct given no data, **but the data-absence
is the bug**. (5)מה חסר: footprint **ingest→buffer** parse — and this snapshot proves the **export file is FRESH**
(`footprint` bridge-gate ts = now) yet 0 bars reach the buffer ⇒ break is **downstream of the file**.
ABSORPTION·STACKED_IMBALANCE·SWEEP_RETURN·EXHAUSTION all un-armable.

### S4 (woodies) — 5-Q · all 9 "Data ready, trend RED · … not yet detected"; CCI FROZEN (4th snap)
(1)יש נתון ✓ (2)in-band but **FROZEN** (cci_14=-126.44 ×4) ⇒ **stale = finding**. (3)מה חסם: no pattern on the
frozen bar (`active_patterns=[]`; A1 SKIP). (4)n/a. (5)מה חסר: **fresh CCI/5-min export** (~95m). ZLR·TLB·TT·GB100·
Vegas·CCI-H&S·FailedZLR(±200)·HTLB·HFE all "Data ready, trend RED · not yet detected". **A5 PASS advisory
`calculate_size=reject`** with no setup to block (I-2 holds). **UI↔engine CCI divergence confirmed visually:
Woodies-CCI panel = `-148.49` vs endpoint `-126.44` (~22pt gap)** — both on the frozen bar (I-15, for CC).

### S1 / Day Type — 5-Q · 3-way label split persists + session_min still 0
(1)יש נתון ✓ (2)partially — Variation/0.48/B2 plausible, but **opening_type=UNKNOWN** in state while
five_min+UI=OPEN_REJECTION_REVERSE, and **session_min=0** at ~280m into RTH = **not tracking session**. (3) not
blocked (classified). (4)/(5) מה חסר: one consistent day_type instance. **3-way split:** state endpoint + Dashboard
badge ("VAR 48% M") + S2 gate (`nt_day_type` live=Variation) = **Variation**; readiness `s1_day_type_classified`
check = **Normal**. (I-1/C-2, unresolved.)

### Gates / context
- **S6 Killzone / S5 TPO:** not wired (known gate gaps; `tpo_bars` DEAD).
- **Gateway vetoes:** none active; 0 trades.
- **Y IB `dll_missing`** — yesterday IB still omitted by Sierra DLL (known).

### Screenshot (Chrome MCP)
OS `computer action=screenshot save_to_disk=true` again reports **screenshots are not persisted to disk in this
session** (unattended run — relevant to **I-9**). Inline-only capture of localhost:3000 Dashboard confirms: **VAR 48% M**
badge, TODAY RANGE 7552.75/7448.75 (104pt), Woodies-CCI panel **CCI −148.49** (≠ endpoint −126.44 ⇒ I-15), chart
x-axis last labels 11:10/12:10 (consistent with the 11:35 stall), "Day 23/30". Build Status decision chain captured
via API above: ✓day_type Normal · ✓trend RED · ✓RTH · ✗**dead tick_reversal** → verdict **BLOCKED**.

### Suspect status this snapshot
- **I-1/C-2** day_type 3-way split + opening_type=UNKNOWN + session_min=0 — **persists** (🔴).
- **I-2** A5 advisory display — holds. **I-12** A5 `details{}` empty — persists (10th-ish confirm).
- **I-3** ZLR — "Data ready, trend RED · ZLR not yet detected", active_patterns=[]; on a **frozen bar** ⇒ cannot arm
  a fresh ZLR until export resumes; **no counterfactual**.
- **I-4/I-16** choppiness_ok — **NOT reproducing** (blocks are real detection-awaits; all 10 armed).
- **I-5 (B-11)** — **NOT reproducing** (bridge mode live, tick/price fresh).
- **I-11** footprint 0 bars — **persists, 10th confirm**; **NEW: export file is FRESH (ts=now) yet 0 bars** ⇒ break is
  **ingest/parse**, isolated from the export stall (I-21). tick_reversal dead gates board.
- **I-13** A5 sizing — **moot** (NO_SETUP, no reject to calibrate; last_reasoning_notes null).
- **I-14** opening run — INITIATIVE auth-block cleared; blocks on real `b1_expansion` (frozen); moot while stalled.
- **I-15/C-1** trend split — durable RED (snap 7) **but on a FROZEN CCI bar** (4th identical −126.44); **UI panel
  −148.49 vs endpoint −126.44 ~22pt** — Sierra cross-check mandatory.
- **I-17** bar-boundary armed flip — S2 armed=0(@12:38)→10(@13:10) on identical frozen inputs ⇒ strong support;
  confounded by stall.
- **I-18/C-4 + I-20/C-6** TZ-mix + threshold-not-enforced `fresh=true` — **confirmed again**: five_min/woodies
  `lag=+5747s` fresh=true (threshold 660); bridge `lag=-5123s` fresh=true (threshold 90). Masks the ~95m stall; the
  `woodies_5min` gate even prints `[FRESH] 0s ago` for an 11:35 file.
- **I-19/C-5** pattern-status hang — **NOT reproducing** (62ms).
- **I-21** 5-min/study export stall — **worsened to ~95m** (was 64m @12:38); root behind frozen CCI + armed-but-idle
  board. **NEW: now cleanly separated from footprint (I-11 = ingest break, file fresh).**

### NOT-DONE / for CC (Sierra v9_export cross-checks — read-only here)
- **🔴 5-min/study EXPORT stall (I-21):** ~95m and growing — `~/SierraChart_Data/v9_export/` woodies_5min /
  5min_bars file mtimes are frozen at **11:35 CT** while tick/CVD/volume_profile kept flowing. Why did the study/5-min
  export channel stop writing 11:35 CT? Root behind frozen CCI + idle board.
- **🔬 footprint INGEST break (I-11) — distinct:** footprint export file mtime = **now** (bridge-gate ts 21:10:44 IL
  = 18:10 UTC) yet `bars_processed_today=0`. Break is **file→bridge-parse→buffer**, NOT export. Diagnose separately.
- **I-15 / S4 studies** cross-check `cci_14=-126.44 / tcci=-121 / ema_34=7501.32 / lsma=7465.63 / swi=-11.56 /
  czi=-140` + **UI-panel CCI -148.49 vs endpoint -126.44 (~22pt)** against Sierra export — confirm frozen source.
- **I-20/C-6 + I-18/C-4** TZ-normalize `last_bar_ts` to UTC + enforce `|lag|≤threshold` (reject both negative AND
  over-threshold positive lag) before `fresh=true`.
- **No counterfactual** (read-only): no S2/S3/S4 setup fired; nothing to replay.

---

## 13:42 CT snapshot — **STALL I-21 RESOLVED · FIRST FIRES OF THE DAY (2 SHORTs) · R-units bug surfaced**

API ts `2026-06-05T18:40:41Z` = 13:40 CT. `pattern-status` 75ms (I-19 not reproducing).

**Headline changes vs 13:10:**
1. **5-min/study export stall (I-21) RESUMED.** S2 `last_bar_ts=2026-06-05 21:40:00+03:00` (=13:40 CT, lag ~57–97s);
   S4 `last_bar_ts=21:25:00+03:00` (=13:25 CT, lag ~956–989s, 1–3 bars behind). CCI **un-froze**: `cci_14 −126.44 → −171.17`
   (was identical 4 snapshots). Price live `7427.00 · 0.7s ago`. Chart x-axis now reaches 13:40. ⇒ the ~95-min frozen
   channel started writing again ~13:15 CT.
2. **First fires of the session — 2 trades, both SHORT, ~13:15 CT, both directionally correct** (price fell 7444→7427):

| id | sys | pattern | dir | entry | state | exit | T1/T2 | stop(init→now) | exit_reason | reported R |
|----|-----|---------|-----|-------|-------|------|-------|----------------|-------------|------------|
| 10 | S2 | BEAR_FLAG_SHORT | SHORT | 7444.00 | **PARTIAL** (C1 HIT TARGET, 1/3) | — | 7428.75 / 7413.50 | 7457.03 → 7443.75 | — | **pnl_r=61** |
| 12 | S4 | HTLB (Horizontal Trend Line Break) | SHORT | 7443.75 | CLOSED | 7443.50 | 7440.25 / 7436.75 | 7447.25 → 7443.50 (BE) | STOP_HIT | **pnl_r=16** |

Board confirms: S2 "Bear Flag Short" `status=fired`, S4 "Horizontal Trend Line Break" `status=fired`. Right-panel
shows id=10 "▼ SHORT 7444.00 · BEAR_FLAG_SHORT · Variation", C1 **HIT TARGET $76 / 61.0R**, C2/C3 OPEN, stop 1/3 hit.

### 🆕 FINDING F-1 (🔴) — R-units / pnl_r calculation is badly inflated (~50×)
- id=10 hit **T1 on 1/3** for **$76** but reports **61.0R**. MES is $5/pt; entry 7444 → T1 7428.75 = 15.25pt ×$5 = $76.25
  (1 contract). Risk = entry−stop_init = 7457.03−7444 ≈ 13pt ⇒ true ≈ **+1.17R**, not 61R.
- id=12 STOP_HIT at BE (entry 7443.75 → exit 7443.50 = +0.25pt, ~$1) reports **pnl_r=16** ⇒ true ≈ **+0.07R**.
- Both R figures are inflated ~50×. **This corrupts the very ΣR / win-rate the counterfactual is meant to produce.**
  `$76 (61.0R)` on the dashboard = same bug surfaced in UI. **CC: audit the pnl_r formula** (looks like points or
  $ are being divided by tick-size or a 0.25 risk-unit instead of the per-contract stop distance).

### 🆕 FINDING F-2 (🟡) — gateway counters don't track shadow fires
`gateway/status`: `trades_today=0`, `shadow_active_count=0`, `daily_pnl=0` — but `trades/recent` has **2 shadow trades
today**, one (id=10) still **PARTIAL/open**. Gateway's day counters and active-shadow count are not incremented by
shadow fires. (Dashboard top bar separately shows "SHADOW: 2 · $20" so the UI counts them — the gateway endpoint does not.)

### 5-Question deep table

**S4 — Woodies** (`/woodies/current`: now NO_SETUP, active_patterns=[], cci_14 −171.17, tcci −102.49, ema_34 7469.01,
lsma 7449.14, swi 18.23, czi −153, trend RED, buffer 35, predictor_next −174.36)

| pattern | 1.נתון? | 2.הגיוני? | 3.מה חסם? | 4.צריך לחסום? | 5.מה חסר? |
|---------|---------|-----------|-----------|---------------|-----------|
| HTLB | ✅ **FIRED** 13:15 (id=12) | ✅ SHORT into RED, price fell — correct dir | — (fired, then closed BE) | n/a | — (worked) |
| ZLR | ✅ armed | ✅ CCI −171 deep-RED | now NO_SETUP this bar; A3 SKIP "no patterns this bar" | justified (no fresh ZLR setup) | nothing — needs a ZLR structure |
| TLB/TT/GB100/HFE/HTLB(re)/FAMIR | ✅ armed | ✅ | A3 SKIP no patterns this bar (decision_tree pre_fire all SKIP/PASS, A5 advisory reject) | justified | — |

decision_tree (current, post-fire NO_SETUP): A1 SKIP·A2 PASS(11 studies)·A3 SKIP·A4 SKIP·**A5 PASS advisory `calculate_size=reject`**·A6 SKIP·A7. (A5 is advisory only — I-2 holds.)

**S2 — five_min** (mode=DAY_TYPE_MODE, opening_type=OPEN_REJECTION_REVERSE, buffer 7; board last_bar 13:40 lag ~57s)

| pattern | 1.נתון? | 2.הגיוני? | 3.מה חסם? | 4.צריך לחסום? | 5.מה חסר? |
|---------|---------|-----------|-----------|---------------|-----------|
| BEAR_FLAG_SHORT | ✅ **FIRED** 13:15 (id=10) | ✅ short into down-leg, C1 hit | — (fired, running to T2) | n/a | — (worked; only R-report wrong, F-1) |
| Reactive L/S, Initiative L/S, Inv-HnS, HnS-Top, DblBot-EE, DblTop-AA, BullFlag | ✅ data | mixed | **`Missing: data.choppiness_ok`** (9/10) | **NO — I-16 reproduces**: chop score exists (gw chop_state=FOUND) but boolean gate-flag reported missing while Bear Flag on same bar fired ⇒ flag-vs-score wiring gap | the boolean `data.choppiness_ok` derived from chop score |

**S3 — footprint** — `running+hydrated` but **`bars_processed_today=0`, buffer=0, ts=null, fresh=false, cumulative_delta=0**.
All 4 (Absorption/Stacked Imbalance/Sweep Return/Exhaustion) blocked `Insufficient buffer (0 bars, need 5)`.
1.נתון? ❌ · 2.הגיוני? ❌ (0 bars 5h into RTH) · 3.מה חסם? buffer empty · 4.צריך? n/a · 5.מה חסר? footprint ingest.
**I-11 persists (11th confirm). Critically: I-21 resumed but footprint stayed dead ⇒ confirms I-11 = ingest/parse break,
fully independent of the export stall.**

**Gates:** gateway — chop_state=FOUND, cooldown inactive, cluster 0, SSV none, no blocks. day_type/state =
**Variation 0.48 LOCKED_LOW_CONF, opening_type=UNKNOWN, session_min=0, IB WIDE** (I-1 unchanged). Board readiness verdict
= **BLOCKED** via `bridge_streams_fresh=false` (footprint/tick_reversal dead) — even though S2/S4 fresh and fired.

### Screenshot (Chrome MCP / computer-use)
`computer action=screenshot save_to_disk=true` → **not persisted to disk in this session** (unattended — I-9). Image
captured **inline only**. Dashboard (localhost:3000) confirms: top bar **VAR 48% M · 7427.00 · 0.7s ago · SHADOW 2 ·
WR 100%**; right panel id=10 **▼ SHORT 7444.00 BEAR_FLAG_SHORT · C1 HIT TARGET $76/61.0R** (F-1 visible); **Y IB
`dll_missing`** (yesterday-IB / atr_daily absent — feeds I-1); Woodies-CCI panel ≈ **−148.85** vs endpoint **−171.17**
(~22pt UI↔engine divergence, **I-15 persists**); chart shows a clean down-leg 7470→7427, x-axis reaching 13:40.

### Suspect status this snapshot
- **I-21** 5-min/study export stall — **RESOLVED this snapshot** (channel resumed ~13:15 CT; CCI un-froze; 2 fires). Watch for recurrence.
- **I-11** footprint 0 bars — **persists (11th)**; now **cleanly proven independent of I-21** (export resumed, footprint stayed dead). Ingest break. 🔴
- **I-1/C-2** day_type Variation/0.48 + opening_type=UNKNOWN + session_min=0 — **persists** 🔴.
- **I-15/C-1** trend RED durable, but UI-panel CCI −148.85 vs endpoint −171.17 (~22pt) — **persists**; Sierra cross-check mandatory.
- **I-16/I-17** choppiness_ok — **reproduces** (9/10 "Missing" while Bear Flag fired on same bar) → flag-vs-score gap + bar-boundary flip.
- **I-19/C-5** pattern-status hang — **not reproducing** (75ms).
- **I-20/C-6 + I-18/C-4** TZ-mix / threshold-not-enforced — **confirmed again**: bridge `lag=-9858 fresh=true` (thr 90);
  S4 `lag=956 fresh=true` (thr 660, positive over-threshold). Masks both the residual S4 lag and footprint death.
- **I-2** A5 advisory display — holds. **I-12** A5 `details{}` empty — holds.
- **I-13** A5 sizing — moot again (fires went through; NO_SETUP now).

### NOT-DONE / for CC (read-only here)
- **🔴 F-1 pnl_r inflated ~50×** (61.0R for a $76 1/3 T1; 16R for a BE stop). Audit `pnl_r` formula — corrupts ΣR/win-rate. **HIGH: blocks the whole counterfactual deliverable.**
- **🟡 F-2** gateway `trades_today/shadow_active_count/daily_pnl` all 0 despite 2 live shadow trades (1 still open).
- **🔬 I-21 root** still for CC: why did the 5-min/study export freeze 11:35→~13:15 CT then resume? Confirm via `~/SierraChart_Data/v9_export/` woodies_5min/5min_bars mtimes.
- **🔴 I-11 ingest break:** footprint export written but `bars_processed_today=0` — diagnose file→bridge-parse→buffer.
- **I-15** cross-check `cci_14=−171.17` + UI-panel −148.85 vs Sierra export — which is the true value.
- **I-1** `Y IB dll_missing` on dashboard — confirm yesterday-IB / atr_daily input is the missing feed behind opening_type=UNKNOWN/session_min=0.
- **Counterfactual (partial, R suspect):** both SHORTs directionally correct (price 7444→7427, ~17pt favorable); id=10 hit T1, running to T2; id=12 stopped at BE. ΣR cannot be trusted until F-1 fixed.

---

## ⏱ Snapshot — 14:12 CT (2026-06-05) · ~342 min into RTH · 48 min to close

**Clock:** 14:12 CT, inside RTH (08:30–15:00). All 8 endpoints answered (woodies 8ms · footprint 4ms · five_min 6ms · five_min/stats 8ms · trades 48ms · gateway 7ms · day_type 10ms · **build/pattern-status 79ms**). **I-19/C-5 hang NOT reproducing.**

### Raw values (this snapshot)
- **woodies/current:** `cci_14=-123.57` (MOVING — was −126.55 on the first call ~3s earlier; **no longer the 11:35 frozen −126.44** ⇒ 5-min channel live), `tcci=-143.08`, `ema34=7450.23`, `lsma=7414.66`, `swi=-4.49`, `czi=-181`, `trend_state=RED`, `signal=NEUTRAL`, `active_patterns=[]`, `classification=NO_SETUP`, `buffer=50`.
- **five_min/current:** `mode=DAY_TYPE_MODE`, `buffer=20`, `opening_type=OPEN_REJECTION_REVERSE`, `last_pattern=REACTIVE_SHORT`, `last_confluence=75`, `last_reasoning_notes="REACTIVE SHORT size=reject: 4-bar pattern, COT=-22087 vs AMT=-20755, location=far"`. **five_min/stats:** `patterns_detected=0, setups_published=0`.
- **footprint/current:** `running=true, hydrated=true, bars_processed_today=0, buffer_size=0`, all flow `null`, `cumulative_delta=0`; pattern-status `data_freshness: last_bar_ts=null, fresh=false`.
- **day_type/state:** `stage=B2, day_type=Variation, confidence=0.48, lock_state=LOCKED_LOW_CONF, opening_type=UNKNOWN, ib_width=WIDE, behavior=DEVELOPING, range_category=NORMAL, session_min=0`.
- **gateway/status:** `shadow_active_count=1, demo_slot_system=2, demo_enabled_systems=[2,4], live_enabled=[], daily_pnl=0, trades_today=0, consecutive_losses=0`, cooldown inactive, cluster_guard `recent_attempts=1` inactive.
- **trades/recent (3 today):** id=13 sys2 SHORT entry 7414.25 stop 7418 `pnl_r=null` (open, 14:05 CT) · id=12 sys4 SHORT entry 7443.75 stop 7443.5 `pnl_r=16 / $20` · id=10 sys2 SHORT entry 7444 stop 7443.75 `pnl_r=91.5 / $228.75`.
- **build/pattern-status readiness:** `verdict=BLOCKED, reason="dead: tick_reversal"`. checks: `bridge_streams_fresh=false (block)` · `s1_day_type_classified=true "day_type=Normal"` · `s4_trend_not_stuck_gray=true RED` · `in_rth=true`.
- **bridge global_gates:** woodies_5min `[FRESH] 22:05:00`(IL) · footprint `[FRESH] 22:09:35`(IL, **written this second**) · cumulative_delta `[FRESH] 19:05:00Z lag279s` · volume_profile FRESH · **tick_reversal `[DEAD] 198min · 15:51:19` (=10:51 CT)** · imbalance `[FRESH] 18:35:03Z` (actually ~37min old → stale-but-Present) · tpo_bars `[DEAD] 2023-11-25` (S5 unwired) · 5min_bars `[FRESH] 22:05:00`(IL). **bridge data_freshness:** `lag_seconds=-10520, fresh=true, threshold=90`.

### S2 (five_min) — 5-question deep check
| תבנית | יש נתון? | הגיוני? | מה חסם? | צריך לחסום? | מה חסר? |
|---|---|---|---|---|---|
| REACTIVE_SHORT | ✓ | ✓ | **FIRED** (id=13, 14:05 CT) — armed→detect→fire | — | — |
| BEAR_FLAG_SHORT | ✓ | ✓ | **FIRED** (id=10, 13:15 CT) | — | — |
| REACTIVE_LONG | ✓ | ✓ | detection `b3_buyers`: b3 close 7414.25 < open 7415.50 (bearish bar) | כן — תקין (trend RED, אין bullish bar) | — |
| INITIATIVE_L/S | ✓ | ✓ | detection `b1_expansion`: range=11.25 · need [4.5,6.0] | כן — תקין (טווח רחב מדי) | סף ATR-relative — לאמת מול atr_daily (חסר, I-1) |
| INVERSE_HNS_LONG | ✓ | ✓ | `swing_lows_found` 2 in 20 ✗ | כן | — |
| HNS_TOP_SHORT | ✓ | ✓ | `swing_highs_found` 1 in 20 ✗ | כן | — |
| DOUBLE_BOTTOM_EE | ✓ | ✓ | `eve_variant` T1/T2 width=1 bar ✗ | כן | — |
| DOUBLE_TOP_AA | ✓ | ✓ | `swing_highs_found` 1 ✗ | כן | — |
| BULL_FLAG_LONG | ✓ | ✓ | `pole_found` (need ≥5 bullish bars, ≥4pt) ✗ | כן — תקין (trend RED) | — |

**All 10 S2 armed; 2 fired; the other 8 block on REAL detection criteria — NOT "Missing: data.choppiness_ok".** ⇒ **I-16 NOT reproducing this snapshot** (choppiness_ok wired). Consistent with I-17 bar-boundary flip.

### S4 (woodies) — 5-question deep check
| תבנית | יש נתון? | הגיוני? | מה חסם? | צריך לחסום? | מה חסר? |
|---|---|---|---|---|---|
| HTLB | ✓ | ✓ | **FIRED** (id=12, 13:15 CT) | — | — |
| ZLR·TLB·TT·GB100·Vegas·Ghost·FaMir·HFE | ✓ | ✓ | armed · "Data ready, trend RED · not yet detected" (A3 no pattern this bar) | כן — תקין | — |

A1 PASS (11 studies), A5 advisory `calculate_size=reject` (does NOT block — I-2 holds). All woodies armed on live data. **ZLR (I-3):** still armed-not-detected, no counterfactual.

### S3 (footprint) — 5-question deep check
| תבנית | יש נתון? | הגיוני? | מה חסם? | צריך לחסום? | מה חסר? |
|---|---|---|---|---|---|
| ABSORPTION·STACKED_IMBALANCE·SWEEP_RETURN·EXHAUSTION | **✗ (0 bars)** | n/a | "Insufficient buffer (0 bars, need ≥5)" | החסימה תקינה *בהינתן* 0 ברים — אבל ה-0-ברים הוא **באג** | **ingest footprint שבור** (I-11) |

**I-11 persists (12th confirmation)** + **now decisively independent of I-21**: footprint export file is `[FRESH] 22:09:35` (written this second) yet `bars_processed_today=0` ⇒ **file→bridge-parse→buffer break**, not export stall.

### Suspect status this snapshot
- **I-21** (5-min/study export stall) — **stays RESOLVED** (CCI moving −123.57, S2/S4 channels live; was resolved ~13:15 CT). Monitoring recurrence.
- **I-11** footprint 0 bars — **🔴 persists (12th)**; cleanly independent of I-21 (file fresh, 0 bars). Root = ingest/parse, + `tick_reversal` stream DEAD since 10:51 CT.
- **I-1/C-2** day_type **3-way split persists 🔴**: state-endpoint + S2 day_type_gate = **Variation 0.48**, board header + readiness = **Normal**. `opening_type=UNKNOWN`, `session_min=0` (stuck at ~342 min into RTH). Dashboard `Y IB dll_missing` — yesterday-IB/atr_daily still absent.
- **I-15/C-1** trend RED durable; **UI-panel CCI ≈ −138.21/−147.6 vs endpoint −123.57 (~15–24pt divergence) — persists**. Sierra cross-check mandatory.
- **I-16/I-17** choppiness_ok — **NOT reproducing** (all 10 S2 armed/present). Supports I-17 bar-boundary volatility, not a fixed missing input.
- **I-19/C-5** pattern-status hang — **NOT reproducing** (79ms).
- **I-20/C-6 + I-18/C-4** TZ-mix / threshold-not-enforced — **confirmed again**: bridge `lag=-10520 fresh=true (thr 90)`; gates carry mixed TZ (woodies_5min/footprint/5min_bars in IL-local `22:0x`, cumulative_delta/volume_profile in UTC `19:0x`); imbalance Present-but-37min-stale; board shows Day Type/Footprint `? stale`. Masks footprint death + residual lag.
- **I-22/F-1** pnl_r inflated ~50× — **🔴 persists, visible in UI**: dashboard right panel id=13 "Stop 7414.00 | 2/3 hit | **$66 (52.5R)**", C1 $19=15.0R, C2 $47=37.5R; endpoint id=10 `$228.75 = 91.5R`, id=12 `$20 = 16R`.
- **I-23/F-2** gateway counters — **🟡 persists**: `trades_today=0, daily_pnl=0` despite 3 trades today; `shadow_active_count=1` (now non-zero, but day counters still 0).
- **I-2** A5 advisory display · **I-12** A5 `details{}` empty · **I-13** A5 sizing — hold (NO_SETUP / advisory only this snapshot).

### Board verdict judgment (question 4 — "should it block?")
`verdict=BLOCKED` driven **solely** by `bridge_streams_fresh=false` ← `tick_reversal` DEAD 198min. **S2 (×2) and S4 (×1) fired today and are fresh.** ⇒ A footprint/tick_reversal stream death is **gating the entire board** while the two live, firing systems are healthy. Worth a product call (CC/Michael): should S3/footprint death block S2+S4 entries, or degrade S3 only? Currently over-broad.

### Counterfactual (R untrustworthy — F-1)
Both fired SHORTs directionally correct (price drifted 7444→7396, ~48pt favorable to shorts). id=10 BEAR_FLAG: 2/3 targets hit (C1+C2), C3 open. id=12 HTLB: ~BE. id=13 REACTIVE: open, 2/3 hit per UI. **ΣR / win-rate cannot be computed until F-1 (pnl_r) is fixed.**

### Screenshot
`computer action=screenshot save_to_disk=true` → **not persisted to disk in this session** (unattended; tool returned "save_to_disk had no effect"). Captured **inline only** — IDs `ss_1668n1v8j` (Dashboard) + `ss_7360jgew3` (Build Status decision-tree table). Build Status shows: header **BLOCKED · day Normal · heartbeat <1s · 47m לסגירה · פתוח RTH**; chain **verdict BLOCKED → Day Type × stale → S3 BLOCKED → Footprint × stale → Woodies CCI ✓ → Min Patterns-5 ✓ → Bridge·Streams ✓**, root `dead: tick_reversal`; single blocker `bridge_streams_fresh`; S2 ×2, S4 ×1 fires; DATA_FRESHNESS Day Type/Footprint `? stale`, Woodies/Min-Patterns `660s warming 3m`; Killzone ✗. (I-9 file-persist gap.)

### NOT-DONE / for CC (read-only here)
- **🔴 F-1 (I-22)** pnl_r ~50× inflated — audit formula; blocks the counterfactual deliverable. Visible in UI ($66=52.5R).
- **🔴 I-11** footprint ingest break — file fresh, 0 bars → diagnose `file→bridge-parse→buffer`; + why `tick_reversal` stream dead since 10:51 CT.
- **🔴 I-1** confirm `Y IB dll_missing` / atr_daily is the missing feed behind `opening_type=UNKNOWN` + `session_min=0`; resolve Normal↔Variation split (board vs state-endpoint).
- **🟡 I-15** Sierra cross-check `cci_14` (endpoint −123.57 vs UI-panel ~−138/−147) — which is true.
- **🟡 I-20/I-18** TZ-normalize gate ts to UTC + enforce `|lag|≤threshold` (reject negative & positive over-threshold) before `fresh=true`.
- **🟡 I-23** wire gateway day counters (`trades_today/daily_pnl`) to shadow fires.
- **Product call:** should footprint/tick_reversal death block the whole board when S2+S4 are healthy?
