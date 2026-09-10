# REACTIVE ON VARIATION — replay of the `require_with_trend × Variation` cell

**Date:** 2026-09-10, written 10:02–10:35 IL, read-only (no code, `.env`, flag, service or DB write; the only file
created is this report + scratch scripts in the Cowork session outputs folder).
**Question (from the morning doctrine walk, `DOCTRINE_WALK_ENTRIES_2026-09-10.md` §G1):** if `require_with_trend`
(`config/daytype_playbook.yaml:188`) did NOT apply to REACTIVE on Variation days — everything else unchanged,
`DALTON_PLAYBOOK_V1=1` as live — what would the September REACTIVE setups have done, and the whole broker-priced history?
**Repo HEAD:** `c3a5323a` · DB: local Postgres (`v9_trades`, `v9_five_min_setups`, `v9_bars_5min_woodies`, `v9_tpo_sessions`,
`v9_tpo_history`, `v9_day_type_history`) · decisions: `~/SierraChart_Data/v9_export/decisions_archive/*.jsonl` (2026-07-22 → 09-08)
+ `gateway_decisions.jsonl` (09-09).

---

## 0 · Answer in 25 lines

**Not decidable — and the premise is stale.**

| window | setups | Variation-label at the moment | blocked ONLY by the Variation rule | still blocked by a later gate | **admitted by the relaxation** | T1 / STOP / open | win % | **Σ$ first-touch (live bracket, live sizing)** | Σ$ held-with-stop to close |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|
| **September 09-01 → 09-10** (7 sessions) | 17 | 13 | 11 | 2 (live_slot ×2) | **9** | 2 / 4 / 3 | 33 % | **−$422.50** | −$935.00 |
| **07-07 → 08-28** (37 sessions) | 312 | 193 | 130 | 47 (live_slot 31 · entry_not_confirmed 17 · risk_budget 4) | **83** | 47 / 34 / 2 | 58 % | **+$765.00** | −$5,716.25 |
| all 07-07 → 09-10 (45 sessions) | 338 | 209 | 141 | 49 | 92 | 49 / 38 / 5 | 56 % | +$342.50 | −$6,651.25 |

**WITH-extension vs AGAINST-extension on Variation days (admitted setups, first-touch $, live bracket):**

| arm | Jul (07-07→31) | Aug (08-01→28) | **Sep** | 07-07→08-28 | all |
|---|---:|---:|---:|---:|---:|
| **WITH** the day's extension | +$1,176.25 (n=27, 68 %) | −$73.75 (n=16, 56 %) | **−$341.25 (n=3, 0 %)** | +$1,102.50 (n=43, 63 %) | +$761.25 (n=46, 61 %) |
| **AGAINST** the extension (the Dalton warning) | −$1,356.25 (n=30, 40 %) | +$1,018.75 (n=10, 90 %) | **−$81.25 (n=6, 50 %)** | −$337.50 (n=40, 53 %) | −$418.75 (n=46, 52 %) |

Neither arm keeps its sign for two consecutive months; September is negative on both arms with n=3 / n=6. The
model is calibrated: on the 13 broker-priced live REACTIVE trades it gives Σ $733.75 vs Σ broker $722.50 (§5).

**Count still blocked by later gates:** September 2 of 11 (both `live_slot_occupied` — a live trade was open);
07-07→08-28 47 of 130 (31 live-slot, 17 `entry_not_confirmed`, 4 RISK_BUDGET size-reject).

**Trade-off vs the actual September book:** the book earned **−$605.00** on 18 broker-priced trades in the same 7 sessions
(§6). The 9 relaxed REACTIVE would have added **−$422.50** → −$1,027.50; no session is rescued (09-01 −162.50 · 09-03 −210.00
· 09-04 +112.50 · 09-07 −6.25 · 09-09 −156.25).

**The rule change I would put in front of Michael: none on the Variation cell — "not decidable, n too small (n=9, −$422.50)
and sign-unstable across months".** What does go to Michael are two code facts (§1): (a) `require_with_trend` at
`daytype_playbook.yaml:188` is **dead code under the live flag set** — `trading_gateway.py:1419` skips the whole
`daytype_playbook` when `DALTON_PLAYBOOK_V1=1` (live since 09-09 ~16:55), so the question has to be re-asked about
`config/dalton_playbook.yaml:128-134`; (b) in that gate the direction hint **never resolves** (`trading_gateway.py:1136-1142`
reads the plan's strategy string `with_extension`, not `dir_bias`), so every phase-C decision carries `bias=BOTH` — REACTIVE
is refused in **both** directions on Variation, BREAK is admitted in both, and the `kinds_apply_to=counter_bias_only` ruling of
09.09 11:15 has never engaged (0 `dalton_intent:bias` rows in the entire archive, 14/14 kind-blocks on 09-09 say `bias=BOTH`).

---

## 1 · The premise, checked against the live chain (file:line + archive)

1. **`DAYTYPE_PLAYBOOK` is not in today's chain.** `backend/v9/gateway/trading_gateway.py:1419`:
   `if (not _dp_active and os.getenv("DAYTYPE_PLAYBOOK", "0") …)` where `_dp_active = DALTON_PLAYBOOK_V1` (`:1061`).
   Same guard on `location_gate` (`:1785`) and `direction_compass` (`:2257`). `.env`: `DALTON_PLAYBOOK_V1=1`
   (`config/RULED_FLAGS.yaml:75`: ruled 09.09 11:15, switched on 09.09 ~16:55 in the RTH restart).
   Archive per day, `blocked_by` counts:
   ```
   09-07 {'extreme_chase_guard': 8, 'None': 7, 'awaiting_release': 5, 'daytype_playbook': 5, 'direction_compass': 2, 'entry_location_quality': 2, 'rr_entry_gate': 2, 'cold_start_guard': 1, 'location_gate': 1}
   09-08 {'None': 17, 'rr_entry_gate': 17, 'eod_entry_cutoff': 15, 'direction_compass': 9, 'location_gate': 8, 'awaiting_release': 6, 'cold_start_guard': 3, 'daytype_playbook': 2, 'entry_not_confirmed': 1, 'rr_hard_floor': 1}
   09-09 {'dalton_intent:stand_down': 26, 'dalton_intent:kind': 14, 'None': 12, 'entry_location_quality': 5, 'rr_entry_gate': 3, 'extreme_chase_guard': 2, 'cold_start_guard': 1, 'session_gate_closed': 1}
   ```
   → `daytype_playbook` / `location_gate` / `direction_compass`: **0 blocks on 09-09**. The 7 September REACTIVE
   `daytype_playbook` blocks (09-02 ×2, 09-03 ×2, 09-07 ×3) all predate the switch.

2. **What blocks REACTIVE on Variation today.** `config/dalton_playbook.yaml:128-134` (phase C, `day_type in
   [Variation, Normal_Variation]` → `bias: extension_direction_once_then_BOTH`, `entry_kinds: [BREAK, VALUE_RETURN]`)
   + `backend/v9/services/dalton_playbook.py:184-201` (`kinds_apply_to=counter_bias_only`: with a LONG/SHORT bias the
   kinds list blocks only counter-bias entries; under `BOTH` it blocks everything not listed). REACTIVE_* → `EDGE_FADE`
   (`dalton_playbook.yaml:34-35`). The 09-09 20:40 REACTIVE_SHORT @7644.25:
   ```
   "blocked_by": "dalton_intent:kind", "reason": "counter-bias entry_kind=EDGE_FADE not in ['BREAK', 'VALUE_RETURN'] (phase=C cond=day_type in [Variation, Normal_Variation] bias=BOTH)"
   ```
3. **Why `bias` is always BOTH.** `trading_gateway.py:1136-1142`: `_dp_d = _resolve_live_cls().get("direction")`,
   accepted only if in `("UP","LONG")`/`("DOWN","SHORT")`. `direction` in the classify result is the plan STRATEGY string
   (`daytype_classifier.py:63-64` → `config/daytype_trading_plan.yaml:107 direction: with_extension`, `:95 fade_both`);
   the UP/DOWN read is `dir_bias` (`daytype_classifier.py:152-173`), which nothing passes to `intent()`. So
   `_resolve_bias("extension_direction…", direction_hint=None)` → `"BOTH"` (`dalton_playbook.py:97-98`), same for
   `trend_direction` on Trend days. Evidence: every `dalton_intent` reason in the 09-09 file:
   ```
   19 "phase=D cond=default bias=NONE"
   11 "counter-bias entry_kind=X not in ['EDGE_FADE', 'VALUE_RETURN'] (phase=C cond=day_type == Normal bias=BOTH)"
    7 "phase=B cond=default bias=NONE"
    3 "counter-bias entry_kind=X not in ['BREAK', 'VALUE_RETURN'] (phase=C cond=day_type in [Variation, Normal_Variation] bias=BOTH)"
   ```
   and `grep -o '"blocked_by": "dalton_intent:[a-z_]*"' archive/* | sort | uniq -c` → `14 kind · 26 stand_down · 0 bias`.
   **Consequence for today:** on a Variation label the live gate is not "REACTIVE with-trend only" — it is "no REACTIVE at all,
   either direction; BREAK either direction". That is the rule this replay relaxes (§3).

4. **A dead limb found on the way (informational, no trading change proposed):** `trading_gateway.py:1906`
   `from backend.v9.shared.atr import current_atr14` → `ImportError: cannot import name 'current_atr14'` (the symbol lives in
   `systems/target_spacing.py:359` and `systems/mae_scratch.py:137`). The `except: pass` leaves `_elq_atr=None`, so the
   `expensive_stop` test of ENTRY_LOCATION_QUALITY has never executed live: archive reasons = `103 chaser · 4 beyond_value ·
   0 expensive_stop`. The replay mirrors that (chaser limb only).

---

## 2 · Universe — REACTIVE setups 2026-07-07 → 09-10, deduplicated

Sources merged on `(session_ET, direction, entry_price, signal-bar ts)` — `v9_five_min_setups` (339 rows, the detector's own
record; `ts` = signal-bar open, entry = its close), `v9_trades` all modes (74 rows incl. the T-219 twins), decisions archive
(3,571 REACTIVE gate rows from 07-22 18:31 UTC).

```
raw rows: setups=339 trades=74 decisions=3571 (decision archive from 2026-07-22T18:31:07+00:00)
unmatched (no setups row): trades=3 decisions=357
UNIQUE keys (session,dir,entry,signal-bar): 696   by month: {'2026-07': 373, '2026-08': 306, '2026-09': 17}
```
The 357 decision-only keys are **pytest fixture pollution**, not market setups: the same entries recur across days and at
04:00–13:00 IL (`7503.00 / 7508.75 / 7530.00 / 7537.75 / 7589.50 / 7591.00 / 7600.00 / 5250.00`; cf. `conftest.py` "510
phantom lines"; guard added 08-19). Dropped. **Real universe = 339 keys** (all inside RTH 16:xx–22:xx IL), 430 distinct
(session, direction, signal-bar) groups because of T-252 forming/closed re-runs (e.g. 09-07 17:00 bar: 7712.75 at 17:00:07,
7710.75 at 17:05:03 — kept as two keys per the instructed key, so counts are upper bounds of "setups"):

```
real keys: 339   sessions: 44
2026-07 sessions: 18 setups: 224 per session: 12.4     ← old detector regime
2026-08 sessions: 19 setups:  97 per session:  5.1
2026-09 sessions:  7 setups:  17 per session:  2.4     ← today's detector
by IL hour: {'16': 16, '17': 90, '18': 85, '19': 55, '20': 40, '21': 26, '22': 27}
historical first blocker  2026-07 [('None', 142), ('daytype_playbook', 53), ('location_gate', 11), ('awaiting_release', 11), ('eod_entry_cutoff', 7), ('lsma_flat', 1)]
                          2026-08 [('daytype_playbook', 29), ('None', 18), ('awaiting_release', 16), ('location_gate', 8), ('eod_entry_cutoff', 7), ('lsma_flat', 5), …]
                          2026-09 [('daytype_playbook', 7), ('awaiting_release', 2), ('location_gate', 2), ('eod_entry_cutoff', 2), ('None', 2), ('direction_compass', 1), ('dalton_intent:kind', 1)]
```
(`None` = fired shadow/live, or pre-archive.) Note the 5× drop in detection density July → September: the July universe
measures a detector that no longer exists (S2 thresholds/VSA changed in August), which is why the windows are also split by month.

## 3 · Method

* **Label at the moment** — `classify_session` (`backend/v9/systems/day_type/classifier_core.py`) on the session's RTH bars up
  to and including the signal bar, IB = first 12 RTH bars (6-bar provisional IB before lock, exactly as `classify_replay`),
  prior-day PDH/PDL from bars, prior VAH/VAL from `v9_tpo_sessions`, `v9_tpo_history` POCs up to the bar, `vol_ratio` =
  volume-so-far / median complete RTH day (as `backend/main.py:483-487`), Neutral hysteresis carried per bar. Live S1 flags
  loaded from `.env`; `DELTA_FEATURES_V1` unset for the replay (it reads *today's* `cumulative_delta.json`). Checks: bars-IB
  label == Sierra-IB label on **338/338**; `day_type_at_fire` is NULL on every setups row (nothing recorded to compare);
  the live `get_live_day_type()` hysteresis/antiflap/prelock overlays are **not** reproduced. The classifier names the
  Variation state `Normal_Variation`; the dalton row matches both names.
* **Extension direction at the moment** — mechanical: `max(high) − IBH` vs `IBL − min(low)` over bars up to the signal bar
  (IB = first 12 bars); larger positive side wins; before IB lock → NONE. WITH = LONG on UP / SHORT on DOWN; AGAINST =
  the opposite. The classifier's `dir_bias`/`accepted_break` are recorded alongside (raw JSON).
* **Bracket scored = the live one.** `STEP_SCALED_LADDER_V1=1` (`trading_gateway.py:3493-3555`) overrides every setup's
  stop/T1/T2/T3 that reaches it (`grep -c "STEP_SCALED_LADDER OVERRODE" backend.err.log` = 52, `KEPT` = 2). It is a pure
  function of session bars (`five_min/step_scaled_ladder.py:169-231`: stop = max(4, 0.6 × median zigzag step), T1 floored at
  `rr_min × stop`), so it is replayed exactly with `stop_floor=4.0, stop_frac=0.6, zz_rev=5.0, min_rr = 1.0 on Trend / 0.65
  otherwise` (`:728-753`). The producer's own stop/T1 ("as detected": trade row `quality.initial_stop`+`t1` → decision
  `mfe_track` → `v9_five_min_setups.stop_price`, T1 = 1R when unrecorded) is scored as a secondary column.
* **Scoring against bars** (`v9_bars_5min_woodies`, MES, bars after the signal bar until 15:55 ET): first touch of T1 vs stop
  on bar high/low, **same-bar ambiguity counted as STOP**; `$ = pts × $5 × contracts`, short pts = entry − exit; contracts per
  the live sizer `sierra_command.py:694-744` (`RISK_BUDGET_USD=225`, `RISK_MIN_CONTRACTS=3`, cap `FIXED_CONTRACTS_5`; n<3 →
  reject). Also: held-with-stop to the 15:55 close, marked-at-close with no stop, MFE/MAE. Exit model = all contracts at T1
  (no T0/T2/T3/BE ladder) — see §5 for the calibration.
* **Gate walk under today's chain**, in `_route_setup_inner` order, LIVE vs RELAXED. LIVE = `dalton_playbook.intent/
  evaluate_gate` with the label at the moment, the opening type from `detect_opening_type` and `direction_hint=None` (as
  live, §1.3). RELAXED = identical, except a phase-C decision on a `Variation/Normal_Variation` label admits EDGE_FADE in both
  directions (i.e. the Variation row's `entry_kinds` gains EDGE_FADE — the only way "require_with_trend does not apply" can
  be expressed in the live chain). Later gates replayed: `eod_entry_cutoff` (≥22:15 IL), dalton phase D (≥21:00), ELQ chaser
  (T-242 maturity skip + T-236 pullback exemption; VA limb not replayable; expensive-stop limb dead live, §1.4),
  `pattern_stop_cooldown` (live/demo REACTIVE stop-outs ≤30 min, <4 pt), `entry_not_confirmed` (`S4_ENTRY_CONFIRM_V1=1`,
  tol = max(0.10 × mean range14, 0.5)), `t1_wrong_side` / `rr_hard_floor` (0.3) / `rr_entry_gate` (0.65 rotation, 1.0 Trend),
  `daily_loss_halt` (−$450 from live `pnl_sierra` that day), `live_slot_occupied` (a live trade open at the decision time),
  RISK_BUDGET size reject. **Not replayed:** `news_blackout`, `cold_start_guard`/`feed_watchdog`/`cooldown`/`duplicate_fire`,
  `cluster_guard`/`trading_paused`, `position_mismatch`/`strict_risk`/`pre_send_entry_guard`, ELQ `beyond_value`, dalton's
  Trend→other 2-bar hysteresis. (`extreme_chase_guard` is CONT-only: `EXTREME_CHASE_SCOPE=CONT`; `cont_trend_filter` CONT-only;
  `RELEASE_ENTRY_GATE_V1=0`, `LSMA_FLAT_GATE_V1=0`, `ZONE_LIMIT_ENTRY_V1=0`, `DAYTYPE_ENTRY_BUDGET_V1=0`, `DAYTYPE_POSITION_GATE=0`.)

## 4 · September, setup by setup

`n` = contracts by the live sizer on the live bracket · `$first` = first-touch T1/stop · `$holdst` = held to the close with the
stop honoured · PROD = producer bracket.

```
decision IL dir   entry    LIVEstop LIVEt1   PRODstop PRODt1   label@moment      ext   W/A     hist_first_blk       dalton_live            later_gates                                  n  out   $first   $holdst  $close   mfe   mae   PRODout PROD$
09-01 20:35 LONG  7646.50  7640.0   7652.0   7628.75  7673.125 Normal_Variation  UP    WITH    awaiting_release     dalton_intent:kind     []                                           5  STOP   -162.50  -162.50   -62.50   2.8   6.8 STOP       -0.00
09-01 21:35 SHORT 7634.50  7640.5   7629.5   7653.25  7606.375 Neutral_Extreme   UP    AGAINST location_gate        dalton_intent:stand_do []                                           5  T1      125.00  -150.00  -237.50  11.0   1.5 OPEN       -0.00
09-02 20:50 LONG  7676.50  7670.5   7681.5   7666.0   7692.25  Normal_Variation  UP    WITH    daytype_playbook     dalton_intent:kind     ['live_slot_occupied(#971)']                 5  T1      125.00    50.00    50.00  11.0   2.8 OPEN       40.00
09-02 22:10 LONG  7678.50  7672.5   7683.5   7668.25  7687.5   Normal_Variation  UP    WITH    daytype_playbook     dalton_intent:stand_do []                                           5  OPEN      0.00     0.00     0.00   3.2   4.5 OPEN        0.00
09-02 22:15 LONG  7680.25  7674.25  7685.25  7668.25  7698.25  Normal_Variation  UP    WITH    eod_entry_cutoff     dalton_intent:stand_do ['eod_entry_cutoff']                         5  STOP   -150.00  -150.00   -43.75   1.5   6.2 OPEN      -26.25
09-03 18:55 LONG  7757.75  7746.25  7767.25  7694.25  7821.25  Normal_Variation  UP    WITH    None                 dalton_intent:kind     []                                           3  OPEN    -22.50   -22.50   -22.50   8.5  10.8 OPEN       -0.00
09-03 19:10 SHORT 7751.25  7757.75  7745.75  7763.75  7732.5   Normal_Variation  UP    AGAINST daytype_playbook     dalton_intent:kind     []                                           5  STOP   -162.50  -162.50  -125.00   3.2   7.0 STOP     -187.50
09-03 19:30 SHORT 7750.25  7756.25  7745.25  7763.75  7730.0   Normal_Variation  UP    AGAINST daytype_playbook     dalton_intent:kind     []                                           5  STOP   -150.00  -150.00  -150.00   1.5   6.2 STOP     -202.50
09-03 19:55 SHORT 7754.50  7760.25  7749.5   7763.75  7748.0   Normal_Variation  UP    AGAINST awaiting_release     dalton_intent:kind     []                                           5  T1      125.00  -143.75   -43.75   5.5   1.8 T1        130.00
09-04 19:05 LONG  7723.00  7717.75  7727.5   7717.75  7728.25  Normal_Variation  DOWN  AGAINST None                 dalton_intent:kind     []                                           5  T1      112.50  -131.25    18.75   6.5   2.0 T1        131.25
09-07 17:05 SHORT 7710.75  7721.25  7702.25  7721.25  7702.25  Trend_Normal      None  NONE    location_gate        None                   ['rr_entry_gate(0.81<1.0)']                  4  OPEN     35.00    35.00    35.00   7.2   2.5 OPEN       35.00
09-07 17:05 SHORT 7712.75  7721.25  7702.25  7721.25  7702.25  Trend_Normal      None  NONE    direction_compass    None                   []                                           5  OPEN     93.75    93.75    93.75   9.2   0.5 OPEN       93.75
09-07 18:00 SHORT 7704.50  7709.0   7700.75  7719.75  7702.25  Normal_Variation  DOWN  WITH    daytype_playbook     dalton_intent:kind     ['live_slot_occupied(#1191)']                5  STOP   -112.50  -112.50  -112.50   1.0   4.5 OPEN       -0.00
09-07 19:35 LONG  7708.75  7704.5   7712.5   7701.25  7720.0   Normal_Variation  DOWN  AGAINST daytype_playbook     dalton_intent:kind     []                                           5  OPEN      6.25     6.25     6.25   1.5   1.0 OPEN        6.25
09-07 19:40 LONG  7709.50  7705.0   7713.5   7701.25  7721.0   Normal_Variation  DOWN  AGAINST daytype_playbook     dalton_intent:kind     []                                           5  OPEN    -12.50   -12.50   -12.50   0.8   1.8 OPEN      -12.50
09-08 22:50 SHORT 7686.00  7691.75  7681.0   7696.25  7673.75  Normal            DOWN  WITH    eod_entry_cutoff     dalton_intent:stand_do ['eod_entry_cutoff']                         5  T1      125.00   118.75   118.75  10.0   1.0 T1        245.00
09-09 20:40 SHORT 7644.25  7650.5   7639.0   7657.0   7625.5   Normal_Variation  DOWN  WITH    dalton_intent:kind   dalton_intent:kind     []                                           5  STOP   -156.25  -156.25    -6.25   0.0   7.2 OPEN       -3.75
```
Reading: 13 of 17 were on a Variation label at the moment; the live dalton gate refuses all 13 (11 `kind`, 2 phase-D
`stand_down`). The relaxation lets 11 through; 2 are still blocked by a live slot already held (#971, #1191); **9 admitted:
2 T1 (+$237.50), 4 stops (−$631.25), 3 unresolved at the close (−$28.75) = −$422.50.** The two 09-03 shorts against the UP
extension are the whole stop loss of the AGAINST arm; the WITH arm is 09-01 20:35 and 09-09 20:40, both stopped. Under the
producer bracket (wider structural stops, 3–4 contracts) the same 9 give 2/3/4 = −$138.75 — same sign.
`Trend_Normal` at 09-07 17:05 is the pre-IB-lock provisional label (phase B: `OPEN_AUCTION_*` → EDGE_FADE allowed at half size).

## 5 · Model calibration — 13 broker-priced live REACTIVE trades

Same replay (live bracket, live sizing) run on the setups that actually traded live, against `pnl_sierra`:

```
#299 07-07 17:25 SHORT real=$   56.25 (STOP_HIT_SIERRA, rec stop=7553.75 t1=7531.0) LIVE-model=T1   $  185.00 (n=4, stop=7554.25, t1=7535.75 STEP_LADDER)
#340 07-10 18:40 SHORT real=$    6.25 (STOP_HIT, c=2, rec stop=7603.75 t1=7587.0)   LIVE-model=T1   $  143.75 (n=5, stop=7602.75, t1=7590.25)
#361 07-13 18:05 SHORT real=$  176.25 (T3_HIT, c=3, rec stop=7599.75 t1=7588.25)    LIVE-model=T1   $  150.00 (n=3, stop=7606.0,  t1=7584.25)
#372 07-14 18:30 LONG  real=$  -90.00 (STOP_HIT, c=3, t1=7603.25)                   LIVE-model=STOP $ -217.50 (n=3, stop=7582.75, t1=7609.25)
#420 07-20 17:25 SHORT real=$  -15.00 (STOP_HIT, c=4, t1=7503.5)                    LIVE-model=STOP $ -131.25 (n=5, stop=7514.0,  t1=7503.5 fallback)
#445 07-21 20:00 SHORT real=$   -6.25 (STOP_HIT, c=4, t1=7541.25)                   LIVE-model=T1   $  137.50 (n=5, stop=7555.75, t1=7544.75)
#593 08-03 17:10 LONG  real=$   71.25 (T2_HIT, c=2, rec stop=7582.0 t1=7594.25)     LIVE-model=T1   $    0.00 (n=0 size-reject, stop=7571.0)
#612 08-04 17:05 LONG  real=$  158.75 (T3_HIT, c=3, rec stop=7681.0 t1=7697.5)      LIVE-model=T1   $  225.00 (n=5, stop=7681.75, t1=7699.75)
#615 08-04 17:35 LONG  real=$  170.00 (T3_HIT, c=3, rec stop=7693.5 t1=7710.75)     LIVE-model=T1   $    0.00 (n=0 size-reject, stop=7684.0)
#637 08-06 18:20 SHORT real=$    0.00 (STOP_HIT, c=3, rec stop=7752.75 t1=7736.5)   LIVE-model=T1   $  160.00 (n=4, stop=7749.25, t1=7731.75)
#643 08-06 18:55 SHORT real=$   41.25 (manual, c=3, rec stop=7740.25 t1=7727.5)     LIVE-model=STOP $ -212.50 (n=5, stop=7739.5,  t1=7723.75)
#766 08-21 19:55 SHORT real=$   37.50 (phantom_reconcile, c=4, rec 7701.5/7690.5)   LIVE-model=T1   $  143.75 (n=5, stop=7702.25, t1=7689.75)
#877 08-31 17:00 SHORT real=$  116.25 (phantom_reconcile, c=5, rec 7696.75/7683.0)  LIVE-model=T1   $  150.00 (n=5, stop=7696.75, t1=7683.5)
Σ real=722.50   Σ LIVE-bracket model (first-touch, live sizing)=733.75   n=13
```
The ladder-era brackets reproduce to a tick or two (#877, #766 — the F3 ladder shipped 08-13); the July rows differ
(pre-ladder stops, 2–4 contracts). Row-level P&L differs (the real ladder banks T0/T1/T2/T3 and moves to BE); the **sums
agree**, so the window totals in §0 are broker-scale, not inflated. The producer-bracket variant over-states (Σ $1,602.50 on
the same 13) and is shown only as the "as-detected" column.

## 6 · The book in the same September sessions (live, broker-priced, `pnl_sierra`, state≠CANCELLED)

```
2026-09-01 GB100 n=1 -128.75 · INITIATIVE_LONG n=1 +55.00 · INITIATIVE_SHORT n=1 -156.25          → -230.00
2026-09-02 GHOST n=1 +76.25 · INITIATIVE_LONG n=1 +162.50 · ZLR n=1 +15.00                        → +253.75
2026-09-03 ZLR n=1 -156.25                                                                         → -156.25
2026-09-04 GB100 n=1 +70.00 · INITIATIVE_LONG n=2 -75.00 · INITIATIVE_SHORT n=1 +13.75 · ZLR n=1 -125.00 → -116.25
2026-09-07 ZLR n=1 +2.50                                                                           →   +2.50
2026-09-08 GHOST n=1 -52.50 · INITIATIVE_SHORT n=2 -128.75                                         → -181.25
2026-09-09 BULL_FLAG_LONG n=1 -137.50 · VEGAS n=1 -40.00                                           → -177.50
September total: -605.00 on 18 trades
```
Relaxed REACTIVE by session (§4): 09-01 −162.50 · 09-03 −210.00 (−162.50 −150.00 +125.00 −22.50) · 09-04 +112.50 ·
09-07 −6.25 · 09-09 −156.25 = **−$422.50**. Book + relaxation = −$1,027.50.

## 7 · Where the 07-07 → 08-28 money actually sits (live bracket, admitted-by-relaxation)

| month | admitted | T1/STOP/open | win | Σ$ first | WITH | AGAINST |
|---|---:|---|---:|---:|---|---|
| July (07-07→31, 18 sessions, 12.4 setups/session) | 57 | 29/26/2 | 52.7 % | −$180.00 | +$1,176.25 (27, 68 %) | −$1,356.25 (30, 40 %) |
| August (08-01→28) | 26 | 18/8/0 | 69.2 % | +$945.00 | −$73.75 (16, 56 %) | +$1,018.75 (10, 90 %) |
| **07-07→08-28** | **83** | 47/34/2 | 58.0 % | **+$765.00** | +$1,102.50 (43, 63 %) | −$337.50 (40, 53 %) |
| held-with-stop to close, same 83 | | | | −$5,716.25 | −$2,710.00 | −$3,006.25 |

Every REACTIVE edge in this data is a first-touch scalp against a 4–7 pt ladder stop: holding to the close is negative in
every window and both arms. August's +$945 is 10 winners on the AGAINST arm (08-07 ×3, 08-13, 08-18, 08-19, 08-21 ×2 …) and is
the only month in which "fade against the extension on a Variation day" paid; July (−$1,356.25) and September (−$81.25 on
n=6, the two 09-03 stops) say the opposite. The WITH arm is the mirror image (July +, August −, September −). That is the
definition of "not decidable".

## 8 · Caveats, honestly

* The key `(session, direction, entry, minute)` keeps T-252 forming/closed twins as two setups (430 bar-groups vs 339 keys);
  in live only one of a twin pair can trade, so §0 admitted counts are upper bounds — the sign is unaffected (twins score alike).
* The label is the classifier's own read at the bar (bars-IB, no live hysteresis/prelock overlay); on 2 of 17 September rows
  the decision is pre-IB-lock. Sierra-IB and bars-IB agree on all 338.
* `live_slot_occupied` reflects the live trades that actually existed then; under a different book those 2 (Sep) / 31 (Jul–Aug)
  would have traded — they are listed in the raw output, and they do not change the signs (`work/reactive_replay.json`).
* Exit model = all contracts at T1 or stop; the real (1,2,1,1) ladder + BE differs per row but matches on sums (§5).
* Scripts + JSON (session outputs folder, not in the repo): `work/reactive_enum.py`, `work/reactive_replay.py`,
  `work/reactive_summary.py`, `work/reactive_setups.json`, `work/reactive_replay.json`, `work/summary_out.txt` (appended below).

---

## Appendix A · raw replay output (`reactive_summary.py`, verbatim)

```

===== SEPTEMBER 2026-09-01 → 09-10: 17 setups =====
label@moment: {'Normal_Variation': 13, 'Trend_Normal': 2, 'Neutral_Extreme': 1, 'Normal': 1}
hist first blocker: {'daytype_playbook': 7, 'awaiting_release': 2, 'location_gate': 2, 'eod_entry_cutoff': 2, 'None': 2, 'direction_compass': 1, 'dalton_intent:kind': 1}
dalton LIVE verdict: {'dalton_intent:kind': 11, 'dalton_intent:stand_down': 4, 'None': 2}
Variation-label at moment: 13  · pre-IB-lock: 2
blocked ONLY by the Variation rule (dalton live blocks, relaxed passes): 11
  of which still blocked by a later gate: 2  → Counter({'live_slot_occupied': 2})
  ADMITTED by relaxation (passes every replayed later gate) n=  9 | LIVE-bracket(step-ladder): T1=  2 STOP=  4 OPEN= 3 win%= 33.3 Σ$first=  -422.50 Σ$hold(stop)=  -935.00 Σ$close=  -397.50 | PRODUCER-bracket: T1=  2 STOP=  3 win%= 40.0 Σ$first=  -138.75 Σ$hold(stop)=  -716.25
    ├ WITH extension                                       n=  3 | LIVE-bracket(step-ladder): T1=  0 STOP=  2 OPEN= 1 win%=  0.0 Σ$first=  -341.25 Σ$hold(stop)=  -341.25 Σ$close=   -91.25 | PRODUCER-bracket: T1=  0 STOP=  1 win%=  0.0 Σ$first=    -3.75 Σ$hold(stop)=    -3.75
    ├ AGAINST extension                                    n=  6 | LIVE-bracket(step-ladder): T1=  2 STOP=  2 OPEN= 2 win%= 50.0 Σ$first=   -81.25 Σ$hold(stop)=  -593.75 Σ$close=  -306.25 | PRODUCER-bracket: T1=  2 STOP=  2 win%= 50.0 Σ$first=  -135.00 Σ$hold(stop)=  -712.50
    └ no extension (inside IB)                             n=  0 | LIVE-bracket(step-ladder): T1=  0 STOP=  0 OPEN= 0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00 Σ$close=     0.00 | PRODUCER-bracket: T1=  0 STOP=  0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00
  ALL Variation-rule-blocked incl. later-gate (bars only)  n= 11 | LIVE-bracket(step-ladder): T1=  3 STOP=  5 OPEN= 3 win%= 37.5 Σ$first=  -410.00 Σ$hold(stop)=  -997.50 Σ$close=  -460.00 | PRODUCER-bracket: T1=  2 STOP=  3 win%= 40.0 Σ$first=   -98.75 Σ$hold(stop)=  -676.25
    ├ WITH extension                                       n=  5 | LIVE-bracket(step-ladder): T1=  1 STOP=  3 OPEN= 1 win%= 25.0 Σ$first=  -328.75 Σ$hold(stop)=  -403.75 Σ$close=  -153.75 | PRODUCER-bracket: T1=  0 STOP=  1 win%=  0.0 Σ$first=    36.25 Σ$hold(stop)=    36.25
    ├ AGAINST extension                                    n=  6 | LIVE-bracket(step-ladder): T1=  2 STOP=  2 OPEN= 2 win%= 50.0 Σ$first=   -81.25 Σ$hold(stop)=  -593.75 Σ$close=  -306.25 | PRODUCER-bracket: T1=  2 STOP=  2 win%= 50.0 Σ$first=  -135.00 Σ$hold(stop)=  -712.50
    └ no extension                                         n=  0 | LIVE-bracket(step-ladder): T1=  0 STOP=  0 OPEN= 0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00 Σ$close=     0.00 | PRODUCER-bracket: T1=  0 STOP=  0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00
  admitted under LIVE dalton (Normal/Neutral etc.), replayed n=  1 | LIVE-bracket(step-ladder): T1=  0 STOP=  0 OPEN= 1 win%=  nan Σ$first=    93.75 Σ$hold(stop)=    93.75 Σ$close=    93.75 | PRODUCER-bracket: T1=  0 STOP=  0 win%=  nan Σ$first=    93.75 Σ$hold(stop)=    93.75
  every Variation-label setup (context, bars only)         n= 13 | LIVE-bracket(step-ladder): T1=  3 STOP=  6 OPEN= 4 win%= 33.3 Σ$first=  -560.00 Σ$hold(stop)= -1147.50 Σ$close=  -503.75 | PRODUCER-bracket: T1=  2 STOP=  3 win%= 40.0 Σ$first=  -125.00 Σ$hold(stop)=  -702.50
    ├ WITH extension                                       n=  7 | LIVE-bracket(step-ladder): T1=  1 STOP=  4 OPEN= 2 win%= 20.0 Σ$first=  -478.75 Σ$hold(stop)=  -553.75 Σ$close=  -197.50 | PRODUCER-bracket: T1=  0 STOP=  1 win%=  0.0 Σ$first=    10.00 Σ$hold(stop)=    10.00
    ├ AGAINST extension                                    n=  6 | LIVE-bracket(step-ladder): T1=  2 STOP=  2 OPEN= 2 win%= 50.0 Σ$first=   -81.25 Σ$hold(stop)=  -593.75 Σ$close=  -306.25 | PRODUCER-bracket: T1=  2 STOP=  2 win%= 50.0 Σ$first=  -135.00 Σ$hold(stop)=  -712.50
    └ no extension                                         n=  0 | LIVE-bracket(step-ladder): T1=  0 STOP=  0 OPEN= 0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00 Σ$close=     0.00 | PRODUCER-bracket: T1=  0 STOP=  0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00

===== 2026-07-07 → 08-28: 312 setups =====
label@moment: {'Normal_Variation': 193, 'Normal': 60, 'Trend_Normal': 22, 'Neutral_Extreme': 13, 'Neutral_Center': 10, 'FORMING': 7, 'Nonconviction': 4, 'Trend_DD': 3}
hist first blocker: {'None': 156, 'daytype_playbook': 82, 'awaiting_release': 23, 'location_gate': 18, 'eod_entry_cutoff': 14, 'lsma_flat': 6, 'direction_context': 3, 'extreme_chase_guard': 3, 'structural_targets_wrong_side': 2, 'day_entry_budget': 2, 'news_blackout': 1, 'cold_start_guard': 1, 'rr_hard_floor': 1}
dalton LIVE verdict: {'dalton_intent:kind': 167, 'None': 89, 'dalton_intent:stand_down': 56}
Variation-label at moment: 193  · pre-IB-lock: 51
blocked ONLY by the Variation rule (dalton live blocks, relaxed passes): 130
  of which still blocked by a later gate: 47  → Counter({'live_slot_occupied': 31, 'entry_not_confirmed': 17, 'risk_budget_reject': 4})
  ADMITTED by relaxation (passes every replayed later gate) n= 83 | LIVE-bracket(step-ladder): T1= 47 STOP= 34 OPEN= 2 win%= 58.0 Σ$first=   765.00 Σ$hold(stop)= -5716.25 Σ$close= -5858.75 | PRODUCER-bracket: T1= 40 STOP= 36 win%= 52.6 Σ$first=   723.75 Σ$hold(stop)= -1767.50
    ├ WITH extension                                       n= 43 | LIVE-bracket(step-ladder): T1= 26 STOP= 15 OPEN= 2 win%= 63.4 Σ$first=  1102.50 Σ$hold(stop)= -2710.00 Σ$close= -1941.25 | PRODUCER-bracket: T1= 19 STOP= 19 win%= 50.0 Σ$first=   295.00 Σ$hold(stop)= -1966.25
    ├ AGAINST extension                                    n= 40 | LIVE-bracket(step-ladder): T1= 21 STOP= 19 OPEN= 0 win%= 52.5 Σ$first=  -337.50 Σ$hold(stop)= -3006.25 Σ$close= -3917.50 | PRODUCER-bracket: T1= 21 STOP= 17 win%= 55.3 Σ$first=   428.75 Σ$hold(stop)=   198.75
    └ no extension (inside IB)                             n=  0 | LIVE-bracket(step-ladder): T1=  0 STOP=  0 OPEN= 0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00 Σ$close=     0.00 | PRODUCER-bracket: T1=  0 STOP=  0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00
  ALL Variation-rule-blocked incl. later-gate (bars only)  n=130 | LIVE-bracket(step-ladder): T1= 72 STOP= 56 OPEN= 2 win%= 56.2 Σ$first=   570.00 Σ$hold(stop)= -6046.25 Σ$close= -8557.50 | PRODUCER-bracket: T1= 65 STOP= 56 win%= 53.7 Σ$first=  1165.00 Σ$hold(stop)= -2666.25
    ├ WITH extension                                       n= 75 | LIVE-bracket(step-ladder): T1= 41 STOP= 32 OPEN= 2 win%= 56.2 Σ$first=   236.25 Σ$hold(stop)= -4211.25 Σ$close= -5917.50 | PRODUCER-bracket: T1= 35 STOP= 34 win%= 50.7 Σ$first=   336.25 Σ$hold(stop)= -2940.00
    ├ AGAINST extension                                    n= 55 | LIVE-bracket(step-ladder): T1= 31 STOP= 24 OPEN= 0 win%= 56.4 Σ$first=   333.75 Σ$hold(stop)= -1835.00 Σ$close= -2640.00 | PRODUCER-bracket: T1= 30 STOP= 22 win%= 57.7 Σ$first=   828.75 Σ$hold(stop)=   273.75
    └ no extension                                         n=  0 | LIVE-bracket(step-ladder): T1=  0 STOP=  0 OPEN= 0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00 Σ$close=     0.00 | PRODUCER-bracket: T1=  0 STOP=  0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00
  admitted under LIVE dalton (Normal/Neutral etc.), replayed n= 68 | LIVE-bracket(step-ladder): T1= 39 STOP= 29 OPEN= 0 win%= 57.4 Σ$first=   991.25 Σ$hold(stop)=  3555.00 Σ$close= -1578.75 | PRODUCER-bracket: T1= 38 STOP= 27 win%= 58.5 Σ$first=  -176.25 Σ$hold(stop)=  -348.75
  every Variation-label setup (context, bars only)         n=193 | LIVE-bracket(step-ladder): T1=104 STOP= 78 OPEN=11 win%= 57.1 Σ$first=   392.50 Σ$hold(stop)= -4975.00 Σ$close= -9717.50 | PRODUCER-bracket: T1= 88 STOP= 80 win%= 52.4 Σ$first=   533.75 Σ$hold(stop)= -3242.50
    ├ WITH extension                                       n= 99 | LIVE-bracket(step-ladder): T1= 55 STOP= 36 OPEN= 8 win%= 60.4 Σ$first=  1450.00 Σ$hold(stop)=  -468.75 Σ$close= -1572.50 | PRODUCER-bracket: T1= 44 STOP= 40 win%= 52.4 Σ$first=  1150.00 Σ$hold(stop)= -2325.00
    ├ AGAINST extension                                    n= 72 | LIVE-bracket(step-ladder): T1= 36 STOP= 33 OPEN= 3 win%= 52.2 Σ$first=  -476.25 Σ$hold(stop)= -3632.50 Σ$close= -4993.75 | PRODUCER-bracket: T1= 30 STOP= 32 win%= 48.4 Σ$first=  -323.75 Σ$hold(stop)=  -878.75
    └ no extension                                         n= 22 | LIVE-bracket(step-ladder): T1= 13 STOP=  9 OPEN= 0 win%= 59.1 Σ$first=  -581.25 Σ$hold(stop)=  -873.75 Σ$close= -3151.25 | PRODUCER-bracket: T1= 14 STOP=  8 win%= 63.6 Σ$first=  -292.50 Σ$hold(stop)=   -38.75

===== JULY only 07-07 → 07-31 (old detector regime, ~12 setups/session): 224 setups =====
label@moment: {'Normal_Variation': 137, 'Normal': 47, 'Trend_Normal': 13, 'Neutral_Extreme': 9, 'Neutral_Center': 8, 'FORMING': 5, 'Nonconviction': 4, 'Trend_DD': 1}
hist first blocker: {'None': 141, 'daytype_playbook': 53, 'location_gate': 11, 'awaiting_release': 11, 'eod_entry_cutoff': 7, 'lsma_flat': 1}
dalton LIVE verdict: {'dalton_intent:kind': 116, 'None': 71, 'dalton_intent:stand_down': 37}
Variation-label at moment: 137  · pre-IB-lock: 43
blocked ONLY by the Variation rule (dalton live blocks, relaxed passes): 90
  of which still blocked by a later gate: 33  → Counter({'live_slot_occupied': 19, 'entry_not_confirmed': 15, 'risk_budget_reject': 3})
  ADMITTED by relaxation (passes every replayed later gate) n= 57 | LIVE-bracket(step-ladder): T1= 29 STOP= 26 OPEN= 2 win%= 52.7 Σ$first=  -180.00 Σ$hold(stop)= -4898.75 Σ$close= -6091.25 | PRODUCER-bracket: T1= 26 STOP= 29 win%= 47.3 Σ$first=  -808.75 Σ$hold(stop)= -2060.00
    ├ WITH extension                                       n= 27 | LIVE-bracket(step-ladder): T1= 17 STOP=  8 OPEN= 2 win%= 68.0 Σ$first=  1176.25 Σ$hold(stop)= -2836.25 Σ$close= -1905.00 | PRODUCER-bracket: T1= 13 STOP= 13 win%= 50.0 Σ$first=  -275.00 Σ$hold(stop)= -2488.75
    ├ AGAINST extension                                    n= 30 | LIVE-bracket(step-ladder): T1= 12 STOP= 18 OPEN= 0 win%= 40.0 Σ$first= -1356.25 Σ$hold(stop)= -2062.50 Σ$close= -4186.25 | PRODUCER-bracket: T1= 13 STOP= 16 win%= 44.8 Σ$first=  -533.75 Σ$hold(stop)=   428.75
    └ no extension (inside IB)                             n=  0 | LIVE-bracket(step-ladder): T1=  0 STOP=  0 OPEN= 0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00 Σ$close=     0.00 | PRODUCER-bracket: T1=  0 STOP=  0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00
  ALL Variation-rule-blocked incl. later-gate (bars only)  n= 90 | LIVE-bracket(step-ladder): T1= 46 STOP= 42 OPEN= 2 win%= 52.3 Σ$first=  -323.75 Σ$hold(stop)= -5548.75 Σ$close= -8413.75 | PRODUCER-bracket: T1= 41 STOP= 46 win%= 47.1 Σ$first= -1290.00 Σ$hold(stop)= -2821.25
    ├ WITH extension                                       n= 49 | LIVE-bracket(step-ladder): T1= 27 STOP= 20 OPEN= 2 win%= 57.4 Σ$first=   641.25 Σ$hold(stop)= -4858.75 Σ$close= -6298.75 | PRODUCER-bracket: T1= 22 STOP= 26 win%= 45.8 Σ$first=  -810.00 Σ$hold(stop)= -3522.50
    ├ AGAINST extension                                    n= 41 | LIVE-bracket(step-ladder): T1= 19 STOP= 22 OPEN= 0 win%= 46.3 Σ$first=  -965.00 Σ$hold(stop)=  -690.00 Σ$close= -2115.00 | PRODUCER-bracket: T1= 19 STOP= 20 win%= 48.7 Σ$first=  -480.00 Σ$hold(stop)=   701.25
    └ no extension                                         n=  0 | LIVE-bracket(step-ladder): T1=  0 STOP=  0 OPEN= 0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00 Σ$close=     0.00 | PRODUCER-bracket: T1=  0 STOP=  0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00
  admitted under LIVE dalton (Normal/Neutral etc.), replayed n= 54 | LIVE-bracket(step-ladder): T1= 30 STOP= 24 OPEN= 0 win%= 55.6 Σ$first=   345.00 Σ$hold(stop)=   140.00 Σ$close= -3790.00 | PRODUCER-bracket: T1= 31 STOP= 22 win%= 58.5 Σ$first=    32.50 Σ$hold(stop)= -1645.00
  every Variation-label setup (context, bars only)         n=137 | LIVE-bracket(step-ladder): T1= 68 STOP= 61 OPEN= 8 win%= 52.7 Σ$first= -1106.25 Σ$hold(stop)= -4695.00 Σ$close= -9038.75 | PRODUCER-bracket: T1= 57 STOP= 68 win%= 45.6 Σ$first= -2560.00 Σ$hold(stop)= -3868.75
    ├ WITH extension                                       n= 63 | LIVE-bracket(step-ladder): T1= 34 STOP= 23 OPEN= 6 win%= 59.6 Σ$first=  1237.50 Σ$hold(stop)= -1746.25 Σ$close= -2575.00 | PRODUCER-bracket: T1= 25 STOP= 31 win%= 44.6 Σ$first=  -811.25 Σ$hold(stop)= -3555.00
    ├ AGAINST extension                                    n= 54 | LIVE-bracket(step-ladder): T1= 22 STOP= 30 OPEN= 2 win%= 42.3 Σ$first= -1931.25 Σ$hold(stop)= -2243.75 Σ$close= -4125.00 | PRODUCER-bracket: T1= 19 STOP= 30 win%= 38.8 Σ$first= -1677.50 Σ$hold(stop)=  -496.25
    └ no extension                                         n= 20 | LIVE-bracket(step-ladder): T1= 12 STOP=  8 OPEN= 0 win%= 60.0 Σ$first=  -412.50 Σ$hold(stop)=  -705.00 Σ$close= -2338.75 | PRODUCER-bracket: T1= 13 STOP=  7 win%= 65.0 Σ$first=   -71.25 Σ$hold(stop)=   182.50

===== AUGUST only 08-01 → 08-28: 88 setups =====
label@moment: {'Normal_Variation': 56, 'Normal': 13, 'Trend_Normal': 9, 'Neutral_Extreme': 4, 'Trend_DD': 2, 'FORMING': 2, 'Neutral_Center': 2}
hist first blocker: {'daytype_playbook': 29, 'None': 15, 'awaiting_release': 12, 'eod_entry_cutoff': 7, 'location_gate': 7, 'lsma_flat': 5, 'direction_context': 3, 'extreme_chase_guard': 3, 'structural_targets_wrong_side': 2, 'day_entry_budget': 2, 'news_blackout': 1, 'cold_start_guard': 1, 'rr_hard_floor': 1}
dalton LIVE verdict: {'dalton_intent:kind': 51, 'dalton_intent:stand_down': 19, 'None': 18}
Variation-label at moment: 56  · pre-IB-lock: 8
blocked ONLY by the Variation rule (dalton live blocks, relaxed passes): 40
  of which still blocked by a later gate: 14  → Counter({'live_slot_occupied': 12, 'entry_not_confirmed': 2, 'risk_budget_reject': 1})
  ADMITTED by relaxation (passes every replayed later gate) n= 26 | LIVE-bracket(step-ladder): T1= 18 STOP=  8 OPEN= 0 win%= 69.2 Σ$first=   945.00 Σ$hold(stop)=  -817.50 Σ$close=   232.50 | PRODUCER-bracket: T1= 14 STOP=  7 win%= 66.7 Σ$first=  1532.50 Σ$hold(stop)=   292.50
    ├ WITH extension                                       n= 16 | LIVE-bracket(step-ladder): T1=  9 STOP=  7 OPEN= 0 win%= 56.2 Σ$first=   -73.75 Σ$hold(stop)=   126.25 Σ$close=   -36.25 | PRODUCER-bracket: T1=  6 STOP=  6 win%= 50.0 Σ$first=   570.00 Σ$hold(stop)=   522.50
    ├ AGAINST extension                                    n= 10 | LIVE-bracket(step-ladder): T1=  9 STOP=  1 OPEN= 0 win%= 90.0 Σ$first=  1018.75 Σ$hold(stop)=  -943.75 Σ$close=   268.75 | PRODUCER-bracket: T1=  8 STOP=  1 win%= 88.9 Σ$first=   962.50 Σ$hold(stop)=  -230.00
    └ no extension (inside IB)                             n=  0 | LIVE-bracket(step-ladder): T1=  0 STOP=  0 OPEN= 0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00 Σ$close=     0.00 | PRODUCER-bracket: T1=  0 STOP=  0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00
  ALL Variation-rule-blocked incl. later-gate (bars only)  n= 40 | LIVE-bracket(step-ladder): T1= 26 STOP= 14 OPEN= 0 win%= 65.0 Σ$first=   893.75 Σ$hold(stop)=  -497.50 Σ$close=  -143.75 | PRODUCER-bracket: T1= 24 STOP= 10 win%= 70.6 Σ$first=  2455.00 Σ$hold(stop)=   155.00
    ├ WITH extension                                       n= 26 | LIVE-bracket(step-ladder): T1= 14 STOP= 12 OPEN= 0 win%= 53.8 Σ$first=  -405.00 Σ$hold(stop)=   647.50 Σ$close=   381.25 | PRODUCER-bracket: T1= 13 STOP=  8 win%= 61.9 Σ$first=  1146.25 Σ$hold(stop)=   582.50
    ├ AGAINST extension                                    n= 14 | LIVE-bracket(step-ladder): T1= 12 STOP=  2 OPEN= 0 win%= 85.7 Σ$first=  1298.75 Σ$hold(stop)= -1145.00 Σ$close=  -525.00 | PRODUCER-bracket: T1= 11 STOP=  2 win%= 84.6 Σ$first=  1308.75 Σ$hold(stop)=  -427.50
    └ no extension                                         n=  0 | LIVE-bracket(step-ladder): T1=  0 STOP=  0 OPEN= 0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00 Σ$close=     0.00 | PRODUCER-bracket: T1=  0 STOP=  0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00
  admitted under LIVE dalton (Normal/Neutral etc.), replayed n= 14 | LIVE-bracket(step-ladder): T1=  9 STOP=  5 OPEN= 0 win%= 64.3 Σ$first=   646.25 Σ$hold(stop)=  3415.00 Σ$close=  2211.25 | PRODUCER-bracket: T1=  7 STOP=  5 win%= 58.3 Σ$first=  -208.75 Σ$hold(stop)=  1296.25
  every Variation-label setup (context, bars only)         n= 56 | LIVE-bracket(step-ladder): T1= 36 STOP= 17 OPEN= 3 win%= 67.9 Σ$first=  1498.75 Σ$hold(stop)=  -280.00 Σ$close=  -678.75 | PRODUCER-bracket: T1= 31 STOP= 12 win%= 72.1 Σ$first=  3093.75 Σ$hold(stop)=   626.25
    ├ WITH extension                                       n= 36 | LIVE-bracket(step-ladder): T1= 21 STOP= 13 OPEN= 2 win%= 61.8 Σ$first=   212.50 Σ$hold(stop)=  1277.50 Σ$close=  1002.50 | PRODUCER-bracket: T1= 19 STOP=  9 win%= 67.9 Σ$first=  1961.25 Σ$hold(stop)=  1230.00
    ├ AGAINST extension                                    n= 18 | LIVE-bracket(step-ladder): T1= 14 STOP=  3 OPEN= 1 win%= 82.4 Σ$first=  1455.00 Σ$hold(stop)= -1388.75 Σ$close=  -868.75 | PRODUCER-bracket: T1= 11 STOP=  2 win%= 84.6 Σ$first=  1353.75 Σ$hold(stop)=  -382.50
    └ no extension                                         n=  2 | LIVE-bracket(step-ladder): T1=  1 STOP=  1 OPEN= 0 win%= 50.0 Σ$first=  -168.75 Σ$hold(stop)=  -168.75 Σ$close=  -812.50 | PRODUCER-bracket: T1=  1 STOP=  1 win%= 50.0 Σ$first=  -221.25 Σ$hold(stop)=  -221.25

===== 2026-08-31 (between windows): 9 setups =====
label@moment: {'Normal': 6, 'Normal_Variation': 3}
hist first blocker: {'awaiting_release': 4, 'None': 3, 'rr_hard_floor': 1, 'location_gate': 1}
dalton LIVE verdict: {'None': 5, 'dalton_intent:kind': 3, 'dalton_intent:stand_down': 1}
Variation-label at moment: 3  · pre-IB-lock: 3
blocked ONLY by the Variation rule (dalton live blocks, relaxed passes): 0
  of which still blocked by a later gate: 0  → Counter()
  ADMITTED by relaxation (passes every replayed later gate) n=  0 | LIVE-bracket(step-ladder): T1=  0 STOP=  0 OPEN= 0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00 Σ$close=     0.00 | PRODUCER-bracket: T1=  0 STOP=  0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00
    ├ WITH extension                                       n=  0 | LIVE-bracket(step-ladder): T1=  0 STOP=  0 OPEN= 0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00 Σ$close=     0.00 | PRODUCER-bracket: T1=  0 STOP=  0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00
    ├ AGAINST extension                                    n=  0 | LIVE-bracket(step-ladder): T1=  0 STOP=  0 OPEN= 0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00 Σ$close=     0.00 | PRODUCER-bracket: T1=  0 STOP=  0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00
    └ no extension (inside IB)                             n=  0 | LIVE-bracket(step-ladder): T1=  0 STOP=  0 OPEN= 0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00 Σ$close=     0.00 | PRODUCER-bracket: T1=  0 STOP=  0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00
  ALL Variation-rule-blocked incl. later-gate (bars only)  n=  0 | LIVE-bracket(step-ladder): T1=  0 STOP=  0 OPEN= 0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00 Σ$close=     0.00 | PRODUCER-bracket: T1=  0 STOP=  0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00
    ├ WITH extension                                       n=  0 | LIVE-bracket(step-ladder): T1=  0 STOP=  0 OPEN= 0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00 Σ$close=     0.00 | PRODUCER-bracket: T1=  0 STOP=  0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00
    ├ AGAINST extension                                    n=  0 | LIVE-bracket(step-ladder): T1=  0 STOP=  0 OPEN= 0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00 Σ$close=     0.00 | PRODUCER-bracket: T1=  0 STOP=  0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00
    └ no extension                                         n=  0 | LIVE-bracket(step-ladder): T1=  0 STOP=  0 OPEN= 0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00 Σ$close=     0.00 | PRODUCER-bracket: T1=  0 STOP=  0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00
  admitted under LIVE dalton (Normal/Neutral etc.), replayed n=  3 | LIVE-bracket(step-ladder): T1=  1 STOP=  2 OPEN= 0 win%= 33.3 Σ$first=  -200.00 Σ$hold(stop)=  -456.25 Σ$close=   162.50 | PRODUCER-bracket: T1=  0 STOP=  3 win%=  0.0 Σ$first=  -610.00 Σ$hold(stop)=  -610.00
  every Variation-label setup (context, bars only)         n=  3 | LIVE-bracket(step-ladder): T1=  3 STOP=  0 OPEN= 0 win%=100.0 Σ$first=   475.00 Σ$hold(stop)=  -575.00 Σ$close=  -887.50 | PRODUCER-bracket: T1=  3 STOP=  0 win%=100.0 Σ$first=   412.50 Σ$hold(stop)=  -575.00
    ├ WITH extension                                       n=  0 | LIVE-bracket(step-ladder): T1=  0 STOP=  0 OPEN= 0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00 Σ$close=     0.00 | PRODUCER-bracket: T1=  0 STOP=  0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00
    ├ AGAINST extension                                    n=  0 | LIVE-bracket(step-ladder): T1=  0 STOP=  0 OPEN= 0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00 Σ$close=     0.00 | PRODUCER-bracket: T1=  0 STOP=  0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00
    └ no extension                                         n=  3 | LIVE-bracket(step-ladder): T1=  3 STOP=  0 OPEN= 0 win%=100.0 Σ$first=   475.00 Σ$hold(stop)=  -575.00 Σ$close=  -887.50 | PRODUCER-bracket: T1=  3 STOP=  0 win%=100.0 Σ$first=   412.50 Σ$hold(stop)=  -575.00

===== ALL 07-07 → 09-10: 338 setups =====
label@moment: {'Normal_Variation': 209, 'Normal': 67, 'Trend_Normal': 24, 'Neutral_Extreme': 14, 'Neutral_Center': 10, 'FORMING': 7, 'Nonconviction': 4, 'Trend_DD': 3}
hist first blocker: {'None': 161, 'daytype_playbook': 89, 'awaiting_release': 29, 'location_gate': 21, 'eod_entry_cutoff': 16, 'lsma_flat': 6, 'direction_context': 3, 'extreme_chase_guard': 3, 'structural_targets_wrong_side': 2, 'day_entry_budget': 2, 'rr_hard_floor': 2, 'news_blackout': 1, 'cold_start_guard': 1, 'direction_compass': 1, 'dalton_intent:kind': 1}
dalton LIVE verdict: {'dalton_intent:kind': 181, 'None': 96, 'dalton_intent:stand_down': 61}
Variation-label at moment: 209  · pre-IB-lock: 56
blocked ONLY by the Variation rule (dalton live blocks, relaxed passes): 141
  of which still blocked by a later gate: 49  → Counter({'live_slot_occupied': 33, 'entry_not_confirmed': 17, 'risk_budget_reject': 4})
  ADMITTED by relaxation (passes every replayed later gate) n= 92 | LIVE-bracket(step-ladder): T1= 49 STOP= 38 OPEN= 5 win%= 56.3 Σ$first=   342.50 Σ$hold(stop)= -6651.25 Σ$close= -6256.25 | PRODUCER-bracket: T1= 42 STOP= 39 win%= 51.9 Σ$first=   585.00 Σ$hold(stop)= -2483.75
    ├ WITH extension                                       n= 46 | LIVE-bracket(step-ladder): T1= 26 STOP= 17 OPEN= 3 win%= 60.5 Σ$first=   761.25 Σ$hold(stop)= -3051.25 Σ$close= -2032.50 | PRODUCER-bracket: T1= 19 STOP= 20 win%= 48.7 Σ$first=   291.25 Σ$hold(stop)= -1970.00
    ├ AGAINST extension                                    n= 46 | LIVE-bracket(step-ladder): T1= 23 STOP= 21 OPEN= 2 win%= 52.3 Σ$first=  -418.75 Σ$hold(stop)= -3600.00 Σ$close= -4223.75 | PRODUCER-bracket: T1= 23 STOP= 19 win%= 54.8 Σ$first=   293.75 Σ$hold(stop)=  -513.75
    └ no extension (inside IB)                             n=  0 | LIVE-bracket(step-ladder): T1=  0 STOP=  0 OPEN= 0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00 Σ$close=     0.00 | PRODUCER-bracket: T1=  0 STOP=  0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00
  ALL Variation-rule-blocked incl. later-gate (bars only)  n=141 | LIVE-bracket(step-ladder): T1= 75 STOP= 61 OPEN= 5 win%= 55.1 Σ$first=   160.00 Σ$hold(stop)= -7043.75 Σ$close= -9017.50 | PRODUCER-bracket: T1= 67 STOP= 59 win%= 53.2 Σ$first=  1066.25 Σ$hold(stop)= -3342.50
    ├ WITH extension                                       n= 80 | LIVE-bracket(step-ladder): T1= 42 STOP= 35 OPEN= 3 win%= 54.5 Σ$first=   -92.50 Σ$hold(stop)= -4615.00 Σ$close= -6071.25 | PRODUCER-bracket: T1= 35 STOP= 35 win%= 50.0 Σ$first=   372.50 Σ$hold(stop)= -2903.75
    ├ AGAINST extension                                    n= 61 | LIVE-bracket(step-ladder): T1= 33 STOP= 26 OPEN= 2 win%= 55.9 Σ$first=   252.50 Σ$hold(stop)= -2428.75 Σ$close= -2946.25 | PRODUCER-bracket: T1= 32 STOP= 24 win%= 57.1 Σ$first=   693.75 Σ$hold(stop)=  -438.75
    └ no extension                                         n=  0 | LIVE-bracket(step-ladder): T1=  0 STOP=  0 OPEN= 0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00 Σ$close=     0.00 | PRODUCER-bracket: T1=  0 STOP=  0 win%=  nan Σ$first=     0.00 Σ$hold(stop)=     0.00
  admitted under LIVE dalton (Normal/Neutral etc.), replayed n= 72 | LIVE-bracket(step-ladder): T1= 40 STOP= 31 OPEN= 1 win%= 56.3 Σ$first=   885.00 Σ$hold(stop)=  3192.50 Σ$close= -1322.50 | PRODUCER-bracket: T1= 38 STOP= 30 win%= 55.9 Σ$first=  -692.50 Σ$hold(stop)=  -865.00
  every Variation-label setup (context, bars only)         n=209 | LIVE-bracket(step-ladder): T1=110 STOP= 84 OPEN=15 win%= 56.7 Σ$first=   307.50 Σ$hold(stop)= -6697.50 Σ$close=-11108.75 | PRODUCER-bracket: T1= 93 STOP= 83 win%= 52.8 Σ$first=   821.25 Σ$hold(stop)= -4520.00
    ├ WITH extension                                       n=106 | LIVE-bracket(step-ladder): T1= 56 STOP= 40 OPEN=10 win%= 58.3 Σ$first=   971.25 Σ$hold(stop)= -1022.50 Σ$close= -1770.00 | PRODUCER-bracket: T1= 44 STOP= 41 win%= 51.8 Σ$first=  1160.00 Σ$hold(stop)= -2315.00
    ├ AGAINST extension                                    n= 78 | LIVE-bracket(step-ladder): T1= 38 STOP= 35 OPEN= 5 win%= 52.1 Σ$first=  -557.50 Σ$hold(stop)= -4226.25 Σ$close= -5300.00 | PRODUCER-bracket: T1= 32 STOP= 34 win%= 48.5 Σ$first=  -458.75 Σ$hold(stop)= -1591.25
    └ no extension                                         n= 25 | LIVE-bracket(step-ladder): T1= 16 STOP=  9 OPEN= 0 win%= 64.0 Σ$first=  -106.25 Σ$hold(stop)= -1448.75 Σ$close= -4038.75 | PRODUCER-bracket: T1= 17 STOP=  8 win%= 68.0 Σ$first=   120.00 Σ$hold(stop)=  -613.75

===== detection density (real setups / session) =====
2026-07 sessions: 18 setups: 224 per session: 12.4
2026-08 sessions: 19 setups: 97 per session: 5.1
2026-09 sessions: 7 setups: 17 per session: 2.4

===== admitted-by-relaxation, per-setup list (all windows) =====
07-07 19:00 LONG  e=7550.75  LIVE stop=7543.75  t1=7556.75  risk= 7.00 n=5 out=T1   $first=  150.00 $holdstop= -175.00 | PROD stop=7544.25  t1=7563.75   trade#304    n=5 out=T1   $first=  325.00 | ext=DOWN AGAINST mfe= 7.50 mae= 1.00 label=Normal_Variation hist=None
07-07 20:05 LONG  e=7569.25  LIVE stop=7563.75  t1=7574.0   risk= 5.50 n=5 out=STOP $first= -137.50 $holdstop= -137.50 | PROD stop=7561.75  t1=7576.75   1R-fallback  n=5 out=STOP $first= -187.50 | ext=DOWN AGAINST mfe= 1.75 mae= 7.50 label=Normal_Variation hist=None
07-08 17:50 SHORT e=7488.00  LIVE stop=7500.5   t1=7477.5   risk=12.50 n=3 out=STOP $first= -187.50 $holdstop= -187.50 | PROD stop=7500.75  t1=7475.25   1R-fallback  n=3 out=STOP $first= -191.25 | ext=DOWN WITH    mfe= 3.75 mae=15.25 label=Normal_Variation hist=None
07-08 18:00 SHORT e=7493.25  LIVE stop=7505.75  t1=7482.75  risk=12.50 n=3 out=T1   $first=  157.50 $holdstop= -187.50 | PROD stop=7502.75  t1=7483.75   1R-fallback  n=4 out=T1   $first=  190.00 | ext=DOWN WITH    mfe=15.00 mae= 2.25 label=Normal_Variation hist=None
07-08 18:20 LONG  e=7488.00  LIVE stop=7477.0   t1=7497.25  risk=11.00 n=4 out=STOP $first= -220.00 $holdstop= -220.00 | PROD stop=7477.5   t1=7498.5    1R-fallback  n=4 out=STOP $first= -210.00 | ext=DOWN AGAINST mfe= 2.75 mae=13.00 label=Normal_Variation hist=None
07-08 18:25 SHORT e=7477.00  LIVE stop=7491.5   t1=7465.0   risk=14.50 n=3 out=STOP $first= -217.50 $holdstop= -217.50 | PROD stop=7491.5   t1=7462.5    1R-fallback  n=3 out=STOP $first= -217.50 | ext=DOWN WITH    mfe= 7.75 mae=15.50 label=Normal_Variation hist=None
07-08 19:05 LONG  e=7484.25  LIVE stop=7473.5   t1=7493.25  risk=10.75 n=4 out=T1   $first=  180.00 $holdstop=  850.00 | PROD stop=7479.75  t1=7493.25   trade#307    n=5 out=T1   $first=  225.00 | ext=DOWN AGAINST mfe=14.25 mae= 0.00 label=Normal_Variation hist=None
07-08 19:35 SHORT e=7505.25  LIVE stop=7517.75  t1=7494.75  risk=12.50 n=3 out=STOP $first= -187.50 $holdstop= -187.50 | PROD stop=7514.5   t1=7496.0    1R-fallback  n=4 out=STOP $first= -185.00 | ext=DOWN WITH    mfe= 5.75 mae=12.75 label=Normal_Variation hist=None
07-09 18:35 SHORT e=7570.75  LIVE stop=7577.5   t1=7565.0   risk= 6.75 n=5 out=STOP $first= -168.75 $holdstop= -168.75 | PROD stop=7575.75  t1=7565.75   1R-fallback  n=5 out=STOP $first= -125.00 | ext=UP   AGAINST mfe= 0.50 mae= 7.00 label=Normal_Variation hist=None
07-09 18:45 LONG  e=7576.75  LIVE stop=7564.5   t1=7587.0   risk=12.25 n=3 out=T1   $first=  153.75 $holdstop=  206.25 | PROD stop=7572.25  t1=7566.5    trade#332    n=5 out=T1   $first= -256.25 | ext=UP   WITH    mfe=11.00 mae= 3.50 label=Normal_Variation hist=None
07-10 17:45 LONG  e=7593.25  LIVE stop=7586.0   t1=7599.5   risk= 7.25 n=5 out=STOP $first= -181.25 $holdstop= -181.25 | PROD stop=7575.0   t1=7611.5    1R-fallback  n=0 out=T1   $first=    0.00 | ext=DOWN AGAINST mfe= 5.00 mae=10.50 label=Normal_Variation hist=None
07-10 17:55 SHORT e=7591.25  LIVE stop=7598.75  t1=7585.0   risk= 7.50 n=5 out=T1   $first=  156.25 $holdstop= -187.50 | PROD stop=7597.5   t1=7583.75   trade#336    n=5 out=T1   $first=  187.50 | ext=DOWN WITH    mfe= 8.50 mae= 1.25 label=Normal_Variation hist=None
07-10 17:55 SHORT e=7591.50  LIVE stop=7599.0   t1=7585.25  risk= 7.50 n=5 out=T1   $first=  156.25 $holdstop= -187.50 | PROD stop=7599.0   t1=7584.0    1R-fallback  n=5 out=T1   $first=  187.50 | ext=DOWN WITH    mfe= 8.75 mae= 1.00 label=Normal_Variation hist=None
07-13 19:45 LONG  e=7574.50  LIVE stop=7566.25  t1=7581.5   risk= 8.25 n=5 out=STOP $first= -206.25 $holdstop= -206.25 | PROD stop=7559.25  t1=7589.75   1R-fallback  n=0 out=STOP $first=   -0.00 | ext=DOWN AGAINST mfe= 3.50 mae=11.00 label=Normal_Variation hist=None
07-13 20:25 SHORT e=7568.25  LIVE stop=7578.25  t1=7560.0   risk=10.00 n=4 out=T1   $first=  165.00 $holdstop=  105.00 | PROD stop=7572.5   t1=7559.25   trade#369    n=5 out=STOP $first= -106.25 | ext=DOWN WITH    mfe=10.50 mae= 6.00 label=Normal_Variation hist=None
07-14 17:55 LONG  e=7586.75  LIVE stop=7572.25  t1=7598.75  risk=14.50 n=3 out=T1   $first=  180.00 $holdstop= -217.50 | PROD stop=7574.5   t1=7599.0    1R-fallback  n=3 out=T1   $first=  183.75 | ext=UP   WITH    mfe=13.50 mae= 3.75 label=Normal_Variation hist=None
07-14 18:20 SHORT e=7589.75  LIVE stop=7602.75  t1=7578.75  risk=13.00 n=3 out=T1   $first=  165.00 $holdstop=   -3.75 | PROD stop=7601.75  t1=7577.75   1R-fallback  n=3 out=T1   $first=  180.00 | ext=UP   AGAINST mfe=12.00 mae=10.00 label=Normal_Variation hist=None
07-14 18:30 LONG  e=7597.25  LIVE stop=7582.75  t1=7609.25  risk=14.50 n=3 out=STOP $first= -217.50 $holdstop= -217.50 | PROD stop=7591.25  t1=7603.25   trade#371    n=5 out=STOP $first= -150.00 | ext=UP   WITH    mfe= 2.50 mae=19.50 label=Normal_Variation hist=None
07-14 20:10 LONG  e=7591.50  LIVE stop=7580.75  t1=7600.5   risk=10.75 n=4 out=OPEN $first=  -30.00 $holdstop=  -30.00 | PROD stop=7585.0   t1=7598.0    1R-fallback  n=5 out=STOP $first= -162.50 | ext=UP   WITH    mfe= 6.75 mae= 6.75 label=Normal_Variation hist=None
07-14 20:55 LONG  e=7592.75  LIVE stop=7585.25  t1=7599.25  risk= 7.50 n=5 out=OPEN $first=  -68.75 $holdstop=  -68.75 | PROD stop=7587.0   t1=7598.5    1R-fallback  n=5 out=STOP $first= -143.75 | ext=UP   WITH    mfe= 5.50 mae= 6.00 label=Normal_Variation hist=None
07-15 18:50 LONG  e=7583.50  LIVE stop=7574.75  t1=7590.75  risk= 8.75 n=5 out=T1   $first=  181.25 $holdstop=  562.50 | PROD stop=7571.0   t1=7596.0    1R-fallback  n=3 out=T1   $first=  187.50 | ext=DOWN AGAINST mfe= 7.25 mae= 4.00 label=Normal_Variation hist=None
07-15 20:10 LONG  e=7616.25  LIVE stop=7607.5   t1=7623.5   risk= 8.75 n=5 out=STOP $first= -218.75 $holdstop= -218.75 | PROD stop=7611.0   t1=7621.5    1R-fallback  n=5 out=STOP $first= -131.25 | ext=DOWN AGAINST mfe= 3.50 mae=11.50 label=Normal_Variation hist=None
07-17 18:05 SHORT e=7521.00  LIVE stop=7529.5   t1=7514.0   risk= 8.50 n=5 out=T1   $first=  175.00 $holdstop= -212.50 | PROD stop=7537.75  t1=7504.25   1R-fallback  n=0 out=STOP $first=   -0.00 | ext=UP   AGAINST mfe= 7.25 mae= 4.00 label=Normal_Variation hist=None
07-17 18:10 LONG  e=7525.00  LIVE stop=7516.25  t1=7532.25  risk= 8.75 n=5 out=T1   $first=  181.25 $holdstop= -218.75 | PROD stop=7513.0   t1=7537.0    1R-fallback  n=3 out=T1   $first=  180.00 | ext=UP   WITH    mfe=11.00 mae= 8.50 label=Normal_Variation hist=None
07-17 18:35 SHORT e=7516.00  LIVE stop=7524.75  t1=7508.5   risk= 8.75 n=5 out=STOP $first= -218.75 $holdstop= -218.75 | PROD stop=7525.75  t1=7506.25   1R-fallback  n=4 out=STOP $first= -195.00 | ext=UP   AGAINST mfe= 0.00 mae=10.25 label=Normal_Variation hist=None
07-17 18:40 LONG  e=7524.50  LIVE stop=7515.75  t1=7531.75  risk= 8.75 n=5 out=T1   $first=  181.25 $holdstop= -218.75 | PROD stop=7520.0   t1=7529.0    1R-fallback  n=5 out=T1   $first=  112.50 | ext=UP   WITH    mfe=11.50 mae= 3.25 label=Normal_Variation hist=None
07-17 18:50 LONG  e=7521.00  LIVE stop=7512.0   t1=7528.5   risk= 9.00 n=5 out=T1   $first=  187.50 $holdstop= -225.00 | PROD stop=7513.5   t1=7528.5    1R-fallback  n=5 out=T1   $first=  187.50 | ext=UP   WITH    mfe=18.00 mae= 0.00 label=Normal_Variation hist=None
07-17 19:25 SHORT e=7518.25  LIVE stop=7526.0   t1=7511.75  risk= 7.75 n=5 out=STOP $first= -193.75 $holdstop= -193.75 | PROD stop=7531.75  t1=7504.75   1R-fallback  n=3 out=STOP $first= -202.50 | ext=UP   AGAINST mfe= 0.00 mae=17.75 label=Normal_Variation hist=None
07-20 19:15 SHORT e=7503.00  LIVE stop=7510.0   t1=7497.25  risk= 7.00 n=5 out=STOP $first= -175.00 $holdstop= -175.00 | PROD stop=7511.75  t1=7494.25   1R-fallback  n=5 out=STOP $first= -218.75 | ext=DOWN WITH    mfe= 4.00 mae= 9.50 label=Normal_Variation hist=None
07-20 19:50 LONG  e=7525.00  LIVE stop=7519.25  t1=7529.75  risk= 5.75 n=5 out=STOP $first= -143.75 $holdstop= -143.75 | PROD stop=7518.0   t1=7531.0    trade#428    n=5 out=STOP $first= -175.00 | ext=DOWN AGAINST mfe= 0.00 mae=19.50 label=Normal_Variation hist=None
07-20 20:25 SHORT e=7508.25  LIVE stop=7514.0   t1=7503.25  risk= 5.75 n=5 out=T1   $first=  125.00 $holdstop=  618.75 | PROD stop=7519.25  t1=7497.25   1R-fallback  n=4 out=T1   $first=  220.00 | ext=DOWN WITH    mfe=10.25 mae= 3.75 label=Normal_Variation hist=None
07-21 18:25 LONG  e=7541.50  LIVE stop=7533.0   t1=7548.75  risk= 8.50 n=5 out=T1   $first=  181.25 $holdstop=   -6.25 | PROD stop=7533.25  t1=7549.75   1R-fallback  n=5 out=T1   $first=  206.25 | ext=UP   WITH    mfe= 9.00 mae= 0.00 label=Normal_Variation hist=None
07-22 19:35 SHORT e=7551.00  LIVE stop=7556.75  t1=7546.25  risk= 5.75 n=5 out=STOP $first= -143.75 $holdstop= -143.75 | PROD stop=7558.5   t1=7543.5    1R-fallback  n=5 out=STOP $first= -187.50 | ext=UP   AGAINST mfe= 0.00 mae=11.25 label=Normal_Variation hist=None
07-23 20:50 LONG  e=7442.50  LIVE stop=7435.0   t1=7448.75  risk= 7.50 n=5 out=STOP $first= -187.50 $holdstop= -187.50 | PROD stop=7428.75  t1=7456.25   1R-fallback  n=3 out=STOP $first= -206.25 | ext=DOWN AGAINST mfe= 0.00 mae=15.00 label=Normal_Variation hist=daytype_playbook
07-24 17:55 LONG  e=7448.75  LIVE stop=7436.25  t1=7459.25  risk=12.50 n=3 out=T1   $first=  157.50 $holdstop= -187.50 | PROD stop=7428.75  t1=7468.75   1R-fallback  n=0 out=T1   $first=    0.00 | ext=UP   WITH    mfe=41.50 mae= 0.00 label=Normal_Variation hist=lsma_flat
07-24 18:50 SHORT e=7480.25  LIVE stop=7492.5   t1=7469.75  risk=12.25 n=3 out=T1   $first=  157.50 $holdstop=  543.75 | PROD stop=7491.0   t1=7456.625  trade#510    n=4 out=T1   $first=  472.50 | ext=UP   AGAINST mfe=14.00 mae= 0.00 label=Normal_Variation hist=None
07-27 17:50 LONG  e=7438.00  LIVE stop=7431.25  t1=7443.75  risk= 6.75 n=5 out=T1   $first=  143.75 $holdstop= -168.75 | PROD stop=7418.75  t1=7457.25   1R-fallback  n=0 out=T1   $first=    0.00 | ext=DOWN AGAINST mfe= 8.50 mae= 1.00 label=Normal_Variation hist=daytype_playbook
07-27 18:25 SHORT e=7440.25  LIVE stop=7455.0   t1=7428.0   risk=14.75 n=3 out=T1   $first=  183.75 $holdstop= -221.25 | PROD stop=7466.0   t1=7414.5    1R-fallback  n=0 out=OPEN $first=   -0.00 | ext=DOWN WITH    mfe=19.00 mae= 3.75 label=Normal_Variation hist=daytype_playbook
07-27 19:20 SHORT e=7431.00  LIVE stop=7445.5   t1=7418.75  risk=14.50 n=3 out=T1   $first=  183.75 $holdstop= -217.50 | PROD stop=7449.0   t1=7413.0    1R-fallback  n=0 out=STOP $first=   -0.00 | ext=DOWN WITH    mfe=12.25 mae= 0.00 label=Normal_Variation hist=daytype_playbook
07-27 20:20 SHORT e=7420.25  LIVE stop=7432.5   t1=7410.0   risk=12.25 n=3 out=STOP $first= -183.75 $holdstop= -183.75 | PROD stop=7425.25  t1=7412.0    trade#542    n=5 out=STOP $first= -125.00 | ext=DOWN WITH    mfe= 0.00 mae=14.75 label=Normal_Variation hist=None
07-27 20:55 LONG  e=7433.00  LIVE stop=7426.25  t1=7438.75  risk= 6.75 n=5 out=STOP $first= -168.75 $holdstop= -168.75 | PROD stop=7415.5   t1=7450.5    1R-fallback  n=0 out=T1   $first=    0.00 | ext=DOWN AGAINST mfe= 4.75 mae= 8.25 label=Normal_Variation hist=daytype_playbook
07-28 18:05 SHORT e=7439.25  LIVE stop=7451.0   t1=7429.5   risk=11.75 n=3 out=STOP $first= -176.25 $holdstop= -176.25 | PROD stop=7459.75  t1=7418.75   1R-fallback  n=0 out=STOP $first=   -0.00 | ext=UP   AGAINST mfe= 0.00 mae=40.25 label=Normal_Variation hist=daytype_playbook
07-28 18:15 LONG  e=7451.25  LIVE stop=7438.75  t1=7461.75  risk=12.50 n=3 out=T1   $first=  157.50 $holdstop=  352.50 | PROD stop=7432.25  t1=7470.25   1R-fallback  n=0 out=T1   $first=    0.00 | ext=UP   WITH    mfe=25.75 mae= 0.00 label=Normal_Variation hist=daytype_playbook
07-28 18:35 SHORT e=7469.00  LIVE stop=7479.25  t1=7460.25  risk=10.25 n=4 out=STOP $first= -205.00 $holdstop= -205.00 | PROD stop=7480.75  t1=7457.25   1R-fallback  n=3 out=STOP $first= -176.25 | ext=UP   AGAINST mfe= 0.50 mae=10.25 label=Normal_Variation hist=None
07-28 19:30 SHORT e=7470.75  LIVE stop=7479.5   t1=7463.25  risk= 8.75 n=5 out=T1   $first=  187.50 $holdstop= -100.00 | PROD stop=7485.0   t1=7456.5    1R-fallback  n=3 out=OPEN $first=  -60.00 | ext=UP   AGAINST mfe= 8.25 mae= 6.25 label=Normal_Variation hist=location_gate
07-29 17:55 LONG  e=7406.00  LIVE stop=7396.25  t1=7414.25  risk= 9.75 n=4 out=STOP $first= -195.00 $holdstop= -195.00 | PROD stop=7389.25  t1=7422.75   1R-fallback  n=0 out=STOP $first=   -0.00 | ext=DOWN AGAINST mfe= 6.50 mae=10.50 label=Normal_Variation hist=daytype_playbook
07-29 18:10 LONG  e=7411.50  LIVE stop=7402.0   t1=7419.5   risk= 9.50 n=4 out=STOP $first= -190.00 $holdstop= -190.00 | PROD stop=7389.25  t1=7433.75   1R-fallback  n=0 out=STOP $first=   -0.00 | ext=DOWN AGAINST mfe= 1.00 mae=10.75 label=Normal_Variation hist=daytype_playbook
07-29 18:20 SHORT e=7401.50  LIVE stop=7414.5   t1=7390.5   risk=13.00 n=3 out=T1   $first=  165.00 $holdstop= -195.00 | PROD stop=7416.5   t1=7386.5    1R-fallback  n=3 out=T1   $first=  225.00 | ext=DOWN WITH    mfe=11.25 mae= 6.25 label=Normal_Variation hist=daytype_playbook
07-29 19:10 SHORT e=7382.25  LIVE stop=7395.5   t1=7371.0   risk=13.25 n=3 out=STOP $first= -198.75 $holdstop= -198.75 | PROD stop=7408.75  t1=7355.75   1R-fallback  n=0 out=STOP $first=   -0.00 | ext=DOWN WITH    mfe= 9.25 mae=16.50 label=Normal_Variation hist=daytype_playbook
07-29 19:25 LONG  e=7388.75  LIVE stop=7379.25  t1=7396.75  risk= 9.50 n=4 out=T1   $first=  160.00 $holdstop= -190.00 | PROD stop=7369.0   t1=7408.5    1R-fallback  n=0 out=T1   $first=    0.00 | ext=DOWN AGAINST mfe=10.00 mae= 0.50 label=Normal_Variation hist=daytype_playbook
07-29 19:40 LONG  e=7391.25  LIVE stop=7381.75  t1=7399.25  risk= 9.50 n=4 out=T1   $first=  160.00 $holdstop= -190.00 | PROD stop=7369.0   t1=7413.5    1R-fallback  n=0 out=T1   $first=    0.00 | ext=DOWN AGAINST mfe= 9.50 mae= 7.00 label=Normal_Variation hist=daytype_playbook
07-29 19:55 LONG  e=7398.25  LIVE stop=7388.5   t1=7406.5   risk= 9.75 n=4 out=T1   $first=  165.00 $holdstop= -195.00 | PROD stop=7380.25  t1=7416.25   1R-fallback  n=0 out=T1   $first=    0.00 | ext=DOWN AGAINST mfe=17.50 mae= 1.75 label=Normal_Variation hist=daytype_playbook
07-29 20:10 SHORT e=7409.75  LIVE stop=7422.5   t1=7399.0   risk=12.75 n=3 out=STOP $first= -191.25 $holdstop= -191.25 | PROD stop=7419.75  t1=7399.75   1R-fallback  n=4 out=STOP $first= -200.00 | ext=DOWN WITH    mfe= 1.00 mae=14.75 label=Normal_Variation hist=None
07-29 20:15 LONG  e=7421.75  LIVE stop=7412.25  t1=7429.75  risk= 9.50 n=4 out=STOP $first= -190.00 $holdstop= -190.00 | PROD stop=7388.75  t1=7454.75   1R-fallback  n=0 out=T1   $first=    0.00 | ext=DOWN AGAINST mfe= 6.75 mae=13.25 label=Normal_Variation hist=daytype_playbook
07-29 20:25 SHORT e=7419.25  LIVE stop=7432.0   t1=7408.5   risk=12.75 n=3 out=T1   $first=  161.25 $holdstop= -191.25 | PROD stop=7432.5   t1=7406.0    1R-fallback  n=3 out=STOP $first= -198.75 | ext=DOWN WITH    mfe=10.75 mae= 1.25 label=Normal_Variation hist=daytype_playbook
07-29 20:50 LONG  e=7415.75  LIVE stop=7406.25  t1=7423.75  risk= 9.50 n=4 out=STOP $first= -190.00 $holdstop= -190.00 | PROD stop=7404.5   t1=7427.0    1R-fallback  n=4 out=STOP $first= -225.00 | ext=DOWN AGAINST mfe=35.50 mae=17.75 label=Normal_Variation hist=daytype_playbook
07-30 19:05 LONG  e=7436.00  LIVE stop=7423.75  t1=7446.25  risk=12.25 n=3 out=T1   $first=  153.75 $holdstop=  551.25 | PROD stop=7422.0   t1=7446.5    trade#567    n=3 out=T1   $first=  157.50 | ext=DOWN AGAINST mfe=19.50 mae= 5.00 label=Normal_Variation hist=None
08-04 19:25 LONG  e=7744.50  LIVE stop=7734.25  t1=7753.25  risk=10.25 n=4 out=T1   $first=  175.00 $holdstop=  200.00 | PROD stop=7729.25  t1=7759.75   1R-fallback  n=0 out=OPEN $first=    0.00 | ext=UP   WITH    mfe=10.25 mae= 2.25 label=Normal_Variation hist=daytype_playbook
08-06 18:35 SHORT e=7734.75  LIVE stop=7744.25  t1=7726.75  risk= 9.50 n=4 out=STOP $first= -190.00 $holdstop= -190.00 | PROD stop=7744.0   t1=7732.0    trade#641    n=4 out=STOP $first= -185.00 | ext=DOWN WITH    mfe= 2.00 mae=11.00 label=Normal_Variation hist=None
08-06 18:55 SHORT e=7731.00  LIVE stop=7739.5   t1=7723.75  risk= 8.50 n=5 out=STOP $first= -212.50 $holdstop= -212.50 | PROD stop=7740.25  t1=7727.25   trade#642    n=4 out=T1   $first=   75.00 | ext=DOWN WITH    mfe= 6.75 mae= 9.50 label=Normal_Variation hist=None
08-07 18:15 LONG  e=7778.25  LIVE stop=7771.25  t1=7784.0   risk= 7.00 n=5 out=T1   $first=  143.75 $holdstop= -175.00 | PROD stop=7762.25  t1=7794.25   1R-fallback  n=0 out=STOP $first=   -0.00 | ext=UP   WITH    mfe= 5.75 mae= 3.00 label=Normal_Variation hist=daytype_playbook
08-07 18:30 LONG  e=7784.25  LIVE stop=7777.25  t1=7790.0   risk= 7.00 n=5 out=STOP $first= -175.00 $holdstop= -175.00 | PROD stop=7768.25  t1=7800.25   1R-fallback  n=0 out=STOP $first=   -0.00 | ext=UP   WITH    mfe= 2.50 mae= 7.75 label=Normal_Variation hist=daytype_playbook
08-07 18:40 SHORT e=7781.50  LIVE stop=7786.25  t1=7777.5   risk= 4.75 n=5 out=T1   $first=  100.00 $holdstop=   75.00 | PROD stop=7790.75  t1=7772.25   1R-fallback  n=4 out=T1   $first=  185.00 | ext=UP   AGAINST mfe= 5.00 mae= 2.50 label=Normal_Variation hist=daytype_playbook
08-07 19:00 SHORT e=7777.75  LIVE stop=7783.25  t1=7773.25  risk= 5.50 n=5 out=T1   $first=  112.50 $holdstop= -137.50 | PROD stop=7790.75  t1=7764.75   1R-fallback  n=3 out=T1   $first=  195.00 | ext=UP   AGAINST mfe= 8.00 mae= 3.50 label=Normal_Variation hist=daytype_playbook
08-07 19:15 SHORT e=7777.50  LIVE stop=7783.0   t1=7772.75  risk= 5.50 n=5 out=T1   $first=  118.75 $holdstop= -137.50 | PROD stop=7788.0   t1=7767.0    1R-fallback  n=4 out=T1   $first=  210.00 | ext=UP   AGAINST mfe= 7.75 mae= 3.75 label=Normal_Variation hist=daytype_playbook
08-10 18:10 SHORT e=7782.00  LIVE stop=7789.25  t1=7776.0   risk= 7.25 n=5 out=STOP $first= -181.25 $holdstop= -181.25 | PROD stop=7800.25  t1=7763.75   1R-fallback  n=0 out=T1   $first=    0.00 | ext=UP   AGAINST mfe= 4.00 mae= 8.00 label=Normal_Variation hist=daytype_playbook
08-11 18:30 SHORT e=7769.50  LIVE stop=7776.5   t1=7763.5   risk= 7.00 n=5 out=T1   $first=  150.00 $holdstop=  487.50 | PROD stop=7785.0   t1=7754.0    1R-fallback  n=0 out=T1   $first=    0.00 | ext=DOWN WITH    mfe= 6.25 mae= 1.75 label=Normal_Variation hist=extreme_chase_guard
08-11 18:55 SHORT e=7763.75  LIVE stop=7770.75  t1=7757.75  risk= 7.00 n=5 out=T1   $first=  150.00 $holdstop=  343.75 | PROD stop=7776.5   t1=7751.0    1R-fallback  n=3 out=T1   $first=  191.25 | ext=DOWN WITH    mfe= 8.25 mae= 6.25 label=Normal_Variation hist=extreme_chase_guard
08-13 18:30 SHORT e=7805.75  LIVE stop=7814.0   t1=7798.75  risk= 8.25 n=5 out=T1   $first=  175.00 $holdstop= -206.25 | PROD stop=7834.25  t1=7777.25   1R-fallback  n=0 out=OPEN $first=   -0.00 | ext=UP   AGAINST mfe= 8.00 mae= 2.25 label=Normal_Variation hist=daytype_playbook
08-13 19:25 LONG  e=7804.75  LIVE stop=7799.5   t1=7809.25  risk= 5.25 n=5 out=T1   $first=  112.50 $holdstop=  462.50 | PROD stop=7795.75  t1=7813.75   1R-fallback  n=5 out=T1   $first=  225.00 | ext=UP   WITH    mfe= 4.75 mae= 0.25 label=Normal_Variation hist=None
08-13 19:30 LONG  e=7809.50  LIVE stop=7803.75  t1=7814.25  risk= 5.75 n=5 out=T1   $first=  118.75 $holdstop=  343.75 | PROD stop=7795.75  t1=7823.25   1R-fallback  n=3 out=T1   $first=  206.25 | ext=UP   WITH    mfe= 5.25 mae= 3.50 label=Normal_Variation hist=daytype_playbook
08-18 18:30 LONG  e=7718.25  LIVE stop=7711.25  t1=7724.0   risk= 7.00 n=5 out=T1   $first=  143.75 $holdstop= -175.00 | PROD stop=7709.25  t1=7727.25   1R-fallback  n=5 out=T1   $first=  225.00 | ext=DOWN AGAINST mfe= 7.25 mae= 2.25 label=Normal_Variation hist=None
08-18 20:20 SHORT e=7723.00  LIVE stop=7728.0   t1=7718.75  risk= 5.00 n=5 out=T1   $first=  106.25 $holdstop=  193.75 | PROD stop=7732.75  t1=7713.25   1R-fallback  n=4 out=T1   $first=  195.00 | ext=DOWN WITH    mfe= 7.25 mae= 2.50 label=Normal_Variation hist=None
08-19 18:00 LONG  e=7762.00  LIVE stop=7750.75  t1=7771.5   risk=11.25 n=4 out=STOP $first= -225.00 $holdstop= -225.00 | PROD stop=7722.75  t1=7801.25   1R-fallback  n=0 out=STOP $first=   -0.00 | ext=UP   WITH    mfe= 2.75 mae=13.75 label=Normal_Variation hist=daytype_playbook
08-19 18:30 SHORT e=7750.50  LIVE stop=7757.0   t1=7745.0   risk= 6.50 n=5 out=T1   $first=  137.50 $holdstop= -162.50 | PROD stop=7768.75  t1=7732.25   1R-fallback  n=0 out=T1   $first=    0.00 | ext=UP   AGAINST mfe= 7.50 mae= 0.75 label=Normal_Variation hist=awaiting_release
08-19 19:10 LONG  e=7754.25  LIVE stop=7744.75  t1=7762.25  risk= 9.50 n=4 out=STOP $first= -190.00 $holdstop= -190.00 | PROD stop=7736.0   t1=7772.5    1R-fallback  n=0 out=STOP $first=   -0.00 | ext=UP   WITH    mfe= 5.25 mae=11.00 label=Normal_Variation hist=lsma_flat
08-21 18:35 LONG  e=7700.25  LIVE stop=7693.75  t1=7705.75  risk= 6.50 n=5 out=T1   $first=  137.50 $holdstop= -162.50 | PROD stop=7673.25  t1=7727.25   1R-fallback  n=0 out=OPEN $first=   -0.00 | ext=UP   WITH    mfe= 5.75 mae= 0.75 label=Normal_Variation hist=day_entry_budget
08-21 18:40 LONG  e=7702.50  LIVE stop=7693.75  t1=7709.75  risk= 8.75 n=5 out=T1   $first=  181.25 $holdstop= -218.75 | PROD stop=7673.25  t1=7731.75   1R-fallback  n=0 out=OPEN $first=   -0.00 | ext=UP   WITH    mfe= 7.50 mae= 0.00 label=Normal_Variation hist=cold_start_guard
08-21 19:05 SHORT e=7703.00  LIVE stop=7710.25  t1=7696.75  risk= 7.25 n=5 out=T1   $first=  156.25 $holdstop=  281.25 | PROD stop=7718.0   t1=7688.0    1R-fallback  n=3 out=T1   $first=  225.00 | ext=UP   AGAINST mfe= 6.25 mae= 0.00 label=Normal_Variation hist=day_entry_budget
08-21 19:55 SHORT e=7695.50  LIVE stop=7702.25  t1=7689.75  risk= 6.75 n=5 out=T1   $first=  143.75 $holdstop= -168.75 | PROD stop=7701.5   t1=7690.5    trade#765    n=5 out=T1   $first=  125.00 | ext=UP   AGAINST mfe= 6.00 mae= 5.25 label=Normal_Variation hist=None
08-25 20:30 SHORT e=7681.00  LIVE stop=7686.5   t1=7676.25  risk= 5.50 n=5 out=STOP $first= -137.50 $holdstop= -137.50 | PROD stop=7686.5   t1=7679.75   decision.mfe n=5 out=STOP $first= -137.50 | ext=DOWN WITH    mfe= 0.75 mae= 6.25 label=Normal_Variation hist=rr_hard_floor
08-27 18:20 LONG  e=7741.25  LIVE stop=7732.5   t1=7748.5   risk= 8.75 n=5 out=STOP $first= -218.75 $holdstop= -218.75 | PROD stop=7717.75  t1=7776.5    decision.mfe n=0 out=OPEN $first=    0.00 | ext=UP   WITH    mfe= 1.25 mae= 9.00 label=Normal_Variation hist=daytype_playbook
08-27 18:35 SHORT e=7733.25  LIVE stop=7738.5   t1=7728.75  risk= 5.25 n=5 out=T1   $first=  112.50 $holdstop= -131.25 | PROD stop=7746.75  t1=7713.0    decision.mfe n=3 out=STOP $first= -202.50 | ext=UP   AGAINST mfe= 6.00 mae= 2.00 label=Normal_Variation hist=daytype_playbook
09-01 20:35 LONG  e=7646.50  LIVE stop=7640.0   t1=7652.0   risk= 6.50 n=5 out=STOP $first= -162.50 $holdstop= -162.50 | PROD stop=7628.75  t1=7673.125  decision.mfe n=0 out=STOP $first=   -0.00 | ext=UP   WITH    mfe= 2.75 mae= 6.75 label=Normal_Variation hist=awaiting_release
09-03 18:55 LONG  e=7757.75  LIVE stop=7746.25  t1=7767.25  risk=11.50 n=3 out=OPEN $first=  -22.50 $holdstop=  -22.50 | PROD stop=7694.25  t1=7821.25   1R-fallback  n=0 out=OPEN $first=   -0.00 | ext=UP   WITH    mfe= 8.50 mae=10.75 label=Normal_Variation hist=None
09-03 19:10 SHORT e=7751.25  LIVE stop=7757.75  t1=7745.75  risk= 6.50 n=5 out=STOP $first= -162.50 $holdstop= -162.50 | PROD stop=7763.75  t1=7732.5    decision.mfe n=3 out=STOP $first= -187.50 | ext=UP   AGAINST mfe= 3.25 mae= 7.00 label=Normal_Variation hist=daytype_playbook
09-03 19:30 SHORT e=7750.25  LIVE stop=7756.25  t1=7745.25  risk= 6.00 n=5 out=STOP $first= -150.00 $holdstop= -150.00 | PROD stop=7763.75  t1=7730.0    decision.mfe n=3 out=STOP $first= -202.50 | ext=UP   AGAINST mfe= 1.50 mae= 6.25 label=Normal_Variation hist=daytype_playbook
09-03 19:55 SHORT e=7754.50  LIVE stop=7760.25  t1=7749.5   risk= 5.75 n=5 out=T1   $first=  125.00 $holdstop= -143.75 | PROD stop=7763.75  t1=7748.0    decision.mfe n=4 out=T1   $first=  130.00 | ext=UP   AGAINST mfe= 5.50 mae= 1.75 label=Normal_Variation hist=awaiting_release
09-04 19:05 LONG  e=7723.00  LIVE stop=7717.75  t1=7727.5   risk= 5.25 n=5 out=T1   $first=  112.50 $holdstop= -131.25 | PROD stop=7717.75  t1=7728.25   trade#1067   n=5 out=T1   $first=  131.25 | ext=DOWN AGAINST mfe= 6.50 mae= 2.00 label=Normal_Variation hist=None
09-07 19:35 LONG  e=7708.75  LIVE stop=7704.5   t1=7712.5   risk= 4.25 n=5 out=OPEN $first=    6.25 $holdstop=    6.25 | PROD stop=7701.25  t1=7720.0    trade#1207   n=5 out=OPEN $first=    6.25 | ext=DOWN AGAINST mfe= 1.50 mae= 1.00 label=Normal_Variation hist=daytype_playbook
09-07 19:40 LONG  e=7709.50  LIVE stop=7705.0   t1=7713.5   risk= 4.50 n=5 out=OPEN $first=  -12.50 $holdstop=  -12.50 | PROD stop=7701.25  t1=7721.0    trade#1208   n=5 out=OPEN $first=  -12.50 | ext=DOWN AGAINST mfe= 0.75 mae= 1.75 label=Normal_Variation hist=daytype_playbook
09-09 20:40 SHORT e=7644.25  LIVE stop=7650.5   t1=7639.0   risk= 6.25 n=5 out=STOP $first= -156.25 $holdstop= -156.25 | PROD stop=7657.0   t1=7625.5    trade#1338   n=3 out=OPEN $first=   -3.75 | ext=DOWN WITH    mfe= 0.00 mae= 7.25 label=Normal_Variation hist=dalton_intent:kind

===== September setup-by-setup =====
decision IL dir   entry    LIVEstop LIVEt1   PRODstop PRODt1   label@moment      ext   W/A     hist_first_blk       dalton_live            later_gates                                  n  out   $first   $holdst  $close   mfe   mae   PRODout PROD$   
09-01 20:35 LONG  7646.50  7640.0   7652.0   7628.75  7673.125 Normal_Variation  UP    WITH    awaiting_release     dalton_intent:kind     []                                           5  STOP   -162.50  -162.50   -62.50   2.8   6.8 STOP       -0.00
09-01 21:35 SHORT 7634.50  7640.5   7629.5   7653.25  7606.375 Neutral_Extreme   UP    AGAINST location_gate        dalton_intent:stand_do []                                           5  T1      125.00  -150.00  -237.50  11.0   1.5 OPEN       -0.00
09-02 20:50 LONG  7676.50  7670.5   7681.5   7666.0   7692.25  Normal_Variation  UP    WITH    daytype_playbook     dalton_intent:kind     ['live_slot_occupied(#971)']                 5  T1      125.00    50.00    50.00  11.0   2.8 OPEN       40.00
09-02 22:10 LONG  7678.50  7672.5   7683.5   7668.25  7687.5   Normal_Variation  UP    WITH    daytype_playbook     dalton_intent:stand_do []                                           5  OPEN      0.00     0.00     0.00   3.2   4.5 OPEN        0.00
09-02 22:15 LONG  7680.25  7674.25  7685.25  7668.25  7698.25  Normal_Variation  UP    WITH    eod_entry_cutoff     dalton_intent:stand_do ['eod_entry_cutoff']                         5  STOP   -150.00  -150.00   -43.75   1.5   6.2 OPEN      -26.25
09-03 18:55 LONG  7757.75  7746.25  7767.25  7694.25  7821.25  Normal_Variation  UP    WITH    None                 dalton_intent:kind     []                                           3  OPEN    -22.50   -22.50   -22.50   8.5  10.8 OPEN       -0.00
09-03 19:10 SHORT 7751.25  7757.75  7745.75  7763.75  7732.5   Normal_Variation  UP    AGAINST daytype_playbook     dalton_intent:kind     []                                           5  STOP   -162.50  -162.50  -125.00   3.2   7.0 STOP     -187.50
09-03 19:30 SHORT 7750.25  7756.25  7745.25  7763.75  7730.0   Normal_Variation  UP    AGAINST daytype_playbook     dalton_intent:kind     []                                           5  STOP   -150.00  -150.00  -150.00   1.5   6.2 STOP     -202.50
09-03 19:55 SHORT 7754.50  7760.25  7749.5   7763.75  7748.0   Normal_Variation  UP    AGAINST awaiting_release     dalton_intent:kind     []                                           5  T1      125.00  -143.75   -43.75   5.5   1.8 T1        130.00
09-04 19:05 LONG  7723.00  7717.75  7727.5   7717.75  7728.25  Normal_Variation  DOWN  AGAINST None                 dalton_intent:kind     []                                           5  T1      112.50  -131.25    18.75   6.5   2.0 T1        131.25
09-07 17:05 SHORT 7710.75  7721.25  7702.25  7721.25  7702.25  Trend_Normal      None  NONE    location_gate        None                   ['rr_entry_gate(0.81<1.0)']                  4  OPEN     35.00    35.00    35.00   7.2   2.5 OPEN       35.00
09-07 17:05 SHORT 7712.75  7721.25  7702.25  7721.25  7702.25  Trend_Normal      None  NONE    direction_compass    None                   []                                           5  OPEN     93.75    93.75    93.75   9.2   0.5 OPEN       93.75
09-07 18:00 SHORT 7704.50  7709.0   7700.75  7719.75  7702.25  Normal_Variation  DOWN  WITH    daytype_playbook     dalton_intent:kind     ['live_slot_occupied(#1191)']                5  STOP   -112.50  -112.50  -112.50   1.0   4.5 OPEN       -0.00
09-07 19:35 LONG  7708.75  7704.5   7712.5   7701.25  7720.0   Normal_Variation  DOWN  AGAINST daytype_playbook     dalton_intent:kind     []                                           5  OPEN      6.25     6.25     6.25   1.5   1.0 OPEN        6.25
09-07 19:40 LONG  7709.50  7705.0   7713.5   7701.25  7721.0   Normal_Variation  DOWN  AGAINST daytype_playbook     dalton_intent:kind     []                                           5  OPEN    -12.50   -12.50   -12.50   0.8   1.8 OPEN      -12.50
09-08 22:50 SHORT 7686.00  7691.75  7681.0   7696.25  7673.75  Normal            DOWN  WITH    eod_entry_cutoff     dalton_intent:stand_do ['eod_entry_cutoff']                         5  T1      125.00   118.75   118.75  10.0   1.0 T1        245.00
09-09 20:40 SHORT 7644.25  7650.5   7639.0   7657.0   7625.5   Normal_Variation  DOWN  WITH    dalton_intent:kind   dalton_intent:kind     []                                           5  STOP   -156.25  -156.25    -6.25   0.0   7.2 OPEN       -3.75

===== label agreement =====
bars-IB label == Sierra-IB label: 338 / 338
bars-IB label == recorded day_type_at_fire: 0 / 0
recorded day_type_at_fire distribution: {'None': 338}

===== scoring-model sanity vs broker-priced live REACTIVE =====
#299 07-07 17:25 SHORT real=$   56.25 (STOP_HIT_SIERRA, c=None, rec stop=7553.75 t1=7531.0) LIVE-model=T1   $  185.00 (n=4, stop=7554.25, t1=7535.75 STEP_LADDER) mfe=9.25 mae=2.75 label=Trend_Normal ext=NONE
#340 07-10 18:40 SHORT real=$    6.25 (STOP_HIT, c=2, rec stop=7603.75 t1=7587.0) LIVE-model=T1   $  143.75 (n=5, stop=7602.75, t1=7590.25 STEP_LADDER) mfe=10.25 mae=1.5 label=Neutral_Extreme ext=WITH
#361 07-13 18:05 SHORT real=$  176.25 (T3_HIT, c=3, rec stop=7599.75 t1=7588.25) LIVE-model=T1   $  150.00 (n=3, stop=7606.0, t1=7584.25 STEP_LADDER) mfe=12.0 mae=3.25 label=Nonconviction ext=NONE
#372 07-14 18:30 LONG  real=$  -90.00 (STOP_HIT, c=3, rec stop=None t1=7603.25) LIVE-model=STOP $ -217.50 (n=3, stop=7582.75, t1=7609.25 STEP_LADDER) mfe=2.5 mae=19.5 label=Normal_Variation ext=WITH
#420 07-20 17:25 SHORT real=$  -15.00 (STOP_HIT, c=4, rec stop=None t1=7503.5) LIVE-model=STOP $ -131.25 (n=5, stop=7514.0, t1=7503.5 fallback:trade#419/trade#419) mfe=0.0 mae=12.5 label=Neutral_Center ext=NONE
#445 07-21 20:00 SHORT real=$   -6.25 (STOP_HIT, c=4, rec stop=None t1=7541.25) LIVE-model=T1   $  137.50 (n=5, stop=7555.75, t1=7544.75 STEP_LADDER) mfe=5.75 mae=0.5 label=Trend_DD ext=AGAINST
#593 08-03 17:10 LONG  real=$   71.25 (T2_HIT, c=2, rec stop=7582.0 t1=7594.25) LIVE-model=T1   $    0.00 (n=0, stop=7571.0, t1=7605.0 STEP_LADDER) mfe=18.0 mae=0.0 label=Trend_Normal ext=NONE
#612 08-04 17:05 LONG  real=$  158.75 (T3_HIT, c=3, rec stop=7681.0 t1=7697.5) LIVE-model=T1   $  225.00 (n=5, stop=7681.75, t1=7699.75 STEP_LADDER) mfe=9.75 mae=1.0 label=Trend_Normal ext=NONE
#615 08-04 17:35 LONG  real=$  170.00 (T3_HIT, c=3, rec stop=7693.5 t1=7710.75) LIVE-model=T1   $    0.00 (n=0, stop=7684.0, t1=7714.75 STEP_LADDER) mfe=15.75 mae=1.0 label=Normal ext=NONE
#637 08-06 18:20 SHORT real=$    0.00 (STOP_HIT, c=3, rec stop=7752.75 t1=7736.5) LIVE-model=T1   $  160.00 (n=4, stop=7749.25, t1=7731.75 STEP_LADDER) mfe=9.5 mae=8.0 label=Normal ext=WITH
#643 08-06 18:55 SHORT real=$   41.25 (manual, c=3, rec stop=7740.25 t1=7727.5) LIVE-model=STOP $ -212.50 (n=5, stop=7739.5, t1=7723.75 STEP_LADDER) mfe=6.75 mae=9.5 label=Normal_Variation ext=WITH
#766 08-21 19:55 SHORT real=$   37.50 (phantom_reconcile, c=4, rec stop=7701.5 t1=7690.5) LIVE-model=T1   $  143.75 (n=5, stop=7702.25, t1=7689.75 STEP_LADDER) mfe=6.0 mae=5.25 label=Normal_Variation ext=AGAINST
#877 08-31 17:00 SHORT real=$  116.25 (phantom_reconcile, c=5, rec stop=7696.75 t1=7683.0) LIVE-model=T1   $  150.00 (n=5, stop=7696.75, t1=7683.5 STEP_LADDER) mfe=8.5 mae=0.0 label=Normal_Variation ext=NONE
Σ real=722.50  Σ LIVE-bracket model(first-touch, live sizing)=733.75  n=13

===== September book (live, broker-priced) by session =====
2026-09-01 GB100                    n=1 Σ$ -128.75
2026-09-01 INITIATIVE_LONG          n=1 Σ$   55.00
2026-09-01 INITIATIVE_SHORT         n=1 Σ$ -156.25
2026-09-02 GHOST                    n=1 Σ$   76.25
2026-09-02 INITIATIVE_LONG          n=1 Σ$  162.50
2026-09-02 ZLR                      n=1 Σ$   15.00
2026-09-03 ZLR                      n=1 Σ$ -156.25
2026-09-04 GB100                    n=1 Σ$   70.00
2026-09-04 INITIATIVE_LONG          n=2 Σ$  -75.00
2026-09-04 INITIATIVE_SHORT         n=1 Σ$   13.75
2026-09-04 ZLR                      n=1 Σ$ -125.00
2026-09-07 ZLR                      n=1 Σ$    2.50
2026-09-08 GHOST                    n=1 Σ$  -52.50
2026-09-08 INITIATIVE_SHORT         n=2 Σ$ -128.75
2026-09-09 BULL_FLAG_LONG           n=1 Σ$ -137.50
2026-09-09 VEGAS                    n=1 Σ$  -40.00
September total: -605.0
by session: [('2026-09-01', 3, -230.0), ('2026-09-02', 3, 253.75), ('2026-09-03', 1, -156.25), ('2026-09-04', 5, -116.25), ('2026-09-07', 1, 2.5), ('2026-09-08', 3, -181.25), ('2026-09-09', 2, -177.5)]
```

## Appendix B · enumeration output (`reactive_enum.py`, head + per-month table is in `enum_out.txt`; first 12 lines)
```
raw rows: setups=339 trades=74 decisions=3571 (decision archive from 2026-07-22T18:31:07+00:00)
unmatched (no setups row): trades=3 decisions=357

UNIQUE setups (session,dir,entry,signal-bar): 696
by month: {'2026-07': 373, '2026-08': 306, '2026-09': 17}
September unique: 17
signal(IL)   dir   entry    stop_s   setup#       modes          first_blk              blockers_seen / trade rows
07-07 17:15  LONG  7552.50  7541.75  [352]                       None                   [] 
07-07 17:15  LONG  7553.00  7541.75  [353]                       None                   [] 
07-07 17:20  SHORT 7544.00  7556.0   [355]        shadow         None                   [] shadow#300
07-07 17:20  SHORT 7545.00  7556.0   [354]        live,shadow    None                   [] shadow#298,live#299$56.25
07-07 18:00  SHORT 7541.25  7547.25  [357]                       None                   [] 
```

## Appendix C · replay scripts (copied verbatim for reproducibility)

### reactive_enum.py
```python
"""Step 1 — enumerate REACTIVE setups 2026-07-07 → today from 3 sources, dedup.
Read-only. Output: JSON list to work/reactive_setups.json + a printed table.
"""
import os, sys, json, glob, collections
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import psycopg2, psycopg2.extras

IL = ZoneInfo("Asia/Jerusalem"); ET = ZoneInfo("America/New_York")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reactive_setups.json")
SINCE = "2026-07-07"

def il(ts):
    return ts.astimezone(IL)

def sess(ts):
    """ET trading date of a UTC/aware timestamp."""
    return ts.astimezone(ET).strftime("%Y-%m-%d")

def floor5(ts):
    ts = ts.astimezone(timezone.utc)
    return ts.replace(minute=ts.minute - ts.minute % 5, second=0, microsecond=0)

conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ---------- source A: v9_five_min_setups (detection rows) ----------
cur.execute("""SELECT id, ts, pattern, direction, entry_price, stop_price, t1_price, t2_price,
                      day_type_at_fire, created_at
               FROM v9_five_min_setups
               WHERE pattern LIKE 'REACTIVE%%' AND ts >= %s ORDER BY ts, id""", (SINCE,))
setups_rows = cur.fetchall()

# ---------- source B: v9_trades (all modes) ----------
cur.execute("""SELECT id, mode, entry_ts, pattern_id_at_entry, direction, entry_price, stop, t1, t2, t3,
                      quality, state, exit_ts, exit_price, exit_reason, pnl_sierra, pnl_usd, day_type_at_entry,
                      t1_hit_ts, t2_hit_ts, t3_hit_ts, stop_hit_ts
               FROM v9_trades WHERE pattern_id_at_entry LIKE 'REACTIVE%%' AND entry_ts >= %s
               ORDER BY entry_ts, id""", (SINCE,))
trade_rows = cur.fetchall()

# ---------- source C: decisions archive ----------
files = sorted(glob.glob(os.path.expanduser("~/SierraChart_Data/v9_export/decisions_archive/*.jsonl"))) + \
        [os.path.expanduser("~/SierraChart_Data/v9_export/gateway_decisions.jsonl")]
dec_rows = []
for f in files:
    for line in open(f, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if "schema" in d:          # candidate_ledger events — skip (not gate decisions)
            continue
        if not str(d.get("pattern") or "").startswith("REACTIVE"):
            continue
        try:
            ts = datetime.fromisoformat(d["ts"])
        except Exception:
            continue
        if ts < datetime.fromisoformat(SINCE + "T00:00:00+00:00"):
            continue
        d["_ts"] = ts
        dec_rows.append(d)

print(f"raw rows: setups={len(setups_rows)} trades={len(trade_rows)} decisions={len(dec_rows)} "
      f"(decision archive from {min(r['_ts'] for r in dec_rows).isoformat()})")

# ---------- build setup universe ----------
# identity: (session, direction, entry_price, signal_bar_ts_utc)
universe = {}

def key_of(session, direction, entry, bar_ts):
    return f"{session}|{direction}|{float(entry):.2f}|{bar_ts.strftime('%H:%M')}Z"

for r in setups_rows:
    ts = r["ts"]
    k = key_of(sess(ts), r["direction"], r["entry_price"], floor5(ts))
    u = universe.setdefault(k, {"key": k, "session": sess(ts), "direction": r["direction"],
                                "classification": r["pattern"], "entry": float(r["entry_price"]),
                                "signal_bar_utc": floor5(ts).isoformat(), "signal_bar_il": il(ts).strftime("%m-%d %H:%M"),
                                "setup_ids": [], "trade_rows": [], "decisions": [],
                                "stop_setup": float(r["stop_price"]) if r["stop_price"] is not None else None,
                                "t1_setup": float(r["t1_price"]) if r["t1_price"] is not None else None,
                                "day_type_at_fire": r["day_type_at_fire"]})
    u["setup_ids"].append(r["id"])

def find_match(session, direction, entry, ts):
    best = None
    for k, u in universe.items():
        if u["session"] != session or u["direction"] != direction or abs(u["entry"] - float(entry)) > 1e-9:
            continue
        bt = datetime.fromisoformat(u["signal_bar_utc"])
        dt = (ts.astimezone(timezone.utc) - bt).total_seconds()
        if -60 <= dt <= 12 * 60:
            if best is None or abs(dt) < best[0]:
                best = (abs(dt), k)
    return best[1] if best else None

unmatched_trades, unmatched_decs = 0, 0
for r in trade_rows:
    ts = r["entry_ts"]
    k = find_match(sess(ts), r["direction"], r["entry_price"], ts)
    if k is None:
        unmatched_trades += 1
        bar = floor5(ts - timedelta(minutes=5))
        k = key_of(sess(ts), r["direction"], r["entry_price"], bar)
        universe.setdefault(k, {"key": k, "session": sess(ts), "direction": r["direction"],
                                "classification": r["pattern_id_at_entry"], "entry": float(r["entry_price"]),
                                "signal_bar_utc": bar.isoformat(), "signal_bar_il": il(bar).strftime("%m-%d %H:%M"),
                                "setup_ids": [], "trade_rows": [], "decisions": [], "stop_setup": None,
                                "t1_setup": None, "day_type_at_fire": None, "no_setup_row": True})
    q = r["quality"] if isinstance(r["quality"], dict) else {}
    universe[k]["trade_rows"].append({
        "id": r["id"], "mode": r["mode"], "entry_ts_il": il(ts).strftime("%m-%d %H:%M:%S"),
        "stop_col": float(r["stop"]) if r["stop"] is not None else None,
        "initial_stop": float(q["initial_stop"]) if q.get("initial_stop") is not None else None,
        "t1": float(r["t1"]) if r["t1"] is not None else None,
        "t2": float(r["t2"]) if r["t2"] is not None else None,
        "t3": float(r["t3"]) if r["t3"] is not None else None,
        "state": r["state"], "exit_reason": r["exit_reason"],
        "pnl_sierra": float(r["pnl_sierra"]) if r["pnl_sierra"] is not None else None,
        "pnl_usd": float(r["pnl_usd"]) if r["pnl_usd"] is not None else None,
        "blocked_by": q.get("blocked_by"), "shadow_blocked": bool(q.get("shadow_blocked")),
        "day_type_at_entry": r["day_type_at_entry"],
        "contracts": q.get("contracts"),
        "exit_ts_il": il(r["exit_ts"]).strftime("%m-%d %H:%M:%S") if r["exit_ts"] else None,
        "exit_price": float(r["exit_price"]) if r["exit_price"] is not None else None,
    })

for d in dec_rows:
    ts = d["_ts"]
    k = find_match(sess(ts), d["direction"], d["entry"], ts)
    if k is None:
        unmatched_decs += 1
        bar = floor5(ts - timedelta(minutes=5))
        k = key_of(sess(ts), d["direction"], d["entry"], bar)
        universe.setdefault(k, {"key": k, "session": sess(ts), "direction": d["direction"],
                                "classification": d["pattern"], "entry": float(d["entry"]),
                                "signal_bar_utc": bar.isoformat(), "signal_bar_il": il(bar).strftime("%m-%d %H:%M"),
                                "setup_ids": [], "trade_rows": [], "decisions": [], "stop_setup": None,
                                "t1_setup": None, "day_type_at_fire": None, "no_setup_row": True})
    universe[k]["decisions"].append({
        "ts_il": il(ts).strftime("%m-%d %H:%M:%S"), "blocked_by": d.get("blocked_by"),
        "reason": d.get("reason"), "outcome": d.get("outcome"), "trade_id": d.get("trade_id"),
        "live_blocked_by": d.get("live_blocked_by"), "mfe_track": d.get("mfe_track"),
    })

print(f"unmatched (no setups row): trades={unmatched_trades} decisions={unmatched_decs}")
rows = sorted(universe.values(), key=lambda u: (u["signal_bar_utc"], u["direction"], u["entry"]))
for u in rows:
    bbs = [d["blocked_by"] for d in u["decisions"]]
    u["blockers_seen"] = sorted(set(str(b) for b in bbs))
    first = None
    for d in u["decisions"]:
        if d["blocked_by"] not in ("duplicate_fire",):
            first = d["blocked_by"]; break
    u["first_blocker"] = first
    u["modes"] = sorted(set(t["mode"] for t in u["trade_rows"] if not t["shadow_blocked"]))
json.dump(rows, open(OUT, "w"), indent=1, default=str)

# ---------- summary ----------
print(f"\nUNIQUE setups (session,dir,entry,signal-bar): {len(rows)}")
by_month = collections.Counter(u["session"][:7] for u in rows)
print("by month:", dict(by_month))
sep = [u for u in rows if u["session"] >= "2026-09-01"]
print(f"September unique: {len(sep)}")
print(f"{'signal(IL)':12s} {'dir':5s} {'entry':8s} {'stop_s':8s} {'setup#':12s} {'modes':14s} {'first_blk':22s} blockers_seen / trade rows")
for u in rows:
    tr = ",".join(f"{t['mode']}#{t['id']}{'(twin:'+str(t['blocked_by'])+')' if t['shadow_blocked'] else ''}"
                  f"{'$'+str(t['pnl_sierra']) if t['pnl_sierra'] is not None else ''}" for t in u["trade_rows"])
    print(f"{u['signal_bar_il']:12s} {u['direction']:5s} {u['entry']:<8.2f} {str(u['stop_setup']):8s} "
          f"{str(u['setup_ids']):12s} {','.join(u['modes']):14s} {str(u['first_blocker']):22s} "
          f"{u['blockers_seen']} {tr}")
```

### reactive_replay.py
```python
"""Step 2 — replay every real REACTIVE setup (07-07 → today):
  * day-type label AT THAT MOMENT: classify_session on RTH bars up to the signal bar,
    IB = first 12 RTH bars (6-bar provisional IB before lock), same flags as live .env
    (DELTA_FEATURES_V1 unset — it would read TODAY's cumulative_delta.json)
  * extension direction at that moment (mechanical: which IB edge the session has broken further)
  * bar scoring: T1-before-stop, $ at T1 / stop, $ to close (held), MFE/MAE, contracts per live sizing
  * gate walk under TODAY's chain (DALTON_PLAYBOOK_V1=1): LIVE vs RELAXED (EDGE_FADE admitted on Variation)
Read-only. Output: work/reactive_replay.json + printed tables.
"""
import os, sys, json, math, collections
from datetime import datetime, timedelta, timezone, time as dtime
from zoneinfo import ZoneInfo
import psycopg2, psycopg2.extras

REPO = "/Users/michael/Downloads/mems26_web_git"
sys.path.insert(0, REPO)
os.environ.pop("DELTA_FEATURES_V1", None)          # replay honesty: no today's-file lookahead
os.environ.pop("MULTIDAY_CONTEXT_V1", None)

from backend.v9.systems.day_type.classifier_core import classify_session
from backend.v9.systems.day_type.opening_detector_v2 import detect_opening_type
from backend.v9.systems.entry_location_quality import assess_entry_quality
from backend.v9.services.dalton_playbook import intent as dp_intent, evaluate_gate as dp_eval, load_config as dp_cfg
from backend.v9.systems.five_min.step_scaled_ladder import build_step_ladder

IL = ZoneInfo("Asia/Jerusalem"); ET = ZoneInfo("America/New_York")
W = os.path.dirname(os.path.abspath(__file__))
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

def q(sql, params=()):
    cur.execute(sql, params); return cur.fetchall()

def f(v):
    try: return float(v) if v is not None else None
    except (TypeError, ValueError): return None

# ---------------------------------------------------------------- session context
_sess_cache = {}
def load_session(date):
    if date in _sess_cache:
        return _sess_cache[date]
    rows = q("""SELECT ts, open, high, low, close, volume FROM v9_bars_5min_woodies
                WHERE symbol='MES' AND (ts AT TIME ZONE 'America/New_York')::date BETWEEN (%s::date - 1) AND %s::date
                ORDER BY ts""", (date, date))
    allbars = [{"ts": r["ts"], "o": f(r["open"]), "h": f(r["high"]), "l": f(r["low"]), "c": f(r["close"]), "v": f(r["volume"]) or 0.0}
               for r in rows]
    rth = [b for b in allbars if b["ts"].astimezone(ET).strftime("%Y-%m-%d") == date
           and dtime(9, 30) <= b["ts"].astimezone(ET).time() < dtime(16, 0)]
    sib = q("""SELECT ib_high, ib_low, profile_shape, vah_price, val_price, poc_price FROM v9_tpo_sessions
               WHERE trading_date=%s AND session_type='CASH' ORDER BY id DESC LIMIT 1""", (date,))
    sib = sib[0] if sib else {}
    hist = q("SELECT ib_width FROM v9_day_type_history WHERE date < %s AND ib_width IS NOT NULL", (date,))
    ib_hist = [float(r["ib_width"]) for r in hist]
    vol_rows = q("""SELECT sum(volume) AS vol FROM v9_bars_5min_woodies WHERE symbol='MES'
                    AND (ts AT TIME ZONE 'America/New_York')::date < %s
                    AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30'
                    AND (ts AT TIME ZONE 'America/New_York')::time < '16:00'
                    GROUP BY (ts AT TIME ZONE 'America/New_York')::date HAVING count(*) >= 60""", (date,))
    vols = sorted(float(r["vol"]) for r in vol_rows if r["vol"] is not None)
    med_vol = vols[len(vols) // 2] if len(vols) >= 3 else None
    pd_ = q("""SELECT max((ts AT TIME ZONE 'America/New_York')::date) AS d FROM v9_bars_5min_woodies
               WHERE (ts AT TIME ZONE 'America/New_York')::date < %s AND symbol='MES'""", (date,))[0]["d"]
    pdh = pdl = pvah = pval = None
    if pd_ is not None:
        hl = q("""SELECT max(high) AS h, min(low) AS l FROM v9_bars_5min_woodies
                  WHERE (ts AT TIME ZONE 'America/New_York')::date = %s AND symbol='MES'""", (pd_,))[0]
        pdh, pdl = f(hl["h"]), f(hl["l"])
        pv = q("SELECT vah_price AS vah, val_price AS val FROM v9_tpo_sessions WHERE trading_date=%s ORDER BY id DESC LIMIT 1", (pd_.isoformat(),))
        if pv:
            pvah, pval = f(pv[0]["vah"]), f(pv[0]["val"])
    tpo_rows = q("SELECT ts, poc FROM v9_tpo_history WHERE (ts AT TIME ZONE 'America/New_York')::date = %s ORDER BY ts", (date,))
    pocs = [(r["ts"], f(r["poc"])) for r in tpo_rows if f(r["poc"]) is not None]
    ibm_rows = q("""SELECT (ib_high - ib_low) AS w FROM v9_tpo_sessions WHERE session_type='CASH' AND trading_date < %s
                    AND ib_high IS NOT NULL AND ib_low IS NOT NULL ORDER BY trading_date DESC LIMIT 20""", (date,))
    ibmeds = sorted(float(r["w"]) for r in ibm_rows if r["w"] is not None)
    ctx = {"date": date, "all": allbars, "rth": rth, "sierra_ib": (f(sib.get("ib_high")), f(sib.get("ib_low"))),
           "profile_shape": sib.get("profile_shape"), "ib_hist": ib_hist, "ibmeds": ibmeds, "med_vol": med_vol,
           "pdh": pdh, "pdl": pdl, "pvah": pvah, "pval": pval, "pocs": pocs}
    ctx["timeline"] = run_timeline(ctx, "bars12")
    ctx["timeline_sierra"] = run_timeline(ctx, "sierra") if ctx["sierra_ib"][0] and ctx["sierra_ib"][1] else None
    _sess_cache[date] = ctx
    return ctx

def run_timeline(ctx, ib_mode):
    rth = ctx["rth"]; n = len(rth)
    if not n:
        return []
    open_price = rth[0]["o"]
    ib6 = (max(b["h"] for b in rth[:min(6, n)]), min(b["l"] for b in rth[:min(6, n)]))
    ib12 = (max(b["h"] for b in rth[:min(12, n)]), min(b["l"] for b in rth[:min(12, n)]))
    if ib_mode == "sierra":
        ib12 = ctx["sierra_ib"]
    out = []; prev_neutral = None; cum_v = 0.0
    for i in range(n):
        cum_v += rth[i]["v"] or 0.0
        ibh, ibl = ib6 if i + 1 < 12 else ib12
        pocs_upto = [p for (t, p) in ctx["pocs"] if t <= rth[i]["ts"] + timedelta(minutes=5)]
        poc_now = pocs_upto[-1] if pocs_upto else None
        poc_at_ib = pocs_upto[1] if len(pocs_upto) >= 2 else (pocs_upto[0] if pocs_upto else None)
        vr = round(cum_v / ctx["med_vol"], 3) if ctx["med_vol"] else None
        try:
            res = classify_session(bars=rth[:i + 1], ib_high=ibh, ib_low=ibl, open_price=open_price,
                                   ib_width_hist=ctx["ibmeds"], profile_shape=ctx["profile_shape"], vol_ratio=vr,
                                   prior_vah=ctx["pvah"], prior_val=ctx["pval"], pdh=ctx["pdh"], pdl=ctx["pdl"],
                                   poc_now=poc_now, poc_at_ib=poc_at_ib, is_eod=False, prev_neutral_subtype=prev_neutral)
        except Exception as e:
            res = {"day_type": "ERROR", "status": "ERROR", "reason": str(e)}
        dt = res.get("day_type", "")
        if dt.startswith("Neutral_"):
            prev_neutral = dt
        elif dt not in ("FORMING", ""):
            prev_neutral = None
        out.append({"i": i, "day_type": dt, "status": res.get("status"), "dir_bias": res.get("dir_bias"),
                    "accepted_break": res.get("accepted_break"), "one_tf": (res.get("measured") or {}).get("one_tf"),
                    "ibh": ibh, "ibl": ibl, "reason": res.get("reason")})
    return out

def opening_type(ctx):
    rth = ctx["rth"]
    if not rth:
        return "UNKNOWN"
    try:
        op = detect_opening_type(rth[:6], rth[0]["o"], prior_vah=ctx["pvah"], prior_val=ctx["pval"], pdh=ctx["pdh"], pdl=ctx["pdl"])
        return op.get("opening_type") or "UNKNOWN"
    except Exception:
        return "UNKNOWN"

# ---------------------------------------------------------------- live trade state helpers
live_trades = q("""SELECT id, entry_ts, exit_ts, direction, pattern_id_at_entry, entry_price, stop_hit_ts, pnl_sierra, state, mode
                   FROM v9_trades WHERE mode IN ('live','demo') AND entry_ts >= '2026-07-01' ORDER BY entry_ts""")

def live_slot_open(t_utc):
    for r in live_trades:
        if r["mode"] != "live" or r["state"] == "CANCELLED":
            continue
        if r["entry_ts"] <= t_utc and (r["exit_ts"] is None and r["entry_ts"].astimezone(ET).date() == t_utc.astimezone(ET).date()
                                       or (r["exit_ts"] is not None and r["exit_ts"] > t_utc)):
            return r["id"]
    return None

def daily_pnl_before(t_utc):
    d = t_utc.astimezone(ET).date(); s = 0.0
    for r in live_trades:
        if r["mode"] == "live" and r["pnl_sierra"] is not None and r["exit_ts"] and r["exit_ts"] <= t_utc \
                and r["exit_ts"].astimezone(ET).date() == d:
            s += float(r["pnl_sierra"])
    return s

def stop_cooldown(t_utc, direction, entry):
    for r in live_trades:
        if r["stop_hit_ts"] and str(r["pattern_id_at_entry"] or "").startswith("REACTIVE") and r["direction"] == direction \
                and t_utc - timedelta(minutes=30) <= r["stop_hit_ts"] <= t_utc and r["entry_price"] is not None \
                and abs(float(r["entry_price"]) - entry) < 4.0:
            return r["id"]
    return None

# ---------------------------------------------------------------- sizing (live: RISK_BUDGET_SIZING_V1 + FIXED_CONTRACTS_5)
def contracts_for(risk_pts):
    if risk_pts is None or risk_pts <= 0:
        return None, "no-risk"
    if risk_pts > 30:
        return 0, "risk>30 hard max"
    n = int(225.0 / (risk_pts * 5.0))
    if n < 3:
        return 0, f"n={n}<3 (risk {risk_pts:.2f}pt)"
    return min(n, 5), "ok"

# ---------------------------------------------------------------- main loop
rows = json.load(open(os.path.join(W, "reactive_setups.json")))
real = [u for u in rows if u["setup_ids"] or u["modes"]]
cfg = dp_cfg()
results = []
for u in real:
    r = dict(u)
    date = u["session"]; ctx = load_session(date); rth = ctx["rth"]
    sig = datetime.fromisoformat(u["signal_bar_utc"])
    idx = next((i for i, b in enumerate(rth) if b["ts"].astimezone(timezone.utc) == sig), None)
    r["bars_in_session"] = len(rth)
    if idx is None:
        r["skip"] = "signal bar not in RTH bar set"; results.append(r); continue
    decision_utc = sig + timedelta(minutes=5)                     # the bar closes → gateway decision
    il = decision_utc.astimezone(IL); r["decision_il"] = il.strftime("%m-%d %H:%M")
    tl = ctx["timeline"][idx]
    r["label"] = tl["day_type"]; r["label_status"] = tl["status"]; r["dir_bias"] = tl["dir_bias"]
    r["accepted_break"] = tl["accepted_break"]; r["one_tf"] = tl["one_tf"]
    r["label_sierra_ib"] = ctx["timeline_sierra"][idx]["day_type"] if ctx["timeline_sierra"] else None
    r["pre_ib_lock"] = idx + 1 < 12
    # mechanical extension direction at the moment (IB = first 12 bars, only once locked)
    if idx + 1 >= 12:
        ibh = max(b["h"] for b in rth[:12]); ibl = min(b["l"] for b in rth[:12])
        eu = max(b["h"] for b in rth[:idx + 1]) - ibh; ed = ibl - min(b["l"] for b in rth[:idx + 1])
        r["ext_up"] = round(eu, 2); r["ext_dn"] = round(ed, 2); r["ib_width"] = round(ibh - ibl, 2)
        if eu > 0 and eu >= ed:
            ext = "UP"
        elif ed > 0 and ed > eu:
            ext = "DOWN"
        else:
            ext = None
    else:
        ext = None; r["ext_up"] = r["ext_dn"] = r["ib_width"] = None
    r["ext_dir"] = ext
    d = u["direction"]
    r["with_ext"] = ("WITH" if (d == "LONG" and ext == "UP") or (d == "SHORT" and ext == "DOWN")
                     else "AGAINST" if ext in ("UP", "DOWN") else "NONE")
    # ---- stop / t1 (recorded first)
    stop = t1 = None; src = None
    for t in u["trade_rows"]:
        if t["initial_stop"] is not None or t["stop_col"] is not None:
            stop = t["initial_stop"] if t["initial_stop"] is not None else t["stop_col"]
            t1 = t["t1"]; src = f"trade#{t['id']}"; break
    if stop is None:
        for dd in u["decisions"]:
            m = dd.get("mfe_track") or {}
            if m.get("stop") is not None:
                stop = f(m["stop"]); t1 = f(m.get("t1")); src = "decision.mfe_track"; break
    if stop is None and u.get("stop_setup") is not None:
        stop = u["stop_setup"]; src = "setups.stop_price"
    entry = u["entry"]
    risk = abs(entry - stop) if stop is not None else None
    if t1 is None and risk:
        t1 = entry + risk if d == "LONG" else entry - risk; r["t1_source"] = "1R-fallback"
    else:
        r["t1_source"] = src
    r["stop_prod"] = stop; r["t1_prod"] = t1; r["risk_prod"] = round(risk, 2) if risk else None; r["stop_source_prod"] = src
    # ---- LIVE bracket: STEP_SCALED_LADDER_V1=1 overrides stop/t1/t2/t3 for every setup that reaches
    # trading_gateway.py:3493 (52 OVERRODE / 2 KEPT in the current log). Pure function of session bars → exact replay.
    rr_min = 1.0 if str(tl["day_type"]).startswith("Trend") else 0.65
    ladder = None
    try:
        ladder = build_step_ladder(entry, d, [{"h": b["h"], "l": b["l"]} for b in rth[:idx + 1]],
                                   stop_floor=4.0, stop_frac=0.6, zz_rev=5.0, min_rr=rr_min)
    except Exception as e:
        r["ladder_err"] = str(e)
    if ladder:
        stop_l, t1_l, t2_l, t3_l = ladder["stop"], ladder["t1"], ladder["t2"], ladder["t3"]
        r["bracket_source"] = "STEP_LADDER"; r["median_step"] = ladder["median_step"]
    else:
        stop_l, t1_l, t2_l, t3_l = stop, t1, None, None
        r["bracket_source"] = f"fallback:{src}/{r['t1_source']}"
    risk_l = abs(entry - stop_l) if stop_l is not None else None
    r["stop"] = stop_l; r["t1"] = t1_l; r["t2"] = t2_l; r["t3"] = t3_l; r["risk_pts"] = round(risk_l, 2) if risk_l else None
    n_c, n_why = contracts_for(risk_l); r["contracts"] = n_c; r["contracts_why"] = n_why
    fwd = rth[idx + 1:]
    sgn = 1.0 if d == "LONG" else -1.0

    def score(stop_, t1_, tag, nn_):
        outcome = "OPEN"; exit_px = None; mfe = mae = 0.0; bars_to_exit = None
        for j, b in enumerate(fwd):
            fav = (b["h"] - entry) if d == "LONG" else (entry - b["l"])
            adv = (entry - b["l"]) if d == "LONG" else (b["h"] - entry)
            mfe = max(mfe, fav); mae = max(mae, adv)
            stop_hit = (stop_ is not None) and ((b["l"] <= stop_) if d == "LONG" else (b["h"] >= stop_))
            t1_hit = (t1_ is not None) and ((b["h"] >= t1_) if d == "LONG" else (b["l"] <= t1_))
            if stop_hit:                      # same-bar ambiguity → STOP (conservative)
                outcome = "STOP"; exit_px = stop_; bars_to_exit = j + 1; break
            if t1_hit:
                outcome = "T1"; exit_px = t1_; bars_to_exit = j + 1; break
        close_px = fwd[-1]["c"] if fwd else entry
        if outcome == "OPEN":
            exit_px = close_px
        pts_first = (exit_px - entry) * sgn
        pts_close = (close_px - entry) * sgn
        stopped_pre_close = any(((b["l"] <= stop_) if d == "LONG" else (b["h"] >= stop_)) for b in fwd) if stop_ is not None else False
        pts_hold_stop = (stop_ - entry) * sgn if stopped_pre_close else pts_close
        return {f"outcome{tag}": outcome, f"exit_px{tag}": exit_px, f"pts_first{tag}": round(pts_first, 2),
                f"usd_first{tag}": round(pts_first * 5 * nn_, 2), f"pts_close{tag}": round(pts_close, 2),
                f"usd_close{tag}": round(pts_close * 5 * nn_, 2), f"pts_hold_stop{tag}": round(pts_hold_stop, 2),
                f"usd_hold_stop{tag}": round(pts_hold_stop * 5 * nn_, 2), f"mfe{tag}": round(mfe, 2), f"mae{tag}": round(mae, 2),
                f"bars_to_exit{tag}": bars_to_exit, f"usd_first_5c{tag}": round(pts_first * 25, 2)}
    nn = n_c if n_c else 0
    r.update(score(stop_l, t1_l, "", nn)); r["fwd_bars"] = len(fwd)
    n_p, _ = contracts_for(risk); r["contracts_prod"] = n_p
    r.update(score(stop, t1, "_prod", n_p if n_p else 0))
    # ---- today's chain, replayable gates, in chain order
    blocks_live, blocks_relaxed = [], []
    hhmm = il.strftime("%H:%M")
    ot = opening_type(ctx)
    it = dp_intent(opening_type=ot, day_type=r["label"], now_il_hhmm=hhmm, direction_hint=None)
    setup_d = {"direction": d, "classification": u["classification"]}
    g = dp_eval(setup_d, it)
    r["dalton_live"] = g["blocked_by"] if g else None; r["dalton_reason"] = (g or {}).get("reason") or it.reason
    if g:
        blocks_live.append(g["blocked_by"])
    # RELAXED: Variation phase-C row admits EDGE_FADE (both directions); everything else unchanged
    g2 = g
    if g and r["label"] in ("Variation", "Normal_Variation") and it.reason.startswith("phase=C"):
        g2 = None
    r["dalton_relaxed"] = g2["blocked_by"] if g2 else None
    if g2:
        blocks_relaxed.append(g2["blocked_by"])
    later = []
    if il.time() >= dtime(22, 15):
        later.append("eod_entry_cutoff")
    # entry_location_quality
    sess_bars = rth[:idx + 1]
    sh = max(b["h"] for b in sess_bars); sl = min(b["l"] for b in sess_bars)
    leg_base = sl if d == "LONG" else sh; leg_ext = sh if d == "LONG" else sl
    pos_all = ctx["all"]; k = next(i for i, b in enumerate(pos_all) if b["ts"] == rth[idx]["ts"])
    atr_bars = pos_all[max(0, k - 13):k + 1]
    trs, prev = [], None
    for b in atr_bars:
        trs.append(b["h"] - b["l"] if prev is None else max(b["h"] - b["l"], abs(b["h"] - prev), abs(b["l"] - prev))); prev = b["c"]
    atr = sum(trs) / len(trs) if trs else None
    r["atr14"] = round(atr, 2) if atr else None
    L = abs(leg_ext - leg_base); L_floor = max(1.0, 0.5 * atr) if atr else 1.0
    immature = (idx + 1) < 2 or L < L_floor
    recent = sess_bars[-3:]
    has_pb = any(b["l"] <= sh - 3.0 for b in recent) if d == "LONG" else any(b["h"] >= sl + 3.0 for b in recent)
    # LIVE MIRROR: trading_gateway.py:1906 `from backend.v9.shared.atr import current_atr14` raises ImportError
    # (verified 10.09) → _elq_atr is None → the expensive-stop limb never runs live (0 blocks in the archive).
    # VA limb needs tpo.json at the time → not replayable (skipped, honest). Only the chaser limb is replayed.
    elq = assess_entry_quality(entry_price=entry, direction=d, leg_base=None if immature else leg_base,
                               leg_extreme=None if immature else leg_ext, stop_distance=risk, atr=None,
                               vah=None, val=None, has_pullback=has_pb)
    r["elq_expensive_stop_would_be"] = (risk / atr) if (atr and risk) else None
    r["elq"] = elq["reasons"]
    if not elq["pass"]:
        later.append("entry_location_quality")
    cd = stop_cooldown(decision_utc, d, entry)
    if cd:
        later.append(f"pattern_stop_cooldown(#{cd})")
    # entry_not_confirmed (S4_ENTRY_CONFIRM_V1=1): signal bar close in trade direction, tol = max(0.10×mean range14, 0.5)
    rng14 = [b["h"] - b["l"] for b in pos_all[max(0, k - 14):k]]
    tol = max(0.10 * (sum(rng14) / len(rng14)) if rng14 else 0.0, 0.5)
    sb = rth[idx]
    conf_ok = (sb["c"] > sb["o"] - tol) if d == "LONG" else (sb["c"] < sb["o"] + tol)
    if not conf_ok:
        later.append("entry_not_confirmed")
    # RR gates — judged on the bracket that reaches :3774 (the step ladder when it exists)
    if t1_l is not None and risk_l and (ladder or r["t1_source"] != "1R-fallback"):
        t1d = (t1_l - entry) * sgn
        if t1d <= 0:
            later.append("t1_wrong_side")
        elif t1d / risk_l < 0.3:
            later.append("rr_hard_floor")
        elif t1d < risk_l * rr_min:
            later.append(f"rr_entry_gate({t1d / risk_l:.2f}<{rr_min})")
        r["rr"] = round(t1d / risk_l, 2)
    else:
        r["rr"] = None
    if daily_pnl_before(decision_utc) <= -450:
        later.append("daily_loss_halt")
    ls = live_slot_open(decision_utc)
    if ls:
        later.append(f"live_slot_occupied(#{ls})")
    if n_c == 0:
        later.append(f"risk_budget_reject[{n_why}]")
    r["later_gates"] = later
    r["admitted_live"] = (not blocks_live) and not later
    r["admitted_relaxed"] = (not blocks_relaxed) and not later
    r["relaxation_delta"] = r["admitted_relaxed"] and not r["admitted_live"]
    r["blocked_only_by_variation_rule"] = (bool(blocks_live) and not blocks_relaxed)
    results.append(r)

json.dump(results, open(os.path.join(W, "reactive_replay.json"), "w"), indent=1, default=str)
print("replayed:", len(results), "skipped:", sum(1 for r in results if r.get("skip")))
```

### reactive_summary.py
```python
import os, sys, json, collections
import psycopg2, psycopg2.extras
from zoneinfo import ZoneInfo
W = os.path.dirname(os.path.abspath(__file__))
R = [r for r in json.load(open(os.path.join(W, "reactive_replay.json"))) if not r.get("skip")]
IL = ZoneInfo("Asia/Jerusalem")

def win(rs):
    dec = [r for r in rs if r["outcome"] in ("T1", "STOP")]
    return (100.0 * sum(1 for r in dec if r["outcome"] == "T1") / len(dec)) if dec else float("nan")

def agg(rs, label):
    n = len(rs)
    usd = sum(r["usd_first"] for r in rs); usdc = sum(r["usd_close"] for r in rs); usdh = sum(r["usd_hold_stop"] for r in rs)
    t1 = sum(1 for r in rs if r["outcome"] == "T1"); st = sum(1 for r in rs if r["outcome"] == "STOP"); op = n - t1 - st
    usdp = sum(r["usd_first_prod"] for r in rs); usdhp = sum(r["usd_hold_stop_prod"] for r in rs)
    t1p = sum(1 for r in rs if r["outcome_prod"] == "T1"); stp = sum(1 for r in rs if r["outcome_prod"] == "STOP")
    wp = (100.0 * t1p / (t1p + stp)) if (t1p + stp) else float("nan")
    print(f"{label:58s} n={n:3d} | LIVE-bracket(step-ladder): T1={t1:3d} STOP={st:3d} OPEN={op:2d} win%={win(rs):5.1f} Σ$first={usd:9.2f} Σ$hold(stop)={usdh:9.2f} Σ$close={usdc:9.2f}"
          f" | PRODUCER-bracket: T1={t1p:3d} STOP={stp:3d} win%={wp:5.1f} Σ$first={usdp:9.2f} Σ$hold(stop)={usdhp:9.2f}")

def window(rs, name):
    print(f"\n===== {name}: {len(rs)} setups =====")
    lab = collections.Counter(r["label"] for r in rs)
    print("label@moment:", dict(lab.most_common()))
    print("hist first blocker:", dict(collections.Counter(str(r["first_blocker"]) for r in rs).most_common()))
    print("dalton LIVE verdict:", dict(collections.Counter(str(r["dalton_live"]) for r in rs).most_common()))
    var = [r for r in rs if r["label"] in ("Variation", "Normal_Variation")]
    print(f"Variation-label at moment: {len(var)}  · pre-IB-lock: {sum(1 for r in rs if r['pre_ib_lock'])}")
    only_var = [r for r in rs if r["blocked_only_by_variation_rule"]]
    print(f"blocked ONLY by the Variation rule (dalton live blocks, relaxed passes): {len(only_var)}")
    still = [r for r in only_var if r["later_gates"]]
    print(f"  of which still blocked by a later gate: {len(still)}  →", collections.Counter(g.split('(')[0].split('[')[0] for r in still for g in r["later_gates"]))
    adm = [r for r in only_var if not r["later_gates"]]
    agg(adm, "  ADMITTED by relaxation (passes every replayed later gate)")
    agg([r for r in adm if r["with_ext"] == "WITH"], "    ├ WITH extension")
    agg([r for r in adm if r["with_ext"] == "AGAINST"], "    ├ AGAINST extension")
    agg([r for r in adm if r["with_ext"] == "NONE"], "    └ no extension (inside IB)")
    agg(only_var, "  ALL Variation-rule-blocked incl. later-gate (bars only)")
    agg([r for r in only_var if r["with_ext"] == "WITH"], "    ├ WITH extension")
    agg([r for r in only_var if r["with_ext"] == "AGAINST"], "    ├ AGAINST extension")
    agg([r for r in only_var if r["with_ext"] == "NONE"], "    └ no extension")
    live_adm = [r for r in rs if r["admitted_live"]]
    agg(live_adm, "  admitted under LIVE dalton (Normal/Neutral etc.), replayed")
    agg(var, "  every Variation-label setup (context, bars only)")
    agg([r for r in var if r["with_ext"] == "WITH"], "    ├ WITH extension")
    agg([r for r in var if r["with_ext"] == "AGAINST"], "    ├ AGAINST extension")
    agg([r for r in var if r["with_ext"] == "NONE"], "    └ no extension")
    return adm

sep = [r for r in R if r["session"] >= "2026-09-01"]
w1 = [r for r in R if "2026-07-07" <= r["session"] <= "2026-08-28"]
w2 = [r for r in R if r["session"] == "2026-08-31"]
adm_sep = window(sep, "SEPTEMBER 2026-09-01 → 09-10")
adm_w1 = window(w1, "2026-07-07 → 08-28")
window([r for r in R if "2026-07-07" <= r["session"] <= "2026-07-31"], "JULY only 07-07 → 07-31 (old detector regime, ~12 setups/session)")
window([r for r in R if "2026-08-01" <= r["session"] <= "2026-08-28"], "AUGUST only 08-01 → 08-28")
window(w2, "2026-08-31 (between windows)")
window(R, "ALL 07-07 → 09-10")
print("\n===== detection density (real setups / session) =====")
per = collections.Counter(r["session"] for r in R)
for m in ("2026-07", "2026-08", "2026-09"):
    ss = [s for s in per if s.startswith(m)]
    print(m, "sessions:", len(ss), "setups:", sum(per[s] for s in ss), "per session: %.1f" % (sum(per[s] for s in ss) / max(1, len(ss))))
print("\n===== admitted-by-relaxation, per-setup list (all windows) =====")
for r in sorted([r for r in R if r["blocked_only_by_variation_rule"] and not r["later_gates"]], key=lambda r: r["signal_bar_utc"]):
    print(f"{r['decision_il']} {r['direction']:5s} e={r['entry']:<8.2f} LIVE stop={str(r['stop']):8s} t1={str(r['t1']):8s} risk={r['risk_pts']:5.2f} n={r['contracts']} out={r['outcome']:4s} $first={r['usd_first']:8.2f} $holdstop={r['usd_hold_stop']:8.2f}"
          f" | PROD stop={str(r['stop_prod']):8s} t1={str(r['t1_prod']):9s} {str(r['t1_source'])[:12]:12s} n={r['contracts_prod']} out={r['outcome_prod']:4s} $first={r['usd_first_prod']:8.2f}"
          f" | ext={str(r['ext_dir']):4s} {r['with_ext']:7s} mfe={r['mfe']:5.2f} mae={r['mae']:5.2f} label={r['label']} hist={str(r['first_blocker'])}")

print("\n===== September setup-by-setup =====")
hdr = f"{'decision IL':11s} {'dir':5s} {'entry':8s} {'LIVEstop':8s} {'LIVEt1':8s} {'PRODstop':8s} {'PRODt1':8s} {'label@moment':17s} {'ext':5s} {'W/A':7s} {'hist_first_blk':20s} {'dalton_live':22s} {'later_gates':44s} {'n':2s} {'out':5s} {'$first':8s} {'$holdst':8s} {'$close':8s} {'mfe':5s} {'mae':5s} {'PRODout':7s} {'PROD$':8s}"
print(hdr)
for r in sorted(sep, key=lambda r: r["signal_bar_utc"]):
    print(f"{r['decision_il']:11s} {r['direction']:5s} {r['entry']:<8.2f} {str(r['stop']):8s} {str(r['t1']):8s} {str(r['stop_prod']):8s} {str(r['t1_prod'])[:8]:8s} "
          f"{str(r['label']):17s} {str(r['ext_dir']):5s} {r['with_ext']:7s} "
          f"{str(r['first_blocker'])[:20]:20s} {str(r['dalton_live'])[:22]:22s} {str(r['later_gates'])[:44]:44s} {str(r['contracts']):2s} "
          f"{r['outcome']:5s} {r['usd_first']:8.2f} {r['usd_hold_stop']:8.2f} {r['usd_close']:8.2f} {r['mfe']:5.1f} {r['mae']:5.1f} {r['outcome_prod']:7s} {r['usd_first_prod']:8.2f}")

print("\n===== label agreement =====")
both = [r for r in R if r["label_sierra_ib"] is not None]
print("bars-IB label == Sierra-IB label:", sum(1 for r in both if r["label"] == r["label_sierra_ib"]), "/", len(both))
rec = [r for r in R if r["day_type_at_fire"]]
print("bars-IB label == recorded day_type_at_fire:", sum(1 for r in rec if r["label"] == r["day_type_at_fire"]), "/", len(rec))
print("recorded day_type_at_fire distribution:", dict(collections.Counter(str(r["day_type_at_fire"]) for r in R).most_common()))

print("\n===== scoring-model sanity vs broker-priced live REACTIVE =====")
conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("""SELECT id, entry_ts, direction, entry_price, pnl_sierra, exit_reason, quality->>'contracts' AS c, t1_hit_ts, stop_hit_ts
               FROM v9_trades WHERE mode='live' AND pnl_sierra IS NOT NULL AND state<>'CANCELLED' AND pattern_id_at_entry LIKE 'REACTIVE%%'
               AND entry_ts >= '2026-07-07' ORDER BY entry_ts""")
live = cur.fetchall()
tot_model = tot_real = 0.0
for t in live:
    m = next((r for r in R if any(tr["id"] == t["id"] for tr in r["trade_rows"])), None)
    if m:
        tot_model += m["usd_first"]; tot_real += float(t["pnl_sierra"])
        rec = next((tr for tr in m["trade_rows"] if tr["id"] == t["id"]), {})
        print(f"#{t['id']} {t['entry_ts'].astimezone(IL).strftime('%m-%d %H:%M')} {t['direction']:5s} real=${float(t['pnl_sierra']):8.2f} ({t['exit_reason']}, c={t['c']}, rec stop={rec.get('initial_stop')} t1={rec.get('t1')}) "
              f"LIVE-model={m['outcome']:4s} ${m['usd_first']:8.2f} (n={m['contracts']}, stop={m['stop']}, t1={m['t1']} {m['bracket_source']}) mfe={m['mfe']} mae={m['mae']} label={m['label']} ext={m['with_ext']}")
print(f"Σ real={tot_real:.2f}  Σ LIVE-bracket model(first-touch, live sizing)={tot_model:.2f}  n={len(live)}")

print("\n===== September book (live, broker-priced) by session =====")
cur.execute("""SELECT (entry_ts AT TIME ZONE 'America/New_York')::date AS d, pattern_id_at_entry, count(*) n, sum(pnl_sierra) usd
               FROM v9_trades WHERE mode='live' AND pnl_sierra IS NOT NULL AND state<>'CANCELLED' AND entry_ts >= '2026-09-01'
               GROUP BY 1,2 ORDER BY 1,2""")
tot = 0.0
for r in cur.fetchall():
    tot += float(r["usd"]); print(f"{r['d']} {str(r['pattern_id_at_entry']):24s} n={r['n']} Σ${float(r['usd']):8.2f}")
print("September total:", round(tot, 2))
cur.execute("""SELECT (entry_ts AT TIME ZONE 'America/New_York')::date AS d, count(*) n, sum(pnl_sierra) usd
               FROM v9_trades WHERE mode='live' AND pnl_sierra IS NOT NULL AND state<>'CANCELLED' AND entry_ts >= '2026-09-01' GROUP BY 1 ORDER BY 1""")
print("by session:", [(str(r["d"]), r["n"], float(r["usd"])) for r in cur.fetchall()])
```
