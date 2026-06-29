# MEMS26 — Flag Index (canonical)

> **AUTO-GENERATED — do not hand-edit.** Run `python3 scripts/gen_flag_index.py`.
> Meaning of each flag is hand-authored in `docs/FLAG_REGISTRY.yaml`; every other
> column is read live from the code + `.env` at generation time, so this file
> cannot go stale the way `SOURCE_OF_TRUTH.md` did.

_Generated 2026-06-29 19:24 · `.env` last modified 2026-06-29 16:32 · scan dirs: backend, bridge_

**Legend:** ✅ ON · 🔴 OFF · 🟡 ON·inert (set ON but superseded at runtime) · 🔢 numeric param · ⚪ not built.

**Summary:** 66 documented · 43 ON (of which 3 inert) · 9 OFF (3 standing-OFF) · 13 numeric params · 1 awaiting backtest · 1 rejected · 1 not built.

> ⚠ **3 registry flag(s) not referenced in code** (dead or renamed?): `RISK_CONSECUTIVE_LOSS_LIMIT`, `RISK_DAILY_LOSS_CAP`, `RISK_MAX_TRADES_DAY`

## S1 — Day-type / classification

| Flag | State | Current | Code default | What it does | Why / state | Where (file:line) | Notes |
|------|-------|---------|--------------|--------------|-------------|-------------------|-------|
| REHYDRATE_CLS_BARS | ✅ ON | unset → "1" | "1" | On mid-session restart, seed _cls_rth_bars from DB (v9_bars_5min_woodies) when IB locked but buffer short. Prevents ~1h classifier starvation (#11). | ON by default (fail-safe, not a trading-logic change — restores the buffer that existed before restart). Disable with =0 + restart. | `backend/main.py:315` |  |
| S1_CVD_OPENING | ✅ ON | `true` (.env) | False (flag() default) | Seed the early day-type read from opening-window CVD. | SHADOW calibration, enabled before the soak (Michael 31/5). | `backend/v9/shared/atr.py:103` |  |
| S1_DAYTYPE_STAGING | ✅ ON | `true` (.env) | False (flag() default) | Staged day-type lifecycle: opening_type@15m / day_type@30m / IB-lock@60m / intraday reclass. | PERMANENT S1 staging spec; enabled before SHADOW soak. | `backend/v9/shared/atr.py:104` | memory: project_s1_staging_spec |
| S1_DYNAMIC_RECLASS | ✅ ON | `true` (.env) | "" (empty → OFF) | Continuously re-evaluate day-type IB-relative after IB lock (shadow log). | Michael 2026-06-08 — "the system constantly checks which day-type". | `backend/main.py:196`<br>`backend/v9/shared/atr.py:106` |  |
| S1_ENGINE_NEW_CLASSIFIER | ✅ ON | `1` (.env) | "" (empty → OFF) | Live per-bar engine uses the 7-type classifier instead of the old 3-type engine (part-b). | Michael approved 2026-06-22 mid-session. | `backend/main.py:346` |  |
| S1_IB_WIDTH_ATR | ✅ ON | `true` (.env) | False (flag() default) | Measure IB width in ATR units (relative) for day-type width tests. | SHADOW calibration (Michael 31/5). | `backend/v9/shared/atr.py:105` |  |
| S1_LIVE_RECLASS | ✅ ON | `true` (.env) | "" (empty → OFF) | Apply the dynamic reclassification to the LIVE day_type (not just log it). | Pair of S1_DYNAMIC_RECLASS — both required for the day-type to keep re-evaluating. | `backend/main.py:502`<br>`backend/v9/shared/atr.py:110` |  |
| S1_NEW_CLASSIFIER | ✅ ON | `1` (.env) | (no default) | Promote the validated 7-type classifier label to the trade gate (day_type_at_entry → 3 gates + stamp). | Michael approved 2026-06-20; fail-safe. Off-switch: =0 + restart. | `backend/env_loader.py:76`<br>`backend/v9/services/trade_context.py:511` | memory: project_s1_promotion_live |
| S1_PROVISIONAL_DAYTYPE | ✅ ON | `1` (.env) | "" (empty → OFF) | Emit a provisional day_type at 30m (before the 60m IB lock); lock still overrides. | Eliminates the 60-min UNKNOWN gap. | `backend/v9/systems/day_type/state_machine.py:390` |  |

## S2 — 5-min (Reactive / Initiative)

| Flag | State | Current | Code default | What it does | Why / state | Where (file:line) | Notes |
|------|-------|---------|--------------|--------------|-------------|-------------------|-------|
| OPENING_FIRE_CVD_V1 | 🔴 OFF | unset → "0" | "0" | CVD-confirm OPEN_DRIVE + suppress pre-IB-lock old-engine directional fallback for pattern selection. | OFF (default, SHADOW only). 2026-06-29 incident: 4× INITIATIVE_SHORT fired on premature Variation + unconfirmed drive (CVD absorption ignored). Michael sign-off required to enable. | `backend/v9/systems/opening_type_gate.py:67`<br>`backend/v9/services/trade_context.py:524` | deferred; docs/handoff/CC_STAGE0_OPENING_FIRE_CVD_2026-06-29.md |
| S2_ATR_RELATIVE | ✅ ON | `true` (.env) | default=True | Scale S2 thresholds to ATR (relative) instead of fixed points. | SHADOW calibration (Michael 31/5). | `backend/v9/shared/atr.py:101` |  |
| S2_CHART_ALL_DAYTYPES | ✅ ON | `1` (.env) | "" (empty → OFF) | Allow the S2 chart-pattern family (FLAGS/HnS/…) to evaluate across all day-types. | Anchor-trial (2026-06-12). | `backend/v9/systems/five_min/five_min_system.py:107` |  |
| S2_CHOPPINESS_GATE<br><sub>chop gate (1 of 2)</sub> | 🔴 OFF | unset → "0" | "0" | S2 arming/display gate requiring choppiness_score < 70 (5-bar candle geometry; >=70 = choppy). | DISABLED by Michael 2026-06-08. Inspector/build-status surface only — never vetoed a real fire. | `backend/v9/systems/build_status/s2_inspector.py:153` | STANDING-OFF — Michael sign-off to enable; CLAUDE.md §Chop Gates |
| S2_DETECTION_LOG | ✅ ON | `1` (.env) | "" (empty → OFF) | Verbose S2 detection logging (observability). | Anchor-trial diagnostics (2026-06-12). | `backend/v9/systems/five_min/five_min_system.py:709`<br>`backend/v9/systems/five_min/five_min_system.py:808` |  |
| S2_REQUIRE_COT_AMT | 🔴 OFF | unset → "" (empty → OFF) | "" (empty → OFF) | Re-require footprint COT/AMT order-flow confirmation for S2 fires (S2 depends on S3). | DISABLED 2026-06-08 (S2 ⟂ S3): S3 is muted/broken (S3_MUTE / I-11); requiring it would block all S2. | `backend/v9/systems/five_min/five_min_system.py:605`<br>`backend/v9/systems/five_min/five_min_system.py:747` | STANDING-OFF — Michael sign-off to enable; CLAUDE.md §S2 ⟂ S3 |
| S2_VOL_ADAPTIVE | ✅ ON | `1` (.env) | "" (empty → OFF) | Adaptive volatility-regime adjustment for S2 thresholds/sizing. | Anchor-trial (2026-06-12). | `backend/v9/systems/five_min/five_min_system.py:75` |  |
| S2_VSA_VOLUME | ✅ ON | `1` (.env) | False (flag() default) | Enable the 3-variant VSA/RVOL volume gate; variant selected from config/s2_firing.yaml. | Moved into .env so all launch paths share it; matches prior start_all.sh export. | `backend/v9/shared/atr.py:111`<br>`backend/v9/systems/build_status/s2_pattern_probe.py:569`<br>`backend/v9/systems/five_min/five_min_system.py:616`<br>(+1) |  |

## S3 — Footprint (suppressed pre-LIVE)

| Flag | State | Current | Code default | What it does | Why / state | Where (file:line) | Notes |
|------|-------|---------|--------------|--------------|-------------|-------------------|-------|
| FOOTPRINT_DISABLED | ✅ ON | `1` (.env) | False (flag() default) | Fully disable S3 footprint processing AND writing (process_bar returns immediately) — not just fires. | Michael 2026-06-08: take S3 down until after LIVE; it has not ingested a bar all session (I-11). | `backend/v9/shared/atr.py:109` | STANDING-OFF — Michael sign-off to enable; CLAUDE.md §S3 Footprint |
| S3_MUTE | ✅ ON | `1` (.env) | False (flag() default) | Mute S3 fires (footprint signals computed but not routed). | S3 muted pre-LIVE (I-11). | `backend/v9/shared/atr.py:108` |  |
| S3_RELATIVE | ✅ ON | `true` (.env) | False (flag() default) | S3 footprint thresholds relative/ATR-scaled. | SHADOW calibration (Michael 31/5). (S3 itself is disabled — see FOOTPRINT_DISABLED.) | `backend/v9/shared/atr.py:102` |  |

## S4 — Woodies (ZLR / HFE / TLB / …)

| Flag | State | Current | Code default | What it does | Why / state | Where (file:line) | Notes |
|------|-------|---------|--------------|--------------|-------------|-------------------|-------|
| HFE_DISABLED | ✅ ON | `1` (.env) | (no default) | Disable all HFE (Hook From Extreme) fires — both Python detector and DLL hfe_detected flag. No HFE fire emitted from any source. | ON 2026-06-24, Michael's rule: HFE is not his pattern ('אני לא מכיר hfe'). Single biggest loser: 27 fires, -$2,987 (9W/18L). Disabling removes the largest drag. | `backend/env_loader.py:73`<br>`backend/v9/systems/woodies/woodies_system.py:357` | docs/handoff/CC_HFE_DISABLE_TAXONOMY_2026-06-24.md |
| HTLB_DIRECTION_GATE<br><sub>HTLB direction signal</sub> | ✅ ON | `1` (.env) | False (flag() default) | HTLB signals the directional bias for ALL Woodies patterns: a zoned HTLB break (resistance in [-200,-100] broken up = UP / support in [+100,+200] broken down = DOWN) latches a direction until the next zoned HTLB; while latched, only patterns in that direction fire (the rest are dropped). | ENABLED in SHADOW 2026-06-23 (Michael) after backtest: blocks 25 counter-bias S4 fires, removes $2681 losses vs $912 wins -> net +$1769. Latched until next zoned HTLB; inert on days with no zoned HTLB. | `backend/v9/systems/woodies/woodies_system.py:479` | docs/spec_authority/S4_WOODIES_TABLE_A_Pattern_Setup.csv |
| S4_EXTREME_TREND_RELABEL | ✅ ON | `true` (.env) | False (flag() default) | Relabel extreme-trend Woodies CCI states (trend-color handling). | SHADOW calibration. | `backend/v9/shared/atr.py:107`<br>`backend/v9/systems/woodies/trend_relabel.py:23` |  |
| TLB_SPEC_V2<br><sub>TLB source-spec</sub> | ✅ ON | `1` (.env) | False (flag() default) | Gate TLB to the source spec (Stage 1): require a +/-200 (SWI) extreme on the trade side within 12 bars AND a confirming CONT partner (GB100/ZLR/TT) same-direction; else reject. Old linreg geometry stays when OFF. | ENABLED in SHADOW 2026-06-23 by Michael's explicit override: fire TLB per the source characterization (±200/SWI extreme + a confirming CONT partner). The past-data backtest was net-negative (±200 -$961, ±100 -$962, no-combo -$755; it blocks the #188-class losers but also winning TLB), but Michael prioritizes spec-fidelity + live SHADOW observation over the noisy past P&L. SHADOW only (no real orders). | `backend/v9/systems/woodies/patterns/tlb.py:134` | outputs/tlb_v2_backtest.py |
| VEGAS_SPEC_V2<br><sub>VEGAS source-spec</sub> | ✅ ON | `1` (.env) | (no default) | Replace VEGAS divergence detector with CCI cup-and-handle (Michael's spec): <-200 cup → recovery crossing -100 (rim) → handle (higher-low/flat ≥3 bars) → entry on rim break. Off = legacy divergence. | ON SHADOW 2026-06-24. Current VEGAS implements price/CCI divergence which is NOT Michael's pattern. Cup-and-handle is the correct reversal structure. Redefined 2026-06-24 to EXACT 4-step spec incl. SHALLOW-handle gate (handle retrace <50% of cup-rim; CC's first build over-fired = falling knives, 20 fires/15d). Strict build = 10 fires/15d. Ungated forward-move backtest still negative (raw CCI reversal); judged on REAL managed shadow (C1-BE + runners-to-LSMA) via the vegas-shadow-tracker scheduled task, not the naive proxy. | `backend/env_loader.py:78`<br>`backend/v9/systems/woodies/patterns/vegas.py:205` | docs/handoff/CC_VEGAS_SPEC_V2_2026-06-24.md |
| WOODIES_30MIN_DISABLED | 🔴 OFF | unset → False (flag() default) | False (flag() default) | Disable the 30-minute Woodies path when set. | Default OFF in code (path enabled by default). Not present in .env. | `backend/v9/api/v9/bars.py:805` |  |
| ZLR_SPEC_V2<br><sub>ZLR source-spec</sub> | ✅ ON | `1` (.env) | (no default) | Gate ZLR fire to Michael's source characterization (Stage 1: 6-bar blue + SWI yellow + EMA-34; Stage 3: CCI diff >=15, entry <=120, SWI yellow/green, CZI cyan 3 bars). Off = CCI-only. | ON SHADOW 2026-06-24. Current ZLR fires on CCI-14 geometry alone ignoring all Woodies confirmations → 35 fires, -$268. Spec gates remove low-quality setups. | `backend/env_loader.py:77`<br>`backend/v9/systems/woodies/patterns/zlr.py:211`<br>`backend/v9/systems/woodies/patterns/zlr.py:287` | docs/handoff/CC_ZLR_SPEC_V2_2026-06-24.md |

## Cascade alignment gates (gateway)

| Flag | State | Current | Code default | What it does | Why / state | Where (file:line) | Notes |
|------|-------|---------|--------------|--------------|-------------|-------------------|-------|
| CONT_TREND_FILTER<br><sub>direction engine</sub> | ✅ ON | `1` (.env) | "0" | Continuation patterns (Flag/TLB/ZLR/TT/GB100 + S2 Reactive/Initiative) fire only WITH a SUSTAINED K-bar LSMA trend (dir_sustained). REVERSAL patterns (VEGAS/GHOST/FAMIR/HTLB + S2 Double/HnS) are EXEMPT (fire against the trend by design). Applied in trading_gateway after DIRECTION_CONTEXT; fail-open. | ON SHADOW 2026-06-25, Michael. Fixes BULL_FLAG_LONG (0/3, -$596): the single-bar veto passed a momentary 1-bar poke above LSMA in chop (06-24 10:25). Counterfactual: blocks 102 continuation chop/counter losers = +$911, keeps reversal winners (HTLB +$720). K = LSMA_SUSTAIN_BARS. | `backend/v9/gateway/trading_gateway.py:332` | outputs/trend_filter_counterfactual.py |
| DAYTYPE_PLAYBOOK | 🟡 ON·inert | `1` (.env) | (no default) | Pattern x day-type SKIP/REDUCED matrix + require_with_trend (config/daytype_playbook.yaml). | ON, but a NO-OP: decide() returns FULL for every pattern whenever DAYTYPE_POSITION_GATE=1. | `backend/env_loader.py:80`<br>`backend/v9/systems/daytype_playbook.py:49`<br>`backend/v9/gateway/trading_gateway.py:237` | inert: DAYTYPE_POSITION_GATE=1 (returns FULL before reading the matrix — root hole R1).; CASCADE_AUDIT §5 R1; daytype_playbook.py:104 |
| DAYTYPE_POSITION_GATE | ✅ ON | `1` (.env) | (no default) | Per day-type direction x price-vs-POC/IB gate; supersedes the legacy CCI/reactive gates. | ON. Correct on direction/location but PATTERN-BLIND — ignores its pattern arg (can't tell CONT from REV). | `backend/env_loader.py:79`<br>`backend/v9/systems/daytype_playbook.py:105`<br>`backend/v9/systems/daytype_position_gate.py:31`<br>(+1) | CASCADE_AUDIT §5 R2 |
| DEDUP_FIRE_GUARD | ✅ ON | `1` (.env) | "0" | Block an identical sys+dir+pattern+entry(+-0.5pt) fire within 30s. | ON (Michael 2026-06-22). Was OFF when 199/200 double-fired on 06-22. | `backend/v9/gateway/trading_gateway.py:169` |  |
| DEMO_EXECUTION_ENABLED | ✅ ON | `1` (.env) | "0" | Enable DEMO execution branch in the gateway. When OFF (default), no DEMO trades are placed. When ON, approved setups go to Sierra SIM via trade_command.json. | OFF (default). Pipeline 5 runtime gate. Michael sign-off required to enable. DEMO + Sim account ONLY. | `backend/main.py:751`<br>`backend/v9/gateway/trading_gateway.py:588` | docs/handoff/CC_PIPELINE5_2026-06-25.md |
| DIRECTION_CONTEXT | ✅ ON | `1` (.env) | "0" | Block fires AGAINST the live CVD+breakout auction direction (direction_context_live); fail-open. | ENABLED in SHADOW 2026-06-23 (Michael) after backtest #18: actual -$2747 -> +$70 excl in-progress (+$2817), blocks 19 losers / 12 winners. Inert at the open (NEUTRAL); gates once direction establishes. | `backend/v9/gateway/trading_gateway.py:321` | outputs/dc_gate_backtest.py |
| DIRECTION_LSMA_VETO<br><sub>direction engine</sub> | ✅ ON | `1` (.env) | (no default) | Override the CVD+breakout direction engine with LSMA-lead + CVD-veto: direction = LSMA side, CVD only vetoes (→ NEUTRAL) when opposing. Source = v9_bars_5min_woodies lsma_value. | ON SHADOW 2026-06-24, Michael approved. LSMA-lead+CVD-veto validated standalone 06-23 (74% hit +$2,452). Replaces the breakout/location/trend-day brain WHILE ON; reversible (flag off = today's engine). | `backend/env_loader.py:75`<br>`backend/v9/systems/direction_context_live.py:100` | docs/handoff/CC_DIRECTION_LSMA_VETO_2026-06-24.md |
| FEED_WATCHDOG | 🔴 OFF | unset → "0" | "0" | Block ALL fires when canonical trading streams (5min + woodies_5min) are stale (>90s during RTH). Auto-resumes when fresh. LIVE blocker #0. | OFF in SHADOW. Designed for ON at LIVE. 06-19 incident: bridge died mid-RTH, orphan position (186/187). Never trade on a dead feed. | `backend/v9/services/feed_watchdog.py:41` | docs/handoff/CC_BATCH_QUEUE_2026-06-24.md §T2 |
| LAYER0_CHOP_GATE<br><sub>chop gate (2 of 2)</sub> | 🔴 OFF | unset → "0" | "0" | System-wide gateway fire-veto for S2+S4 when chop_state == SEARCHING (6-indicator composite, 30-60min). | DISABLED by Michael 2026-06-08. Still computed+logged; when off, _get_chop_state() is skipped entirely (avoids a uvicorn-deadlocking HTTP self-call). | `backend/v9/gateway/trading_gateway.py:192` | STANDING-OFF — Michael sign-off to enable; CLAUDE.md §Chop Gates |
| NONTREND_DISABLE_ALL | ✅ ON | `1` (.env) | (no default) | Block ALL fires (S2+S4, both directions) on Nontrend days. Michael's rule: every pattern fires full on every day-type EXCEPT Nontrend. | ON SHADOW 2026-06-24, Michael approved. Backtest 06-22: 5 Nontrend fires = -$555, all blocked. Selectivity via DAYTYPE_POSITION_GATE + DIRECTION_LSMA_VETO, not per-pattern matrices. | `backend/env_loader.py:74`<br>`backend/v9/systems/daytype_position_gate.py:61` | docs/handoff/CC_NONTREND_DISABLE_2026-06-24.md |
| NONTREND_WIDTH_FLOOR | ✅ ON | `1` (.env) | "0" | Range > floor (pts) => NOT Nontrend (prevents a wide day being mis-stamped Nontrend). | ON (Michael 2026-06-22). | `backend/v9/systems/day_type/daytype_classifier.py:92` |  |
| OPENING_TYPE_GATE | ✅ ON | `1` (.env) | "0" | Block counter-drive fires in the opening window (RTH open → IB lock); inert after IB lock. | ON (Michael 2026-06-22). Was OFF during the 06-22 morning fire window. | `backend/v9/systems/opening_type_gate.py:25`<br>`backend/v9/gateway/trading_gateway.py:204` |  |
| REACTIVE_LOCATION_GATE | 🟡 ON·inert | `1` (.env) | "0" | Block REACTIVE_LONG above POC / REACTIVE_SHORT below POC (fail-open). | ON, but runtime-SKIPPED when DAYTYPE_POSITION_GATE=1 (superseded). | `backend/v9/systems/reactive_location_gate.py:20`<br>`backend/v9/gateway/trading_gateway.py:275` | inert: DAYTYPE_POSITION_GATE=1 (gateway skips it). |
| TREND_DIRECTION_GATE | 🟡 ON·inert | `1` (.env) | "0" | Block counter-trend fires for HFE / REACTIVE_LONG / ZLR-SHORT using live trend_state. | ON, but runtime-SKIPPED when DAYTYPE_POSITION_GATE=1 (superseded). | `backend/v9/systems/trend_direction_gate.py:38`<br>`backend/v9/gateway/trading_gateway.py:260` | inert: DAYTYPE_POSITION_GATE=1 (gateway skips it). |

## Targets

| Flag | State | Current | Code default | What it does | Why / state | Where (file:line) | Notes |
|------|-------|---------|--------------|--------------|-------------|-------------------|-------|
| DAYTYPE_TARGETS_STRUCTURAL | ✅ ON | `1` (.env) | "0" | Override setup T1/T2/T3 with structural IB/POC/VA prices for location-style day-types; fail-safe to R-based. | Michael approved SHADOW 2026-06-21. 98/104 sim trades resolved structural. | `backend/v9/systems/structural_targets.py:63`<br>`backend/v9/gateway/trading_gateway.py:362` | CASCADE_AUDIT §7 |
| RUNNER_TARGETS_V1 | ✅ ON | `1` (.env) | False (flag() default) | Runner target ladder v1. | Anchor-trial (2026-06-12). | `backend/v9/systems/woodies/woodies_system.py:761`<br>`backend/v9/services/trade_manager/manager.py:719` |  |

## Stops / sizing

| Flag | State | Current | Code default | What it does | Why / state | Where (file:line) | Notes |
|------|-------|---------|--------------|--------------|-------------|-------------------|-------|
| DYNAMIC_STRUCT_TRAIL | ✅ ON | `1` (.env) | "0" | Dynamic structure-trailing: after T1, detect consolidation zones (K bars, range ≤ R) → re-anchor stop beyond zone + advance target to nearer of {zone projection, key level}. Replaces simple hwm trail when ON. | OFF (default). Michael's trade management rule (2026-06-24): runners re-anchor on each NEW CONSOLIDATION. Trading-surface change → Michael sign-off to enable. | `backend/v9/services/trade_manager/bar_level_detector.py:110` | docs/handoff/CC_DYNAMIC_STRUCT_TRAIL_2026-06-24.md |
| GIANT_BAR_STOP_V1 | ✅ ON | `1` (.env) | False (flag() default) | Cap the initial stop on giant bars (volatility-spike protection). | Anchor-trial (2026-06-12). | `backend/v9/systems/woodies/woodies_system.py:682` |  |
| RUNNER_TRAIL_V1 | ✅ ON | `1` (.env) | "0" | Trail the runner stop (hwm - 1x initial_risk) after T1; never-widen; floor BE+1T (fail-safe). | Michael-approved SHADOW trial 2026-06-18 (backtest +$273 — a real lever). | `backend/v9/services/trade_manager/bar_level_detector.py:116` | memory: project_trend_gate_t1_widen |
| STOP_AFTER_T1_STRUCTURAL | ⚪ not built | — | — | (Intended) move the stop to a structural level after T1 is hit. | NOT BUILT — no code references it; only a commented placeholder in .env. Deferred (one variable at a time). | — | not wired in code |
| STOP_ANCHORS_V2 | ✅ ON | `1` (.env) | False (flag() default) | v2 stop-anchor logic (per-pattern anchors from stop_anchors.yaml). | Enabled pre-soak. | `backend/v9/systems/woodies/woodies_system.py:398`<br>`backend/v9/systems/woodies/woodies_system.py:437`<br>`backend/v9/systems/woodies/woodies_system.py:567`<br>(+23) |  |
| T1_LADDER_V2 | 🔴 OFF | unset → False (flag() default) | False (flag() default) | Swap T1 computation to a wider v2 ladder (t1_ladder_continuation_v2 / t1_reversal_multiplier_v2 / flag_relative_t1_v2). | REJECTED — backtest flat -$144 (struct -$624). Do NOT enable. | `backend/v9/systems/woodies/woodies_system.py:747`<br>`backend/v9/systems/stop_anchors/sizing.py:88`<br>`backend/v9/systems/five_min/five_min_system.py:1337` | REJECTED by backtest — do not enable; memory: project_trend_gate_t1_widen |

## Risk breakers

| Flag | State | Current | Code default | What it does | Why / state | Where (file:line) | Notes |
|------|-------|---------|--------------|--------------|-------------|-------------------|-------|
| PATTERN_LOSS_BREAKER | ✅ ON | `1` (.env) | False (flag() default) | Halt a pattern after N consecutive losses (circuit breaker). | Anchor-trial (2026-06-12). | `backend/v9/systems/woodies/woodies_system.py:642` |  |
| PATTERN_RISK_CAPS | ✅ ON | `1` (.env) | False (flag() default) | Per-pattern maximum-risk caps. | Anchor-trial (2026-06-12). | `backend/v9/systems/woodies/woodies_system.py:632` |  |
| RISK_CAPS_SHADOW | 🔴 OFF | unset → "0" | "0" | Enforce LIVE risk caps (daily loss, max trades, consecutive losses) also in SHADOW mode. Default OFF (SHADOW bypasses risk caps). | OFF. Enable to test risk caps during SHADOW observation before LIVE. | `backend/v9/gateway/risk_checks.py:55` |  |

## Numeric parameters

| Flag | State | Current | Code default | What it does | Why / state | Where (file:line) | Notes |
|------|-------|---------|--------------|--------------|-------------|-------------------|-------|
| GIANT_BAR_MIN_RANGE_PT<br><sub>Giant-bar stop</sub> | 🔢 param | unset → "12.0" | "12.0" | Bar range (points) above which a bar counts as a giant bar. |  | `backend/v9/systems/woodies/woodies_system.py:81` |  |
| GIANT_BAR_STOP_FLOOR_PT<br><sub>Giant-bar stop</sub> | 🔢 param | unset → "6.0" | "6.0" | Minimum stop distance (points) floor for the giant-bar cap. |  | `backend/v9/systems/woodies/woodies_system.py:71` |  |
| GIANT_BAR_STOP_FRACTION<br><sub>Giant-bar stop</sub> | 🔢 param | unset → "0.38" | "0.38" | Fraction of the giant bar used to place the capped stop. |  | `backend/v9/systems/woodies/woodies_system.py:66` |  |
| LSMA_SUSTAIN_BARS<br><sub>direction engine</sub> | 🔢 param | `3` (.env) | "3" | K = consecutive most-recent bars that must be on the same side of the LSMA for dir_sustained to be UP/DOWN (else NEUTRAL). Used by CONT_TREND_FILTER. Default 3 (=15min). | Tunable trend-filter strictness. 1 = old single-bar behavior (momentary poke passes); 3 = a continuation must hold the LSMA side for 3 bars. | `backend/v9/systems/direction_context_live.py:132` | backend/v9/systems/direction_context_live.py |
| MEMS_MAX_RISK_POINTS<br><sub>Pre-fire stop sanity</sub> | 🔢 param | `60` (.env) | "0" | Reject a setup whose stop risk exceeds this many points (oversized-stop guard). |  | `backend/v9/shared/pre_fire_validator.py:74` |  |
| MEMS_MIN_RISK_POINTS<br><sub>Pre-fire stop sanity</sub> | 🔢 param | `2` (.env) | "0" | Reject a setup whose stop risk is below this many points (degenerate-stop guard). |  | `backend/v9/shared/pre_fire_validator.py:73` |  |
| NONTREND_MAX_RANGE_PTS<br><sub>Nontrend width floor</sub> | 🔢 param | unset → "18" | "18" | The range floor (points) used by NONTREND_WIDTH_FLOOR (range above this => not Nontrend). |  | `backend/v9/systems/day_type/daytype_classifier.py:93` |  |
| PATTERN_LOSS_BREAKER_N<br><sub>Pattern loss breaker</sub> | 🔢 param | unset → "2" | "2" | Number of losses (N) that trips PATTERN_LOSS_BREAKER. |  | `backend/v9/systems/woodies/woodies_system.py:645` |  |
| RISK_CONSECUTIVE_LOSS_LIMIT<br><sub>Risk caps</sub> | 🔢 param | — | — | Consecutive losses before STOP DAY. Default 2. |  | — |  |
| RISK_DAILY_LOSS_CAP<br><sub>Risk caps</sub> | 🔢 param | — | — | Daily loss cap in USD. Gateway halts all fires for the day when total P&L reaches -$X. Default $250. |  | — |  |
| RISK_MAX_TRADES_DAY<br><sub>Risk caps</sub> | 🔢 param | — | — | Maximum trades per day. Gateway halts after N fires. Default 5. |  | — |  |
| S2_VOL_REGIME_PT<br><sub>S2 vol-adaptive</sub> | 🔢 param | unset → _VOL_REGIME_PT (constant) | _VOL_REGIME_PT (constant) | Volatility-regime boundary (points) for S2_VOL_ADAPTIVE: avg 14-bar range >= this => VOLATILE. Default constant _VOL_REGIME_PT = 8.0. |  | `backend/v9/systems/five_min/five_min_system.py:82` |  |
| ZLR_CCI_MIN<br><sub>ZLR threshold (S4)</sub> | 🔢 param | unset → "100" | "100" | Minimum \|CCI\| magnitude required for a ZLR fire. unset/invalid => 100 = current behavior (no stricter gate); set 200 to enforce Liran's strong-extreme rule (150 = middle tier). | Built + tested 2026-06-19; left at default 100 = ZERO change to current firing. Raising it is the lever, not yet enabled. | `backend/v9/systems/woodies/patterns/zlr.py:139` | awaiting backtest before enable; memory: project_daytype_location_gate_todo |

## Misc

| Flag | State | Current | Code default | What it does | Why / state | Where (file:line) | Notes |
|------|-------|---------|--------------|--------------|-------------|-------------------|-------|
| TICK_REVERSAL_DISABLED | 🔴 OFF | unset → False (flag() default) | False (flag() default) | Disable the tick-reversal micro-pattern when set. | Default OFF in code. tick_reversal is non-critical for readiness (CLAUDE.md standing decision). | `backend/v9/api/v9/bars.py:455` |  |

---

### How to maintain (future agents)

1. **Add / change a behavior flag in code** → add or edit its entry in `docs/FLAG_REGISTRY.yaml` (category / what / why / status).
2. Run `python3 scripts/gen_flag_index.py` and commit both files.
3. `python3 scripts/gen_flag_index.py --check` fails (exit 1) if any behavior flag in code is undocumented — wire it into CI / pre-commit to keep this honest.
4. Enabling a **standing-OFF**, **rejected**, or **awaiting-backtest** flag is a trading-risk-surface change → Michael sign-off (CLAUDE.md §Standing Decisions).

