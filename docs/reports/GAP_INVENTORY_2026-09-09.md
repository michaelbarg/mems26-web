# GAP INVENTORY — 09.09.2026 · "להשלים את הפערים שמעולם לא פותחו ולסדר את כל המערכת"

**Question (Michael 09.09 09:20):** one inventory of everything he ruled/asked that became a gate instead of a producer, was built and silently vetoed, was specified and never built, or landed dead.
**Written:** 09.09 09:55 IL · cowork-dev · **READ-ONLY** at `HEAD d5a5cf46` (09:10). No code, service, `.env`, flag or position touched. Sibling report from the same hour, hygiene angle: `docs/reports/CLEANUP_LIST_2026-09-09.md` — cross-referenced, not duplicated.
**Sources swept:** `config/RULED_FLAGS.yaml` (248 rows) · `docs/plans/TASK_LOG.md` (288 T-rows, 212 open) · `docs/handoff/CC_*.md` (433 files; the 14 since 06.09 read in full, older ones via the citations they carry) · `docs/spec_authority/*.md` (49) + `docs/*SPEC*.md` (2) · `docs/handoff/PHONE_THREAD.jsonl` (451 lines, 106 by Michael; searched `אני רוצה`/`צריך`/`חייב`/`לתקן`) · `docs/reports/MEASUREMENTS.md` · `.env` (314 keys; values only, no secrets quoted).
**Verification:** four read-only code sweeps (producers · stops/targets/sizing · trade-management/DLL · S1/gates/flags), every claim below carries `file:line` or the exact grep string and its count. Line numbers are HEAD, not the estimates in older handoffs. `grep ⇒ 0` rows list the variants tried.

## 0 · Counts

| status | rows | meaning |
|---|---|---|
| **SPEC-ONLY** | 18 | ruled/ordered, zero production code |
| **RULED-AS-GATE** | 10 | Michael asked for an entry/producer; what exists is a veto/exemption |
| **LIVE-DEAD** | 25 | flag on (or code present), path cannot execute |
| **LIVE-VETOED** | 10 | built + enabled, another gate/stage makes it unreachable |
| **CONTRADICTED** | 15 | two rulings/docs/measurements conflict |
| **SHADOW-UNMEASURED** | 8 | in shadow, no number in `MEASUREMENTS.md` |
| **SHADOW-MEASURED** | 9 | in shadow with a number |
| **LIVE-OK** | 12 | built, reachable, measured, matches the ruling (listed for completeness) |
| **total** | **107** | |

**The shape, in one sentence:** every positive instruction ("enter here", "trade the belly", "5 contracts", "size to the stop") was absorbed by the subtractive half of the system — 24 gates, 5 target writers and 3 stop rewriters, each individually ruled — and the item was closed; the four things Michael asked for that are *producers* (`CONTEXT_ENTRY`, `VALUE_RETURN`, `BALANCE_DEPART`, the session state-machine) have **zero lines of code** at HEAD.

Column key: **asked/ruled** = file · date · quote (≤12 words) · **code** = what exists at HEAD · **evidence** = number or grep.

---

## 1 · SPEC-ONLY — ruled or ordered, no production code (18)

| # | item | asked / ruled | code at HEAD | evidence |
|---|---|---|---|---|
| G-01 | **`CONTEXT_ENTRY_V1`** — balance→discovery producer ("price is searching for a new place") | `MICHAEL_ISSUES_LEDGER.md:73` item 24 (02.07) *"יום טרנדי שמחפש מקום"* · `CC_TASK_DALTON_SIM_FIRST.md:9-11` (23.08) *"המערכת כולה חיסורית… אין היגיון חיובי"* · `CC_BUILD_2026-08-24.md:23-31` ruling | `grep -rn "CONTEXT_ENTRY\|context_entry\|BALANCE_DEPART" backend/ config/ scripts/` ⇒ **0** | replay **+$5,973 / 34 sessions (OOS +$2,235)** (`TASK_LOG.md:84`, `SIM_DALTON_OVER_DETECTORS.md`); T-105 next-step reads `אל תתחיל`, blocked on T-103→T-100/T-104 since 25.08 (`TASK_LOG.md:312`) |
| G-02 | **`VALUE_RETURN_V1`** — first rotation back toward the developing POC ("the belly") | raised 7× 15.07→06.09 (`AUDIT_VALUE_RETURN_REQUEST_2026-09-08.md` §1 A1-A7) · `CC_REBUILD_2026-09-09.md` §4 (09.09 08:40) | `grep -rn "VALUE_RETURN\|toward_poc\|revert_to_poc\|mean_revert" backend/` ⇒ **0** | closest measurement `TERMINATION_REVERSAL_2026-09-08.md`: T3 (return through IB edge) **+$150 / n=10**, T1 −$1,473.75 — "the read is right, the geometry is wrong" |
| G-03 | **`BALANCE_DEPART_V1`** — entry on the acceptance bar leaving balance | `CC_REBUILD_2026-09-09.md` §4 · same ruling as G-01 | `grep -rn "BALANCE_DEPART\|balance_exit\|leaves_value\|break_of_balance" backend/` ⇒ **0** | `SYSTEM_BRAIN.html:54` (22.08): *"✗ לא קיים בכלל — וזה המצב הבסיסי ביותר בדלתון"* |
| G-04 | **`DALTON_PLAYBOOK_V1`** — session state machine `intent(phase, opening_type, day_type)` replacing compass/playbook/location_gate | Michael 09.09 09:15 *"כל סוג-פתיחה צריך להיכנס לעץ-החלטות אחר"* (`CC_DALTON_PLAYBOOK_2026-09-09.md:4`) | `grep -rn "DALTON_PLAYBOOK\|dalton_intent\|dalton_playbook" backend/ config/` ⇒ **0** | replay gate defined (`:60-69`); `CLEANUP_LIST §3.1`: ≈400 lines of `trading_gateway.py` become obsolete |
| G-05 | **`TRADE_ECONOMICS_AUTHORITY_V1`** — one pure `economics()`: producer's anchor + S1 table, no ATR compression | Michael 09.09 08:40 *"5 חוזים, פשוט שיסחור נכון"* + 09:05 *"אני רוצה תיקון היום"* (`CC_REBUILD §2-§3`) | `grep -rn "trade_economics\|TRADE_ECONOMICS" backend/` ⇒ **0** | reference case 08.09 18:20: S2 stop 7676/t1 7711 → chain 7693.75/7703.25 → `rr_hard_floor` 0.27 (`trading_gateway.py:3667-3674` comment) |
| G-06 | **`NO_LABEL_NO_FIRE_V1`** — after IB lock, `get_live_day_type() is None` ⇒ shadow | Michael 09.09 *"S1 צריכה לזהות… S2/S4 בתיאום"* (`CC_REBUILD §5א`) · T-266 (07.09) | `grep -n "day_type_known\|no_daytype_label" trading_gateway.py` ⇒ 0; every consumer fail-opens on None: `daytype_playbook.py:190-191` (unmapped⇒FULL), `daytype_position_gate.py:108-109`, S4 `woodies_system.py:673-700` never refuses | 20/46 live trades fired without a label (`DAY_AUDIT_*`); 14/39 since 24.08 with `t4=NULL` (`CC_TODAY_GAPS §A`) |
| G-07 | **REACTIVE spec 28.06** — second-test entry · stop `min(low b1..b3)−2T` · targets HVN→POC→VAH · C1→T1/C2→T2/C3→T3 | `REACTIVE_SPEC_DRAFT.md:3` *"לא יושם בקוד — מסמך-אישור בלבד"*; Michael closed 3/4 items 28.06 (`:89-91`) | `_detect_reactive` `five_min_system.py:874-1130`: no second-test (only mention `:1138` INITIATIVE docstring); stop = 12-bar+6T (`stop_anchors.yaml:16-17,94`); targets = 5 R/structure writers, none HVN (`S1_S2_SPEC_CONFORMANCE §2.3`) | **72 days**; `v9_tpo_sessions.hvn_zones` empty ⇒ no backtest possible (`REACTIVE_SPEC_DRAFT.md:67`) |
| G-08 | **INITIATIVE spec 30.06** — acceptance `accept_N` closes, reference-distance cap `min(IB,ATR)`, trail-first R | `INITIATIVE_SPEC_TOOLCONSTRAINED_2026-06-30.md:3` *"PRIORS to calibrate"* — never explicitly ruled to build | `_detect_initiative` `five_min_system.py:1127-…`: none of acceptance / reference-distance / trail exists (`S1_S2 §1.2`) | T-80: `b1_exp ∧ b3_join` = 0/64 bars on 20.08 — the built geometry rarely completes |
| G-09 | **SCALE_IN pullback + continuation confirmation** | Michael phone 28.08 14:27 `15618e84` *"לא תגדיל עסקה ללא אישור של פול-באק וזיהוי המשך מגמה"* (T-121 🔴) | `grep -i pullback backend/v9/services/trade_manager/scale_in.py` ⇒ **0**; P3 adds at the bar's favourable extreme (`scale_in.py:161`, spacing/RR/edge-ban only `:165-189`) | SCALE_IN itself is dead since 01.09 (G-45) — condition can be built when it is revived |
| G-10 | **Auto-renew `config/manual_position_ack.json` in the pre-open gate** | ruled 01.09 (T-171 closure: *"לחדש להיום + לבנות חידוש-אוטומטי"*), T-234 🔵 | `grep -rn manual_position_ack scripts/ backend/` ⇒ 2 hits, both `entry_guard.py` (:56 path, :168 comment) — **no writer** | 4th manual renewal 07.09; renewed by cowork again 09.09; expired ack ⇒ `ENTRY_GUARD` blocks 100% while Eti holds a position (25.08: 19/19) |
| G-11 | **Learning loop stages 4-5** (judge vs threshold · surface) | Michael 01.09 *"לבנות לולאת למידה ותיקוני עומק"* (T-204 🔴) · `CC_TUESDAY_2026-09-06.md §9ג` | `scripts/mechanism_verdict.py` exists (07.09) — **no scheduler/caller** (`grep mechanism_verdict *.sh *.plist` ⇒ 0); `DAILY_VERDICT.md` last generated 07.09; backend `RESOLVED` writer ⇒ **0** (T-233); `candidate_resolver.py` writes JSONL, not a table | ledger funnel 02.09: `RESOLVED 0/43` (`TASK_LOG.md:301`) |
| G-12 | **EXIT-v2** — partial exit (`op=EXIT` returns r=−1 because every contract is bracketed) | `CLAUDE.md` §op=EXIT (13.07, *"until EXIT-v2 ships"*) · `CC_PROMPT_2026-07-14_EXIT_OP_REBUILD.md` · T-199 🔴 | `sc_study/MES_AI_DataExport_merged.cpp:3572-3630` unchanged since 07-13; `grep -ri "EXIT_V2\|ExitV2\|FlattenPartial" sc_study/` ⇒ 0; `git log --since=2026-07-14 -- sc_study/` = 39 commits, none EXIT | blocks: partial realise, `CF_BANK_LONG` "bank half", S6 reversal half, `STALL_EXIT`/`OPPOSITE_EXIT` (both unset by ruling) |
| G-13 | **`STRUCTURE_EXIT_REVERSAL_V1`** (grade of the 4-grade exit ladder) | T-141 ruled 30.08 *"מאשר"* (`TASK_LOG.md:528`) · `STRUCTURE_EXIT_DOCTRINE.md` | `should_exit_on_reversal` (`structure_exit.py:156`) — **0 production callers**; **no `getenv` anywhere** for the flag; RULED_FLAGS `:399` expects `unset_or_0` | the other two grades are wired (FAILBREAK shadow `bar_level_detector.py:1620`, DOUBLE `:1782`) |
| G-14 | **CF consumers** `CF_BANK_LONG_V1` (tighten on double-top vs position) · `CF_EDGE_LOCK_V1` (no new long under a failed ceiling) | Michael 08.09 08:30 *"כן"* (`CC_CF_CONSUMERS_2026-09-08.md`) · original 28.08 spec (T-138: `CEILING_EXIT/LONG_LOCK`) | `grep -rn "CF_BANK_LONG\|CF_EDGE_LOCK\|CEILING_EXIT\|LONG_LOCK" backend/ config/` ⇒ code **0** (only `RULED_FLAGS.yaml:401` note) | ordered for after 20:00 08.09 — not landed; `CEILING_FLOOR_STATE_V1` detects only (`five_min_system.py:1664,1771-1772`) |
| G-15 | **"הכל יחסי" conversion scan** — absolute thresholds → ATR/leg/VA-relative in existing gates | Michael 28.08 ruling (T-132 🔴 *"ספים מוחלטים→יחס-ATR/רגל/VA… + סריקת-המרה"*) | still absolute in `.env`: `RELEASE_ZONE_POINTS=8`, `RELEASE_TREND_BYPASS_PTS=12`, `STOP_ANCHOR_OFFSET_TICKS_OVERRIDE=16`, `T0_TARGET_PTS=3.0`, `CHASE_MIN_SESSION_BARS=8`, `PULLBACK_MIN_PTS=3.0` (`entry_location_quality`) | converted so far: `LSMA_FLAT_ATR_V1`, `S6_MAE_SCRATCH_ATR_V1`, `STOP_FLOOR_IB_V1`, `S2_ADAPTIVE_THRESHOLDS_V1` |
| G-16 | **Mid-trade re-pricing on day-type change** | Michael 01.09 18:10 (T-214 🔴 *"המימוש אינו מסתגל לשינוי סוג-היום"*) — #942 tagged Trend_Normal, day became Variation 14:35, t3 never moved | `RUNNER_BY_DAYTYPE_V1` acts at **entry only** (`sierra_command.py:985-1010`); `apply_target_realism_perbar` tightens only on session extreme (`manager.py:1122`); no reclass listener on open trades | T-214 belt (`T3_REQUIRED_V1`) was built instead — see G-25 |
| G-17 | **TREND_STEP with candle body + volume expansion** (Michael's two inputs) | Michael 13.08 *"שוב יש מדרגה למעלה שהמערכת לא זיהתה"*; inputs named 08.09 | detector never reads open (`trend_step/detector.py`: `"o"` ⇒ 1 hit, `:309` row-mapping only); volume test contradicts expansion (`VOL_RATIO_MAX≤1.10` vs `VOL_EXP_MIN≥1.15`, same bar) | `TREND_STEP_AUDIT_2026-09-08.md`: **n=0 under every expansion value**, `ENTRY_ON_BREAK` n=0 IS and OOS ⇒ *"גרסה-מאושרת היא גלאי חדש, לא פרמטר"* |
| G-18 | **TPO `market_ts`/`available_at` columns** (causal §D for every TPO-fed pattern) | T-185 🟠 · T-100 🔴 (TPO lookahead **92.3%**: 2,294/2,486 choices used a row created 3h after the candidate) | writer fixed (`7645a4de`), columns absent: 728/729 historical rows `created_at > ts` | `DALTON_EDGE_V1=live` runs on this input; the +$5,973 of G-01 is on the uncorrected feed (fix flipped a parallel metric +$339→−$558.76) |

---

## 2 · RULED-AS-GATE — asked for an entry, got a veto/exemption (10)

| # | item | asked / ruled | what got built | evidence |
|---|---|---|---|---|
| G-19 | **"rotation to POC" A1-A5** → `DAYTYPE_LOCATION_GATE=1` | 15.07 `EXECUTION_REPORT_2026-07-15.md:9` *"רוטציה סביב VAH/VAL/POC"* · 16.07 `CC_NIGHT_PROMPT_2026-07-16.md:14` *"מכיוון-לכיוון ואז POC"* · 21.07 `CC_T1_STRUCTURE_END_2026-07-21.md:71` *"כניסה ב-VAH שורט לאחר בדיקה"* | gate: `trading_gateway.py:1660` → `location_gate.decide_location:170` (REV only at VA edge after probe; CONT against expansion ⇒ block `:187-199`), `blocked_by="location_gate"` `:1733` | `ASYMMETRY_17D §`: `location_gate` n=11, saved/blocked 1.52; the POC-destination *trigger* does not exist (G-02) |
| G-20 | **POC rule 19.07 "✅ אושר"** → `reactive_location_gate.py` | `DIRECTION_AUTHORITY_MAP_2026-07-19.md:36,57` | gate, `REACTIVE_LOCATION_GATE` default `"0"`, `.env=0`; blocks REACTIVE_LONG above POC / SHORT below (`reactive_location_gate.py:43-46`, gateway `:1639-1649`) | POC is a *boundary* in code, never a destination |
| G-21 | **"trend day searching for a place — only with-direction until a proven stop"** → `DAY_DIRECTION_DOCTRINE_V1` | `MICHAEL_ISSUES_LEDGER.md:73` item 24 (02.07, *"נפסק (פריט-18)"*) · `CC_PATTERN_ECONOMICS_PACKAGE_2026-07-02.md:206` | gate: `trading_gateway.py:2750` `getenv("DAY_DIRECTION_DOCTRINE_V1","0")` → `blocked_by="day_direction_doctrine"` `:2796`; **unset in `.env`, no RULED_FLAGS row** (dead branch, unowned) | the departure entry itself = G-03 (zero code) |
| G-22 | **"unless we see it searching a new place / stairs above VAH"** → exemption clause of `NO_CHASE_V1` | `CC_WORKORDER_2026-09-01_NO_CHASE.md:16-17` + `:138` *"לא לייצר כניסות חדשות. זה שער-חסימה בלבד"* | `grep -rn "NO_CHASE\|no_chase" backend/ config/ scripts/` ⇒ **0** — neither the gate nor the exemption was built | Michael's positive signal was specified as a negative gate's escape hatch (`AUDIT_VALUE_RETURN §2 B6`) |
| G-23 | **"the market went to build the belly and the system didn't use it"** → fix #1 `DAYTYPE_DIR_DISCIPLINE_V1` (a SKIP gate) | Michael 06.09 17:49 (`CC_DAYTYPE_MGMT_2026-09-06.md:4`) | `grep -rn DAYTYPE_DIR_DISCIPLINE backend/ config/` ⇒ **0**; withdrawn 06.09 19:50 after 10-day replay | **−$121 net** (blocks 8 winners −$577.50 vs 3 losers +$300) (`CC_TUESDAY_2026-09-06.md:5`) |
| G-24 | **"contracts relative to risk, so the stop sits right — fewer contracts"** → `RISK_BUDGET_SIZING_V1` that **rejects** | Michael 01.09 (T-198 🔴 *"כן נכנס לעסקה ופחות חוזים"*) · then `RISK_MIN_CONTRACTS=3` ruled the same day (`RULED_FLAGS` *"n<3=דחייה"*) | `sierra_command.py:712-721`: `n=floor(225/(risk×5))`, `n<3 ⇒ return 0` ⇒ hard ceiling **risk ≤ 15.00 pt**; `RISK_MAX_PTS_HARD=30` (`:711`) dead in practice; `contract_ladder` in `stop_anchors.yaml:22-25` (≤15→3 · 15-25→2 · >25→1) overwritten by `sizing.py:124-126` `contracts=_n` | 30/54 structural stops rejected outright, every sent stop ≤15.00 (`RELEASE_EXEMPTION`/`STRUCTURAL_STOP_REPLAY` 08.09); sizer slope inverted: losers 3.24c/6.07pt vs winners 3.06c/7.36pt, monotone over 6 bands (`ASYMMETRY_17D`) |
| G-25 | **"stop + realisation for the last contract in every certainty state"** → `T3_REQUIRED_V1` belt | Michael 01.09 (T-214) · RULED_FLAGS 02.09 *"PLACE בלי t3 תקף ב-≥3 חוזים נדחה"* | `sierra_command.py:894-904` rejects `t3<=0 and contracts>=3` | rejected **100% of opening trades 02.09→08.09** (`opening_entry` emitted `t2/t3=None`) — 6 sessions silent, gateway read the rejection dict as success (P0 #1220, `ca558bd9`); still rejects every `SCALE_IN` child (G-45) |
| G-26 | **"the right entries (17:00-17:35) were blocked, the chasers passed"** → `ENTRY_LOCATION_QUALITY_V1=1` | T-130 (28.08) → Michael ruled the gate 28.08 18:50 *"pos>0.66 בלי פולבק = רודף"* | gate `trading_gateway.py:1769` → `entry_location_quality.py:90`; leg = session extreme (T-236/T-242) ⇒ self-tightening on trend days; `has_pullback` not passed until `8514bf33` (T-235); `ELQ_LEG_FROM_BREAK_V1=1` (06.09) | 03.09: **28 with-direction longs blocked in a 61.5-pt belly** (`CC_DAYTYPE_MGMT §3`); after fixes 82/103 pass, 0 stay blocked (T-244) ⇒ near-inert; `ASYMMETRY`: n=60, saved/blocked **0.54** |
| G-27 | **Playbook prose Michael ruled** (Variation *"WITH the IB expansion only; enter on pullback to broken edge"*, Normal *"fade VA edges"*) | `config/daytype_playbook.yaml:70,81-92` (rulings 16.07 / 01.09) | fields `bias` · `fade_edges` · `ref_points` · `runner` · `c3` · `contracts` · `time_stop_minutes` — **0 readers** (`grep -rn "fade_edges\|ref_points\|\"bias\"" backend/` ⇒ 0; only `structural_targets.py:38` reads `style.get("target")`; `_pb.contracts` 0 consumers in gateway) | the only playbook effect on a fire is `allow/SKIP` (`trading_gateway.py:1494`) — the ruling became a cell, the instruction stayed prose |
| G-28 | **"allow the counter-side when an EXCESS extreme stops the move"** → exemption inside a SKIP | Michael 11.08 live ruling (`RULED_FLAGS` `EXCESS_COUNTER_ENTRY_V1`) | `daytype_playbook.py:274-283` `_excess_exempt` inside the Variation counter-trend SKIP branch; creates no setup | replay n=4, **+$2** (RULED_FLAGS note); no fire attributable since |

---

## 3 · LIVE-DEAD — flag on / code present, path cannot execute (25)

| # | item | asked / ruled | code at HEAD | evidence |
|---|---|---|---|---|
| G-29 | **`STOP_MOVE_TARGET_RESTORE_V1`** (backend restore of a target dragged by BE) | `CC_TUESDAY_2026-09-06.md §4` (*"תיקון-באג — יעד לא אמור לזוז עם סטופ"*), $91.25 measured 3/3 | reads `quality.c{n}_target_price` (`manager.py:386`) — **0 writers** (`grep _target_price backend/` ⇒ 2, both MGR); `manager.py:396` `_ord.get("order_id")` vs DLL writes `"id"` (`cpp:2047`) — **not fixed**; `.env=0` declared 07.09 pending sim | dead ×2 as landed (`CC_FIX_DEAD_2026-09-07 §3`) |
| G-30 | **DLL MODIFY_STOP target-restore branch** | same ruling; broker log 04.09 (`CC_DAYTYPE_MGMT §2`) | `MES_AI_DataExport_merged.cpp:3176-3186` snapshot, `:3203-3218` restore `if (to2.Price1 != tgt_prices[ti])` — did not run in 3/3 BE events; `MODIFY_TARGET` handler `:3227-3249` bare `ModifyOrder` **no stop protection** (18:31:04 dragged stop +8.00) | #1008 target +8.00 · #1069 +5.50 · #1073 −6.50 (missed fill +$52.50); sim diagnosis ordered 06.09 — `git log sc_study/` since: 0 |
| G-31 | **`DYNAMIC_STRUCT_TRAIL=1` + `STOP_PERBAR_STRUCT_V1=1`** (*"לבדוק על כל נר את הסטופ"*, ruled 07-10) | RULED_FLAGS 07-10 FIX-15 | `bar_level_detector.py:961-962` `if _f5 is not None: pass` — F5 (`RUNNER_TRAIL_V2`) returns **False** on HOLD (`manager.py:1311-1316`), False ≠ None ⇒ `:963 elif DYNAMIC_STRUCT_TRAIL` and `STOP_PERBAR_STRUCT_V1` (`manager.py:1084`, only via `apply_dynamic_struct_trail :1521-1539`) never run post-T1 | #1073: **0 stop moves in 88 min**, `SWING_TRAIL n=0` all day (`CC_DAYTYPE_MGMT §4`); §4(b) "give DYNAMIC a turn when tightens=False" — `grep tightens\|_f5` in diff since 06.09 ⇒ 0 |
| G-32 | **`swing_trail` reversal threshold from the *prior* session** | `CC_DAYTYPE_MGMT §4(a)` (rev from current-RTH ATR after 14 bars) | `swing_trail.py:64-85`: `rev = clamp(mean TR of prior RTH, 4, 12)` only; caller `manager.py:1270-1288` | 03.09 mean-TR 5.07 ⇒ rev 5.0 vs real swing 12.75 ⇒ `tightens=False` on 19/19 bars; runner leg −$161.25/14 (`CC_TUESDAY_2026-09-06.md:11`) |
| G-33 | **`TREND_LEG_CHASE_EXEMPT_V1=1`** | ruled 11.08 live (5 with-trend shorts blocked) | fixed 08.09 §C (`trading_gateway.py:2456` `str(_ecg_gldt() or "")`), but its **only consumer** is the revoke block `:2478-2481` gated by `EXTREME_CHASE_TIP_REVOKE_V1` — unset, no ruling row (`grep -c .env` ⇒ 0) | exemption logs only; harmless (revocation itself is off) |
| G-34 | **`S7_SHADOW_LOG_V1=1`** → ruling on `SYSTEM7_SCORE_V1` after 3 days (T-17) | ruled 05.08 (*"מצב-צל-3-ימים ⇒ דוח ⇒ פסיקת-הדלקה"*) | shadow logger `trading_gateway.py:3276-3283` receives `bar_ts=None` on live trades | `AUDIT_S7_2026-08-15.md:23`: *"13 עסקאות LIVE בחלון — 0 שורות S7"* — 35 days, ruling never became possible |
| G-35 | **`va_rule_read()` — Dalton's 80% rule** (open outside value, accepted back ⇒ rotation target = far VA edge) | `DALTON_DOCTRINE.md` P2-11 · `MOM_GAP_ANALYSIS` layer A | computed every bar since 07-13 (`day_context_extras.py:93`), consumer = `classifier_core.py:231-233` *"no gate yet"*; readers outside those two files ⇒ **0** | the one rule that models rotation-to-value is emitted and unconsumed |
| G-36 | **`balance_imbalance_toggle.py`** (BALANCE/IMBALANCE/TRANSITIONAL — the state Michael calls the most basic) | docstring `:10` *"consumable by S2 and S4 fire paths"* | no `getenv` (`grep getenv\|environ` in file ⇒ 0); sole caller `api/v9/context_radar.py:238` (dashboard) | this is the `phase` input G-04 needs |
| G-37 | **S1 targets table → S2 trades** (t2_r 2.5 on Variation · `time_stop_minutes` · contracts) | `S1_TRADE_MANAGEMENT_3CONTRACTS.md:3` (Michael 20.06 *"הגשר… כל היעדים מבוססי-מבנה"*) | live branch `five_min_system.py:3073-3079` (V2) prices `t1=R-ladder, t2=2R, t3=None`; table branch `:3080-3102` only on V2 failure; S2 time-stop consumer ⇒ **0** (only S4 `woodies_system.py:1478`); contracts `min(5, auth)` (`sierra_command.py:775`) | 07.09 16:35/16:40 REACTIVE `t2=2.00R` exactly while the gateway rejected the same setup *"on Variation"* (table says 2.5R, `targets_table.py:65`) — `S1_S2 §2.3` |
| G-38 | **`OPENING_FIRST_TRADE_STRICT_V1=1` direction arm** | ruled 31.07 *"העסקה הראשונה… בוודאות של סוג הפתיחה"* | `opening_entry.py:451-452` compares `OPEN_DRIVE_UP/DOWN`, `TEST_DRIVE_UP/DOWN` — labels **no producer emits** (`opening_detector_v2.py` returns `OPEN_DRIVE`/`OPEN_TEST_DRIVE`/… + separate `direction`); `grep OPEN_DRIVE_UP backend/` ⇒ only `opening_entry.py:407-408,451-452` | the binary veto at `:453` can never be True (T-15 pending: "$227.50 on 14.08") |
| G-39 | **`TREND_STEP_STAIR_OR_V1=1`** (*"ב להפעיל היום"* 18.08, +$350.50 replay) | RULED_FLAGS 18.08 | `trend_step/detector.py:184` relaxes the session-extreme filter — but every TREND_STEP setup is `shadow_only=True` (`backend/main.py:1144-1145`) since `TREND_STEP_ENTRY_V1=shadow` (23.08) | ON flag with zero live effect; changes which *shadow* candidates appear |
| G-40 | **`BULL_FLAG` arithmetic block** | T-92(a) 🟡 awaiting ruling | `stop_anchors.yaml:104 t1_r_max: 0.8` (`five_min_system.py:3008-3024`) vs `_effective_rr_min` 1.0 on Trend (`trading_gateway.py:737`) ⇒ **0.8 < 1.0 always** on its only FULL cells | one YAML line (0.8→1.05) or a `FLAG_RR_MIN` — never ruled |
| G-41 | **`EDGE_FADE_V1`** nesting (latent) | ruled OFF 08-02; T-92(c) | block `five_min_system.py:2242` sits inside `:1991 OPENING_ENTRY` → `:1989 FIRST_HOUR_TACTICAL` ⇒ 09:30-10:30 ET only; flag unset, no ruling row | 0 fires in 34 sessions even if enabled |
| G-42 | **Ownership exemption unreachable when the manual position is protected** | Michael 26.08 *"היום המערכת תסחור"* (`ENTRY_GUARD_OWNERSHIP_V1=1`), T-273 🔴 | `entry_guard.py:173-179` ack exemption, then `:204-217` unconditional `working > 0` ⇒ False — an acked position with stops blocks every fire | 24-25.08 27/27 blocks class; only a *naked* manual position can be exempted |
| G-43 | **`exit_fills` for FLATTEN exits** (T-62 anchor) | T-270 🟠 · T-193 (53 `incomplete` trades) | writer `manager.py:2189-2294` fed only by T1-T4/STOP branches of `fill_poller.py:1195/1216`; no EXIT/FLATTEN branch; DLL `FLATTEN_ACCOUNT` writes no fill (`cpp:3636-3644`) | every EOD/T10/MAE/manual exit leaves the ledger unpriced (money basis needs `sierra_activity_join`) |
| G-44 | **`EXIT_VERIFY_V1`** (*"ספרים נסגרים רק אחרי שסיירה מוכיחה"*, Michael 14-15.08) covers 2 of 8 exit paths | RULED_FLAGS 15.08 | `register(` callers ⇒ 2: `bar_level_detector.py:1130` (flag-OFF path) and `:1275` (mae_scratch); not registered: `eod_close_t10 :592`, `structure_exit :1760/:1818`, manual FLATTEN `mobile_monitor.py:537`, `write_cancel :640/:690`, `trades.py:171` | T-29: two consecutive days, 0 `[ExitVerify]` lines in live |
| G-45 | **`SCALE_IN_V1=1` / `SCALE_IN_P3_V1=1`** (ruled 13.08/24.08) | *"אפשר גם לחזק בעוד חוזים"* | child = `contracts=2, t2/t3=None` (`bar_level_detector.py:1512-1518`); `sierra_command.py:725-728` reads only `metadata.sizing_contracts` ⇒ RISK_BUDGET sizes the child 4-5; `T3_REQUIRED` `:894-904` rejects ⇒ rollback `:1550/1558` | **3/3 attempts refused since 01.09**; legs n=10 **−$157.50** (5W/5L), level-2 adds 0/3 −$257.50 (`SCALE_IN_CLEAN_2026-09-09.md`) — also the vetoed shape of G-25 |
| G-46 | **`SYSTEM6_AUTOCORRECT=protective` — MODIFY_TARGET half** | ruled 07-15 (protective set) · T-255 (39,639 rejections) | `_exec` `bar_level_detector.py:124-152` handles `MODIFY_STOP`/`DROP_TARGET` only; `MODIFY_TARGET` branch **absent**, `:147` *"has no executor here — advisory only"*; `target_divergence` demoted to WARN (`system6_supervisor.py:295-300`) | the reversal-tighten target correction (`:246/:257`) can never execute even if `SYSTEM6_REVERSAL_TIGHTEN_V1` were on |
| G-47 | **`va_sanity.va_quality()`** (*VA width ∉ [0.5,0.9]×range ⇒ SUSPECT ⇒ consumers get None*) | Michael 01.09 (T-203 🔴🔴, VA wrong **7 of 8 days**) | built `backend/v9/systems/va_sanity.py:54,70`; production callers ⇒ **0** (`grep -rl va_sanity backend` excl. tests ⇒ 0); levels still flow `tpo_system.py:453-478` → gateway `:1380-1390,:1665,:1791` | 4 live consumers: `location_gate`, `DALTON_EDGE`, playbook `fade_edges`, `target_zones` — 31.08 `VA=3.5` while `IB=29.5` |
| G-48 | **`cumulative_delta` dropped on the woodies failover republish** ⇒ `cvd_pos=None` for S1 | S1 "CVD-confirmed" confidence item (`S1_HOW_THE_LOCATOR_MEASURES.md`) | `bars.py:1415-1459` `last_flat` has no `cumulative_delta` key ⇒ `main.py:272/362` `bar.get("cumulative_delta")` = None whenever day-type is fed by failover (T-265 class); direct route `:669` does carry it | S1 confidence never aligns with "CVD-confirmed" on stalled-export days |
| G-49 | **RESOLVED ledger stage** (*"תוסיף… ככלי שבוחן ירי"*, 25.08) | `CANDIDATE_LEDGER_V1=1` · `CANDIDATE_LEDGER_CONTRACT.md` (*"cc-macbook still owns EOD RESOLVED"*) | backend `"RESOLVED"` writers ⇒ **0** (T-233); `trade_id: true` boolean (T-224); reader drops 23% of lines (T-247); migration 024 *"written but not applied"* | funnel 07.09: DETECTED 93.3% · GATE 70% · ROUTED 23.3% · **RESOLVED 0%** |
| G-50 | **`swallow_counter`** (334 swallowed exceptions measurable) | T-98 🔴 | `swallowed(` callers ⇒ 1 (`candidate_ledger.py:252`); `get_counts` consumers ⇒ 0; not in any health payload | logging only |
| G-51 | **Holiday guard on the firing path** | T-264 🔴 (07.09) | `session_gate.py:39-41` weekend-only (`holiday` ⇒ 0 in file and in gateway); `is_market_holiday` (`market_clock.py:215`) callers = `eod_archive_scheduler.py:162,211` only | 07.09 was ruled a trading session anyway; the guard is dead wiring, not a loss |
| G-52 | **7 INERT-ON flags** (`RELEASE_LEG_EXEMPT_V1`, `ENTRY_BUDGET_SKIP_LOSERS_V1`, `ENTRY_BUDGET_QUALITY_V1`, `LSMA_FLAT_ATR_V1`, `LEG_EXEMPT_LSMA_FLAT_V1`, `NEUTRAL_RESPONSIVE_V1`, `NONTREND_DISABLE_ALL`) | each ruled ON 07-08→21.08; their parents ruled OFF later | nested under `RELEASE_ENTRY_GATE_V1=0` (`:2627`), `DAYTYPE_ENTRY_BUDGET_V1=0` (`:2275`), `LSMA_FLAT_GATE_V1=0` (`:2214`), `DIRECTION_CONTEXT=0` (`:2042`), `DAYTYPE_POSITION_GATE=0` (`:1745`) | `flag_guard` PASS on all seven (`CLEANUP_LIST §1.2`) |
| G-53 | **`t3`/`t4` → same Sierra slot under the T0 remap** | T-213 🟡 (#942: price passed T2 by 4 pt, no fill) | `manager.py:2079-2085` `idx = min(col+1, 3)` ⇒ with T0: t1→c2, t2→c3, **t3→c4 and t4→c4** (clamp collision); `_emit_modify_target` `:1184` sent to the wrong order (`10848`, already filled) | `"%s INFERRED (demo/live)"` `bar_level_detector.py:1341` — T2 inferred, never filled, runner returned to BE |

---

## 4 · LIVE-VETOED — built and enabled, another stage makes it unreachable (10)

| # | item | asked / ruled | the veto (file:line) | evidence |
|---|---|---|---|---|
| G-54 | **`DALTON_EDGE_V1=live`** (28.08) | phone `a65f13aa` 28.08 10:34 *"תבנית… לונג ושורט בנקודות סיום של דלתון"* | (1) `direction_compass` — exempt only since **08.09 18:03** (`trading_gateway.py:2152-2161`); (2) `awaiting_release` — OFF only since **08.09 17:20**; (3) volume gate `vol ≥ 2×SMA20` rejects **88.4%** of bars reaching it (`dalton_edge.py:103-105,119-121`); (4) once-per-side-per-IL-day in-memory budget (`five_min_system.py:1483-1490`) | **n=1 live in 11 days** (S7-blocked, −$100 @2c); 08.09: `DALTON_EDGE_SHORT 7711.25` sent to shadow by release gate ⇒ +$220 unclaimed; `DALTON_EDGE_LONG 7685` compass-blocked while `INITIATIVE_SHORT 7684` passed ⇒ −$103.75 (`RULED_FLAGS` note). Zero RTH sessions since both vetoes were lifted |
| G-55 | **S2's own structural stop anchor** (`min/max b1..b3`, the 28.06 spec) | `REACTIVE_SPEC_DRAFT.md:53` (*"2T מעבר ל-min(low B1..B3)"*, Michael 28.06) | computed `five_min_system.py:1044/1114/1246/1275`, read `:2629-2631` (`STRUCTURAL_STOP_ORIGIN_V1`), then overwritten by the window override `:2651-2676` (12 bars + 6T, `stop_anchors.yaml:16-17`), then `STOP_RESOLVER_V1` `trading_gateway.py:2952`, then `STEP_SCALED_LADDER_V1` `:3385-3389` — S2 not in `_STEP_NATIVE_STOP_SOURCES=("TREND_STEP_LEG",)` `:62` | naive fix measured **negative**: structural same-size **−$845** vs as-traded **+$283.80** (n=54, `STRUCTURAL_STOP_REPLAY_2026-09-08`) ⇒ shadow first (`S1_S2 §4` item 1-2) |
| G-56 | **`FIXED_CONTRACTS_5=1`** (31.08 *"תכין את המערכת למסחר חי היום על 5 חוזים"*) | phone `2d68cbc3` 31.08 07:08 | auth-table cap 3 (`sizing.py:84-98` → `sierra_command.py:775 min(_fixed,_cut)`) · `RISK_BUDGET` `:712-722` · `SIZE_CAP_CUT` 5→2 (`sizing.py:135-157`) · margin fallback 5→4 (`margin_sizing.py:155-159`) | T-225: `MARGIN SIZING 5 → 4` on **every** candidate 01.09; T-173 *"פסיקת-5 מגיעה 2 בפועל"*; T-30: 0/17 at 4c; modal live size 2 |
| G-57 | **`STRUCT_TARGETS_WIN_V1=1`** (06.09 *"לתת להן ניהול של דלתון"*) | RULED_FLAGS 06.09 §3 | targets win (`:3435-3439`, after the ladder) but the ladder's **stop** cut stands (`:3385`) ⇒ `rr_hard_floor` rejects the chain's own product; `RR_NO_SELF_INFLICTED_V1` restores **t1 only** (`:3703-3704`), `_stop_dist` untouched | 08.09 18:20 `DOUBLE_BOTTOM_EE_LONG` 5c: stop 7676→7693.75, t1 7711→7703.25, blocked at 0.27 |
| G-58 | **Opening entry (`OPENING_ENTRY_V1`/`OPENING_FIRE_V1`, 24.07)** | RULED_FLAGS 24.07; Michael 04.09 `a57bdf73` *"לבטל את הדגל המגוחך הזה במיידי"* (T-250) | `OPENING_DIR_FUSION_V1=1`: `opening_entry.py:356` `if opening_vol < median_open_vol` (median over all prior days, `trade_context.py:1207-1217`) ⇒ `fusion=None` ⇒ skip | T-31: None in **0/5 openings**, 1,211× *"opening_vol < median"* (04.09); `T3_REQUIRED` veto fixed 08.09 (`OPENING_LADDER_V1`); T-250's three options unanswered since 04.09 18:12 |
| G-59 | **`DOUBLE_TOP_AA_SHORT`** (23.08 *"מאשר — צריך לסחור אותו יותר"*, +$582 replay) | `DOUBLE_TOP_ADAM_FIX_V1=1`; Michael 01.09 `4791ba55` *"שוב פעם לא היה זיהוי לתקרה כפולה"* | `location_gate` (`DAYTYPE_LOCATION_GATE=1`, ruled 22.07) blocks it systematically — 01.09 21:15 conf **1.00**, tier HIGH, 5c, `blocked_by=location_gate`; `EDGE_ENTRY_LOCATION_FIX_V1=1` (02.09) unverified | **0 live trades ever** (T-216 🟡 *"בלתי-ניתן-להכרעה"* — `mfe_track` only since 25.08) |
| G-60 | **`EXTREMES_AWARE_REALIZE_V1=1`** (06.08, replay +$410) | RULED_FLAGS 06.08 (*"EXCESS⇒מימוש-מיידי, POOR⇒דיכוי-מגנט"*) | `target_approach_realize.py:60` returns False when `S6_TARGET_APPROACH_REALIZE_V1=0` — ruled OFF 21.08 after it closed #764 at $0; the extremes logic at `:112-129` never runs | the 21.08 OFF ruling silently retired the 06.08 ON ruling |
| G-61 | **`DELTA_BREAKOUT_RELEASE_V1=shadow`** (06.09 20:05 *"כן"* — release on the acceptance bar's delta) | `CC_TUESDAY_2026-09-06.md §7` | lives in `release_gate.py:93,161` inside the block `trading_gateway.py:2627 if _rg.enabled()` = `RELEASE_ENTRY_GATE_V1=0` (08.09) ⇒ never evaluated; second path via `edge_fade` (`five_min_system.py:2273`) dead (G-41) | its promotion condition (`t1_before_stop ≥ 60%, n ≥ 10`) can never be measured; the *entry* it describes (03.09 18:00 delta +4,130) is G-03 |
| G-62 | **FAMIR / VEGAS** (REV fades) | `daytype_style.Normal.fade_edges: true` (`daytype_playbook.yaml:70`, Michael 01.09 *"fade VA edges"*) | pattern cells `SKIP` in all 8 day types (`daytype_playbook.yaml:181,183`) | 31.08 17:40 `FAMIR LONG @7684.25 blocked_by=daytype_playbook` — MFE **+24.00** / **+21.75** pt (T-195) |
| G-63 | **REACTIVE / INITIATIVE fire, then die at day-type/direction gates** | Constitution V3 §T1 (what runs) | no eligibility in the producer (`five_min_system.py:874-1130`); eligibility only at `setup_emitter.py:118-124` and `daytype_playbook` `trading_gateway.py:1611` | 07.09: all 4 named-spec setups died at `direction_compass` (14:00) / `daytype_playbook` ×3 — *"the day type is used to veto and never to price"* (`S1_S2 §2.6`) |

---

## 5 · CONTRADICTED — two rulings/docs/measurements conflict (15)

| # | item | side A | side B | evidence |
|---|---|---|---|---|
| G-64 | **ZLR shadow vs confluence live** | `ZLR_SHADOW_V1=1` (07.09 *"ZLR לצל לשבוע"*) | `CONFLUENCE_RI_ZLR_LIVE=1` (17.07 *"מאושר להפעיל על לייב"*) | T-279: shadow gate is an exact string compare `trading_gateway.py:774-776` (`"CONFLUENCE_RI_ZLR" != "ZLR"`); nested `metadata.confluence.shadow_only` (`confluence_ri_zlr.py:329-347`) not read at `:4044` |
| G-65 | **REACTIVE eligibility** | `REACTIVE_SPEC_DRAFT.md:28` (28.06): *"Variation / Trend_Normal / Trend_DD → לא REACTIVE"* | `S2_AUTH_TABLE_V1.md:63-64` (🔒 LOCKED 25.05): TN/TDD ⚠️ 2/1/0, NV ✅ 3/2/2; code `daytype_playbook.yaml:188` REACTIVE FULL except Nontrend/Nonconviction | 07.09 REACTIVE fired twice on a Variation day (`S1_S2 §2.4`) |
| G-66 | **5 contracts vs Auth Table 3** | `FIXED_CONTRACTS_5=1` (31.08) | `S2_AUTH_TABLE_V1.md:19` *"cap at 3 · ×0.75"* → `sierra_command.py:775 min(5,3)` | every S2 live fire is capped to ≤3 silently (`S1_S2 §2.5`) — one line from Michael |
| G-67 | **No trading in the first 15 minutes** | phone `e3b07c87` 31.08 14:24 *"אין מסחר ב-15 הדקות הראשונות ללא מחקר"* (T-176) | 20.08 ruling *"אתה לא מגביל שעות בשום אופן"* (`RULED_FLAGS` `DIRECTION_COMPASS_V1` note) + AST test `test_no_hour_gating_anywhere`; `CC_TUESDAY_2026-09-06.md:223` *"לא שער-זמן בלי מילה ממנו"* | opening window 09:30-10:00 ET: **−$328.75, 0/4** — no time gate exists; `first_hour_audit.py` ⇒ ABSENT |
| G-68 | **Nonconviction** | `daytype_playbook.yaml:61-67,164-189` `action: SKIP, contracts: 0` in every cell; `S1_NONCONVICTION_V1=1` ruled 07-12 (P1-8 *"suppresses S2/S4"*) | `daytype_playbook.py:189-191`: `_VALID_DT` excludes `Nonconviction` unless `NONCONVICTION_ACTIVE_V1` (unset, **no ruling row**) ⇒ unmapped ⇒ **FULL** | classifier emits the label (`daytype_classifier.py:355`); the stand-aside day trades at full size |
| G-69 | **`TARGET_STRUCTURE_CLAMP_V1` premise** (07-08 trade 310: *"Variation does not travel beyond IB"*) | ruling 07-08 (`target_structure_clamp.py:23` clamps every non-Neutral/Trend label incl. Variation) | measured: **10/10 Variation sessions left the IB, median +17.00 pt** (`IB_CLAMP_COST_2026-09-08`); clamp events persisted nowhere (`trading_gateway.py:3519` set only; T-272) | #756: healthy structural ladder 7686.25/7682.75/7679.00 crushed to 7691.5 ×3 → dedup-nudged 0.5 pt apart (`REPLAY_TARGET_SPACING`) |
| G-70 | **Ladder shape for 5 contracts** | `LADDER[5]=(1,2,1,1)` — T0 scalp 1c @3pt (`contract_size.py:40-47`, `T0_TARGET_PTS=3.0` ruled 07-21) | `S1_TRADE_MANAGEMENT_3CONTRACTS.md` (Michael 20.06: C1/C2/C3 thirds, structure-based) · `REACTIVE_SPEC_DRAFT.md:56` C1→T1 · `RULED_FLAGS` `FIXED_CONTRACTS_3` note *"⚠️ פתוח לפסיקה… 31.07 't1 t2 t3'"* | T-107 measurement: most of the 3c advantage is *"היעלמות רגל-ה-T0 (≈−$1,010 ב-33 סשנים)"* |
| G-71 | **What "IB" is** | doctrine/spec: IB = first hour of RTH (`DALTON_DOCTRINE.md §1.3`, S1 staging *"IB-lock@60min"*) | engine IB = DLL `tpo.json` session range (`main.py:286-290 _load_sierra_tpo`, `state_machine.py:605-628` Sierra-only); first-12-bars only on boot replay (`:992-995`) | `DAY_AUDIT_2026-07-07_to_07-24`: engine IB = overnight range in **5/13 sessions** (07-17: 66 pt vs 29 real, conf 100); feeds stop floor 0.35×IB, ½IB-ext targets, the clamp and the classifier `rib` |
| G-72 | **Shadow-to-live policy** | Michael 30.08 *"יום אחד של צל וממשיכים ללייב"* (`SHADOW_TO_LIVE_POLICY.md:49`) — evening gate: events>0? each event listed | practice: `VA_FADE` (shadow since 26/30.08) · `FAILED_BREAK_VA` (27.08) · `S2_CVD` (23.08) · `TARGET_MIN_SPACING` (21.08) · `APP_STATE_ROOT_FIX` (26.08 *"סשן אחד ואז §D"*) · `CEILING_*` (30.08/02.09) — **10-19 days, no evening gate row** | T-146: 2 shadow events in 4 days and no one alerted |
| G-73 | **`STRUCTURE_EXIT_REALIZE_V1=live` documented as shadow** | `RULED_FLAGS.yaml:397` (FAILBREAK note): *"`:1500` עוטף את **כל** ענף-הביצוע"* | code: REALIZE branch `bar_level_detector.py:1687-1714` emits real `MODIFY_STOP` **before** `elif _se_a_mode != "shadow"` `:1725` | REALIZE was ruled `live` 02.09 (`:374`) — behaviour is per ruling, the note is false |
| G-74 | **T-03 "no `op=MODIFY_TARGET` in DLL"** (🔴 open) | `TASK_LOG.md` T-03 | handler exists `MES_AI_DataExport_merged.cpp:3227-3249`; T-213 note *"הערת T-03 מיושנת"* | stale blocker in the log |
| G-75 | **Three sizing floors fighting** | `SIZE_CAP_FLOOR_CONTRACTS=2` (19.08 *"במקום 1… 2 או 3"*) | `RISK_MIN_CONTRACTS=3` reject (01.09) vs `contract_ladder` >25pt→1 (`stop_anchors.yaml:22-25` *"הזהיר תמיד גובר"*) vs `sizing.py:124-126` assignment | T-198/T-215: layers compute on a stop the ladder later replaces (`:2695 → sizing.py:135 → :2952 → :3385`); RISK_BUDGET re-derives risk from the final stop (`sierra_command.py:700-704`) |
| G-76 | **MAE-scratch: two replays, opposite sign** | 21.08 replay **+$4,398.75** / 32 sessions (`REPLAY_S6_MAE_SCRATCH_ATR`, ruled ON) | T-84: no-scratch arm **+$3,358** vs today's config **−$3,543** (Δ −$6,901 over 32 sessions) — *"ממתין-פסיקה"*; T-236 *"MAE-scratch מזוכה"* | `S6_MAE_SCRATCH_ATR_V1=1` live; one decisive replay owed before any ruling |
| G-77 | **Five target writers + three stop rewriters, each ruled, order-dependent** | `T1_STRUCTURE_END_V1` · `DAYTYPE_TARGETS_STRUCTURAL` `:3003` · `TARGET_ZONES_V1` `:3275` · `STEP_SCALED_LADDER_V1` `:3337` · `STRUCT_TARGETS_WIN_V1` `:3408` · `TARGET_REALISM_V1` `:3530` | none of them is the spec (HVN→POC→VAH); each ruling valid alone, the sum incoherent (`S1_S2 §2.3`, `CLEANUP_LIST §3.2`) | 07.09 `t1 = 7721.875` — not on a 0.25 tick |
| G-78 | **`flag_guard` PASS vs dead code** | `scripts/flag_guard.py:117-163` liveness = substring `if flag in content` (comments count) | five dead-on-landing instances passed it (`RE_ACCEPTANCE` no delta/vol keys; §2 runner order; §4 restore; §5/§7 `app` NameError — `CC_FIX_DEAD_2026-09-07`, `CC_FIX_RE_ACCEPT_2026-09-08 §1ב`); `docs/FLAG_INDEX.md:389` still ✅ ON for `RELEASE_ENTRY_GATE_V1`; 6 live flags with no row; `gen_flag_index --check` exit 1 (112 undocumented, 64 ruled) | `detector_contract_guard.py` + `test_detector_placement.py` wired 08.09 (`guard_tests.sh:54`) — narrows, does not close |

---

## 6 · SHADOW-UNMEASURED — in shadow, no number in `MEASUREMENTS.md` (8)

| # | item | ruled | code | gap |
|---|---|---|---|---|
| G-79 | `CEILING_FLIP_SHORT_V1=shadow` | T-140 02.09 (*"CEILING_FAILED→SHORT, T1=POC"*) | `five_min_system.py:1775-1805`, `ceiling_flip.py:106` hard-codes `shadow_only` | *"ואין לי מספר"* (`CC_CF_CONSUMERS §ג`) — T-140's neckline-vs-early-confirm ruling still open |
| G-80 | `CEILING_FLOOR_STATE_V1=shadow` | 28.08 (*"בעסקה האחרונה…"*) | detect+ledger only `:1664-1772`; docstring *"Neither mode trades"* | no Σ row; its consumers are G-14 |
| G-81 | `S2_CVD_DETECTION_V1=shadow` | 23.08 21:30 *"תפעיל על שדואו… תיתן לו פרשנות"* | never blocks (`five_min_system.py:1026-1032,1102,1239,1268`); window fix landed 07.09 (`:799`) | *"החלטה אחרי ≥5 סשנים על מספרים"* — 17 days, no SUPPORTING/OPPOSING hit-rate row; T-96 was a no-op (0/76 windows) |
| G-82 | `S1_STRUCTURAL_BINARY_V1=shadow` | T-104 (*"חסום עד T-103 GO"*) | `backend/main.py:518-555` logs `[S1-BINARY]` only | no report (`grep -rl S1-BINARY docs/reports/` ⇒ 0) |
| G-83 | `APP_STATE_ROOT_FIX_V1=shadow` | 26.08 *"סשן אחד ואז §D"* | shadow compare old/new source | 14 days; mentioned in `CC_3ROOTS`/`HYGIENE`, no §D number |
| G-84 | `TSF_SHADOW_LOG_V1=1` (stop-floor would-have) | 06.08 | observability log | referenced only in `AUDIT_S7_2026-08-15.md`/`FLAG_AUDIT`; no decision row |
| G-85 | `STRUCTURE_EXIT_FAILBREAK_V1=shadow` | Michael 30.08 *"אני רוצה לראות סגירה בכישלון פריצה"* → `e655a8bb` *"כן"* 31.08 | `bar_level_detector.py:1620-1622`; exec branch `:1725+`; measured only with an open live position (`:1004`) and does **not** write to the ledger | T-212: one GRADE-A on #942 (17:52 *"FLATTEN would…"*) — n=1 anecdote, 9 days |
| G-86 | `LEG_REPLACES_SUSTAINED_V1` (read `trading_gateway.py:1975`, unset, no ruling row) | Michael phone `7f2de2cf` 27.08 (T-114 *"מדידת-רפליי"*) | built inside `CONT_TREND_FILTER`; T-163: absent from `RULED_FLAGS.yaml` | replay never run |

---

## 7 · SHADOW-MEASURED — in shadow with a number (9)

| # | item | ruled | number | source |
|---|---|---|---|---|
| G-87 | `RE_ACCEPTANCE_V1=shadow` (closest thing to G-03; landed dead ×5 — no `delta`/`vol` keys, FIRST_HOUR nesting — fixed 08.09 `b3996414`/`f3be808c`) | 06.09/07.09 (*"נעזרים בקולמטיב/ווליום כדי להיכנס בזמן"*) | **11 days / 1 fire / +14.25 pt = +$142.50 @2c** (03.09 18:00 LONG @7730.25 = the money bar); `DALTON_EARLY_ENTRY` claimed 4/4 | `RULED_FLAGS.yaml:75`; call site now `five_min_system.py:2413` (process_bar body), enrichment `:1583-1599` |
| G-88 | `FAILED_RE_IB_V1=shadow` | 07.09 (family III) | **11d / 14 fires / 7W / +13.37 pt = +$133.70 @2c** with wrong-side guard (−15.38 pt unguarded; one inverted t1 cost ~29 pt) | `RULED_FLAGS.yaml:76`; `:2412`, `failed_break.py:156` |
| G-89 | `FAILED_BREAK_VA_V1=shadow` (Michael's A6: *"תקרה כפולה… יעד POC… זיגזאג"* `938aa71a` 26.08) | 26.08 → shadow 27.08 | **+$118 / 33 sessions / 56%** ≈ 0 after commissions; ledger: 2 events in 4 days | `AUDIT_VALUE_RETURN §1 A6`; `five_min_system.py:2379-2404` (still nested under `FIRST_HOUR_TACTICAL :1989`) |
| G-90 | `VA_FADE_V1=shadow` | 26.08 / 30.08 | §D **−$1,316 / 26 sessions**, all variants negative | `CC_VA_FADE_CALIBRATION_2026-08-26`; `va_fade.py:170` |
| G-91 | `TREND_STEP_ENTRY_V1=shadow` | 23.08 *"מאשר להעביר לצל"* | OOS **negative at every `ZZ_REV`** (5.0: −$977.50; 12.0: −$280); 08.09 fired 10:15 ET ⇒ STOP −$95 | `TREND_STEP_AUDIT_2026-09-08` |
| G-92 | `S2_DELTA_DBL_V1=shadow` | T-153 policy (new = shadow) | first day 31.08: **41 fires, 0 W, −$6,975** (86% of the day's shadow damage); cannot produce before ~17:50 IL (T-246: CVD rows written from 16:30 only) | `delta_dbl.py:180` fail-closed; `S2_DELTA_DBL_LIVE_RELEASE` unset |
| G-93 | `TARGET_MIN_SPACING_V1=shadow` | 21.08 11:30 *"לבנות ולהפעיל בשדואו"* | live fixed-ladder arm **+$427.50 / 81**, shadow **+$610 / 243**; root of #756 = the clamp (G-69), not structure | `REPLAY_TARGET_SPACING_2026-08-21.md:154-156` |
| G-94 | `S1_DAY_DIRECTION_V1=shadow` (S1's IB-expansion direction never reached the gateway — priority-1 imports the dead `backend.v9.app`) | Michael 25.08 15:55 *"אפשר להפעיל בשדואו ולראות"* | agreement **85.09%** (12,351 vs 2,164; n/a 14,427) | `COWORK_SELF_AUDIT_2026-08-29.md:148`; `trade_context.py:914-924` (shadow ∉ `_flag_on`); live direction still falls to LSMA bias `trading_gateway.py:1357` (T-128) |
| G-95 | `ZLR_SHADOW_V1=1` (ZLR to shadow for a week) | 07.09 15:20 *"כן"* | broker **n=12 −$385** vs non-ZLR +$729; books say +$122.50 because 14/22 rows unpriced | `GATE_REPLAY_2026-09-07`, `ZLR_WHY_2026-09-07`; T-268: second branch fired live 17:55 before the fix moved to `route_setup:771-776` |

---

## 8 · LIVE-OK — built, reachable, measured, matches the ruling (12, for completeness)

| # | item | ruled | evidence |
|---|---|---|---|
| G-96 | `RUNNER_BY_DAYTYPE_V1=1` — runner only on `Trend*` (landed dead 06.09: `RUNNER_TRAIL_V2` overrode it; None-label hole 08.09 §A) | 06.09 19:45 *"5 חוזים ללא ראנר — רק טרנד-דיי"* | `sierra_command.py:985-1010`, `runner_by_daytype` skip `:1027-1029`; caveat: `struct_c3` and `_c3_target` both None ⇒ DLL builds stop-only anyway (`cpp:2962-2971`) |
| G-97 | `RUNNER_TRAIL_V2=1` (structural exit for the swing) | 20.08 *"לתת לסווינג לרוץ"* | **+$2,315 / 32 sessions** (`ORACLE_STUDY_2026-08-20`) — but it silences G-31/G-32 |
| G-98 | `RELEASE_ENTRY_GATE_V1=0` | 08.09 17:20 *"work on live now and make it precise"* | saved/blocked **0.83**, n=150; blocked 8/13 best moments ($2,315) (`ASYMMETRY_17D`, `SIX_DAYS_MOMENTS`); makes T-196/T-181 moot; re-measure after a week |
| G-99 | `DALTON_EDGE_COMPASS_EXEMPT_V1=1` | 08.09 *"אמרתי שברגע שמסתיים לאפשר לונג בהיפוך"* (implements 28.08) | `trading_gateway.py:2152-2161` |
| G-100 | `OPENING_LADDER_V1=1` + P0 rejection-dict fix | 08.09 16:52 *"לתקן ואני מאשר"* | `opening_entry.py:298-319` emits t2=2.5R/t3=4R; gateway consumes `rejected` (`:4771,4973-4975`) — unverified in an RTH session yet |
| G-101 | `ELQ_LEG_FROM_BREAK_V1=1` + `has_pullback` (T-235) | 06.09 §5 (implements 28.08 `ref_points`) | 82/103 ELQ blocks of 03.09 now pass (T-244) — the gate is near-inert on trend days, by design of the fix |
| G-102 | `S1_BAR_REFRESH_V1=1` | 06.09 §1 (classifier read a 2-second snapshot) | `main.py:261-274`; caveat T-267: first IB lock under it still gave `rib≠1` (input wider than IB) and the replace path has no `_is_rth_bar` filter (`:260-274` vs `:349`) |
| G-103 | `RR_NO_SELF_INFLICTED_V1=1` | 08.09 18:45 *"מאשר את פריט 2"* | `:3681-3707` — t1 half of Law 1; the stop half is G-57 |
| G-104 | `EOD_CLOSE_T10_V1=1` | 24.08 | `bar_level_detector.py:573-592`; +$3.28/day |
| G-105 | `PNL_REQUIRES_EXIT_PRICE_V1=1` + `live_pnl.py` | 30.08 / 08.09 night | phantom-heal now books NULL not target profit (`manager.py:1853-1888`); money basis **−$313.75**, single query |
| G-106 | `ENTRY_GUARD_OWNERSHIP_V1=1` (ack path) | 26.08 | 9 tests incl. mutation — but see G-42 for the unreachable branch |
| G-107 | `STOP_FLOOR_IB_V1=1` · `S2_ADAPTIVE_THRESHOLDS_V1=1` · `S2_INITIATIVE_JOIN_ATR_CAP_V1=1` | 19-20.08 | +$241.50 / +$70.50 on 08-20 (`RULED_FLAGS` notes) |

---

## 9 · Resolutions — smallest change per class, and whether it needs a NEW ruling

`existing` = code implementing a ruling already given ⇒ build → verify → enable without a second approval (CLAUDE.md §Rulings are one-time). `NEW` = trading-risk change with no prior ruling, or two rulings collide.

### 9.1 SPEC-ONLY
| # | smallest change | ruling |
|---|---|---|
| G-01/G-03 | one pure producer (`BALANCE_DEPART`) on `accepted_break` from `_resolve_live_cls()` (`trading_gateway.py:195`) + `metadata.doctrine`, `shadow_only=True`, beside `_maybe_dalton_edge`; T-105's `אל תתחיל` lifted for the shadow build only; causal inputs (G-18) before any live number | **existing** (24.08 + 09.09 §4) |
| G-02 | `VALUE_RETURN` producer as ordered §4; target = far value edge (the only T3 variant that was positive) | **existing** (09.09) |
| G-04 | `dalton_playbook.py` + YAML tree behind `DALTON_PLAYBOOK_V1=0`, replay gate as written | **existing** (09.09 09:15) |
| G-05 | `trade_economics()` in `diff` mode after `:3530`, before `rr_hard_floor`; `=1` only through the replay gate | **existing** (09.09 08:40/09:05) |
| G-06 | one branch in `_route_setup_inner`: `ib_locked and get_live_day_type() is None ⇒ metadata.shadow_only + blocked_by="no_daytype_label"` (S2 **and** S4) | **existing** (09.09) |
| G-07 | forward-shadow only: record `hvn_zones` at every fire; anchor exemption per `S1_S2 §4` item 1 built in shadow (naive version −$845) | **existing** (28.06), eligibility half is G-65 |
| G-08 | nothing until ruled — the spec was never approved | **NEW** |
| G-09 | `require_confirmed_pullback` in `scale_in.py` decision — only meaningful once G-45 is revived | **existing** (28.08) |
| G-10 | write the ack in the pre-open gate when `abs(position_qty) ≤ 10` + regression test on date | **existing** (01.09) |
| G-11 | LaunchAgent/cron for `mechanism_verdict.py` at 23:00 + backend `RESOLVED` writer at trade close (`fill_poller`/`manager` where `exit_reason` is stamped) | **existing** (01.09 + 25.08) |
| G-12 | sim-verified EXIT-v2 (`sc.FlattenPosition` per-group or scale-out with a free contract) — DLL work, snapshot first | **existing** (13.07) — but sim is mandatory |
| G-13 | `getenv("STRUCTURE_EXIT_REVERSAL_V1")` + call `should_exit_on_reversal` inside `_maybe_structure_exit`, shadow | **existing** (30.08) |
| G-14 | `_maybe_cf_bank_long` / `_maybe_cf_edge_lock` as spec'd, `shadow`; measure 11-day Σ first | **existing** (08.09 08:30) |
| G-15 | one conversion pass: each absolute param → `k×ATR14` / `k×IB` with the same value at median ATR (the `S6_MAE_SCRATCH_ATR` precedent) | **existing** (28.08), per-param re-verify |
| G-16 | reclass listener on open trades: on `day_type` change re-run `targets_table` for the remaining legs, `MODIFY_TARGET` only after G-30 | **existing** (01.09) — blocked by G-30 |
| G-17 | new detector (body ≤0.5×range pause + expansion bar next), shadow | **NEW** (the audit says a new detector, not a parameter) |
| G-18 | `ALTER TABLE v9_tpo ADD market_ts, available_at` + backfill, off-hours, snapshot first | **existing** (T-185 plan) |

### 9.2 RULED-AS-GATE
| # | smallest change | ruling |
|---|---|---|
| G-19/G-20 | leave the gates; the *producer* is G-02 — once `DALTON_PLAYBOOK_V1=1` these two collapse into `intent.entry_kinds` | **existing** (09.09) |
| G-21/G-22 | delete the dead `day_direction_doctrine` branch (`:2750-2800`) and drop the NO_CHASE work order; the departure entry is G-03 | zero-risk deletion; producer **existing** |
| G-23 | nothing — replay −$121; if wanted, `shadow` only after G-71 (label quality) | **NEW** (Michael must accept the −$121 or re-rule) |
| G-24 | `RISK_MIN_CONTRACTS` 3→1 (size down instead of reject) *or* an edge-fade cap (~11 pt / 1.15×distance-to-edge, T-194) | **NEW** — the same-day ruling `n<3=דחייה` collides with *"פחות חוזים"*; `CC_REBUILD` forbids touching it today |
| G-25 | keep the belt; every producer must emit t3 (opening done; `SCALE_IN` child = G-45) | **existing** |
| G-26 | no threshold change (T-244); measure `BLOCKED_TWIN` one session; the gate is absorbed by G-04 | **existing** |
| G-27 | `config_consumer_guard.py` (exists) must **fail** on unread fields; then either read `bias/ref_points/contracts` in `intent()` or delete the prose | **existing** (06.09 §9א) |
| G-28 | nothing (works as ruled); count fires attributable to it in `gateway_decisions` | — |

### 9.3 LIVE-DEAD
| # | smallest change | ruling |
|---|---|---|
| G-29 | write `c{n}_target_price` in `accept_setup` beside `c{n}_target_id`; `_ord.get("id")`; sim BE ⇒ target unmoved; then `=1` | **existing** (06.09 "bug fix") — sim mandatory |
| G-30 | sim diagnosis of `:3203-3218` with `sc.GetPersistentInt64` logging; add stop snapshot/restore to `MODIFY_TARGET` `:3227-3249` | **existing** — DLL deploy = snapshot + sim |
| G-31/G-32 | `bar_level_detector.py:961`: treat F5 `False` (HOLD) as "no move" and let `DYNAMIC_STRUCT_TRAIL` take the bar; `swing_rev_threshold` from current-RTH TR after 14 bars, prior session before | **existing** (07-10 per-bar ruling; 20.08 runner) — replay #1073 first |
| G-33 | doc-mark INERT or delete the revoke block; no behaviour today | zero-risk |
| G-34 | pass `market_context` + `bar_ts` at `trading_gateway.py:3277` (T-17), then the 3-day report | **existing** (05.08) |
| G-35/G-36 | become inputs of `intent()` (G-04): `va_rule` → `target_rule`, toggle → `phase` | **existing** (09.09) |
| G-37 | in `five_min_system.py:3073-3079` price with `targets_table` for `_emit_day_type` when known; refuse to price without a label (Rule 1) — this is G-05 §3 | **existing** (bug + 09.09) |
| G-38 | compare `(opening_type, direction)` tuple as `opening_type_gate.py:82-90` does | **existing** (31.07) — bug fix |
| G-39 | nothing until TREND_STEP leaves shadow; note in RULED_FLAGS | — |
| G-40 | `stop_anchors.yaml:104` 0.8→1.05 or `FLAG_RR_MIN` | **NEW** (T-92) |
| G-41 | un-nest the block (indent only), flag stays OFF | zero-risk (T-92c) |
| G-42 | `entry_guard.py:204`: skip the `working>0` block when the position is *explained* (TM match or valid ack) | **existing** (26.08) — mutation test |
| G-43 | DLL: write a fill line on `FLATTEN_ACCOUNT`/`EXIT` (`cpp:3636-3644`), or backend join from `TradeActivityLog` at close | **existing** (T-62) — DLL half needs sim |
| G-44 | `exit_verifier.register(...)` at `:592`, `:1760`, `:1818`, `mobile_monitor.py:537` | **existing** (15.08) |
| G-45 | child sizing = `min(RISK_BUDGET n, add_contracts)` + child `t3` from parent's remaining target; then G-09 | **NEW** (per `SCALE_IN_CLEAN`: "restoring it needs child sizing + a t3 = a ruling") |
| G-46 | nothing until G-30 (a `MODIFY_TARGET` executor without stop protection is the 18:31:04 drag) | blocked |
| G-47 | call `va_quality()` in `tpo_system.py:453-478`; `SUSPECT ⇒ vah/val/poc=None`; consumers already fail-open | **existing** (01.09) |
| G-48 | carry `cumulative_delta` in `last_flat` (`bars.py:1415-1459`) — one key | bug fix |
| G-49 | RESOLVED writer at trade close with `pnl_sierra`; apply migration 024 after snapshot | **existing** (25.08) |
| G-50 | expose `get_counts()` in `/api/v9/health` | zero-risk |
| G-51 | `session_gate.py:39`: `or is_market_holiday(ct_now.date())` — but 07.09 shows Michael may *want* holiday sessions ⇒ ask once | **NEW** (one sentence) |
| G-52 | doc-mark INERT (`CLEANUP_LIST §1.2`); no behaviour change | zero-risk |
| G-53 | `_target_order_key`: map t4→c4 only when `n_contracts ≥ 5`, t3→c4 only when no t4 (per `LADDER`) | bug fix — sim on a 5c bracket |

### 9.4 LIVE-VETOED
| # | smallest change | ruling |
|---|---|---|
| G-54 | nothing new: measure the first RTH session with compass-exempt + release OFF; persist `_de_fired` per session; if still n≈0, the volume multiplier (2×SMA20) is the next ruling | **existing** (28.08) — measure before touching |
| G-55 | add `"REACTIVE","OFA_Initiative"` to `_STEP_NATIVE_STOP_SOURCES` **in shadow diff** (log ladder vs producer stop per fire); do not enable — the naive form is −$845 | **NEW** for enabling; measurement needs none |
| G-56 | `contracts = min(ruled_contracts(), table.contracts(day_type))` in `economics()` **and** Michael's one line: does the LOCKED Auth Table's 3 still bind under a 5-ruling? | **NEW** (one line) |
| G-57 | extend `RR_NO_SELF_INFLICTED` to the stop: restore the producer's stop when the floor fails on the chain's own product (Law 1, second half) | **existing** (08.09 18:45) |
| G-58 | T-250 option (b): threshold 0.85×median (or same-window median) — or (c) `=0` | **NEW** (T-250 sent 04.09, unanswered) |
| G-59 | measure via `BLOCKED_TWIN` one session after `EDGE_ENTRY_LOCATION_FIX_V1`; if still 0, exempt `DOUBLE_TOP_AA` from `location_gate` on rotation days | **NEW** (22.07 gate ruling vs 23.08 "trade it more") |
| G-60 | either re-home the EXCESS/POOR logic outside the OFF parent or set `EXTREMES_AWARE_REALIZE_V1=0` with a note | **NEW** (06.08 vs 21.08 rulings) |
| G-61 | retire the flag (release gate OFF) — the entry it wanted is G-03/G-87 | doc + `RULED_FLAGS` note; no ruling |
| G-62 | FAMIR/VEGAS cells like `DBDT` (Normal/Neutral FULL, Trend SKIP) — after G-24 (else they hit the 15-pt ceiling) | **NEW** (was the SKIP deliberate?) |
| G-63 | eligibility inside the producer per `REACTIVE_SPEC_DRAFT.md:28` — only after G-65 is ruled | blocked on G-65 |

### 9.5 CONTRADICTED
| # | smallest change | ruling |
|---|---|---|
| G-64 | `CONFLUENCE_RI_ZLR_LIVE=0` for the shadow week (option א) or a RULED_FLAGS note that the confluence stays live (option ב) | **NEW** (one answer) |
| G-65 | Michael names the winning document (28.06 draft vs 25.05 Auth Table) | **NEW** |
| G-66 | one line: "5 overrides the table" or "table caps S2" | **NEW** |
| G-67 | one line: does 31.08 revoke the 20.08 "no hour gating"? If yes, a 15-min gate with the AST test amended | **NEW** |
| G-68 | `NONCONVICTION_ACTIVE_V1=1` in shadow first: count days labelled, then live | **existing** (07-12 P1-8) — shadow count is the gate |
| G-69 | persist `target_clamp` to `quality` (zero risk, no ruling) + exempt Variation from the clamp | persist: none · exempt: **NEW** (T-272) |
| G-70 | ruling on the 5-contract ladder: keep T0 scalp or (0,2,2,1)/(0,2,1,2) per the 20.06 structure spec | **NEW** |
| G-71 | compute `ib_high/low` from the first 12 RTH bars (boot path `main.py:992-995` already does) and use the DLL value only when the two agree; measurement script first (ordered 5ב) | **existing** (S1 staging spec) — measure today, fix tomorrow |
| G-72 | run the 30.08 evening gate on every shadow flag ≥1 day old: events>0? Σ? — promote or retire | **existing** (30.08) |
| G-73 | fix the `RULED_FLAGS.yaml:397` note | doc only |
| G-74 | close T-03 | doc only |
| G-75 | one sizing law inside `economics()` (min over ladder/budget/margin, floor 1, reject only above `RISK_MAX_PTS_HARD`) | **NEW** (bundled with G-24/G-56) |
| G-76 | one replay with both arms on the same 54 broker-priced trades, then a ruling | **NEW** after the number |
| G-77 | `TRADE_ECONOMICS_AUTHORITY_V1` (G-05) replaces the chain; until then, log every writer's before/after (`ECON-DIFF`) | **existing** (09.09) |
| G-78 | `gen_flag_index.py --check` into `fire_drill`; registry stubs for the 64 ruled-undocumented; `detector_contract_guard` blocking | zero-risk |

---

## 10 · The 15 that touch money first (entries · stops · targets · size)

1. **G-05/G-77** one economic authority — five target writers + three stop rewriters, 08.09 18:20 self-rejection (`existing`, today).
2. **G-24 + G-75 + G-56** sizing: `RISK_MIN_CONTRACTS=3` ⇒ risk ≤15 pt, 30/54 structural stops rejected, ruled 5 delivered 2-4, sizer slope inverted (`NEW`, one law).
3. **G-01/G-03** the departure producer, +$5,973 replay, zero code, `אל תתחיל` (`existing`).
4. **G-02** the belly producer, asked 7×, zero code (`existing`).
5. **G-04** session state machine replacing compass/playbook/location (`existing`, replay-gated).
6. **G-55** producer's stop discarded three times; naive fix −$845 ⇒ shadow diff (`NEW` to enable).
7. **G-71** IB = overnight range in 5/13 sessions — every stop floor/target/clamp/label reads it (`existing`).
8. **G-45 + G-25** SCALE_IN dead since 01.09, legs −$157.50, children rejected 3/3 (`NEW`).
9. **G-30/G-29** BE drags the c3 target +8.00/+5.50/−6.50, restore branch dead, backend restore dead ×2 (`existing`, sim).
10. **G-31/G-32** per-bar structural trail unreachable behind F5; runner −$161.25/14, 0 moves in 88 min (`existing`).
11. **G-54** DALTON_EDGE n=1 in 11 days; two vetoes lifted last night, unmeasured (`existing`, measure).
12. **G-69** IB clamp premise falsified 10/10; #756's ladder crushed to 0.5 pt (`NEW`).
13. **G-58** opening entries: fusion never passes (0/5), Michael's 04.09 demand unanswered (`NEW`, T-250).
14. **G-64** ZLR shadow bypassed by the confluence leg — same fire path, two rulings (`NEW`).
15. **G-37 + G-06** S1's table/time-stop/contracts carried by no S2 trade; 20/46 trades fired with no label (`existing`).

*cowork-dev · 09.09.2026 09:55 IL · read-only · nothing restarted, no order placed, no flag or `.env` touched.*
