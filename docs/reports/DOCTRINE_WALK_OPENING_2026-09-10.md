# Doctrine walk — THE OPEN (§3.1 pp.63–74 + §1.3 IB) vs the code
**2026-09-10 · cowork-dev · READ-ONLY** (no edit / no .env / no flag / no restart).
Scope: Michael's framing — *"תפקיד מערכת 1 לבצע זיהוי של סוג הפתיחה… לאחר זיהוי סוג הפתיחה עליה
לבצע כניסה לפי הזיהוי"*. Question answered: does an identified opening type become an order?

Evidence base: `docs/spec_authority/DALTON_DOCTRINE.md` §3.1 (lines 125–145) · live code on the
MacBook · local Postgres · `/tmp/backend.err.log` (covers 09-06 → 09-10 only) ·
`GET /api/v9/day_type/classify_replay` over the 22 sessions 08-11 → 09-09.

---

## 0 · The one number that frames everything

**The two live opening-type authorities agree on 6 of 22 sessions (27%).**

| source | window | detector | where it lands |
|---|---|---|---|
| `state_machine._stage_a2` (`state_machine.py:569-587`) | **3 RTH bars = 15 min** | LEGACY 4-type `detector.py:162`, then **overridden** by a CVD label (`detector.py:397-402`) | `v9_day_type_state.opening_type`, `v9_day_type_history`, gateway, briefing |
| `classifier_core` (`classifier_core.py:104-109`) | **6 RTH bars = 30 min** | `opening_detector_v2.py:66` (5-type) | `classify_replay`, Build-Status, UI, the canonical day-type |
| `opening_entry.evaluate_opening_entry` (`opening_entry.py:67`) | bars 2–12 | **its own OR-geometry triggers — reads no `opening_type` at all** | the actual orders |

Measured (query: `v9_day_type_history.opening_type` vs `classify_replay(date).opening_type`,
08-11…09-09, n=22): match on 08-11, 08-13, 08-21, 09-01, 09-02, 09-03 → **6/22 = 27%**.
Worked examples: 09-08 live=`OPEN_AUCTION_IN`, canonical=`OPEN_TEST_DRIVE`, order engine fired
`DRIVE SHORT`. 09-07 live=`OPEN_REJECTION_REVERSE`, canonical=`OPEN_AUCTION_IN`, order engine
fired `DRIVE SHORT`. Three answers, same open.

---

## 1 · Status table — every rule §3.1 states

`doctrine (quote ≤12 words · line) · code (file:line) · status · evidence`

| # | Doctrine rule | Code | Status | Evidence |
|---|---|---|---|---|
| 1 | "The market's open often foreshadows the day's outcome" (l.126) | `_provisional_from_open` `daytype_classifier.py:67-95`, called `:328-340` | **ALIGNED** | `classify_replay` 22/22 sessions emit a committed provisional; 0 bare-FORMING past 30 min |
| 2 | "Conviction is readable in the **first few minutes**" (l.126) | provisional committed at bar 5–7 (`segments[]` `time` 09:55/10:05 ET) | **PARTIAL** | 15/22 first non-FORMING at **09:55 ET (25 min)**; 7/22 at **09:35 (5 min)** via `S1_ACCEPTANCE_RECLASS_V1` acceptance-reclass. Never in "the first few minutes" for the other 15 |
| 3 | **Open-Drive**: "drives, never re-trades the opening range" (l.130) | `opening_detector_v2.py:114-152` | **PARTIAL** | Code tests the *opening range* (bar 1 hi/lo), not the opening **print** — deliberately relaxed (`:115-116`). Thresholds `near=0.2×rng6`, `close ≥ open+0.5×rng6`, `tol=1 tick` are **invented** (house calibration from Michael's "סוגי פתיחה" sheet, `:3-5`); Dalton gives no numbers |
| 4 | Open-Drive → "**Trend or Normal Variation**; enter early" (l.130) | `daytype_classifier.py:75-93` maps DRIVE×out_of_range→Trend_Normal, DRIVE×in_range→Normal_Variation | **ALIGNED** | 09-03 replay: `bar7 10:05 Trend_Normal PROVISIONAL "@30m provisional [OPEN_DRIVE/out_of_range]"` |
| 5 | Open-Drive origin: "return through it = exit" (l.130) | `relative_features.py:186-192` `returned_through_open` → blocks Trend (`daytype_classifier.py:120`); `opening_detector_v2.py:135-147` invalidates the label | **PARTIAL** | It reclassifies; **no exit signal is emitted** — no consumer in `system6_supervisor`/gateway |
| 6 | **Open-Test-Drive**: tests a reference, fails, drives opposite (l.131) | `opening_detector_v2.py:158-174`, poke 2–6 ticks beyond PDH/PDL/VAH/VAL | **ALIGNED** | Reference set is the book's (prior H/L + prior VA); poke band 2–6T invented |
| 7 | OTD → "2nd most reliable" (l.131) | conf 0.75 vs DRIVE 0.85 (`:170` vs `:150`) | **ALIGNED** | ordering matches the book |
| 8 | **Open-Rejection-Reverse**: "reverses back through the open"; Trend unlikely (l.132) | `opening_detector_v2.py:176-185`; `daytype_classifier.py:90` → `Neutral_Center` | **ALIGNED** | 08-25 replay: `Neutral_Center PROVISIONAL "rejection-reverse -> two-sided; Trend unlikely (p.68)"` |
| 9 | **Open-Auction in range** → "a big day unlikely" (l.133) | `opening_detector_v2.py:199-201`; `daytype_classifier.py:92` → `Normal` | **ALIGNED** | 09-04/09-07 replay carry that exact reason string |
| 10 | **Open-Auction out of range** → "often gives rise to **DD Trend days**" (l.134) | `opening_detector_v2.py:187-198` (+`OPENING_DALTON_GAPS_V1=1` conviction=high); `daytype_classifier.py:88` → `Normal_Variation` "DD/Trend watch" | **PARTIAL** | Label + watch exist; **no DD-specific behaviour** follows (`dd_features` runs on structure only) |
| 11 | Open **within** prior value + acceptance → balance, range ≈ prior range (l.136) | `context_features.open_location` (`in_value`) + `day_context_extras.range_estimate` | **PARTIAL** | `range_estimate` computed and returned by replay (09-08: `est_target 7674.5`), consumed by **no** gate or target rule |
| 12 | Open **outside range + acceptance** → out of balance, "usually a Trend day" (l.138) | `_provisional_from_open` `daytype_classifier.py:82-84` (DRIVE/TD × `out_of_range` → Trend_Normal) | **PARTIAL** | Only when opening_type is a drive; `OPEN_AUCTION_OUT × out_of_range` → Normal_Variation, not Trend |
| 13 | Outside range + **rejection** → dynamic move the *other* way (l.138) | — | **MISSING** | no code path; `grep -rn "gap_erase\|unfilled gap" backend/v9/{systems,gateway,services}` ⇒ 0 |
| 14 | **Gap = out of balance; not filled in ~first hour → continuation** (l.139) | `state_machine.py:517-556` computes `gap_size/gap_direction/gap_magnitude` into `PreOpenContext`; `detector.py:254 classify_gap_atr` | **MISSING (computed, never consumed)** | `PreOpenContext` reaches only `to_classification()` (`state_machine.py:956`) → a display field. No gate, no target, no timer reads it |
| 15 | "stop where the gap is fully erased" (l.139) | — | **MISSING** | no gap-anchored stop anywhere; `stop_anchors/resolver` has no gap anchor |
| 16 | §1.3 IB = "first two half-hour periods… the *base* of the day" (l.49) | 60-min IB, Sierra TPO SoT (`S1_ACTIVE_CANONICAL §1`); `ib_narrow ≤0.7×median` `classifier_core.py:112` | **ALIGNED** | 09-08 replay `ib_source:"sierra_tpo" ib_width 37.75 ib_pctile 0.59` |
| 17 | §1.3 "Narrow base → easily upset → RE/trend likely" (l.50) | `ib_narrow` used inside Nontrend/Normal/DD branches only | **PARTIAL** (doctrine's own gap P0-2 note, l.54) | narrow IB is not an early trend-watch prior |
| 18 | §3.1 S1-status line: "canonical classifier returns bare FORMING until 12 bars… **Contradiction**" (l.141-145) | closed by `S1_COMMITTED_PROVISIONAL_V1=1` | **ALIGNED (closed)** | doctrine §7 l.264; replay shows PROVISIONAL at ≤bar 7 on 22/22 |
| 19 | Ruling: **`opening_type@15min`** (S1 staging, PERMANENT) | live path = 3 bars/15 min (`state_machine.py:572`) ✔ · canonical path = **6 bars/30 min** (`classifier_core.py:104`) ✘ | **CONTRADICTS** | the two paths implement two different rulings; the 27% agreement above is the consequence |
| 20 | Conviction is a **continuum**, "monitor conviction very early" (§2 l.107) | `_confidence` `daytype_classifier.py:98-140` (8-item evidence vector, `S1_CONFIDENCE_V2=1`) | **ALIGNED** | `opening_type ∈ {DRIVE,TEST_DRIVE}` is 1 of 8 evidence items |
| 21 | Certainty **before** the first trade (Michael 31.07, not Dalton — the book calls the open the highest-information moment) | `opening_first_trade_ok` `opening_entry.py:391-466` | **CONTRADICTS the ruling, ALIGNED with the book by accident** | the veto at `:451-453` compares `OPEN_DRIVE_UP/DOWN`,`TEST_DRIVE_UP/DOWN` — **strings no producer emits** (`opening_detector_v2` returns `OPEN_DRIVE` + a separate `direction`). And its input `market_context.opening_type` is permanently `UNKNOWN` because `APP_STATE_ROOT_FIX_V1=shadow` (`.env:635`) never writes `app.state.opening_type_result` (`main.py:861-876`). **Double-dead** ⇒ the gate reduces to "≥3 bars + last bar closes with direction". Already logged as G-38 |

---

## 2 · "Enter according to the identification" — the full path, and every place it dies

Producer → `opening_entry.evaluate_opening_entry` (`opening_entry.py:67`), 5 triggers, one
initiating entry per session:

| trigger | line | earliest bar | live today? |
|---|---|---|---|
| `ORR` | `:107-113` | 3 | emitted, then **always blocked** (see D3) |
| `PULLBACK_CONT` | `:122-148` | 3 (needs `OPENING_FIRE_V1=1` ✔) | yes |
| `DRIVE` | `:154-172` | 2 (needs `or_width ≤ max(10, 0.25×ATR)`) | yes |
| `TEST_DRIVE` | `:174-188` | 3 | yes, but **only from 16:45** (see D2) |
| `EXTREME_REJECT` | `:190-215` | 3 | emitted, then **always blocked** (see D4) |

**Every point where an identified opening type fails to become an order** (in execution order):

| # | Gate | file:line | state today | effect |
|---|---|---|---|---|
| D0 | `_oe_disabled` — "honest skip today" | `five_min_system.py:2138-2146` | active | first bar seen past 09:30 ET ⇒ **opening engine dead for the whole session**. Fired **3×** in the log window: 09-08 16:56 + 17:19, 09-09 16:58 |
| D1 | `OPENING_DIR_FUSION_V1` gate | `five_min_system.py:2196-2201`, `opening_entry.py:356-360` | `=1` | `opening_vol < trailing median` ⇒ `None` ⇒ trigger dropped. 09-07: `opening_vol 7,293 < median 112,388`; 09-09: `90,310 < 112,388`. **Only applies once `_oe_fusion_done`** (bar ≥6 or a definite UP/DOWN) — the 09-07 DRIVE at bar 5 escaped it. 0 "gate dropped" lines in the window |
| D2 | `OPENING_FIRST_TRADE_STRICT_V1` | `five_min_system.py:2206-2233` → `opening_entry.py:391-466` | `=1` | direction-veto is dead (row 21); the confirmation-bar half **is** live and delays entries: 09-07 held at 16:40 and 16:45, fired 16:50 (bar 5, 20 min late); 09-08 held at 16:35, fired 16:40 |
| D3 | `dalton_intent:bias` on ORR | `trading_gateway.py:1109-1148` + `dalton_playbook.py:88-94` | `DALTON_PLAYBOOK_V1=1` | gateway passes the **setup** direction as `direction_hint`, then `reversal_direction` **inverts it again** ⇒ bias always opposes the ORR. Simulated on the live config: ORR LONG and ORR SHORT both → `dalton_intent:bias` in phase B, `stand_down` in phase A. **ORR can never fire** |
| D4 | `dalton_intent:stand_down` on EXTREME_REJECT | `trading_gateway.py:1112-1117` | `=1` | `_P15_MAP` has no `OPENING_EXTREME_REJECT` key ⇒ `opening_type` stays UNKNOWN ⇒ default rule (`dalton_playbook.yaml:69-75`, `:109-115`) ⇒ `size_frac 0` in **both** phase A and B |
| D5 | Phase A allows only `OPEN_DRIVE` | `dalton_playbook.yaml:58-75` | `=1` | 16:30–16:45: `TEST_DRIVE`, `ORR`, `EXTREME_REJECT` all stand down. Only DRIVE/PULLBACK_CONT survive |
| D6 | `_dp_ot` is never read from the machine | `trading_gateway.py:1096-1101` vs `trading_gateway.py:5201-5212` | `=1` | `_capture_cross_context()` stores `day_type_machine.get_current()` — a **dict** (`state_machine.py:986-1002`). `hasattr(dict,"opening")` is False ⇒ `_dp_ot` is **always** `"UNKNOWN"`. Production proof 09-09: **7 phase-B blocks reading `phase=B cond=default bias=NONE`** (FAILED_RE_IB, ZLR×4, GB100, HTLB) — no opening rule ever matched. Consequence: **from 16:30 to 17:30 the only patterns that can trade at all are `OPENING_*`** (the P1.5 fallback is the only way an opening_type is ever set) |
| D7 | `direction_compass` | `trading_gateway.py:2255-2295` | skipped while `_dp_active` | killed the 09-07 DRIVE: `BLOCKED by direction-compass: OPENING_DRIVE SHORT against compass UP (conf 1.00)`. Now bypassed by the playbook — untested at an open |
| D8 | `OPENING_DRIVE_SKIP_V1` | `five_min_system.py:2234-2244` | **`=0`** (`.env:705`) | inert |
| D9 | `OPENING_PATTERN_SKIP_V1` | `five_min_system.py:2245-2274` | **unset** (`grep ⇒ 0` in `.env`) | inert |
| D10 | Stop cap / max-risk | `opening_entry.py:245-269` | 15 / 25 pt | 09-08: `STOP CAP DRIVE SHORT: structural 15.75pt -> capped 15.0pt` |
| D11 | `T3_REQUIRED_V1` × `RISK_MIN_CONTRACTS=3` | `opening_entry.py:285-308` | fixed by `OPENING_LADDER_V1=1` (`.env:741`) | was rejecting 100% of opening PLACEs from 02.09; now t2/t3 = 2.5R/4.0R |

---

## 3 · Measurement — 22 sessions (08-11 → 09-09)

Method: opening type + provisional timing from `classify_replay` per date (canonical, T-252-safe —
replay classifies closed bars once); orders from `v9_trades` deduplicated by
`(date, pattern_id_at_entry)` because every routed setup writes a **shadow twin + a live row**;
block reasons from `/tmp/backend.err.log` (09-06→09-10 only — earlier logs are gone).

**Opening type detected: 22/22 sessions.** Canonical distribution: `OPEN_AUCTION_IN` 10 ·
`OPEN_TEST_DRIVE` 5 · `OPEN_AUCTION_OUT` 4 · `OPEN_DRIVE` 2 · `OPEN_REJECTION_REVERSE` 1.
**IL minute of first committed classification:** 09:55 ET = 16:55 IL (**25 min**) on 15/22;
09:35 ET = 16:35 IL (**5 min**) on 7/22 (08-12, 08-13, 08-14, 08-25, 08-27, 08-28, 09-03) — all
seven via `acceptance-reclass: accepted PDH/prior_VA break`, not via the opening type.

**Opening setups → orders (the whole window, deduplicated):**

| date | canonical open | trigger | IL | reached broker? | outcome |
|---|---|---|---|---|---|
| 08-11 … 08-26 (12 sessions) | — | **none emitted** | — | — | — |
| 08-27 | `OPEN_AUCTION_IN` | `ORR LONG` | 16:55 | **yes** — live #822 | −$100 STOP_FILL |
| 08-31 | `OPEN_TEST_DRIVE` | `DRIVE SHORT` | 16:40 | **yes** — live #875 | −$100 STOP_FILL |
| 09-01…09-04 (4) | — | none emitted | — | — | — |
| 09-07 | `OPEN_AUCTION_IN` | `DRIVE SHORT` | 16:50 | **no** — `blocked_by=direction_compass` | shadow #1179 −$68.75 |
| 09-08 | `OPEN_TEST_DRIVE` | `DRIVE SHORT` | 16:40 | **yes** — live #1220 routed… | **`entry_ts=NULL`, `exit_reason=SIERRA_FLAT`, `outcome=UNPRICED` — the order never opened** |
| 09-09 | `OPEN_AUCTION_OUT` | — | — | — | `honest skip today` at 16:58 (the RTH restart that enabled `DALTON_PLAYBOOK_V1`) |

**Totals, last 10 sessions (08-27 → 09-09): 7 trigger evaluations → 4 setups emitted → 3 reached
the broker → 1 actually opened a position.** The 7↔4 gap is `OPENING_FIRST_TRADE_STRICT` holds
(09-07 16:40 + 16:45, 09-08 16:35). Over the full 22 sessions the numbers are identical — **no
opening setup at all was emitted on 08-11…08-26.** Deduplicated non-firing reasons:
`honest skip today` ×3 · `OPENING_FIRST_TRADE_STRICT held` ×3 · `direction_compass` ×1 ·
`SIERRA_FLAT / never filled` ×1.

⚠️ **The shadow measurement of opening entries is itself corrupted.** Trade #1219 (09-08 shadow
twin) is recorded `SHORT entry 7701.00 stop 7699.00` — the stop is **below** entry for a short, and
it is the *same* 7699.00 written to #1221 (a different pattern the same second). The log line for
the same setup says `stop=7716.00`. It then books `STOP_HIT +$70.00 WIN`. Any "opening entries are
profitable in shadow" claim built on that row is false.

---

## 4 · What the open tells the rest of the day

| consumer | reads opening_type? | file:line |
|---|---|---|
| provisional day-type (0–60 min) | **yes** | `daytype_classifier.py:75-95` |
| canonical confidence | **yes** (1 of 8 evidence items) | `daytype_classifier.py:118-127` |
| Trend waiver after IB-lock (`S1_OPEN_DRIVE_TREND=1`) | **yes** | `daytype_classifier.py:445-454` |
| **Entry gate, phase C (17:30–21:00)** | **NO** — every phase-C rule keys on `day_type` only | `dalton_playbook.yaml:117-162` |
| Phase D (21:00+) | N/A — `manage_only` stand-down | `dalton_playbook.yaml:164-174` |

So the open's *forecast* survives into S1's label and confidence, but the open's *instruction*
("enter according to the identification") is discarded from the order path at **17:30**. Dalton's
own carry-forward reads — `range_estimate` (pp.75-79), `va_rule_read` (p.278), `eod_continuation_tag`
(p.277) — are all computed (`day_context_extras.py:52,93,124`) and returned by `classify_replay`,
and **none of them is read by a gate, a target rule, or the morning briefing**.

---

## 5 · Gaps ranked by money-relevance

| rank | gap | smallest fix | shippable? |
|---|---|---|---|
| **1** | **D6 — `_dp_ot` is always UNKNOWN**, so 16:30–17:30 stands down every non-opening pattern and the playbook's own phase-A/B opening rules never see the real open. 09-09 already lost 7 phase-B candidates this way. | one line: read `cross_context["day_type_machine"]["opening_type"]` (it is a dict, `state_machine.py:995`) instead of `.opening.opening_type` — **or** read the canonical `classify_replay` opening type. | **Implements the existing 09.09 ruling** ("כל סוג-פתיחה צריך להיכנס לעץ-החלטות אחר") — the tree cannot branch without the input. Ship. ⚠️ Read the *canonical* type, not the state machine's: at 27% agreement, wiring the wrong one is worse than UNKNOWN. |
| **2** | **The identification is not one number (27%/22).** Three producers, two windows (15 vs 30 min), and the live one is overridden by a **synthetic** CVD proxy (`state_machine.py:576-580` builds `sign(c−o)×volume`, not footprint delta) that can only emit 3 of the 5 labels (`detector.py:391-402`). The header at `detector.py:237` still calls it "shadow only" — it is live. | make `classifier_core.detect_opening_type` (v2) the single producer for `state_machine.opening`; keep the CVD read as a shadow field. | **New trading-risk behaviour** → Michael. (It changes the label that feeds day-type, confidence and the playbook.) Rule-1 violation (synthetic value under a canonical flag) is fixable independently and is not a risk change. |
| **3** | **D3 ORR can never fire** (double inversion of `direction_hint`). ORR is the only opening trigger with a positive record (07-31 #577 `T1_HIT +$80`; 4/5 to +1R in the 31-session study, `opening_entry.py:17-22`). | in `trading_gateway.py:1143-1148`, for `OPENING_ORR` pass the **drive** direction (opposite of the setup) as `direction_hint`; `_resolve_bias` then re-inverts to the setup direction. Add a regression asserting ORR LONG passes phase B. | **Implements the 09.09 ruling** — the yaml already says ORR→`REVERSAL`+`reversal_direction`; the code contradicts the config. Ship. |
| **4** | **D0 `honest skip today` — 3 of the last 3 sessions with a post-open restart lost the entire opening engine.** 09-09 lost it to the restart that turned the playbook ON. | none needed in code today: **do not restart the backend after 16:30 IL.** Code fix later: rebuild `_oe_bars` from `v9_bars_5min_woodies` on restart instead of disabling the day (collection already accepts stale bars, `five_min_system.py:2129-2139`). | Operational rule = free. The rebuild is **new behaviour** → Michael. |
| **5** | **D4 EXTREME_REJECT unreachable** — missing `_P15_MAP` key. It is Michael's own 07-22 "מדויק" rule, validated 12/14 to +1R. | add `"OPENING_EXTREME_REJECT": "OPEN_TEST_DRIVE"` (a tested-and-rejected extreme *is* the test-drive family) to `trading_gateway.py:1112-1117`, and a `REVERSAL` row to phase A/B if Michael wants it in the first 15 min. | Map entry alone = **implements** the existing ruling. Adding a phase-A REVERSAL row = **new** → Michael. |
| **6** | **Row 21 — the first-trade certainty ruling is not implemented** (dead strings + `APP_STATE_ROOT_FIX_V1=shadow`). Trade #575 (−$199) is still possible today. | compare `opening_type` + `direction` as two fields (the producer already returns both), and flip `APP_STATE_ROOT_FIX_V1` to `1` so the input exists. | Restores an **existing ruling** (31.07 18:20) → ship, but it *reduces* fires: verify on replay first (it blocked 7/7 candidates in its old form, `opening_entry.py:399-403`). |
| **7** | **Rows 13–15 — the gap is invisible to the trading path.** `gap_size/gap_magnitude` are computed every session and consumed by nothing. | emit `gap_unfilled_at_60min` from `PreOpenContext` + the session bars, and expose it as a `feat` key for `classify()`; shadow-log first. | **New** (a new classification input) → Michael. |
| **8** | Rows 5, 11 — Open-Drive-origin return and `range_estimate` reclassify/compute but never exit or target. | wire `returned_through_open` to a System-6 advisory (never `op=EXIT` — that path is broken). | **New** → Michael. |

---

## 6 · Bottom line for 16:30 today

**No — the opening path is not ready to trade the identification correctly today.**
`OPENING_DRIVE` and `OPENING_PULLBACK_CONT` can fire (and `TEST_DRIVE` from 16:45); `ORR` and
`EXTREME_REJECT` are structurally unreachable; and because `_dp_ot` is always `UNKNOWN`, every
non-opening pattern is stood down from 16:30 to 17:30 — today is the **first full session** with
`DALTON_PLAYBOOK_V1=1` from the open, and that combination has never run through an open.

**The single thing that would stop it: a backend restart after 16:30 IL.** `_oe_disabled`
(`five_min_system.py:2142`) kills the opening engine for the entire session the first time it sees
a bar past 09:30 ET — it fired on 09-08 (twice) and on 09-09, and on 09-09 the restart that did it
was the one that turned the playbook on. Restart before 16:30 or not at all.

*Verified 2026-09-10 09:33–09:46 IL. Backend pid 13274 (boot 09-09 23:37, commit `0151d586`),
newest `v9_bars_5min_woodies` 09:45 IL vs now 09:46 IL.*
