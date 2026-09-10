# Forward production-path test — the four opening/day-type fixes · 2026-09-10

**cowork-dev · 2026-09-10 · READ-ONLY on the live tree** (no edit, no `.env`, no flag, no restart).
Everything ran in a scratch worktree (`git worktree add /tmp/mems26_fwd HEAD` = `c3a5323a`), removed at the end.
Harness + tables + every run's JSON: this session's outputs folder (`fwd_harness.py`, `fwd_apply_fixes.py`,
`fwd_report_tables.py`, `fwd_show.py`, `fwd_diff.py`, `fwd_run_batch.sh`) and `/tmp/fwd_out/*.json` (48 runs).

Michael's question (verbatim): *"תוכל לבחון לא בסריקה אחורה אלא את ההמלצה של עצמך לראות שזה יאפשר ירי ועסקאות נכונות"* —
not a backward replay: feed the real bars one at a time, in order, through the REAL live objects
(S1 `DayTypeStateMachine` → `classify_session` → `FiveMinSystem`/`WoodiesSystem` producers → `TradingGateway.route_setup`
with `DALTON_PLAYBOOK_V1=1` → `command_from_setup`), and see whether the chain **ends in an order** where the doctrine
says it should, and whether those orders were **right against the tape**. Six sessions × {HEAD, HEAD+fixes}.

---

## 0 · The answer in one paragraph

The four fixes do what they claim mechanically — from 16:45 the gateway sees a real opening type instead of a permanent
`UNKNOWN`, ORR is no longer self-inverted, `EXTREME_REJECT` is reachable, and the phase-C label stops flapping — **but they
cannot make the opening path fire in production as it is, because the opening engine never sees a closed bar.**
The harness reproduced 2026-09-09 live decision-for-decision (§3.3) and then showed *why* D2 of the doctrine walk only
"delays" entries: `five_min_system.py:2139/2149` collect `_oe_bars` from the **first push** of each bar (the developing
bar, seconds old, `o≈h≈l≈c`), so `OPENING_FIRST_TRADE_STRICT`'s "last bar confirms the direction" is decided by the first
ticks of the *new* bar, and the opening range is the first seconds of 16:30. Live proof, from `/tmp/backend.err.log`:
`2026-09-07 16:40:05 held DRIVE SHORT — last bar did not confirm SHORT (o=7712.75 c=7713.0)` while the 16:40 bar really
closed 7713.50; `2026-09-08 16:40:08 OPENING_ENTRY DRIVE SHORT entry=7701.00` while that bar opened 7702.00 and closed
7693.25 (DB). Under a faithful clock the strict gate held **every** opening trigger on all six sessions (33 holds, 0
emitted), HEAD or fixed. With the engine pointed at closed bars (a fifth change, run separately and labelled `oe-closed`)
the fixed chain stands aside in phase A on every session, fades the edge on the auction day (08-04 +$427.50, T1 first)
and enters with the drive on the drive day (08-03 +$332.50, T1 first) — and also lets one wrong opening entry through
(09-01 `OPENING_DRIVE LONG` 16:50, −$93.75) because a `DRIVE`-typed setup passes under an `ORR`-typed open once the
reversal bias agrees with it (`kinds_apply_to: counter_bias_only`).

---

## 1 · Verdict

Push cadence = live (`firstpush`: detection on the first push of every bar, final OHLC as the duplicate push). `$` = the
harness's own tape score (5 $/pt, no slippage/commission, stop-before-target on an ambiguous bar, BE after T1 —
see §7 for what that cannot model). "T1-first" = the T1 leg filled before the initial stop.
A fire marked ⁱ is the live system's own setup of that day re-routed through this chain at its real fire time (`v9_trades`
mode=live), not a harness-producer emission — it answers "does this chain admit what live took".

| session | canonical open (v2 @15 min → @30 min) | live that day | **HEAD** fires / T1-first / $ | **HEAD+4 fixes** fires / T1-first / $ | what changed and why |
|---|---|---|---|---|---|
| 2026-08-28 | OPEN_DRIVE/UP → OPEN_AUCTION_IN | +$331.25 (8 trades) | 1ⁱ / 1 / +107.50 | 1ⁱ / 1 / +107.50 | `_dp_ot` becomes `OPEN_DRIVE` at 16:44 and `OPEN_AUCTION_IN` from 16:50; 11 phase-B candidates go from `stand_down` to 10× `kind` (BREAK ∉ [EDGE_FADE]) + 1 shadow-only — same outcome, honest reason. 0 opening triggers survive the strict gate (6 holds). |
| 2026-08-03 | OPEN_DRIVE/UP (stable) | +$167.50 (9) | 3 (1ⁱ) / 3 / +267.50 | **1 / 1 / +332.50** | fix 1 gives bias LONG from 16:45 → `INITIATIVE_LONG 17:10` (with-drive) is admitted and wins (+51 pts MFE, T1 first); it then holds the live slot to EOD, so HEAD's 18:20/18:50 winners are not taken (slot model, §7). `DALTON_EDGE_SHORT 17:05` correctly rejected by bias. |
| 2026-09-02 | OPEN_REJECTION_REVERSE/UP → OPEN_AUCTION_IN | +$253.75 (6) | 3 / 0 / −180.00 | 3 / 0 / −180.00 | at 16:44 the gate sees ORR with hint SHORT → bias **LONG** (fix 2 works); the LONG candidates at 16:45 die on `entry_location_quality` (beyond value); from 16:50 the canonical says AUCTION_IN → EDGE_FADE only. The three phase-C stops are identical in both. |
| 2026-08-04 | OPEN_AUCTION_OUT (stable) · tape ends 12:55 ET | +$477.50 (5) | 0 / 0 / 0 | **1ⁱ / 1 / +427.50** | phase A: stand aside ✓ (GB100 16:30 `stand_down`). Phase B: `REACTIVE_LONG 17:05` = EDGE_FADE under AUCTION → admitted, T1 first (live #612 won +$158.75); `INITIATIVE_LONG 17:10/17:20` (BREAK) correctly refused. |
| 2026-09-09 | OPEN_AUCTION_OUT (stable) | −$147.50 (3) | 3 (1ⁱ) / 0 / −290.00 | 3 (1ⁱ) / 0 / −290.00 | the fixes do not touch phase C: `VEGAS 19:05`, `DOUBLE_BOTTOM 20:15`, `BULL_FLAG 20:55` are admitted under `Variation`/BREAK in both and all three stop out on the tape. Phase B: 5 `stand_down` → 4 `kind` + 1 shadow-only. Stability changes 2 verdicts, 0 fires (§6). |
| 2026-09-01 | OPEN_AUCTION_OUT → ORR/UP (bar 4 only) → AUCTION_OUT | −$230.00 (3) | 3 / 2 / +110.00 | 3 / 2 / +110.00 | identical fires; 6 phase-B candidates `stand_down` → `kind`. (Counterfactual `oe-closed`: fixes admit `OPENING_DRIVE LONG 16:50` under the momentary ORR read → −$93.75.) |

Counterfactual column (`oe-closed`, opening engine on closed bars; all else identical): HEAD 2/1/+62.50 · 3/3/+267.50 ·
3/0/−180 · 0/0/0 · 4/0/−436.25 · 4/2/+70.00 — HEAD+fixes 1/1/+107.50 · 1/1/+332.50 · 3/0/−180 · 1/1/+427.50 · 3/0/−290 ·
4/2/+16.25. The fixes remove HEAD's two P1.5-admitted opening losers (08-28 `PULLBACK_CONT SHORT` −$45, 09-09
`PULLBACK_CONT LONG` −$146.25) and add one of their own (09-01 `OPENING_DRIVE LONG` −$93.75).

**(a) Do the fixes make the opening path fire where the doctrine says it should?** **No, not as production stands — 0
opening entries on 6/6 sessions, HEAD and fixed alike**, because every trigger dies in `OPENING_FIRST_TRADE_STRICT` on a
first-seconds bar (33 holds). What the fixes *do* deliver, with live cadence, is the playbook's phase-B branching for the
other producers: 2 with-open entries admitted on 2 sessions (08-03 with-drive, 08-04 edge-fade), both T1-first winners,
and stand-aside in phase A on 6/6. With the engine on closed bars: opening-typed entries reach the broker on 1/6 sessions
(09-01, wrong), the drive-day entry still comes from `INITIATIVE_LONG`, not from `OPENING_DRIVE`.

**(b) Do they admit anything the tape says was wrong?** With live cadence — **no**: the only new admissions are 08-03
`INITIATIVE_LONG 17:10` (+$332.50, T1 first) and 08-04 `REACTIVE_LONG 17:05` (+$427.50, T1 first). The 09-09 losers
#1328/#1343 are admitted by HEAD and by the fixes identically (phase C, untouched). With the closed-bar engine — **yes**:
`0901_fixedoe FWD-live-3 OPENING_DRIVE LONG 16:50` (−$93.75, MAE −27.75 before any T1).

**(c) Does `DAYTYPE_RECLASS_STABILITY_V1` change any phase-C verdict on 09-09?** Yes, two, both toward *fewer* candidates
and 0 fires: the confirmed label reaches the gate one bar later (Normal 17:35→gate 17:45, Variation 18:15→gate 18:25),
so `ZLR LONG 17:44` is judged under `Variation` (shadow) instead of `Normal` (kind-block), and `INITIATIVE_SHORT 18:20`
is not emitted at all (S2 detection keys on the live label). The two losers fire in both.

**(d) Any session where HEAD+fixes is worse than HEAD?** In $, none with live cadence (4 equal, 08-03 +65, 08-04
+427.50). In fires, 08-03 drops 3→1 because the admitted 17:10 position holds the single live slot to EOD in the harness
(no trail) — a slot-model artefact, not a gate verdict. In the counterfactual, 09-01 is worse (+16.25 vs +70/+110) by
exactly the one wrong opening entry.

**What this is not:** a P&L forecast. Live took different trades on those days under different flags
(`DALTON_PLAYBOOK_V1` went live 09-09 16:58); the harness's $ is a tape score of *this* chain's orders under a fixed set of
management assumptions (§7).

---

## 2 · The four fixes as applied (scratch worktree only — `fwd_apply_fixes.py`, exact-string replacements)

Fix 4 is environment-only: `DAYTYPE_RECLASS_STABILITY_V1=1` set for the run (`.env:297` is `0`; the harness never writes
`.env`). Fixes 1–3 are the diff below (`git diff` of the worktree). Note on fix 1: reading "the dict key" alone would
have wired the legacy state-machine label, which §4-F5 shows is computed on first-seconds bars; the doctrine walk's own
caveat ("read the canonical type, not the state machine's") is followed — the canonical `opening_detector_v2` is called on
the closed RTH bars the machine already exposes (`main.py:366`), from bar 3 (the opening@15min ruling). The direction half
is part of the same fix: without it `drive_direction` resolves to `BOTH`. Targeted regression on the patched tree:
`63 passed` (`test_opening_entry_production_path`, `test_dalton_playbook_identity`, `test_dalton_playbook`,
`test_daytype_reclass_stability`).

```diff
diff --git a/backend/v9/gateway/trading_gateway.py b/backend/v9/gateway/trading_gateway.py
index c270e210..cb1d745f 100644
--- a/backend/v9/gateway/trading_gateway.py
+++ b/backend/v9/gateway/trading_gateway.py
@@ -1091,14 +1091,37 @@ class TradingGateway:
                 else:
                     self._dp_hyst["label"] = _dp_dt_raw
                     _dp_dt = _dp_dt_raw
-                # Opening type from the state machine
+                # Opening type — FWD_FIX_1 (D6, DOCTRINE_WALK_OPENING 2026-09-10):
+                # cross_context["day_type_machine"] is get_current()'s DICT
+                # (state_machine.py:986), so `hasattr(dict, "opening")` was always
+                # False and _dp_ot was ALWAYS "UNKNOWN". Read the CANONICAL v2
+                # detector (the same call classifier_core.py:104 makes) on the closed
+                # RTH bars the machine exposes (main.py:366), from bar 3 (opening@15min
+                # ruling). The legacy state-machine label (27% agreement, computed on
+                # first-seconds bars) is deliberately NOT used. Direction comes with it.
                 _dp_ot = "UNKNOWN"
+                _dp_v2_dir = None
                 try:
-                    _dp_dtm = (cross_context.get("day_type_machine")
-                               if isinstance(cross_context, dict) else None)
-                    if _dp_dtm and hasattr(_dp_dtm, "opening"):
-                        _ot = _dp_dtm.opening.opening_type
-                        _dp_ot = _ot.value if hasattr(_ot, "value") else str(_ot)
+                    _dp_dtm_obj = self._system_registry.get("day_type_machine")
+                    _dp_bars = list(getattr(_dp_dtm_obj, "_opening_gate_bars", None) or [])
+                    if len(_dp_bars) >= 3:
+                        from backend.v9.systems.day_type.opening_detector_v2 import (
+                            detect_opening_type as _dp_v2)
+                        _dp_ob = getattr(_dp_dtm_obj, "opening_bars", None) or []
+                        _dp_v2r = _dp_v2(
+                            _dp_bars[:6], _dp_bars[0].get("o"),
+                            prior_vah=getattr(_dp_dtm_obj, "prev_vah", None),
+                            prior_val=getattr(_dp_dtm_obj, "prev_val", None),
+                            pdh=getattr(_dp_ob[0], "pd_high", None) if _dp_ob else None,
+                            pdl=getattr(_dp_ob[0], "pd_low", None) if _dp_ob else None)
+                        _dp_ot = str(_dp_v2r.get("opening_type") or "UNKNOWN")
+                        _dp_v2_dir = {"UP": "LONG", "DOWN": "SHORT"}.get(
+                            str(_dp_v2r.get("direction") or ""))
+                    else:
+                        _dp_dtm = (cross_context.get("day_type_machine")
+                                   if isinstance(cross_context, dict) else None)
+                        if isinstance(_dp_dtm, dict) and _dp_dtm.get("opening_type"):
+                            _dp_ot = str(_dp_dtm.get("opening_type"))
                 except Exception:
                     pass
                 # P1.5: when machine is UNKNOWN/NA and setup is OPENING_*,
@@ -1112,6 +1135,10 @@ class TradingGateway:
                         "OPENING_TEST_DRIVE": "OPEN_TEST_DRIVE",
                         "OPENING_ORR": "OPEN_REJECTION_REVERSE",
                         "OPENING_PULLBACK_CONT": "OPEN_DRIVE",
+                        # FWD_FIX_3 (D4): a tested-and-rejected extreme is the
+                        # test-drive family; without this key the setup fell to
+                        # the default rule (size_frac 0) in BOTH phase A and B.
+                        "OPENING_EXTREME_REJECT": "OPEN_TEST_DRIVE",
                     }
                     _dp_p15_ot = _P15_MAP.get(_dp_classification)
                     if _dp_p15_ot:
@@ -1142,11 +1169,23 @@ class TradingGateway:
                             _dp_dir_hint = "SHORT"
                 except Exception:
                     pass
+                # FWD_FIX_1 (direction half): before IB lock _resolve_live_cls() has no
+                # direction; the canonical opening detector's direction is the drive.
+                if _dp_dir_hint is None and _dp_v2_dir in ("LONG", "SHORT"):
+                    _dp_dir_hint = _dp_v2_dir
                 # P1.5 fallback: if no direction from classify, use setup direction
                 if _dp_dir_hint is None and _dp_classification.startswith("OPENING_"):
                     _dp_setup_dir = (setup.get("direction") or "").upper()
                     if _dp_setup_dir in ("LONG", "SHORT"):
                         _dp_dir_hint = _dp_setup_dir
+                # FWD_FIX_2 (D3): the playbook's `reversal_direction` rule INVERTS the
+                # hint (dalton_playbook.py:88-94) because the hint is defined as the
+                # DRIVE direction. For a rejection-reverse open every source above
+                # hands the REVERSAL side (the setup's own side / v2 `direction`), so
+                # the rule inverted it again and ORR could never pass. Hand it the
+                # drive side, i.e. the opposite of the reversal.
+                if _dp_ot == "OPEN_REJECTION_REVERSE" and _dp_dir_hint in ("LONG", "SHORT"):
+                    _dp_dir_hint = "SHORT" if _dp_dir_hint == "LONG" else "LONG"
                 _dalton_intent = _dp_intent(
                     opening_type=_dp_ot, day_type=_dp_dt,
                     now_il_hhmm=_dp_il_hhmm, direction_hint=_dp_dir_hint)
```

---

## 3 · The harness (`fwd_harness.py`, 1 session per process, ~17 s, `nice -n 10`, one at a time)

`docs/reports/evidence_2026-07-08_s1_dalton/replay_0708_bars.json` does not exist and `backend/v9/replay/kernel.py` is the
Stage-0B *data-validation* CLI (no detectors), so the harness was built on the template of
`tests/v9/regression/test_opening_entry_production_path.py` / `test_re_acceptance_production_path.py`: real objects, real
entry points, nothing re-implemented that has an importable entry point.

**3.1 What is real.** `DayTypeStateMachine.process_bar` (with `maybe_seed_ib_from_tpo`), `classifier_core.classify_session`
+ `label_stability.confirm_label` + `smooth_confidence` + `DAYTYPE_ACCEPTANCE_DEMOTION_V1` — a line-for-line port of
`backend/main.py:251-898` minus persistence (that code is a closure inside `startup()`; its DB writers and
`bar_router.publish` are the only parts left out); `FiveMinSystem.process_bar` (every S2 producer incl. the opening
engine, DALTON_EDGE, FAILED_RE_IB, RE_ACCEPTANCE, VA_FADE, ceiling/floor, flags, H&S, double tops); `WoodiesSystem.process_bar`
(ZLR/VEGAS/GB100/HTLB/TT/TLB/FAMIR/GHOST, DLL flags from the stored rows, Mechanism-C); `TradingGateway.route_setup` — the
complete `_route_setup_inner` gate chain (kill-switch, session gate, **dalton_intent**, cold-start, EOD cutoff, cooldown,
dedup, opening-type gate, playbook, location, ELQ, cont-trend, compass, LSMA, budget, extreme-chase, pattern cooldown,
S7, release gate, news, structural targets, entry-confirm, R:R, zone-limit, risk halts, cluster guard, live-slot,
`passes_strict_checks`) with the live `.env` (`DALTON_PLAYBOOK_V1=1`, `ZLR_SHADOW_V1=1`, `T3_REQUIRED_V1=1`,
`OPENING_LADDER_V1=1`, `RISK_BUDGET_SIZING_V1=1`, `FIXED_CONTRACTS_5=1`…); `sierra_command.command_from_setup`
(sizing, `RISK_BUDGET` reject, `cap_to_bracketable`, T-214 t3 belt, T0/C4/runner ladder) with `write_trade_command`
replaced by a recorder. `get_live_day_type()` resolves through a fake `backend.main` module whose `app.state` holds the
harness's machine — the same dead-wrapper-safe path production uses.

**3.2 Time is faithful.** `MEMS26_CLOCK_MODE=REPLAY` + `market_clock.update_replay_timestamp` per push, *and* every other
clock the code reads is pinned to the same instant: `datetime.datetime`/`date`/`time.time` rebound in all 46 loaded
modules (freezegun-style, `install_clock()`), and SQL `now()`/`current_date` rewritten to the replay instant in
`backend.v9.db.read`. Every table read is wrapped in an **as-of guard** (`(SELECT * FROM T WHERE ts+5min <= now)` for bar
tables; `created_at <= now` for `v9_tpo_history`/`v9_day_type_*`; the session's own rows of `v9_trades`/setups/signals
hidden entirely) — a live gate that reads "today's bars" with no bound (`direction_context_live._fetch_live_bars`,
`_lsma_row ORDER BY ts DESC LIMIT 1`, `IB_BARS_VALIDATE`, `get_opening_type_seed`…) cannot see a bar that has not closed
yet. `tpo.json` is served from `v9_tpo_history` as observed (`created_at <= now`, 30-min granularity) with the IB from the
first 12 RTH bars (equal to Sierra's stored CASH IB on every session checked); `cumulative_delta.json` from
`v9_bars_cumulative_delta` (closed bars only). The machine sees bar N+1 only after bar N's verdicts are recorded.

**3.3 Push cadence = live.** The bridge routes `current_bar` on every push; S2/S4/S1 dedup on the bar's `ts`, so detection
runs on the **first push of a new bar** (`five_min_system.py:1941-1954`, `woodies_system.py:400-404`, `main.py:259-275`)
with the developing bar at the end of the buffer, and the final OHLC arrives as a duplicate push (S1 refreshes
`_cls_rth_bars[-1]`, S4 re-runs on a DLL ZLR flag). The harness pushes each bar twice: at +3 s as a developing bar
(`o=h=l=c=open`, 1 % of volume, previous bar's studies) and at +4:58 with the final row and DLL flags. Calibration on
2026-09-09 against the live decision file (`gateway_decisions.jsonl`, 65 decisions): the harness reproduced the live
verdict classes bar by bar — `stand_down` in phase B until 17:30, `kind` blocks under `Normal` then `Variation`,
`extreme_chase`/`rr_entry_gate`/`entry_location_quality`/`entry_not_confirmed` on the same ZLRs — and fired the same
three live trades from its own producers or the injected setup: `VEGAS 19:05` (−$40.00 = live −$40.00),
`DOUBLE_BOTTOM_EE 20:15` (−$118.75 = live shadow twin #1336 −$118.75; live #1337 is the T-290 phantom "+$30"),
`BULL_FLAG 20:55` (−$131.25 = live booked −$131.25 / Sierra −$137.50). The injected copies of #1337/#1343 were refused as
`duplicate_fire` because the harness's own producers had already fired the same setup 4 s earlier — the strongest
fidelity signal in the run. Only S4 `VEGAS` was not reproduced by the emulated S4 (its detection needs the developing
bar's live SWI/TCCI, which the harness approximates with the previous bar's) — hence the injection mechanism.

**3.4 Safety.** DB opened with `default_transaction_read_only=on` (every write raises — the read-only belt caught the
producers' own persistence calls, `v9_bars_5min_woodies`/`v9_woodies_signals`/`v9_five_min_setups`, harmlessly);
`PYTEST_CURRENT_TEST` set so the decision file and candidate ledger are untouched; `write_trade_command`, `ntfy`,
`phone_alert`, `ops_log`, `feed_watchdog`, `position_mismatch_blocks_entry`, `margin_sizing.cap_contracts` patched; the
gateway's `_execute_*` replaced by a recorder that calls the real `command_from_setup`. Nothing reached Sierra, the DB,
the phone or the live process. Load stayed ≤ 1 harness process at a time (`uptime` 3.8–4.9 throughout).

---

## 4 · What the harness surfaced beyond the four fixes

**F1 — the opening engine evaluates the first seconds of a bar, not a bar.** `_oe_bars` is appended at the first push
(`five_min_system.py:2139/2149`) and the bar dict is never refreshed (the duplicate-push branch replaces
`_bar_buffer[-1]`, not `_oe_bars[-1]`). `evaluate_opening_entry`, `build_opening_setup` and `opening_first_trade_ok` all
read `_oe_bars`. Consequences, all verified live: the OR is the first seconds of 16:30 (09-08: stop 7716.00 from an OR
whose true high was 7717.75); the "confirmation bar" is the first tick of the new bar (09-07 16:40:05 `o=7712.75
c=7713.0`; passed at 16:50:03 on `c=7714.00` when the bar opened 7714.50 and closed 7714.25); a DRIVE fires whenever a
close lands beyond the opening print ± a tick (09-07 "DRIVE SHORT" on a 3.25-pt opening range). In the harness's
`o=h=l=c` proxy the strict gate never passes — in live it passes at random. **Fixing this is a prerequisite for anything
the four fixes are meant to enable in the opening window**, and it is the same class of change `OPENING_DIR_FUSION` already
made for itself (T7b: "the fusion now reads its volume from the CANONICAL closed bars").

**F2 — under HEAD the playbook cannot contradict an `OPENING_*` setup.** P1.5 sets both `_dp_ot` *and*
`direction_hint` from the setup itself, so `drive_direction` is always the setup's own side: in the `oe-closed` runs HEAD
admitted `OPENING_PULLBACK_CONT SHORT` on the 08-28 drive-up open (−$45) and `OPENING_PULLBACK_CONT LONG` on 09-09
(−$146.25). Fix 1 replaces that with an independent read and both disappear.

**F3 — the canonical v2 label is unstable between bar 3 and bar 6.** Read on the growing window (`bars[:6]`) it said
08-28 `OPEN_DRIVE/UP` @3 bars → `OPEN_AUCTION_IN` @4; 09-02 `ORR/UP` @3 → `AUCTION_IN` @4; 09-01 `AUCTION_OUT` @3 →
`ORR/UP` @4 → `AUCTION_OUT` @5. The gate therefore branched on three different opens within 15 minutes on 09-01 (T3),
and the one wrong opening entry in the counterfactual (09-01 16:50) was admitted during the 10 minutes it read ORR.
Fix 1 needs a commit rule (the opening@15min ruling says bar 3; classifier_core commits at bar 6) — it is not in the
four fixes. At 30 min the harness's v2 agreed with `GET /api/v9/day_type/classify_replay` on 6/6 sessions
(AUCTION_IN, DRIVE, AUCTION_IN, AUCTION_OUT, AUCTION_OUT, AUCTION_OUT).

**F4 — `entry_kind_map` misses the suffixed names.** `DALTON_EDGE_SHORT/LONG` (map has `DALTON_EDGE: REVERSAL`),
`OPENING_PULLBACK_CONT`, `OPENING_EXTREME_REJECT` (map has `EXTREME_REJECT`) all fall to the default `BREAK` — so on an
auction open (EDGE_FADE only) `DALTON_EDGE_SHORT` is refused as a BREAK on 08-28 16:50, 08-03 17:05, 09-01 16:55.

**F5 — the legacy state-machine opening type is computed on first-seconds bars.** `_stage_a2` consumes the `BarInput`
of the first push (main.py dedups on `ts` before `process_bar`); `_prev_bar_ts` refresh only touches `_cls_rth_bars`.
The harness's machine said `OPEN_DRIVE` on all six sessions. This is the mechanical root of the 27 % agreement the
doctrine walk measured, and the reason fix 1 must not read that label.

**F6 — first-hour label.** The legacy engine publishes `Trend_Normal` (conf 0.35) at 17:00 on 6/6 sessions and
`DAYTYPE_ACCEPTANCE_DEMOTION_V1` demotes it to `Variation` 10–20 min later on 5/6 (09-01 held `Trend_Normal` until the 17:30 canonical `Normal`) — before the canonical classifier has
run once (G-5 of the day-type walk, reproduced).

---
## 5 · Session walk — what the gateway saw at each setup, and what the tape said

The full phase-A/B tables (every setup: IL minute, system, entry/stop/t1, `_dp_ot` as the gateway held it, direction
hint, intent bias/kinds/size_frac, `blocked_by` or command) are in §8-T3; every fire with its per-contract exits, MFE/MAE
and hold-to-close in §8-T2. The minute `_dp_ot` first became non-`UNKNOWN`: HEAD — never (6/6); fixed — 16:44 (08-28,
09-02, 09-01), 16:45 (08-03), 16:49 (09-09), 17:05 (08-04, no candidate earlier). Before bar 3 it is `UNKNOWN` exactly as
live (phase A stand-down on 6/6).

**The counterfactual it must not break.**
- *Two drive days, phase A/B, drive direction:* 08-03 — yes: `INITIATIVE_LONG 17:10` admitted under `OPEN_DRIVE`/bias LONG
  (kinds [WITH_DRIVE, PULLBACK] + `counter_bias_only`), fill 7587.50, T1 7594.00 first, T2 7606.50, third contract held
  to the 7628.50 close: +$332.50 (the day's live trades in that window: HTLB 16:35 +$83.75, ZLR 16:45 −$20, REACTIVE 17:10
  +$71.25). `OPENING_DRIVE` itself never triggered on 08-03 (opening range wider than `max(10, 0.25×ATR)`), so the
  "opening entry" on the clearest drive day is a with-drive S2 entry, not the opening engine. 08-28 — no entry: the drive
  read lasts one bar (16:44 `GB100 LONG` refused by `entry_location_quality` ex=7.5), then AUCTION_IN → EDGE_FADE only;
  the live money that day (+$331) came from shorts — ZLR 17:05 +$107.50, 17:10 +$56.25, 20:00 +$143.75, SCALE_IN 19:01
  +$60 — i.e. *against* the up-drive read of the first 15 minutes; the playbook does not admit the phase-B ones under a
  drive-up/auction read (10 `kind` blocks), and the harness's one fire is the injected 19:01 SCALE_IN (+$107.50) in phase C.
- *The ORR day (09-02), reversal direction:* the mechanism is right — at 16:44:58 `_dp_ot=OPEN_REJECTION_REVERSE`, hint
  SHORT (drive), bias resolves **LONG** (the reversal side) — but nothing reaches the broker: the LONG candidates at 16:45
  (`FAILED_BREAK_LONG`, and `OPENING_PULLBACK_CONT LONG` in the counterfactual) die on `entry_location_quality`
  (beyond value ex=3.0), and from 16:50 the canonical read is AUCTION_IN, so the engine's own `OPENING_ORR SHORT`
  (16:50, counterfactual) is refused as REVERSAL ∉ [EDGE_FADE]. The live winner of that morning
  (`INITIATIVE_LONG 17:15` #953 +$162.50) is `stand_down` in HEAD and `kind` (BREAK under AUCTION_IN) in fixed.
- *The auction day (08-04):* phase A stands aside (16:30 `GB100 LONG` stand_down in both); phase B fades the edge
  (`REACTIVE_LONG 17:05` EDGE_FADE → LIVE ×3 → T1 7697.50 first, T2 7705.75, C3 to the 12:55-ET close: +$427.50) and
  refuses the breakouts (`INITIATIVE_LONG 17:10/17:20` BREAK). Note the tape ends at 12:55 ET (41 RTH bars in
  `v9_bars_5min_woodies`); the +$477.50 live day had two more winners after that.

**The two trades live took on 09-09.** Re-routed through every chain at their real fire time (§8-T6): `#1328 VEGAS LONG
19:05` → **LIVE ×2 in HEAD and in all fixed variants** (`Variation`, BREAK ∈ [BREAK, VALUE_RETURN]); on the tape it stops
in the same bar (−$40.00, MAE −10.75, MFE 11.0 only after the stop). `#1343 BULL_FLAG LONG 20:55` → the harness's own
S2 emitted it 4 s earlier and it was admitted in **every** variant (the injected copy is then `duplicate_fire`); on the
tape it stops out (−$131.25, MFE 1.75 / MAE −11.25, hold-to-close −8.0). `#1337 DOUBLE_BOTTOM_EE 20:15` likewise admitted
everywhere and stops (−$118.75; live booked it "+$30 BRACKET_EXIT_ACTIVITY" with `entry_ts=NULL` — T-290). **The four
fixes neither admit nor refuse these three; they are phase-C `Variation` BREAK entries and the fixes do not touch that
rule.** What the day-type walk's §3 said stands: all three were LONG BREAKs into a down-extension day.

---

## 6 · DAYTYPE_RECLASS_STABILITY_V1 on 09-09 (fix 4), isolated

Runs `fixed s=0` vs `fixed s=1` (and `head s=0` vs `head s=1`, identical result): the canonical label now needs two
consecutive bars, so `Normal` is published 17:35 instead of 17:30 and `Variation` 18:15 instead of 18:10; the 600-s
antiflap on the read side then delivers each to the gate one bar later (17:45, 18:25). Two routes change, no fire:

| IL | setup | s=0: label at gate → verdict | s=1: label at gate → verdict |
|---|---|---|---|
| 17:44 | ZLR LONG | Normal → `dalton_intent:kind` | Variation → shadow (ZLR is shadow-only under `ZLR_SHADOW_V1`) |
| 18:20 | INITIATIVE_SHORT | Variation → `entry_location_quality` | not emitted (S2 detection keys on the live label) |

The three fires and their tape outcomes are identical in both. On the other five sessions the flag changed 0 fires; the
first-hour flapping the flag was ruled for (Normal↔Variation) is visible in §8-T4 as one-bar-later promotions.

---

## 7 · What the harness cannot model — do not read the $ as a forecast

- **Intrabar path.** Bars only: when a bar touches both stop and target the stop is taken (`ambiguous_bars` recorded;
  3 on the 08-28 counterfactual `PULLBACK_CONT SHORT`, 0 on every other scored fire). Fill = entry price if inside the next bar's range,
  else that bar's open. No slippage, no commission.
- **The first seconds of each bar.** The developing bar is `o=h=l=c=open` with 1 % of the volume and the previous bar's
  studies; live pushes ~40 times per bar with real ticks. This is exactly what decides `OPENING_FIRST_TRADE_STRICT` (F1),
  so the harness understates how often the strict gate passes *by luck* (live: 4 passes in 10 sessions per the doctrine
  walk) and cannot reproduce S4 `VEGAS` (live SWI/TCCI on the developing bar). Mid-bar DLL ZLR flags are applied at the
  bar's end.
- **Sierra OCO / DLL.** The 5-contract split is unknown to the harness: contracts beyond the 4-slot ladder follow the last
  target; a leg with no target is a runner exiting at BE/EOD. `cap_to_bracketable` real, `cap_contracts` (margin, today's
  account) bypassed, `entry_guard` (today's `sierra_state.json`) not invoked.
- **System6 post-entry management.** Only "stop → BE after T1" is modelled; no trails (`RUNNER_TRAIL_V2` legs run to
  BE/EOD), no `MODIFY_STOP` advisories, no scratch. The live slot stays occupied until every leg exits — the reason
  08-03 fixed shows 1 fire instead of 3.
- **TPO/VA at 30-min granularity** (`v9_tpo_history`), IB from the first 12 RTH bars, delta from closed bars only;
  `DELTA_FEATURES_V1` reads the same historical delta (not today's file, G-7). 08-04's tape stops at 12:55 ET.
  pd-context for 08-03/08-04 substituted from the canonical bars (legacy `v9_bars_5min` purged before 08-27).
- **Producers not in the run:** TREND_STEP (shadow), EDGE_FADE (flag off), footprint/S3 (muted), CONFLUENCE V1 routed as
  in production. The live system's own trades of the day are hidden from the gates (`v9_trades` as-of guard) because this
  chain did not take them; pattern-stop cooldown is computed over the harness's own stops.
- **Different flags on those days.** 08-03…09-02 traded live under pre-playbook gates; the harness applies today's
  `.env` to their tapes. The $ column is a tape score of *this* chain's orders, comparable across HEAD/fixed only.

---

## 8 · Raw output

Generated by `fwd_report_tables.py` over the 48 run JSONs (`/tmp/fwd_out/<mmdd>_<variant>_s<stab>_firstpush.json`);
`headoe`/`fixedoe` = the `--oe-closed` counterfactual. Run summary lines (`batch_full.out`) and the regression run follow
the tables.

### 8-T1 · verdict table (push=firstpush = live cadence; $ = harness tape score, 5$/pt, no slippage/commission)

| session | live that day | HEAD (fires / T1-first / $) | HEAD+fixes s=1 (fires / T1-first / $) | HEAD+fixes s=0 | first non-UNKNOWN `_dp_ot` (HEAD → fixed) | oe-closed counterfactual HEAD / HEAD+fixes |
|---|---|---|---|---|---|---|
| 2026-08-28 | +331.25 (8 live trades) | 1 / 1 / +107.50 | 1 / 1 / +107.50 | 1 / 1 / +107.50 | — → 16:44 | 2 / 1 / +62.50 / 1 / 1 / +107.50 |
| 2026-08-03 | +167.50 (9 live trades) | 3 / 3 / +267.50 | 1 / 1 / +332.50 | 1 / 1 / +332.50 | — → 16:45 | 3 / 3 / +267.50 / 1 / 1 / +332.50 |
| 2026-09-02 | +253.75 (6 live trades) | 3 / 0 / -180.00 | 3 / 0 / -180.00 | 3 / 0 / -180.00 | — → 16:44 | 3 / 0 / -180.00 / 3 / 0 / -180.00 |
| 2026-08-04 | +477.50 (5 live trades) | 0 / 0 / +0.00 | 1 / 1 / +427.50 | 1 / 1 / +427.50 | — → 17:05 | 0 / 0 / +0.00 / 1 / 1 / +427.50 |
| 2026-09-09 | -147.50 (3 live trades) | 3 / 0 / -290.00 | 3 / 0 / -290.00 | 3 / 0 / -290.00 | — → 16:49 | 4 / 0 / -436.25 / 3 / 0 / -290.00 |
| 2026-09-01 | -230.00 (3 live trades) | 3 / 2 / +110.00 | 3 / 2 / +110.00 | 3 / 2 / +110.00 | — → 16:44 | 4 / 2 / +70.00 / 4 / 2 / +16.25 |

### 8-T2 · every fire, scored against the tape

**2026-08-28 · head s=0** — Σ +107.50
- 19:01 SCALE_IN SHORT @7736.0 stop 7750.5 ×3 → **WIN +107.50$** (T1 before stop: YES; full-stop would be -217.5$; MFE 24.25 / MAE -9.25 / hold-to-close 13.25 pts; legs: C1:T1@7724.0 C2:T2@7726.5 C3:BE@7736.0)  ← injected live #853 (live: STOP_HIT 60.0)

**2026-08-28 · head s=1** — Σ +107.50
- 19:01 SCALE_IN SHORT @7736.0 stop 7750.5 ×3 → **WIN +107.50$** (T1 before stop: YES; full-stop would be -217.5$; MFE 24.25 / MAE -9.25 / hold-to-close 13.25 pts; legs: C1:T1@7724.0 C2:T2@7726.5 C3:BE@7736.0)  ← injected live #853 (live: STOP_HIT 60.0)

**2026-08-28 · fixed s=0** — Σ +107.50
- 19:01 SCALE_IN SHORT @7736.0 stop 7750.5 ×3 → **WIN +107.50$** (T1 before stop: YES; full-stop would be -217.5$; MFE 24.25 / MAE -9.25 / hold-to-close 13.25 pts; legs: C1:T1@7724.0 C2:T2@7726.5 C3:BE@7736.0)  ← injected live #853 (live: STOP_HIT 60.0)

**2026-08-28 · fixed s=1** — Σ +107.50
- 19:01 SCALE_IN SHORT @7736.0 stop 7750.5 ×3 → **WIN +107.50$** (T1 before stop: YES; full-stop would be -217.5$; MFE 24.25 / MAE -9.25 / hold-to-close 13.25 pts; legs: C1:T1@7724.0 C2:T2@7726.5 C3:BE@7736.0)  ← injected live #853 (live: STOP_HIT 60.0)

**2026-08-28 · headoe s=1 · oe-closed** — Σ +62.50
- 16:50 OPENING_PULLBACK_CONT SHORT @7750.75 stop 7753.75 ×5 → **STOP -45.00$** (T1 before stop: NO; full-stop would be -75.0$; MFE 39.0 / MAE -31.75 / hold-to-close 28.0 pts; legs: C1:T1@7747.75 C2:STOP@7753.75 C3:STOP(ambiguous)@7753.75 C4:STOP(ambiguous)@7753.75 C5:STOP(ambiguous)@7753.75)
- 19:01 SCALE_IN SHORT @7736.0 stop 7750.5 ×3 → **WIN +107.50$** (T1 before stop: YES; full-stop would be -217.5$; MFE 24.25 / MAE -9.25 / hold-to-close 13.25 pts; legs: C1:T1@7724.0 C2:T2@7726.5 C3:BE@7736.0)  ← injected live #853 (live: STOP_HIT 60.0)

**2026-08-28 · fixedoe s=1 · oe-closed** — Σ +107.50
- 19:01 SCALE_IN SHORT @7736.0 stop 7750.5 ×3 → **WIN +107.50$** (T1 before stop: YES; full-stop would be -217.5$; MFE 24.25 / MAE -9.25 / hold-to-close 13.25 pts; legs: C1:T1@7724.0 C2:T2@7726.5 C3:BE@7736.0)  ← injected live #853 (live: STOP_HIT 60.0)

**2026-08-28 · fixedoe s=0 · oe-closed** — Σ +107.50
- 19:01 SCALE_IN SHORT @7736.0 stop 7750.5 ×3 → **WIN +107.50$** (T1 before stop: YES; full-stop would be -217.5$; MFE 24.25 / MAE -9.25 / hold-to-close 13.25 pts; legs: C1:T1@7724.0 C2:T2@7726.5 C3:BE@7736.0)  ← injected live #853 (live: STOP_HIT 60.0)

**2026-08-03 · head s=0** — Σ +267.50
- 18:20 GB100 LONG @7606.0 stop 7598.5 ×5 → **WIN +28.75$** (T1 before stop: YES; full-stop would be -187.5$; MFE 32.5 / MAE -3.75 / hold-to-close 22.5 pts; legs: C1:T1@7609.0 C2:T2@7608.75 C3:BE@7606.0 C4:BE@7606.0 C5:BE@7606.0)  ← injected live #601 (live: T2_HIT 53.75)
- 18:50 BULL_FLAG_LONG LONG @7612.5 stop 7606.0 ×5 → **WIN +30.00$** (T1 before stop: YES; full-stop would be -162.5$; MFE 26.0 / MAE -3.25 / hold-to-close 16.0 pts; legs: C1:T1@7615.5 C2:T2@7615.5 C3:BE@7612.5 C4:BE@7612.5 C5:BE@7612.5)
- 20:15 INITIATIVE_LONG LONG @7616.75 stop 7609.25 ×5 → **WIN +208.75$** (T1 before stop: YES; full-stop would be -187.5$; MFE 21.75 / MAE -0.5 / hold-to-close 11.75 pts; legs: C1:T1@7619.75 C2:T2@7620.25 C3:EOD@7628.5 C4:EOD@7628.5 C5:EOD@7628.5)

**2026-08-03 · head s=1** — Σ +267.50
- 18:20 GB100 LONG @7606.0 stop 7598.5 ×5 → **WIN +28.75$** (T1 before stop: YES; full-stop would be -187.5$; MFE 32.5 / MAE -3.75 / hold-to-close 22.5 pts; legs: C1:T1@7609.0 C2:T2@7608.75 C3:BE@7606.0 C4:BE@7606.0 C5:BE@7606.0)  ← injected live #601 (live: T2_HIT 53.75)
- 18:50 BULL_FLAG_LONG LONG @7612.5 stop 7606.0 ×5 → **WIN +30.00$** (T1 before stop: YES; full-stop would be -162.5$; MFE 26.0 / MAE -3.25 / hold-to-close 16.0 pts; legs: C1:T1@7615.5 C2:T2@7615.5 C3:BE@7612.5 C4:BE@7612.5 C5:BE@7612.5)
- 20:15 INITIATIVE_LONG LONG @7616.75 stop 7609.25 ×5 → **WIN +208.75$** (T1 before stop: YES; full-stop would be -187.5$; MFE 21.75 / MAE -0.5 / hold-to-close 11.75 pts; legs: C1:T1@7619.75 C2:T2@7620.25 C3:EOD@7628.5 C4:EOD@7628.5 C5:EOD@7628.5)

**2026-08-03 · fixed s=0** — Σ +332.50
- 17:10 INITIATIVE_LONG LONG @7587.5 stop 7576.0 ×3 → **WIN +332.50$** (T1 before stop: YES; full-stop would be -172.5$; MFE 51.0 / MAE -0.25 / hold-to-close 41.0 pts; legs: C1:T1@7594.0 C2:T2@7606.5 C3:EOD@7628.5)

**2026-08-03 · fixed s=1** — Σ +332.50
- 17:10 INITIATIVE_LONG LONG @7587.5 stop 7576.0 ×3 → **WIN +332.50$** (T1 before stop: YES; full-stop would be -172.5$; MFE 51.0 / MAE -0.25 / hold-to-close 41.0 pts; legs: C1:T1@7594.0 C2:T2@7606.5 C3:EOD@7628.5)

**2026-08-03 · headoe s=1 · oe-closed** — Σ +267.50
- 18:20 GB100 LONG @7606.0 stop 7598.5 ×5 → **WIN +28.75$** (T1 before stop: YES; full-stop would be -187.5$; MFE 32.5 / MAE -3.75 / hold-to-close 22.5 pts; legs: C1:T1@7609.0 C2:T2@7608.75 C3:BE@7606.0 C4:BE@7606.0 C5:BE@7606.0)  ← injected live #601 (live: T2_HIT 53.75)
- 18:50 BULL_FLAG_LONG LONG @7612.5 stop 7606.0 ×5 → **WIN +30.00$** (T1 before stop: YES; full-stop would be -162.5$; MFE 26.0 / MAE -3.25 / hold-to-close 16.0 pts; legs: C1:T1@7615.5 C2:T2@7615.5 C3:BE@7612.5 C4:BE@7612.5 C5:BE@7612.5)
- 20:15 INITIATIVE_LONG LONG @7616.75 stop 7609.25 ×5 → **WIN +208.75$** (T1 before stop: YES; full-stop would be -187.5$; MFE 21.75 / MAE -0.5 / hold-to-close 11.75 pts; legs: C1:T1@7619.75 C2:T2@7620.25 C3:EOD@7628.5 C4:EOD@7628.5 C5:EOD@7628.5)

**2026-08-03 · fixedoe s=1 · oe-closed** — Σ +332.50
- 17:10 INITIATIVE_LONG LONG @7587.5 stop 7576.0 ×3 → **WIN +332.50$** (T1 before stop: YES; full-stop would be -172.5$; MFE 51.0 / MAE -0.25 / hold-to-close 41.0 pts; legs: C1:T1@7594.0 C2:T2@7606.5 C3:EOD@7628.5)

**2026-08-03 · fixedoe s=0 · oe-closed** — Σ +332.50
- 17:10 INITIATIVE_LONG LONG @7587.5 stop 7576.0 ×3 → **WIN +332.50$** (T1 before stop: YES; full-stop would be -172.5$; MFE 51.0 / MAE -0.25 / hold-to-close 41.0 pts; legs: C1:T1@7594.0 C2:T2@7606.5 C3:EOD@7628.5)

**2026-09-02 · head s=0** — Σ -180.00
- 19:24 GB100 SHORT @7676.0 stop 7681.25 ×2 → **STOP -52.50$** (T1 before stop: NO; full-stop would be -52.5$; MFE 6.0 / MAE -11.5 / hold-to-close -2.5 pts; legs: C1:STOP@7681.25 C2:STOP@7681.25)
- 20:05 GHOST LONG @7681.0 stop 7673.75 ×2 → **STOP -72.50$** (T1 before stop: NO; full-stop would be -72.5$; MFE 6.5 / MAE -11.0 / hold-to-close -2.5 pts; legs: C1:STOP@7673.75 C2:STOP@7673.75)
- 20:35 GHOST SHORT @7670.25 stop 7675.75 ×2 → **STOP -55.00$** (T1 before stop: NO; full-stop would be -55.0$; MFE 0.25 / MAE -17.25 / hold-to-close -8.25 pts; legs: C1:STOP@7675.75 C2:STOP@7675.75)

**2026-09-02 · head s=1** — Σ -180.00
- 19:24 GB100 SHORT @7676.0 stop 7681.25 ×2 → **STOP -52.50$** (T1 before stop: NO; full-stop would be -52.5$; MFE 6.0 / MAE -11.5 / hold-to-close -2.5 pts; legs: C1:STOP@7681.25 C2:STOP@7681.25)
- 20:05 GHOST LONG @7681.0 stop 7673.75 ×2 → **STOP -72.50$** (T1 before stop: NO; full-stop would be -72.5$; MFE 6.5 / MAE -11.0 / hold-to-close -2.5 pts; legs: C1:STOP@7673.75 C2:STOP@7673.75)
- 20:35 GHOST SHORT @7670.25 stop 7675.75 ×2 → **STOP -55.00$** (T1 before stop: NO; full-stop would be -55.0$; MFE 0.25 / MAE -17.25 / hold-to-close -8.25 pts; legs: C1:STOP@7675.75 C2:STOP@7675.75)

**2026-09-02 · fixed s=0** — Σ -180.00
- 19:24 GB100 SHORT @7676.0 stop 7681.25 ×2 → **STOP -52.50$** (T1 before stop: NO; full-stop would be -52.5$; MFE 6.0 / MAE -11.5 / hold-to-close -2.5 pts; legs: C1:STOP@7681.25 C2:STOP@7681.25)
- 20:05 GHOST LONG @7681.0 stop 7673.75 ×2 → **STOP -72.50$** (T1 before stop: NO; full-stop would be -72.5$; MFE 6.5 / MAE -11.0 / hold-to-close -2.5 pts; legs: C1:STOP@7673.75 C2:STOP@7673.75)
- 20:35 GHOST SHORT @7670.25 stop 7675.75 ×2 → **STOP -55.00$** (T1 before stop: NO; full-stop would be -55.0$; MFE 0.25 / MAE -17.25 / hold-to-close -8.25 pts; legs: C1:STOP@7675.75 C2:STOP@7675.75)

**2026-09-02 · fixed s=1** — Σ -180.00
- 19:24 GB100 SHORT @7676.0 stop 7681.25 ×2 → **STOP -52.50$** (T1 before stop: NO; full-stop would be -52.5$; MFE 6.0 / MAE -11.5 / hold-to-close -2.5 pts; legs: C1:STOP@7681.25 C2:STOP@7681.25)
- 20:05 GHOST LONG @7681.0 stop 7673.75 ×2 → **STOP -72.50$** (T1 before stop: NO; full-stop would be -72.5$; MFE 6.5 / MAE -11.0 / hold-to-close -2.5 pts; legs: C1:STOP@7673.75 C2:STOP@7673.75)
- 20:35 GHOST SHORT @7670.25 stop 7675.75 ×2 → **STOP -55.00$** (T1 before stop: NO; full-stop would be -55.0$; MFE 0.25 / MAE -17.25 / hold-to-close -8.25 pts; legs: C1:STOP@7675.75 C2:STOP@7675.75)

**2026-09-02 · headoe s=1 · oe-closed** — Σ -180.00
- 19:24 GB100 SHORT @7676.0 stop 7681.25 ×2 → **STOP -52.50$** (T1 before stop: NO; full-stop would be -52.5$; MFE 6.0 / MAE -11.5 / hold-to-close -2.5 pts; legs: C1:STOP@7681.25 C2:STOP@7681.25)
- 20:05 GHOST LONG @7681.0 stop 7673.75 ×2 → **STOP -72.50$** (T1 before stop: NO; full-stop would be -72.5$; MFE 6.5 / MAE -11.0 / hold-to-close -2.5 pts; legs: C1:STOP@7673.75 C2:STOP@7673.75)
- 20:35 GHOST SHORT @7670.25 stop 7675.75 ×2 → **STOP -55.00$** (T1 before stop: NO; full-stop would be -55.0$; MFE 0.25 / MAE -17.25 / hold-to-close -8.25 pts; legs: C1:STOP@7675.75 C2:STOP@7675.75)

**2026-09-02 · fixedoe s=1 · oe-closed** — Σ -180.00
- 19:24 GB100 SHORT @7676.0 stop 7681.25 ×2 → **STOP -52.50$** (T1 before stop: NO; full-stop would be -52.5$; MFE 6.0 / MAE -11.5 / hold-to-close -2.5 pts; legs: C1:STOP@7681.25 C2:STOP@7681.25)
- 20:05 GHOST LONG @7681.0 stop 7673.75 ×2 → **STOP -72.50$** (T1 before stop: NO; full-stop would be -72.5$; MFE 6.5 / MAE -11.0 / hold-to-close -2.5 pts; legs: C1:STOP@7673.75 C2:STOP@7673.75)
- 20:35 GHOST SHORT @7670.25 stop 7675.75 ×2 → **STOP -55.00$** (T1 before stop: NO; full-stop would be -55.0$; MFE 0.25 / MAE -17.25 / hold-to-close -8.25 pts; legs: C1:STOP@7675.75 C2:STOP@7675.75)

**2026-09-02 · fixedoe s=0 · oe-closed** — Σ -180.00
- 19:24 GB100 SHORT @7676.0 stop 7681.25 ×2 → **STOP -52.50$** (T1 before stop: NO; full-stop would be -52.5$; MFE 6.0 / MAE -11.5 / hold-to-close -2.5 pts; legs: C1:STOP@7681.25 C2:STOP@7681.25)
- 20:05 GHOST LONG @7681.0 stop 7673.75 ×2 → **STOP -72.50$** (T1 before stop: NO; full-stop would be -72.5$; MFE 6.5 / MAE -11.0 / hold-to-close -2.5 pts; legs: C1:STOP@7673.75 C2:STOP@7673.75)
- 20:35 GHOST SHORT @7670.25 stop 7675.75 ×2 → **STOP -55.00$** (T1 before stop: NO; full-stop would be -55.0$; MFE 0.25 / MAE -17.25 / hold-to-close -8.25 pts; legs: C1:STOP@7675.75 C2:STOP@7675.75)

**2026-08-04 · fixed s=0** — Σ +427.50
- 17:05 REACTIVE_LONG LONG @7690.75 stop 7681.75 ×3 → **WIN +427.50$** (T1 before stop: YES; full-stop would be -135.0$; MFE 64.5 / MAE -1.0 / hold-to-close 63.75 pts; legs: C1:T1@7697.5 C2:T2@7705.75 C3:EOD@7754.5)  ← injected live #612 (live: T3_HIT 158.75)

**2026-08-04 · fixed s=1** — Σ +427.50
- 17:05 REACTIVE_LONG LONG @7690.75 stop 7681.75 ×3 → **WIN +427.50$** (T1 before stop: YES; full-stop would be -135.0$; MFE 64.5 / MAE -1.0 / hold-to-close 63.75 pts; legs: C1:T1@7697.5 C2:T2@7705.75 C3:EOD@7754.5)  ← injected live #612 (live: T3_HIT 158.75)

**2026-08-04 · fixedoe s=1 · oe-closed** — Σ +427.50
- 17:05 REACTIVE_LONG LONG @7690.75 stop 7681.75 ×3 → **WIN +427.50$** (T1 before stop: YES; full-stop would be -135.0$; MFE 64.5 / MAE -1.0 / hold-to-close 63.75 pts; legs: C1:T1@7697.5 C2:T2@7705.75 C3:EOD@7754.5)  ← injected live #612 (live: T3_HIT 158.75)

**2026-08-04 · fixedoe s=0 · oe-closed** — Σ +427.50
- 17:05 REACTIVE_LONG LONG @7690.75 stop 7681.75 ×3 → **WIN +427.50$** (T1 before stop: YES; full-stop would be -135.0$; MFE 64.5 / MAE -1.0 / hold-to-close 63.75 pts; legs: C1:T1@7697.5 C2:T2@7705.75 C3:EOD@7754.5)  ← injected live #612 (live: T3_HIT 158.75)

**2026-09-09 · head s=0** — Σ -290.00
- 19:05 VEGAS LONG @7643.25 stop 7639.25 ×2 → **STOP -40.00$** (T1 before stop: NO; full-stop would be -40.0$; MFE 11.0 / MAE -10.75 / hold-to-close 1.25 pts; legs: C1:STOP@7639.25 C2:STOP@7639.25)  ← injected live #1328 (live: STOP_HIT -40.0)
- 20:15 DOUBLE_BOTTOM_EE_LONG LONG @7651.5 stop 7646.75 ×5 → **STOP -118.75$** (T1 before stop: NO; full-stop would be -118.75$; MFE 2.75 / MAE -10.25 / hold-to-close -7.0 pts; legs: C1:STOP@7646.75 C2:STOP@7646.75 C3:STOP@7646.75 C4:STOP@7646.75 C5:STOP@7646.75)
- 20:55 BULL_FLAG_LONG LONG @7652.5 stop 7647.25 ×5 → **STOP -131.25$** (T1 before stop: NO; full-stop would be -131.25$; MFE 1.75 / MAE -11.25 / hold-to-close -8.0 pts; legs: C1:STOP@7647.25 C2:STOP@7647.25 C3:STOP@7647.25 C4:STOP@7647.25 C5:STOP@7647.25)

**2026-09-09 · head s=1** — Σ -290.00
- 19:05 VEGAS LONG @7643.25 stop 7639.25 ×2 → **STOP -40.00$** (T1 before stop: NO; full-stop would be -40.0$; MFE 11.0 / MAE -10.75 / hold-to-close 1.25 pts; legs: C1:STOP@7639.25 C2:STOP@7639.25)  ← injected live #1328 (live: STOP_HIT -40.0)
- 20:15 DOUBLE_BOTTOM_EE_LONG LONG @7651.5 stop 7646.75 ×5 → **STOP -118.75$** (T1 before stop: NO; full-stop would be -118.75$; MFE 2.75 / MAE -10.25 / hold-to-close -7.0 pts; legs: C1:STOP@7646.75 C2:STOP@7646.75 C3:STOP@7646.75 C4:STOP@7646.75 C5:STOP@7646.75)
- 20:55 BULL_FLAG_LONG LONG @7652.5 stop 7647.25 ×5 → **STOP -131.25$** (T1 before stop: NO; full-stop would be -131.25$; MFE 1.75 / MAE -11.25 / hold-to-close -8.0 pts; legs: C1:STOP@7647.25 C2:STOP@7647.25 C3:STOP@7647.25 C4:STOP@7647.25 C5:STOP@7647.25)

**2026-09-09 · fixed s=0** — Σ -290.00
- 19:05 VEGAS LONG @7643.25 stop 7639.25 ×2 → **STOP -40.00$** (T1 before stop: NO; full-stop would be -40.0$; MFE 11.0 / MAE -10.75 / hold-to-close 1.25 pts; legs: C1:STOP@7639.25 C2:STOP@7639.25)  ← injected live #1328 (live: STOP_HIT -40.0)
- 20:15 DOUBLE_BOTTOM_EE_LONG LONG @7651.5 stop 7646.75 ×5 → **STOP -118.75$** (T1 before stop: NO; full-stop would be -118.75$; MFE 2.75 / MAE -10.25 / hold-to-close -7.0 pts; legs: C1:STOP@7646.75 C2:STOP@7646.75 C3:STOP@7646.75 C4:STOP@7646.75 C5:STOP@7646.75)
- 20:55 BULL_FLAG_LONG LONG @7652.5 stop 7647.25 ×5 → **STOP -131.25$** (T1 before stop: NO; full-stop would be -131.25$; MFE 1.75 / MAE -11.25 / hold-to-close -8.0 pts; legs: C1:STOP@7647.25 C2:STOP@7647.25 C3:STOP@7647.25 C4:STOP@7647.25 C5:STOP@7647.25)

**2026-09-09 · fixed s=1** — Σ -290.00
- 19:05 VEGAS LONG @7643.25 stop 7639.25 ×2 → **STOP -40.00$** (T1 before stop: NO; full-stop would be -40.0$; MFE 11.0 / MAE -10.75 / hold-to-close 1.25 pts; legs: C1:STOP@7639.25 C2:STOP@7639.25)  ← injected live #1328 (live: STOP_HIT -40.0)
- 20:15 DOUBLE_BOTTOM_EE_LONG LONG @7651.5 stop 7646.75 ×5 → **STOP -118.75$** (T1 before stop: NO; full-stop would be -118.75$; MFE 2.75 / MAE -10.25 / hold-to-close -7.0 pts; legs: C1:STOP@7646.75 C2:STOP@7646.75 C3:STOP@7646.75 C4:STOP@7646.75 C5:STOP@7646.75)
- 20:55 BULL_FLAG_LONG LONG @7652.5 stop 7647.25 ×5 → **STOP -131.25$** (T1 before stop: NO; full-stop would be -131.25$; MFE 1.75 / MAE -11.25 / hold-to-close -8.0 pts; legs: C1:STOP@7647.25 C2:STOP@7647.25 C3:STOP@7647.25 C4:STOP@7647.25 C5:STOP@7647.25)

**2026-09-09 · headoe s=1 · oe-closed** — Σ -436.25
- 16:50 OPENING_PULLBACK_CONT LONG @7658.75 stop 7648.0 ×4 → **STOP -146.25$** (T1 before stop: NO; full-stop would be -215.0$; MFE 6.25 / MAE -30.0 / hold-to-close -14.25 pts; legs: C1:T1@7661.75 C2:STOP@7648.0 C3:STOP@7648.0 C4:STOP@7648.0)
- 19:05 VEGAS LONG @7643.25 stop 7639.25 ×2 → **STOP -40.00$** (T1 before stop: NO; full-stop would be -40.0$; MFE 11.0 / MAE -10.75 / hold-to-close 1.25 pts; legs: C1:STOP@7639.25 C2:STOP@7639.25)  ← injected live #1328 (live: STOP_HIT -40.0)
- 20:15 DOUBLE_BOTTOM_EE_LONG LONG @7651.5 stop 7646.75 ×5 → **STOP -118.75$** (T1 before stop: NO; full-stop would be -118.75$; MFE 2.75 / MAE -10.25 / hold-to-close -7.0 pts; legs: C1:STOP@7646.75 C2:STOP@7646.75 C3:STOP@7646.75 C4:STOP@7646.75 C5:STOP@7646.75)
- 20:55 BULL_FLAG_LONG LONG @7652.5 stop 7647.25 ×5 → **STOP -131.25$** (T1 before stop: NO; full-stop would be -131.25$; MFE 1.75 / MAE -11.25 / hold-to-close -8.0 pts; legs: C1:STOP@7647.25 C2:STOP@7647.25 C3:STOP@7647.25 C4:STOP@7647.25 C5:STOP@7647.25)

**2026-09-09 · fixedoe s=1 · oe-closed** — Σ -290.00
- 19:05 VEGAS LONG @7643.25 stop 7639.25 ×2 → **STOP -40.00$** (T1 before stop: NO; full-stop would be -40.0$; MFE 11.0 / MAE -10.75 / hold-to-close 1.25 pts; legs: C1:STOP@7639.25 C2:STOP@7639.25)  ← injected live #1328 (live: STOP_HIT -40.0)
- 20:15 DOUBLE_BOTTOM_EE_LONG LONG @7651.5 stop 7646.75 ×5 → **STOP -118.75$** (T1 before stop: NO; full-stop would be -118.75$; MFE 2.75 / MAE -10.25 / hold-to-close -7.0 pts; legs: C1:STOP@7646.75 C2:STOP@7646.75 C3:STOP@7646.75 C4:STOP@7646.75 C5:STOP@7646.75)
- 20:55 BULL_FLAG_LONG LONG @7652.5 stop 7647.25 ×5 → **STOP -131.25$** (T1 before stop: NO; full-stop would be -131.25$; MFE 1.75 / MAE -11.25 / hold-to-close -8.0 pts; legs: C1:STOP@7647.25 C2:STOP@7647.25 C3:STOP@7647.25 C4:STOP@7647.25 C5:STOP@7647.25)

**2026-09-09 · fixedoe s=0 · oe-closed** — Σ -290.00
- 19:05 VEGAS LONG @7643.25 stop 7639.25 ×2 → **STOP -40.00$** (T1 before stop: NO; full-stop would be -40.0$; MFE 11.0 / MAE -10.75 / hold-to-close 1.25 pts; legs: C1:STOP@7639.25 C2:STOP@7639.25)  ← injected live #1328 (live: STOP_HIT -40.0)
- 20:15 DOUBLE_BOTTOM_EE_LONG LONG @7651.5 stop 7646.75 ×5 → **STOP -118.75$** (T1 before stop: NO; full-stop would be -118.75$; MFE 2.75 / MAE -10.25 / hold-to-close -7.0 pts; legs: C1:STOP@7646.75 C2:STOP@7646.75 C3:STOP@7646.75 C4:STOP@7646.75 C5:STOP@7646.75)
- 20:55 BULL_FLAG_LONG LONG @7652.5 stop 7647.25 ×5 → **STOP -131.25$** (T1 before stop: NO; full-stop would be -131.25$; MFE 1.75 / MAE -11.25 / hold-to-close -8.0 pts; legs: C1:STOP@7647.25 C2:STOP@7647.25 C3:STOP@7647.25 C4:STOP@7647.25 C5:STOP@7647.25)

**2026-09-01 · head s=0** — Σ +110.00
- 18:34 CONFLUENCE_RI_ZLR LONG @7663.5 stop 7656.5 ×2 → **WIN +60.00$** (T1 before stop: YES; full-stop would be -70.0$; MFE 10.25 / MAE -42.0 / hold-to-close -19.5 pts; legs: C1:T1@7667.5 C2:T2@7671.5)
- 18:55 INITIATIVE_LONG LONG @7672.5 stop 7665.0 ×5 → **STOP -187.50$** (T1 before stop: NO; full-stop would be -187.5$; MFE 0.25 / MAE -51.0 / hold-to-close -28.5 pts; legs: C1:STOP@7665.0 C2:STOP@7665.0 C3:STOP@7665.0 C4:STOP@7665.0 C5:STOP@7665.0)
- 19:30 INITIATIVE_SHORT SHORT @7652.25 stop 7658.5 ×5 → **WIN +237.50$** (T1 before stop: YES; full-stop would be -156.25$; MFE 30.75 / MAE -1.0 / hold-to-close 8.25 pts; legs: C1:T1@7649.25 C2:T2@7638.5 C3:T3@7638.0 C4:EOD@7644.0 C5:EOD@7644.0)

**2026-09-01 · head s=1** — Σ +110.00
- 18:34 CONFLUENCE_RI_ZLR LONG @7663.5 stop 7656.5 ×2 → **WIN +60.00$** (T1 before stop: YES; full-stop would be -70.0$; MFE 10.25 / MAE -42.0 / hold-to-close -19.5 pts; legs: C1:T1@7667.5 C2:T2@7671.5)
- 18:55 INITIATIVE_LONG LONG @7672.5 stop 7665.0 ×5 → **STOP -187.50$** (T1 before stop: NO; full-stop would be -187.5$; MFE 0.25 / MAE -51.0 / hold-to-close -28.5 pts; legs: C1:STOP@7665.0 C2:STOP@7665.0 C3:STOP@7665.0 C4:STOP@7665.0 C5:STOP@7665.0)
- 19:30 INITIATIVE_SHORT SHORT @7652.25 stop 7658.5 ×5 → **WIN +237.50$** (T1 before stop: YES; full-stop would be -156.25$; MFE 30.75 / MAE -1.0 / hold-to-close 8.25 pts; legs: C1:T1@7649.25 C2:T2@7638.5 C3:T3@7638.0 C4:EOD@7644.0 C5:EOD@7644.0)

**2026-09-01 · fixed s=0** — Σ +110.00
- 18:34 CONFLUENCE_RI_ZLR LONG @7663.5 stop 7656.5 ×2 → **WIN +60.00$** (T1 before stop: YES; full-stop would be -70.0$; MFE 10.25 / MAE -42.0 / hold-to-close -19.5 pts; legs: C1:T1@7667.5 C2:T2@7671.5)
- 18:55 INITIATIVE_LONG LONG @7672.5 stop 7665.0 ×5 → **STOP -187.50$** (T1 before stop: NO; full-stop would be -187.5$; MFE 0.25 / MAE -51.0 / hold-to-close -28.5 pts; legs: C1:STOP@7665.0 C2:STOP@7665.0 C3:STOP@7665.0 C4:STOP@7665.0 C5:STOP@7665.0)
- 19:30 INITIATIVE_SHORT SHORT @7652.25 stop 7658.5 ×5 → **WIN +237.50$** (T1 before stop: YES; full-stop would be -156.25$; MFE 30.75 / MAE -1.0 / hold-to-close 8.25 pts; legs: C1:T1@7649.25 C2:T2@7638.5 C3:T3@7638.0 C4:EOD@7644.0 C5:EOD@7644.0)

**2026-09-01 · fixed s=1** — Σ +110.00
- 18:34 CONFLUENCE_RI_ZLR LONG @7663.5 stop 7656.5 ×2 → **WIN +60.00$** (T1 before stop: YES; full-stop would be -70.0$; MFE 10.25 / MAE -42.0 / hold-to-close -19.5 pts; legs: C1:T1@7667.5 C2:T2@7671.5)
- 18:55 INITIATIVE_LONG LONG @7672.5 stop 7665.0 ×5 → **STOP -187.50$** (T1 before stop: NO; full-stop would be -187.5$; MFE 0.25 / MAE -51.0 / hold-to-close -28.5 pts; legs: C1:STOP@7665.0 C2:STOP@7665.0 C3:STOP@7665.0 C4:STOP@7665.0 C5:STOP@7665.0)
- 19:30 INITIATIVE_SHORT SHORT @7652.25 stop 7658.5 ×5 → **WIN +237.50$** (T1 before stop: YES; full-stop would be -156.25$; MFE 30.75 / MAE -1.0 / hold-to-close 8.25 pts; legs: C1:T1@7649.25 C2:T2@7638.5 C3:T3@7638.0 C4:EOD@7644.0 C5:EOD@7644.0)

**2026-09-01 · headoe s=1 · oe-closed** — Σ +70.00
- 16:45 OPENING_PULLBACK_CONT LONG @7646.25 stop 7643.5 ×5 → **STOP -40.00$** (T1 before stop: NO; full-stop would be -68.75$; MFE 27.5 / MAE -24.75 / hold-to-close -2.25 pts; legs: C1:T1@7649.25 C2:STOP@7643.5 C3:STOP@7643.5 C4:STOP@7643.5 C5:STOP@7643.5)
- 18:34 CONFLUENCE_RI_ZLR LONG @7663.5 stop 7656.5 ×2 → **WIN +60.00$** (T1 before stop: YES; full-stop would be -70.0$; MFE 10.25 / MAE -42.0 / hold-to-close -19.5 pts; legs: C1:T1@7667.5 C2:T2@7671.5)
- 18:55 INITIATIVE_LONG LONG @7672.5 stop 7665.0 ×5 → **STOP -187.50$** (T1 before stop: NO; full-stop would be -187.5$; MFE 0.25 / MAE -51.0 / hold-to-close -28.5 pts; legs: C1:STOP@7665.0 C2:STOP@7665.0 C3:STOP@7665.0 C4:STOP@7665.0 C5:STOP@7665.0)
- 19:30 INITIATIVE_SHORT SHORT @7652.25 stop 7658.5 ×5 → **WIN +237.50$** (T1 before stop: YES; full-stop would be -156.25$; MFE 30.75 / MAE -1.0 / hold-to-close 8.25 pts; legs: C1:T1@7649.25 C2:T2@7638.5 C3:T3@7638.0 C4:EOD@7644.0 C5:EOD@7644.0)

**2026-09-01 · fixedoe s=1 · oe-closed** — Σ +16.25
- 16:50 OPENING_DRIVE LONG @7649.25 stop 7645.5 ×5 → **STOP -93.75$** (T1 before stop: NO; full-stop would be -93.75$; MFE 24.5 / MAE -27.75 / hold-to-close -5.25 pts; legs: C1:STOP@7645.5 C2:STOP@7645.5 C3:STOP@7645.5 C4:STOP@7645.5 C5:STOP@7645.5)
- 18:34 CONFLUENCE_RI_ZLR LONG @7663.5 stop 7656.5 ×2 → **WIN +60.00$** (T1 before stop: YES; full-stop would be -70.0$; MFE 10.25 / MAE -42.0 / hold-to-close -19.5 pts; legs: C1:T1@7667.5 C2:T2@7671.5)
- 18:55 INITIATIVE_LONG LONG @7672.5 stop 7665.0 ×5 → **STOP -187.50$** (T1 before stop: NO; full-stop would be -187.5$; MFE 0.25 / MAE -51.0 / hold-to-close -28.5 pts; legs: C1:STOP@7665.0 C2:STOP@7665.0 C3:STOP@7665.0 C4:STOP@7665.0 C5:STOP@7665.0)
- 19:30 INITIATIVE_SHORT SHORT @7652.25 stop 7658.5 ×5 → **WIN +237.50$** (T1 before stop: YES; full-stop would be -156.25$; MFE 30.75 / MAE -1.0 / hold-to-close 8.25 pts; legs: C1:T1@7649.25 C2:T2@7638.5 C3:T3@7638.0 C4:EOD@7644.0 C5:EOD@7644.0)

**2026-09-01 · fixedoe s=0 · oe-closed** — Σ +16.25
- 16:50 OPENING_DRIVE LONG @7649.25 stop 7645.5 ×5 → **STOP -93.75$** (T1 before stop: NO; full-stop would be -93.75$; MFE 24.5 / MAE -27.75 / hold-to-close -5.25 pts; legs: C1:STOP@7645.5 C2:STOP@7645.5 C3:STOP@7645.5 C4:STOP@7645.5 C5:STOP@7645.5)
- 18:34 CONFLUENCE_RI_ZLR LONG @7663.5 stop 7656.5 ×2 → **WIN +60.00$** (T1 before stop: YES; full-stop would be -70.0$; MFE 10.25 / MAE -42.0 / hold-to-close -19.5 pts; legs: C1:T1@7667.5 C2:T2@7671.5)
- 18:55 INITIATIVE_LONG LONG @7672.5 stop 7665.0 ×5 → **STOP -187.50$** (T1 before stop: NO; full-stop would be -187.5$; MFE 0.25 / MAE -51.0 / hold-to-close -28.5 pts; legs: C1:STOP@7665.0 C2:STOP@7665.0 C3:STOP@7665.0 C4:STOP@7665.0 C5:STOP@7665.0)
- 19:30 INITIATIVE_SHORT SHORT @7652.25 stop 7658.5 ×5 → **WIN +237.50$** (T1 before stop: YES; full-stop would be -156.25$; MFE 30.75 / MAE -1.0 / hold-to-close 8.25 pts; legs: C1:T1@7649.25 C2:T2@7638.5 C3:T3@7638.0 C4:EOD@7644.0 C5:EOD@7644.0)


### 8-T3 · phase A/B (16:30–17:30): what the gateway saw and did

**2026-08-28 · head s=0**

| IL | sys | setup | dir | entry/stop/t1 | `_dp_ot` | hint | intent bias/kinds/size | verdict |
|---|---|---|---|---|---|---|---|---|
| 16:30:03 | S4 | GB100 | SHORT | 7746.25/7750.25/7731.5 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:30:03 | S2 | DALTON_EDGE_LONG | LONG | 7746.25/7740.75/7751.75 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:35:03 | S2 | FAILED_BREAK_LONG | LONG | 7749.5/7741.25/7757.75 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:39:58 | S4 | ZLR | LONG | 7751.5/7736.5/7774.0 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:44:58 | S4 | GB100 | LONG | 7754.75/7739.75/7777.25 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:50:03 | S2 | DALTON_EDGE_SHORT | SHORT | 7750.75/7760.0/7741.5 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 16:54:58 | S4 | FAMIR | SHORT | 7746.25/7758.25/7731.5 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 16:55:03 | S2 | FAILED_BREAK_SHORT | SHORT | 7746.25/7758.25/7734.25 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 16:59:58 | S4 | HTLB | LONG | 7747.0/7727.5/7776.25 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 17:04:58 | S4 | ZLR | SHORT | 7746.0/7761.0/7731.5 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 17:05:03 | S4 | ZLR (injected live #838) | SHORT | 7746.5/7746.5/7738.25 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 17:09:58 | S4 | GB100 | SHORT | 7738.75/7753.75/7716.25 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 17:10:03 | S4 | SCALE_IN (injected live #840) | SHORT | 7738.75/7738.5/7726.5 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 17:15:03 | S4 | SCALE_IN (injected live #841) | SHORT | 7731.0/7738.62/7719.57 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 17:24:58 | S4 | ZLR | LONG | 7744.5/7729.5/7760.5 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 17:29:58 | S4 | ZLR | SHORT | 7742.0/7757.0/7726.5 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |

**2026-08-28 · fixed s=1**

| IL | sys | setup | dir | entry/stop/t1 | `_dp_ot` | hint | intent bias/kinds/size | verdict |
|---|---|---|---|---|---|---|---|---|
| 16:30:03 | S4 | GB100 | SHORT | 7746.25/7750.25/7731.5 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:30:03 | S2 | DALTON_EDGE_LONG | LONG | 7746.25/7740.75/7751.75 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:35:03 | S2 | FAILED_BREAK_LONG | LONG | 7749.5/7741.25/7757.75 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:39:58 | S4 | ZLR | LONG | 7751.5/7736.5/7774.0 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:44:58 | S4 | GB100 | LONG | 7754.75/7739.75/7777.25 | OPEN_DRIVE | LONG | LONG / WITH_DRIVE / 0.5 | entry_location_quality — beyond_value: ex=7.50 > 0.25 (entry past value area) |
| 16:50:03 | S2 | DALTON_EDGE_SHORT | SHORT | 7750.75/7760.0/7741.5 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 16:54:58 | S4 | FAMIR | SHORT | 7746.25/7758.25/7731.5 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 16:55:03 | S2 | FAILED_BREAK_SHORT | SHORT | 7746.25/7758.25/7734.25 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | shadow  |
| 16:59:58 | S4 | HTLB | LONG | 7747.0/7727.5/7776.25 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:04:58 | S4 | ZLR | SHORT | 7746.0/7761.0/7731.5 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:05:03 | S4 | ZLR (injected live #838) | SHORT | 7746.5/7746.5/7738.25 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:09:58 | S4 | GB100 | SHORT | 7738.75/7753.75/7716.25 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:10:03 | S4 | SCALE_IN (injected live #840) | SHORT | 7738.75/7738.5/7726.5 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:15:03 | S4 | SCALE_IN (injected live #841) | SHORT | 7731.0/7738.62/7719.57 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:24:58 | S4 | ZLR | LONG | 7744.5/7729.5/7760.5 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:29:58 | S4 | ZLR | SHORT | 7742.0/7757.0/7726.5 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |

**2026-08-28 · fixedoe s=1 · oe-closed**

| IL | sys | setup | dir | entry/stop/t1 | `_dp_ot` | hint | intent bias/kinds/size | verdict |
|---|---|---|---|---|---|---|---|---|
| 16:30:03 | S4 | GB100 | SHORT | 7746.25/7750.25/7731.5 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:30:03 | S2 | DALTON_EDGE_LONG | LONG | 7746.25/7740.75/7751.75 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:35:03 | S2 | FAILED_BREAK_LONG | LONG | 7749.5/7741.25/7757.75 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:39:58 | S4 | ZLR | LONG | 7751.5/7736.5/7774.0 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:44:58 | S4 | GB100 | LONG | 7754.75/7739.75/7777.25 | OPEN_DRIVE | LONG | LONG / WITH_DRIVE / 0.5 | entry_location_quality — beyond_value: ex=7.50 > 0.25 (entry past value area) |
| 16:45:03 | S2 | OPENING_DRIVE | LONG | 7754.75/7742.25/7773.5 | OPEN_DRIVE | LONG | LONG / PULLBACK,WITH_DRIVE / 1.0 | entry_location_quality — beyond_value: ex=7.50 > 0.25 (entry past value area) |
| 16:50:03 | S2 | OPENING_PULLBACK_CONT | SHORT | 7750.75/7762.0/7733.88 | OPEN_AUCTION_IN | SHORT | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 16:50:03 | S2 | DALTON_EDGE_SHORT | SHORT | 7750.75/7760.0/7741.5 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 16:54:58 | S4 | FAMIR | SHORT | 7746.25/7758.25/7731.5 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 16:55:03 | S2 | FAILED_BREAK_SHORT | SHORT | 7746.25/7758.25/7734.25 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | shadow  |
| 16:59:58 | S4 | HTLB | LONG | 7747.0/7727.5/7776.25 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:04:58 | S4 | ZLR | SHORT | 7746.0/7761.0/7731.5 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:05:03 | S4 | ZLR (injected live #838) | SHORT | 7746.5/7746.5/7738.25 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:09:58 | S4 | GB100 | SHORT | 7738.75/7753.75/7716.25 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:10:03 | S4 | SCALE_IN (injected live #840) | SHORT | 7738.75/7738.5/7726.5 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:15:03 | S4 | SCALE_IN (injected live #841) | SHORT | 7731.0/7738.62/7719.57 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:24:58 | S4 | ZLR | LONG | 7744.5/7729.5/7760.5 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:29:58 | S4 | ZLR | SHORT | 7742.0/7757.0/7726.5 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |

**2026-08-03 · head s=0**

| IL | sys | setup | dir | entry/stop/t1 | `_dp_ot` | hint | intent bias/kinds/size | verdict |
|---|---|---|---|---|---|---|---|---|
| 16:35:21 | S4 | HTLB (injected live #588) | LONG | 7563.5/7563.75/7568.75 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:45:09 | S4 | ZLR (injected live #591) | LONG | 7569.5/7565.75/7572.5 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 17:05:03 | S2 | DALTON_EDGE_SHORT | SHORT | 7585.75/7593.25/7578.25 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 17:10:03 | S2 | INITIATIVE_LONG | LONG | 7587.5/7538.75/7660.625 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 17:10:03 | S2 | REACTIVE_LONG (injected live #593) | LONG | 7588.0/7588.25/7594.25 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |

**2026-08-03 · fixed s=1**

| IL | sys | setup | dir | entry/stop/t1 | `_dp_ot` | hint | intent bias/kinds/size | verdict |
|---|---|---|---|---|---|---|---|---|
| 16:35:21 | S4 | HTLB (injected live #588) | LONG | 7563.5/7563.75/7568.75 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:45:09 | S4 | ZLR (injected live #591) | LONG | 7569.5/7565.75/7572.5 | OPEN_DRIVE | LONG | LONG / PULLBACK,WITH_DRIVE / 1.0 | entry_location_quality — beyond_value: ex=0.62 > 0.25 (entry past value area) |
| 17:05:03 | S2 | DALTON_EDGE_SHORT | SHORT | 7585.75/7593.25/7578.25 | OPEN_DRIVE | LONG | LONG / PULLBACK,WITH_DRIVE / 1.0 | dalton_intent:bias — bias=LONG rejects SHORT (phase=B cond=opening_type == OPEN_D |
| 17:10:03 | S2 | INITIATIVE_LONG | LONG | 7587.5/7538.75/7660.625 | OPEN_DRIVE | LONG | LONG / PULLBACK,WITH_DRIVE / 1.0 | LIVE CMD ×3  |
| 17:10:03 | S2 | REACTIVE_LONG (injected live #593) | LONG | 7588.0/7588.25/7594.25 | OPEN_DRIVE | LONG | LONG / PULLBACK,WITH_DRIVE / 1.0 | live:live_slot_occupied  |

**2026-08-03 · fixedoe s=1 · oe-closed**

| IL | sys | setup | dir | entry/stop/t1 | `_dp_ot` | hint | intent bias/kinds/size | verdict |
|---|---|---|---|---|---|---|---|---|
| 16:35:21 | S4 | HTLB (injected live #588) | LONG | 7563.5/7563.75/7568.75 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:45:09 | S4 | ZLR (injected live #591) | LONG | 7569.5/7565.75/7572.5 | OPEN_DRIVE | LONG | LONG / PULLBACK,WITH_DRIVE / 1.0 | entry_location_quality — beyond_value: ex=0.62 > 0.25 (entry past value area) |
| 17:05:03 | S2 | DALTON_EDGE_SHORT | SHORT | 7585.75/7593.25/7578.25 | OPEN_DRIVE | LONG | LONG / PULLBACK,WITH_DRIVE / 1.0 | dalton_intent:bias — bias=LONG rejects SHORT (phase=B cond=opening_type == OPEN_D |
| 17:10:03 | S2 | INITIATIVE_LONG | LONG | 7587.5/7538.75/7660.625 | OPEN_DRIVE | LONG | LONG / PULLBACK,WITH_DRIVE / 1.0 | LIVE CMD ×3  |
| 17:10:03 | S2 | REACTIVE_LONG (injected live #593) | LONG | 7588.0/7588.25/7594.25 | OPEN_DRIVE | LONG | LONG / PULLBACK,WITH_DRIVE / 1.0 | live:live_slot_occupied  |

**2026-09-02 · head s=0**

| IL | sys | setup | dir | entry/stop/t1 | `_dp_ot` | hint | intent bias/kinds/size | verdict |
|---|---|---|---|---|---|---|---|---|
| 16:30:03 | S2 | DALTON_EDGE_SHORT | SHORT | 7650.25/7656.75/7643.75 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:39:58 | S4 | ZLR | LONG | 7651.0/7639.0/7669.0 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:44:58 | S4 | GB100 | LONG | 7654.25/7639.25/7676.75 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:45:03 | S2 | FAILED_BREAK_LONG | LONG | 7654.25/7642.25/7666.25 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 16:54:58 | S4 | ZLR | LONG | 7650.5/7639.25/7667.375 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 16:59:58 | S4 | HTLB | LONG | 7656.75/7639.25/7683.0 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 17:15:03 | S2 | INITIATIVE_LONG | LONG | 7668.75/7639.25/7713.0 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 17:15:06 | S2 | INITIATIVE_LONG (injected live #953) | LONG | 7668.75/7677.75/7672.5 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 17:20:03 | S2 | INITIATIVE_LONG | LONG | 7674.75/7639.25/7728.0 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |

**2026-09-02 · fixed s=1**

| IL | sys | setup | dir | entry/stop/t1 | `_dp_ot` | hint | intent bias/kinds/size | verdict |
|---|---|---|---|---|---|---|---|---|
| 16:30:03 | S2 | DALTON_EDGE_SHORT | SHORT | 7650.25/7656.75/7643.75 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:39:58 | S4 | ZLR | LONG | 7651.0/7639.0/7669.0 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:44:58 | S4 | GB100 | LONG | 7654.25/7639.25/7676.75 | OPEN_REJECTION_REVERSE | SHORT | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:45:03 | S2 | FAILED_BREAK_LONG | LONG | 7654.25/7642.25/7666.25 | OPEN_REJECTION_REVERSE | SHORT | LONG / PULLBACK,REVERSAL / 1.0 | entry_location_quality — beyond_value: ex=3.00 > 0.25 (entry past value area) |
| 16:54:58 | S4 | ZLR | LONG | 7650.5/7639.25/7667.375 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 16:59:58 | S4 | HTLB | LONG | 7656.75/7639.25/7683.0 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:15:03 | S2 | INITIATIVE_LONG | LONG | 7668.75/7639.25/7713.0 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:15:06 | S2 | INITIATIVE_LONG (injected live #953) | LONG | 7668.75/7677.75/7672.5 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:20:03 | S2 | INITIATIVE_LONG | LONG | 7674.75/7639.25/7728.0 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |

**2026-09-02 · fixedoe s=1 · oe-closed**

| IL | sys | setup | dir | entry/stop/t1 | `_dp_ot` | hint | intent bias/kinds/size | verdict |
|---|---|---|---|---|---|---|---|---|
| 16:30:03 | S2 | DALTON_EDGE_SHORT | SHORT | 7650.25/7656.75/7643.75 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:39:58 | S4 | ZLR | LONG | 7651.0/7639.0/7669.0 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:44:58 | S4 | GB100 | LONG | 7654.25/7639.25/7676.75 | OPEN_REJECTION_REVERSE | SHORT | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:45:03 | S2 | OPENING_PULLBACK_CONT | LONG | 7654.25/7639.25/7676.75 | OPEN_REJECTION_REVERSE | SHORT | LONG / PULLBACK,REVERSAL / 1.0 | entry_location_quality — beyond_value: ex=3.00 > 0.25 (entry past value area) |
| 16:45:03 | S2 | FAILED_BREAK_LONG | LONG | 7654.25/7642.25/7666.25 | OPEN_REJECTION_REVERSE | SHORT | LONG / PULLBACK,REVERSAL / 1.0 | entry_location_quality — beyond_value: ex=3.00 > 0.25 (entry past value area) |
| 16:50:03 | S2 | OPENING_ORR | SHORT | 7647.0/7657.0/7632.0 | OPEN_AUCTION_IN | SHORT | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=REVERSAL not in ['EDGE_FADE'] (phase |
| 16:54:58 | S4 | ZLR | LONG | 7650.5/7639.25/7667.375 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 16:59:58 | S4 | HTLB | LONG | 7656.75/7639.25/7683.0 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:00:03 | S2 | OPENING_DRIVE | LONG | 7656.75/7641.75/7679.25 | OPEN_AUCTION_IN | LONG | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=WITH_DRIVE not in ['EDGE_FADE'] (pha |
| 17:15:03 | S2 | INITIATIVE_LONG | LONG | 7668.75/7639.25/7713.0 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:15:06 | S2 | INITIATIVE_LONG (injected live #953) | LONG | 7668.75/7677.75/7672.5 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:20:03 | S2 | INITIATIVE_LONG | LONG | 7674.75/7639.25/7728.0 | OPEN_AUCTION_IN | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |

**2026-08-04 · head s=0**

| IL | sys | setup | dir | entry/stop/t1 | `_dp_ot` | hint | intent bias/kinds/size | verdict |
|---|---|---|---|---|---|---|---|---|
| 16:30:03 | S4 | GB100 | LONG | 7657.5/7642.5/7680.0 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 17:05:03 | S2 | REACTIVE_LONG (injected live #612) | LONG | 7690.75/7691.0/7697.5 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 17:10:03 | S2 | INITIATIVE_LONG | LONG | 7695.5/7649.25/7764.875 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 17:20:03 | S2 | INITIATIVE_LONG | LONG | 7704.75/7652.0/7783.875 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |

**2026-08-04 · fixed s=1**

| IL | sys | setup | dir | entry/stop/t1 | `_dp_ot` | hint | intent bias/kinds/size | verdict |
|---|---|---|---|---|---|---|---|---|
| 16:30:03 | S4 | GB100 | LONG | 7657.5/7642.5/7680.0 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 17:05:03 | S2 | REACTIVE_LONG (injected live #612) | LONG | 7690.75/7691.0/7697.5 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | LIVE CMD ×3  |
| 17:10:03 | S2 | INITIATIVE_LONG | LONG | 7695.5/7649.25/7764.875 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:20:03 | S2 | INITIATIVE_LONG | LONG | 7704.75/7652.0/7783.875 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |

**2026-08-04 · fixedoe s=1 · oe-closed**

| IL | sys | setup | dir | entry/stop/t1 | `_dp_ot` | hint | intent bias/kinds/size | verdict |
|---|---|---|---|---|---|---|---|---|
| 16:30:03 | S4 | GB100 | LONG | 7657.5/7642.5/7680.0 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:50:03 | S2 | OPENING_DRIVE | LONG | 7676.75/7661.75/7699.25 | OPEN_AUCTION_OUT | LONG | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=WITH_DRIVE not in ['EDGE_FADE'] (pha |
| 17:05:03 | S2 | REACTIVE_LONG (injected live #612) | LONG | 7690.75/7691.0/7697.5 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | LIVE CMD ×3  |
| 17:10:03 | S2 | INITIATIVE_LONG | LONG | 7695.5/7649.25/7764.875 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:20:03 | S2 | INITIATIVE_LONG | LONG | 7704.75/7652.0/7783.875 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |

**2026-09-09 · head s=0**

| IL | sys | setup | dir | entry/stop/t1 | `_dp_ot` | hint | intent bias/kinds/size | verdict |
|---|---|---|---|---|---|---|---|---|
| 16:30:03 | S4 | GB100 | LONG | 7660.5/7656.5/7679.75 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:49:58 | S4 | ZLR | LONG | 7658.75/7648.0/7679.75 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 16:59:58 | S4 | GB100 | LONG | 7661.0/7648.0/7679.25 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 17:09:58 | S4 | ZLR | LONG | 7660.5/7648.0/7679.25 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 17:10:03 | S2 | FAILED_BREAK_LONG | LONG | 7660.5/7652.0/7669.0 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 17:20:03 | S2 | INITIATIVE_SHORT | SHORT | 7650.0/7667.75/7623.375 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |

**2026-09-09 · fixed s=1**

| IL | sys | setup | dir | entry/stop/t1 | `_dp_ot` | hint | intent bias/kinds/size | verdict |
|---|---|---|---|---|---|---|---|---|
| 16:30:03 | S4 | GB100 | LONG | 7660.5/7656.5/7679.75 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:49:58 | S4 | ZLR | LONG | 7658.75/7648.0/7679.75 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 16:59:58 | S4 | GB100 | LONG | 7661.0/7648.0/7679.25 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:09:58 | S4 | ZLR | LONG | 7660.5/7648.0/7679.25 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:10:03 | S2 | FAILED_BREAK_LONG | LONG | 7660.5/7652.0/7669.0 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | shadow  |
| 17:20:03 | S2 | INITIATIVE_SHORT | SHORT | 7650.0/7667.75/7623.375 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |

**2026-09-09 · fixedoe s=1 · oe-closed**

| IL | sys | setup | dir | entry/stop/t1 | `_dp_ot` | hint | intent bias/kinds/size | verdict |
|---|---|---|---|---|---|---|---|---|
| 16:30:03 | S4 | GB100 | LONG | 7660.5/7656.5/7679.75 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:49:58 | S4 | ZLR | LONG | 7658.75/7648.0/7679.75 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 16:50:03 | S2 | OPENING_PULLBACK_CONT | LONG | 7658.75/7648.0/7674.88 | OPEN_AUCTION_OUT | LONG | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 16:59:58 | S4 | GB100 | LONG | 7661.0/7648.0/7679.25 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:00:03 | S2 | OPENING_TEST_DRIVE | LONG | 7661.0/7650.5/7676.75 | OPEN_AUCTION_OUT | LONG | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=WITH_DRIVE not in ['EDGE_FADE'] (pha |
| 17:09:58 | S4 | ZLR | LONG | 7660.5/7648.0/7679.25 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:10:03 | S2 | FAILED_BREAK_LONG | LONG | 7660.5/7652.0/7669.0 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | shadow  |
| 17:20:03 | S2 | INITIATIVE_SHORT | SHORT | 7650.0/7667.75/7623.375 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |

**2026-09-01 · head s=0**

| IL | sys | setup | dir | entry/stop/t1 | `_dp_ot` | hint | intent bias/kinds/size | verdict |
|---|---|---|---|---|---|---|---|---|
| 16:34:58 | S4 | ZLR | SHORT | 7646.5/7661.5/7624.0 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:44:58 | S4 | ZLR | SHORT | 7646.25/7661.25/7623.75 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:54:58 | S4 | ZLR | SHORT | 7645.25/7660.25/7622.75 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 16:55:03 | S2 | DALTON_EDGE_SHORT | SHORT | 7645.25/7654.0/7636.5 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 16:59:58 | S4 | ZLR | SHORT | 7647.0/7662.0/7624.5 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 17:20:03 | S2 | INITIATIVE_LONG | LONG | 7660.25/7634.5/7698.875 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 17:20:09 | S2 | INITIATIVE_LONG (injected live #942) | LONG | 7660.25/7660.5/7667.75 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |
| 17:25:03 | S2 | INITIATIVE_LONG | LONG | 7664.0/7634.5/7708.25 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=B cond=default bias=NONE |

**2026-09-01 · fixed s=1**

| IL | sys | setup | dir | entry/stop/t1 | `_dp_ot` | hint | intent bias/kinds/size | verdict |
|---|---|---|---|---|---|---|---|---|
| 16:34:58 | S4 | ZLR | SHORT | 7646.5/7661.5/7624.0 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:44:58 | S4 | ZLR | SHORT | 7646.25/7661.25/7623.75 | OPEN_AUCTION_OUT | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:54:58 | S4 | ZLR | SHORT | 7645.25/7660.25/7622.75 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 16:55:03 | S2 | DALTON_EDGE_SHORT | SHORT | 7645.25/7654.0/7636.5 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 16:59:58 | S4 | ZLR | SHORT | 7647.0/7662.0/7624.5 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:20:03 | S2 | INITIATIVE_LONG | LONG | 7660.25/7634.5/7698.875 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:20:09 | S2 | INITIATIVE_LONG (injected live #942) | LONG | 7660.25/7660.5/7667.75 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:25:03 | S2 | INITIATIVE_LONG | LONG | 7664.0/7634.5/7708.25 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |

**2026-09-01 · fixedoe s=1 · oe-closed**

| IL | sys | setup | dir | entry/stop/t1 | `_dp_ot` | hint | intent bias/kinds/size | verdict |
|---|---|---|---|---|---|---|---|---|
| 16:34:58 | S4 | ZLR | SHORT | 7646.5/7661.5/7624.0 | UNKNOWN | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:44:58 | S4 | ZLR | SHORT | 7646.25/7661.25/7623.75 | OPEN_AUCTION_OUT | None | NONE /  / 0.0 | dalton_intent:stand_down — phase=A cond=default bias=NONE |
| 16:45:03 | S2 | OPENING_PULLBACK_CONT | LONG | 7646.25/7634.5/7663.88 | OPEN_AUCTION_OUT | LONG | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 16:50:03 | S2 | OPENING_DRIVE | LONG | 7649.25/7637.0/7667.62 | OPEN_REJECTION_REVERSE | SHORT | LONG / PULLBACK,REVERSAL / 1.0 | LIVE CMD ×5  |
| 16:54:58 | S4 | ZLR | SHORT | 7645.25/7660.25/7622.75 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 16:55:03 | S2 | OPENING_ORR | SHORT | 7645.25/7653.5/7632.88 | OPEN_AUCTION_OUT | SHORT | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=REVERSAL not in ['EDGE_FADE'] (phase |
| 16:55:03 | S2 | DALTON_EDGE_SHORT | SHORT | 7645.25/7654.0/7636.5 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 16:59:58 | S4 | ZLR | SHORT | 7647.0/7662.0/7624.5 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:20:03 | S2 | INITIATIVE_LONG | LONG | 7660.25/7634.5/7698.875 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:20:09 | S2 | INITIATIVE_LONG (injected live #942) | LONG | 7660.25/7660.5/7667.75 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |
| 17:25:03 | S2 | INITIATIVE_LONG | LONG | 7664.0/7634.5/7708.25 | OPEN_AUCTION_OUT | None | BOTH / EDGE_FADE / 0.5 | dalton_intent:kind — counter-bias entry_kind=BREAK not in ['EDGE_FADE'] (phase=B  |


### 8-T4 · S1 as the harness saw it (opening type on closed bars · label the gate used)

**2026-08-28 · s=0** (machine legacy opening = OPEN_DRIVE; pd_ctx {'pd_high': 7755.75, 'pd_low': 7702.75, 'pd_close': 7732.75, 'pd_context_status': 'OK'})
- 16:30 v2=UNKNOWN(<3 bars) pub=UNKNOWN gate=None canon=None
- 16:45 v2=OPEN_DRIVE/UP pub=UNKNOWN gate=None canon=None
- 16:50 v2=OPEN_AUCTION_IN/NEUTRAL pub=UNKNOWN gate=None canon=None
- 17:00 v2=OPEN_AUCTION_IN/NEUTRAL pub=Trend_Normal gate=Trend_Normal canon=None
- 17:10 v2=OPEN_AUCTION_IN/NEUTRAL pub=Variation gate=Trend_Normal canon=None [Trend_Normal->Normal_Variation]
- 17:20 v2=OPEN_AUCTION_IN/NEUTRAL pub=Variation gate=Variation canon=None
- 17:30 v2=OPEN_AUCTION_IN/NEUTRAL pub=Trend_Normal gate=Variation canon=Nonconviction
- 17:35 v2=OPEN_AUCTION_IN/NEUTRAL pub=Normal gate=Variation canon=Normal [Trend_Normal->Normal (PROVISIONAL)]
- 17:45 v2=OPEN_AUCTION_IN/NEUTRAL pub=Variation gate=Normal canon=Normal_Variation [Normal->Variation (PROVISIONAL)]
- 17:55 v2=OPEN_AUCTION_IN/NEUTRAL pub=Variation gate=Variation canon=Normal_Variation
- 19:25 v2=OPEN_AUCTION_IN/NEUTRAL pub=Neutral_Extreme gate=Variation canon=Neutral_Extreme [Variation->Neutral_Extreme (PROVISIONAL)]
- 19:35 v2=OPEN_AUCTION_IN/NEUTRAL pub=Neutral_Extreme gate=Neutral_Extreme canon=Neutral_Extreme
- 19:50 v2=OPEN_AUCTION_IN/NEUTRAL pub=Neutral_Center gate=Neutral_Extreme canon=Neutral_Center [Neutral_Extreme->Neutral_Center (PROVISIONAL)]
- 20:00 v2=OPEN_AUCTION_IN/NEUTRAL pub=Neutral_Extreme gate=Neutral_Center canon=Neutral_Extreme [Neutral_Center->Neutral_Extreme (PROVISIONAL)]
- 20:10 v2=OPEN_AUCTION_IN/NEUTRAL pub=Neutral_Extreme gate=Neutral_Extreme canon=Neutral_Extreme

**2026-08-28 · s=1** (machine legacy opening = OPEN_DRIVE; pd_ctx {'pd_high': 7755.75, 'pd_low': 7702.75, 'pd_close': 7732.75, 'pd_context_status': 'OK'})
- 16:30 v2=UNKNOWN(<3 bars) pub=UNKNOWN gate=None canon=None
- 16:45 v2=OPEN_DRIVE/UP pub=UNKNOWN gate=None canon=None
- 16:50 v2=OPEN_AUCTION_IN/NEUTRAL pub=UNKNOWN gate=None canon=None
- 17:00 v2=OPEN_AUCTION_IN/NEUTRAL pub=Trend_Normal gate=Trend_Normal canon=None
- 17:10 v2=OPEN_AUCTION_IN/NEUTRAL pub=Variation gate=Trend_Normal canon=None [Trend_Normal->Normal_Variation]
- 17:20 v2=OPEN_AUCTION_IN/NEUTRAL pub=Variation gate=Variation canon=None
- 17:30 v2=OPEN_AUCTION_IN/NEUTRAL pub=Trend_Normal gate=Variation canon=Nonconviction
- 17:35 v2=OPEN_AUCTION_IN/NEUTRAL pub=Trend_Normal gate=Variation canon=Normal [Trend_Normal->Normal pending Normal 1]
- 17:40 v2=OPEN_AUCTION_IN/NEUTRAL pub=Normal gate=Trend_Normal canon=Normal [Trend_Normal->Normal (PROVISIONAL)]
- 17:45 v2=OPEN_AUCTION_IN/NEUTRAL pub=Normal gate=Trend_Normal canon=Normal_Variation [Normal->Variation pending Variation 1]
- 17:50 v2=OPEN_AUCTION_IN/NEUTRAL pub=Variation gate=Normal canon=Normal_Variation [Normal->Variation (PROVISIONAL)]
- 18:00 v2=OPEN_AUCTION_IN/NEUTRAL pub=Variation gate=Variation canon=Normal_Variation
- 19:25 v2=OPEN_AUCTION_IN/NEUTRAL pub=Neutral_Extreme gate=Variation canon=Neutral_Extreme [Variation->Neutral_Extreme (PROVISIONAL)]
- 19:35 v2=OPEN_AUCTION_IN/NEUTRAL pub=Neutral_Extreme gate=Neutral_Extreme canon=Neutral_Extreme
- 19:50 v2=OPEN_AUCTION_IN/NEUTRAL pub=Neutral_Center gate=Neutral_Extreme canon=Neutral_Center [Neutral_Extreme->Neutral_Center (PROVISIONAL)]
- 20:00 v2=OPEN_AUCTION_IN/NEUTRAL pub=Neutral_Extreme gate=Neutral_Center canon=Neutral_Extreme [Neutral_Center->Neutral_Extreme (PROVISIONAL)]
- …

**2026-08-03 · s=0** (machine legacy opening = OPEN_DRIVE; pd_ctx {'pd_high': 7479.75, 'pd_low': 7462.75, 'pd_close': 7473.25, 'pd_context_status': 'OK'})
- 16:30 v2=UNKNOWN(<3 bars) pub=UNKNOWN gate=None canon=None
- 16:45 v2=OPEN_DRIVE/UP pub=UNKNOWN gate=None canon=None
- 17:00 v2=OPEN_DRIVE/UP pub=Trend_Normal gate=Trend_Normal canon=None
- 17:15 v2=OPEN_DRIVE/UP pub=Variation gate=Trend_Normal canon=None [Trend_Normal->Normal_Variation]
- 17:25 v2=OPEN_DRIVE/UP pub=Variation gate=Variation canon=None
- 17:30 v2=OPEN_DRIVE/UP pub=Normal gate=Variation canon=Normal [Trend_Normal->Normal (PROVISIONAL)]
- 17:40 v2=OPEN_DRIVE/UP pub=Normal gate=Normal canon=Normal
- 17:45 v2=OPEN_DRIVE/UP pub=Trend_Normal gate=Normal canon=Trend_Normal [Normal->Trend_Normal (CLASSIFIED)]
- 17:55 v2=OPEN_DRIVE/UP pub=Trend_Normal gate=Trend_Normal canon=Trend_Normal
- 21:35 v2=OPEN_DRIVE/UP pub=Variation gate=Trend_Normal canon=Normal_Variation [Trend_Normal->Variation (PROVISIONAL)]
- 21:45 v2=OPEN_DRIVE/UP pub=Variation gate=Variation canon=Normal_Variation

**2026-08-03 · s=1** (machine legacy opening = OPEN_DRIVE; pd_ctx {'pd_high': 7479.75, 'pd_low': 7462.75, 'pd_close': 7473.25, 'pd_context_status': 'OK'})
- 16:30 v2=UNKNOWN(<3 bars) pub=UNKNOWN gate=None canon=None
- 16:45 v2=OPEN_DRIVE/UP pub=UNKNOWN gate=None canon=None
- 17:00 v2=OPEN_DRIVE/UP pub=Trend_Normal gate=Trend_Normal canon=None
- 17:15 v2=OPEN_DRIVE/UP pub=Variation gate=Trend_Normal canon=None [Trend_Normal->Normal_Variation]
- 17:25 v2=OPEN_DRIVE/UP pub=Variation gate=Variation canon=None
- 17:30 v2=OPEN_DRIVE/UP pub=Trend_Normal gate=Variation canon=Normal [Trend_Normal->Normal pending Normal 1]
- 17:35 v2=OPEN_DRIVE/UP pub=Normal gate=Variation canon=Normal [Trend_Normal->Normal (PROVISIONAL)]
- 17:45 v2=OPEN_DRIVE/UP pub=Normal gate=Normal canon=Trend_Normal [Normal->Trend_Normal pending Trend_Normal 1]
- 17:50 v2=OPEN_DRIVE/UP pub=Trend_Normal gate=Normal canon=Trend_Normal [Normal->Trend_Normal (CLASSIFIED)]
- 18:00 v2=OPEN_DRIVE/UP pub=Trend_Normal gate=Trend_Normal canon=Trend_Normal
- 21:35 v2=OPEN_DRIVE/UP pub=Trend_Normal gate=Trend_Normal canon=Normal_Variation [Trend_Normal->Variation pending Variation 1]
- 21:40 v2=OPEN_DRIVE/UP pub=Variation gate=Trend_Normal canon=Normal_Variation [Trend_Normal->Variation (PROVISIONAL)]
- 21:50 v2=OPEN_DRIVE/UP pub=Variation gate=Variation canon=Normal_Variation

**2026-09-02 · s=0** (machine legacy opening = OPEN_DRIVE; pd_ctx {'pd_high': 7673.75, 'pd_low': 7621.5, 'pd_close': 7647.5, 'pd_context_status': 'OK'})
- 16:30 v2=UNKNOWN(<3 bars) pub=UNKNOWN gate=None canon=None
- 16:45 v2=OPEN_REJECTION_REVERSE/UP pub=UNKNOWN gate=None canon=None
- 16:50 v2=OPEN_AUCTION_IN/NEUTRAL pub=UNKNOWN gate=None canon=None
- 17:00 v2=OPEN_AUCTION_IN/NEUTRAL pub=Trend_Normal gate=Trend_Normal canon=None
- 17:20 v2=OPEN_AUCTION_IN/NEUTRAL pub=Variation gate=Trend_Normal canon=None [Trend_Normal->Normal_Variation]
- 17:30 v2=OPEN_AUCTION_IN/NEUTRAL pub=Normal gate=Variation canon=Normal [Trend_Normal->Normal (PROVISIONAL)]
- 17:40 v2=OPEN_AUCTION_IN/NEUTRAL pub=Variation gate=Normal canon=Normal_Variation [Normal->Variation (PROVISIONAL)]
- 17:50 v2=OPEN_AUCTION_IN/NEUTRAL pub=Variation gate=Variation canon=Normal_Variation

**2026-09-02 · s=1** (machine legacy opening = OPEN_DRIVE; pd_ctx {'pd_high': 7673.75, 'pd_low': 7621.5, 'pd_close': 7647.5, 'pd_context_status': 'OK'})
- 16:30 v2=UNKNOWN(<3 bars) pub=UNKNOWN gate=None canon=None
- 16:45 v2=OPEN_REJECTION_REVERSE/UP pub=UNKNOWN gate=None canon=None
- 16:50 v2=OPEN_AUCTION_IN/NEUTRAL pub=UNKNOWN gate=None canon=None
- 17:00 v2=OPEN_AUCTION_IN/NEUTRAL pub=Trend_Normal gate=Trend_Normal canon=None
- 17:20 v2=OPEN_AUCTION_IN/NEUTRAL pub=Variation gate=Trend_Normal canon=None [Trend_Normal->Normal_Variation]
- 17:30 v2=OPEN_AUCTION_IN/NEUTRAL pub=Trend_Normal gate=Variation canon=Normal [Trend_Normal->Normal pending Normal 1]
- 17:35 v2=OPEN_AUCTION_IN/NEUTRAL pub=Normal gate=Variation canon=Normal [Trend_Normal->Normal (PROVISIONAL)]
- 17:40 v2=OPEN_AUCTION_IN/NEUTRAL pub=Normal gate=Variation canon=Normal_Variation [Normal->Variation pending Variation 1]
- 17:45 v2=OPEN_AUCTION_IN/NEUTRAL pub=Variation gate=Normal canon=Normal_Variation [Normal->Variation (PROVISIONAL)]
- 17:55 v2=OPEN_AUCTION_IN/NEUTRAL pub=Variation gate=Variation canon=Normal_Variation

**2026-08-04 · s=0** (machine legacy opening = OPEN_DRIVE; pd_ctx {'pd_high': 7638.5, 'pd_low': 7542.75, 'pd_close': 7628.5, 'pd_context_status': 'OK'} · pd context substituted from v9_bars_5min_woodies (legacy v9_bars_5min purged for this date))
- 16:30 v2=UNKNOWN(<3 bars) pub=UNKNOWN gate=None canon=None
- 16:45 v2=OPEN_AUCTION_OUT/NEUTRAL pub=UNKNOWN gate=None canon=None
- 17:00 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Trend_Normal gate=Trend_Normal canon=None
- 17:10 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Variation gate=Trend_Normal canon=None [Trend_Normal->Normal_Variation]
- 17:20 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Variation gate=Variation canon=None
- 17:30 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Normal gate=Variation canon=Normal [Trend_Normal->Normal (PROVISIONAL)]
- 17:40 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Normal gate=Normal canon=Normal
- 17:45 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Variation gate=Normal canon=Normal_Variation [Normal->Variation (PROVISIONAL)]
- 17:55 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Variation gate=Variation canon=Normal_Variation
- 19:35 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Trend_Normal gate=Variation canon=Trend_Normal [Variation->Trend_Normal (CLASSIFIED)]
- 19:45 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Trend_Normal gate=Trend_Normal canon=Trend_Normal

**2026-08-04 · s=1** (machine legacy opening = OPEN_DRIVE; pd_ctx {'pd_high': 7638.5, 'pd_low': 7542.75, 'pd_close': 7628.5, 'pd_context_status': 'OK'} · pd context substituted from v9_bars_5min_woodies (legacy v9_bars_5min purged for this date))
- 16:30 v2=UNKNOWN(<3 bars) pub=UNKNOWN gate=None canon=None
- 16:45 v2=OPEN_AUCTION_OUT/NEUTRAL pub=UNKNOWN gate=None canon=None
- 17:00 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Trend_Normal gate=Trend_Normal canon=None
- 17:10 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Variation gate=Trend_Normal canon=None [Trend_Normal->Normal_Variation]
- 17:20 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Variation gate=Variation canon=None
- 17:30 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Trend_Normal gate=Variation canon=Normal [Trend_Normal->Normal pending Normal 1]
- 17:35 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Normal gate=Variation canon=Normal [Trend_Normal->Normal (PROVISIONAL)]
- 17:45 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Normal gate=Normal canon=Normal_Variation [Normal->Variation pending Variation 1]
- 17:50 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Variation gate=Normal canon=Normal_Variation [Normal->Variation (PROVISIONAL)]
- 18:00 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Variation gate=Variation canon=Normal_Variation
- 19:35 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Variation gate=Variation canon=Trend_Normal [Variation->Trend_Normal pending Trend_Normal 1]
- 19:40 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Trend_Normal gate=Variation canon=Trend_Normal [Variation->Trend_Normal (CLASSIFIED)]
- 19:50 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Trend_Normal gate=Trend_Normal canon=Trend_Normal

**2026-09-09 · s=0** (machine legacy opening = OPEN_DRIVE; pd_ctx {'pd_high': 7717.75, 'pd_low': 7672.25, 'pd_close': 7678.5, 'pd_context_status': 'OK'})
- 16:30 v2=UNKNOWN(<3 bars) pub=UNKNOWN gate=None canon=None
- 16:45 v2=OPEN_AUCTION_OUT/NEUTRAL pub=UNKNOWN gate=None canon=None
- 17:00 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Trend_Normal gate=Trend_Normal canon=None
- 17:10 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Variation gate=Trend_Normal canon=None [Trend_Normal->Normal_Variation]
- 17:20 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Variation gate=Variation canon=None
- 17:30 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Normal gate=Variation canon=Normal [Trend_Normal->Normal (PROVISIONAL)]
- 17:40 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Normal gate=Normal canon=Normal
- 18:10 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Variation gate=Normal canon=Normal_Variation [Normal->Variation (PROVISIONAL)]
- 18:20 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Variation gate=Variation canon=Normal_Variation

**2026-09-09 · s=1** (machine legacy opening = OPEN_DRIVE; pd_ctx {'pd_high': 7717.75, 'pd_low': 7672.25, 'pd_close': 7678.5, 'pd_context_status': 'OK'})
- 16:30 v2=UNKNOWN(<3 bars) pub=UNKNOWN gate=None canon=None
- 16:45 v2=OPEN_AUCTION_OUT/NEUTRAL pub=UNKNOWN gate=None canon=None
- 17:00 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Trend_Normal gate=Trend_Normal canon=None
- 17:10 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Variation gate=Trend_Normal canon=None [Trend_Normal->Normal_Variation]
- 17:20 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Variation gate=Variation canon=None
- 17:30 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Trend_Normal gate=Variation canon=Normal [Trend_Normal->Normal pending Normal 1]
- 17:35 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Normal gate=Variation canon=Normal [Trend_Normal->Normal (PROVISIONAL)]
- 17:45 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Normal gate=Normal canon=Normal
- 18:10 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Normal gate=Normal canon=Normal_Variation [Normal->Variation pending Variation 1]
- 18:15 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Variation gate=Normal canon=Normal_Variation [Normal->Variation (PROVISIONAL)]
- 18:25 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Variation gate=Variation canon=Normal_Variation

**2026-09-01 · s=0** (machine legacy opening = OPEN_DRIVE; pd_ctx {'pd_high': 7704.25, 'pd_low': 7674.75, 'pd_close': 7701.5, 'pd_context_status': 'OK'})
- 16:30 v2=UNKNOWN(<3 bars) pub=UNKNOWN gate=None canon=None
- 16:45 v2=OPEN_AUCTION_OUT/NEUTRAL pub=UNKNOWN gate=None canon=None
- 16:50 v2=OPEN_REJECTION_REVERSE/UP pub=UNKNOWN gate=None canon=None
- 16:55 v2=OPEN_AUCTION_OUT/NEUTRAL pub=UNKNOWN gate=None canon=None
- 17:00 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Trend_Normal gate=Trend_Normal canon=None
- 17:30 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Normal gate=Trend_Normal canon=Normal [Trend_Normal->Normal (PROVISIONAL)]
- 17:35 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Variation gate=Trend_Normal canon=Normal_Variation [Normal->Variation (PROVISIONAL)]
- 17:45 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Variation gate=Variation canon=Normal_Variation
- 21:30 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Neutral_Extreme gate=Variation canon=Neutral_Extreme [Variation->Neutral_Extreme (PROVISIONAL)]
- 21:40 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Neutral_Extreme gate=Neutral_Extreme canon=Neutral_Extreme
- 22:00 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Neutral_Center gate=Neutral_Extreme canon=Neutral_Center [Neutral_Extreme->Neutral_Center (PROVISIONAL)]
- 22:10 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Neutral_Center gate=Neutral_Center canon=Neutral_Center

**2026-09-01 · s=1** (machine legacy opening = OPEN_DRIVE; pd_ctx {'pd_high': 7704.25, 'pd_low': 7674.75, 'pd_close': 7701.5, 'pd_context_status': 'OK'})
- 16:30 v2=UNKNOWN(<3 bars) pub=UNKNOWN gate=None canon=None
- 16:45 v2=OPEN_AUCTION_OUT/NEUTRAL pub=UNKNOWN gate=None canon=None
- 16:50 v2=OPEN_REJECTION_REVERSE/UP pub=UNKNOWN gate=None canon=None
- 16:55 v2=OPEN_AUCTION_OUT/NEUTRAL pub=UNKNOWN gate=None canon=None
- 17:00 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Trend_Normal gate=Trend_Normal canon=None
- 17:30 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Trend_Normal gate=Trend_Normal canon=Normal [Trend_Normal->Normal pending Normal 1]
- 17:35 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Trend_Normal gate=Trend_Normal canon=Normal_Variation [Trend_Normal->Variation pending Variation 1]
- 17:40 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Variation gate=Trend_Normal canon=Normal_Variation [Trend_Normal->Variation (PROVISIONAL)]
- 17:50 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Variation gate=Variation canon=Normal_Variation
- 21:30 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Neutral_Extreme gate=Variation canon=Neutral_Extreme [Variation->Neutral_Extreme (PROVISIONAL)]
- 21:40 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Neutral_Extreme gate=Neutral_Extreme canon=Neutral_Extreme
- 22:00 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Neutral_Center gate=Neutral_Extreme canon=Neutral_Center [Neutral_Extreme->Neutral_Center (PROVISIONAL)]
- 22:10 v2=OPEN_AUCTION_OUT/NEUTRAL pub=Neutral_Center gate=Neutral_Center canon=Neutral_Center


### 8-T5 · 2026-09-09 phase C: what DAYTYPE_RECLASS_STABILITY_V1 changed

| IL | setup | dir | s=0: label → verdict | s=1: label → verdict |
|---|---|---|---|---|
| 17:44 | ZLR | LONG | Normal → dalton_intent:kind | Variation → shadow |
| 18:20 | INITIATIVE_SHORT | SHORT | Variation → entry_location_quality | None → (not emitted) |

2 route(s) differ; fires s=0: [('19:05', 'VEGAS', -40.0), ('20:15', 'DOUBLE_BOTTOM_EE_LONG', -118.75), ('20:55', 'BULL_FLAG_LONG', -131.25)] · fires s=1: [('19:05', 'VEGAS', -40.0), ('20:15', 'DOUBLE_BOTTOM_EE_LONG', -118.75), ('20:55', 'BULL_FLAG_LONG', -131.25)]

### 8-T6 · the two 09-09 live trades re-routed through each chain

| variant | #1328 VEGAS LONG 19:05 | #1343 BULL_FLAG LONG 20:55 | #1337 DOUBLE_BOTTOM_EE 20:15 |
|---|---|---|---|
| head s=0 | ot=UNKNOWN dt=Variation → LIVE CMD ×2 | ot=UNKNOWN dt=Variation → duplicate_fire | ot=UNKNOWN dt=Variation → duplicate_fire |
| head s=1 | ot=UNKNOWN dt=Variation → LIVE CMD ×2 | ot=UNKNOWN dt=Variation → duplicate_fire | ot=UNKNOWN dt=Variation → duplicate_fire |
| fixed s=0 | ot=OPEN_AUCTION_OUT dt=Variation → LIVE CMD ×2 | ot=OPEN_AUCTION_OUT dt=Variation → duplicate_fire | ot=OPEN_AUCTION_OUT dt=Variation → duplicate_fire |
| fixed s=1 | ot=OPEN_AUCTION_OUT dt=Variation → LIVE CMD ×2 | ot=OPEN_AUCTION_OUT dt=Variation → duplicate_fire | ot=OPEN_AUCTION_OUT dt=Variation → duplicate_fire |
| headoe s=1 oe | ot=UNKNOWN dt=Variation → LIVE CMD ×2 | ot=UNKNOWN dt=Variation → duplicate_fire | ot=UNKNOWN dt=Variation → duplicate_fire |
| fixedoe s=1 oe | ot=OPEN_AUCTION_OUT dt=Variation → LIVE CMD ×2 | ot=OPEN_AUCTION_OUT dt=Variation → duplicate_fire | ot=OPEN_AUCTION_OUT dt=Variation → duplicate_fire |
| fixedoe s=0 oe | ot=OPEN_AUCTION_OUT dt=Variation → LIVE CMD ×2 | ot=OPEN_AUCTION_OUT dt=Variation → duplicate_fire | ot=OPEN_AUCTION_OUT dt=Variation → duplicate_fire |

### 8-R · run lines (`batch_full.out`, 48 runs, one process at a time)

```
[fwd] 2026-08-28 head push=firstpush routes=64 blocked=61 live_cmds=1 -> 0828_head_s0_firstpush.json
[fwd] 2026-08-03 head push=firstpush routes=38 blocked=22 live_cmds=3 -> 0803_head_s0_firstpush.json
[fwd] 2026-09-02 head push=firstpush routes=48 blocked=36 live_cmds=3 -> 0902_head_s0_firstpush.json
[fwd] 2026-08-04 head push=firstpush routes=21 blocked=20 live_cmds=0 -> 0804_head_s0_firstpush.json
[fwd] 2026-09-09 head push=firstpush routes=50 blocked=43 live_cmds=3 -> 0909_head_s0_firstpush.json
[fwd] 2026-09-01 head push=firstpush routes=36 blocked=27 live_cmds=3 -> 0901_head_s0_firstpush.json
[fwd] 2026-08-28 head push=firstpush routes=64 blocked=61 live_cmds=1 -> 0828_head_s1_firstpush.json
[fwd] 2026-08-03 head push=firstpush routes=38 blocked=22 live_cmds=3 -> 0803_head_s1_firstpush.json
[fwd] 2026-09-02 head push=firstpush routes=48 blocked=36 live_cmds=3 -> 0902_head_s1_firstpush.json
[fwd] 2026-08-04 head push=firstpush routes=20 blocked=18 live_cmds=0 -> 0804_head_s1_firstpush.json
[fwd] 2026-09-09 head push=firstpush routes=49 blocked=41 live_cmds=3 -> 0909_head_s1_firstpush.json
[fwd] 2026-09-01 head push=firstpush routes=36 blocked=27 live_cmds=3 -> 0901_head_s1_firstpush.json
[fwd] 2026-08-28 headoe push=firstpush routes=66 blocked=62 live_cmds=2 -> 0828_headoe_s1_firstpush.json
[fwd] 2026-08-03 headoe push=firstpush routes=38 blocked=22 live_cmds=3 -> 0803_headoe_s1_firstpush.json
[fwd] 2026-09-02 headoe push=firstpush routes=51 blocked=39 live_cmds=3 -> 0902_headoe_s1_firstpush.json
[fwd] 2026-08-04 headoe push=firstpush routes=21 blocked=19 live_cmds=0 -> 0804_headoe_s1_firstpush.json
[fwd] 2026-09-09 headoe push=firstpush routes=51 blocked=41 live_cmds=4 -> 0909_headoe_s1_firstpush.json
[fwd] 2026-09-01 headoe push=firstpush routes=39 blocked=28 live_cmds=4 -> 0901_headoe_s1_firstpush.json
[fwd] 2026-08-28 headoe push=firstpush routes=66 blocked=62 live_cmds=2 -> 0828_headoe_s0_firstpush.json
[fwd] 2026-08-03 headoe push=firstpush routes=38 blocked=22 live_cmds=3 -> 0803_headoe_s0_firstpush.json
[fwd] 2026-09-02 headoe push=firstpush routes=51 blocked=39 live_cmds=3 -> 0902_headoe_s0_firstpush.json
[fwd] 2026-08-04 headoe push=firstpush routes=22 blocked=21 live_cmds=0 -> 0804_headoe_s0_firstpush.json
[fwd] 2026-09-09 headoe push=firstpush routes=52 blocked=43 live_cmds=4 -> 0909_headoe_s0_firstpush.json
[fwd] 2026-09-01 headoe push=firstpush routes=39 blocked=28 live_cmds=4 -> 0901_headoe_s0_firstpush.json
[fwd] 2026-08-28 fixed push=firstpush routes=64 blocked=60 live_cmds=1 -> 0828_fixed_s1_firstpush.json
[fwd] 2026-08-03 fixed push=firstpush routes=38 blocked=20 live_cmds=1 -> 0803_fixed_s1_firstpush.json
[fwd] 2026-09-02 fixed push=firstpush routes=48 blocked=36 live_cmds=3 -> 0902_fixed_s1_firstpush.json
[fwd] 2026-08-04 fixed push=firstpush routes=20 blocked=17 live_cmds=1 -> 0804_fixed_s1_firstpush.json
[fwd] 2026-09-09 fixed push=firstpush routes=49 blocked=40 live_cmds=3 -> 0909_fixed_s1_firstpush.json
[fwd] 2026-09-01 fixed push=firstpush routes=36 blocked=27 live_cmds=3 -> 0901_fixed_s1_firstpush.json
[fwd] 2026-08-28 fixed push=firstpush routes=64 blocked=60 live_cmds=1 -> 0828_fixed_s0_firstpush.json
[fwd] 2026-08-03 fixed push=firstpush routes=38 blocked=20 live_cmds=1 -> 0803_fixed_s0_firstpush.json
[fwd] 2026-09-02 fixed push=firstpush routes=48 blocked=36 live_cmds=3 -> 0902_fixed_s0_firstpush.json
[fwd] 2026-08-04 fixed push=firstpush routes=21 blocked=19 live_cmds=1 -> 0804_fixed_s0_firstpush.json
[fwd] 2026-09-09 fixed push=firstpush routes=50 blocked=42 live_cmds=3 -> 0909_fixed_s0_firstpush.json
[fwd] 2026-09-01 fixed push=firstpush routes=36 blocked=27 live_cmds=3 -> 0901_fixed_s0_firstpush.json
[fwd] 2026-08-28 fixedoe push=firstpush routes=66 blocked=62 live_cmds=1 -> 0828_fixedoe_s1_firstpush.json
[fwd] 2026-08-03 fixedoe push=firstpush routes=38 blocked=20 live_cmds=1 -> 0803_fixedoe_s1_firstpush.json
[fwd] 2026-09-02 fixedoe push=firstpush routes=51 blocked=39 live_cmds=3 -> 0902_fixedoe_s1_firstpush.json
[fwd] 2026-08-04 fixedoe push=firstpush routes=21 blocked=18 live_cmds=1 -> 0804_fixedoe_s1_firstpush.json
[fwd] 2026-09-09 fixedoe push=firstpush routes=51 blocked=42 live_cmds=3 -> 0909_fixedoe_s1_firstpush.json
[fwd] 2026-09-01 fixedoe push=firstpush routes=39 blocked=29 live_cmds=4 -> 0901_fixedoe_s1_firstpush.json
[fwd] 2026-08-28 fixedoe push=firstpush routes=66 blocked=62 live_cmds=1 -> 0828_fixedoe_s0_firstpush.json
[fwd] 2026-08-03 fixedoe push=firstpush routes=38 blocked=20 live_cmds=1 -> 0803_fixedoe_s0_firstpush.json
[fwd] 2026-09-02 fixedoe push=firstpush routes=51 blocked=39 live_cmds=3 -> 0902_fixedoe_s0_firstpush.json
[fwd] 2026-08-04 fixedoe push=firstpush routes=22 blocked=20 live_cmds=1 -> 0804_fixedoe_s0_firstpush.json
[fwd] 2026-09-09 fixedoe push=firstpush routes=52 blocked=44 live_cmds=3 -> 0909_fixedoe_s0_firstpush.json
[fwd] 2026-09-01 fixedoe push=firstpush routes=39 blocked=29 live_cmds=4 -> 0901_fixedoe_s0_firstpush.json
```

### 8-P · targeted regression on the patched worktree

```
$ cd /tmp/mems26_fwd && python3 -m pytest -q tests/v9/regression/test_opening_entry_production_path.py tests/v9/regression/test_dalton_playbook_identity.py backend/v9/tests/test_dalton_playbook.py tests/v9/regression/test_daytype_reclass_stability.py
63 passed, 2 warnings in 1.08s
```

### 8-L · the live log lines behind F1 (`/tmp/backend.err.log`)

```
2026-09-07 16:40:05 [WARNING] [mems26.systems.five_min] [FiveMin] OPENING_FIRST_TRADE_STRICT held DRIVE SHORT — last bar did not confirm SHORT (o=7712.75 c=7713.0)
2026-09-07 16:45:02 [WARNING] [mems26.systems.five_min] [FiveMin] OPENING_FIRST_TRADE_STRICT held DRIVE SHORT — last bar did not confirm SHORT (o=7713.25 c=7713.5)
2026-09-07 16:50:03 [INFO] [mems26.systems.five_min] [FiveMin] OPENING_ENTRY DRIVE SHORT entry=7714.00 stop=7716.75 t1=7709.88 (live-eligible)
2026-09-08 16:35:05 [WARNING] [mems26.systems.five_min] [FiveMin] OPENING_FIRST_TRADE_STRICT held DRIVE SHORT — only 2 bars < 3 — confirmation bar required
2026-09-08 16:40:08 [INFO] [mems26.systems.five_min] [FiveMin] OPENING_ENTRY DRIVE SHORT entry=7701.00 stop=7716.00 t1=7678.50 (live-eligible)
DB (v9_bars_5min_woodies, IL):
 09-07 16:40 o=7712.75 h=7714.25 l=7711.75 c=7713.50 · 16:45 o=7713.25 c=7714.50 · 16:50 o=7714.50 c=7714.25 · 16:30 range 7714.00–7717.25
 09-08 16:30 o=7711.25 h=7717.75 l=7707.00 c=7708.75 · 16:40 o=7702.00 c=7693.25
```

*Verified 2026-09-10 10:00–11:15 IL on the MacBook. Worktree `/tmp/mems26_fwd` removed after this report; live tree untouched (`git status` in the live repo shows only this report as new).*
