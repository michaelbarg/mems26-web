
# Status Board · Pre-LIVE Pipeline V2

**Version:** V2 (full restructure 23/5 17:30) · **Updated:** 2026-05-30 (Cowork verification pass · Shabbat — market closed) ·

---

## 📋 סיכום יום שישי 2026-05-29 — מה הושלם היום

| # | משימה | סטטוס | commit |
|---|-------|--------|--------|
| P31 | Daily Reset/Archive backend (8 tasks A-H) | ✅ CC DONE | multiple |
| P31.1 | Fix-up 9 gaps (T1-T6 · 101 tests) | ✅ CC+Cursor DONE | multiple |
| DLL Frozen-Tail | mapIdx clamp-detect patch · DLL rebuilt v9.4.3-p31.1 | 🔴 FIX SHIPPED · NOT verified (see blocker ↓) | ada6c88 |
| Backend routing | current_bar override S4 gets live SWI/CCI | ✅ DONE | in ada6c88 |
| Bug E | stop_hit_ts < entry_ts — entry guard in BarLevelDetector | ✅ DONE | e3b986c |
| S2 None warn | current_day_type=None logged (rate-limited 1/min) | ✅ DONE | e3b986c |
| Readiness Check | CC_MEGA_PROMPT_SYSTEM_READINESS_CHECK_2026-05-29.md | ✅ WRITTEN | — |
| Backend recovery | backend was down — restarted screen session | ✅ DONE | — |

**Test count (end of day):** 7/7 trade_manager · 4/4 DLL regression · 2/2 bar routing · 101/101 P31.1 · 17/17 day_type · all green.

---

## 🧪 Verification Log — Cowork 2026-05-30 (finding → fix → evidence)

- `[2026-05-30]` **TZ bars_5min future-ts** — root=aggregator wrote ET not UTC (+1h in EDT) → fixed (UTC + ingest guard `bars.py:307`/`bar_ingestion.py:74`, `c581f4d`+`b76d5e2`) → **verified: 0 future-ts rows in `v9_bars_5min`** (was 514).
- `[2026-05-30]` **DLL frozen-tail** — root=DLL mapIdx clamp → identical study tail. fix shipped (v9.4.3-p31.1 `ada6c88`) → **NOT verified: last 5 `v9_bars_5min_woodies` rows all `cci_14=-40.49`** → still OPEN/BLOCKER until live RTH (Sun).
- `[2026-05-30]` **Fake @5900 PARTIAL** — 12 phantom rows (entry 5900/stop 5900.25), source=test fixtures or bootstrap → fix: flagged `is_synthetic=1` + API filters `is_synthetic=0` in GET /trades + /recent (`trades.py:331,357`) → verified: 0 phantom trades in non-synthetic query.
- `[2026-05-30]` **Footprint dedup** — root=no per-(level,bar_ts) dedup in `_fire()`, every Sierra UPDATE → new trade (30/min bursts) → fix: dedup gate per `(level, direction, bar_ts)` in `footprint_system.py:39,426-436` → needs RTH verification.
- `[2026-05-30]` **pnl_r UI 60R vs DB 1.5R** — root=phantom @5900 trades have 1-tick stop ($1.25 risk), any movement → absurd R → fix: phantom trades flagged synthetic, API filters them → resolved (formula correct, data was wrong).
- `[2026-05-30]` **S2 zero-fire root cause** — root=EXPANSION_MIN/MAX_PT [1.5-1.75] vs avg bar range 5.19 pts → 0/20 bars pass. COT/AMT from Sierra CDV works (COT=-14284, AMT=-9644). Fix: convert to ATR-relative thresholds (Phase 6, needs Michael).
- `[2026-05-30]` **bars.py POST future guard** — root=`bars.py::post_bars_5min` had no future-ts guard (only `bar_ingestion.py` did) → fix: added `ts > now+2min` guard at `bars.py:305-309` → verified: 0 future-ts rows after cleaning 28 remaining.
- `[2026-05-30]` **S1 Day Type timing gates** — verified: A2(09:30)→A3(09:30)→B2(10:30)→C3(13:00 forced lock) all correct after TZ fix. opening_type=UNKNOWN→conf 0.68<0.70→LOCKED_LOW_CONF. Root: opening detector, not timing.
- `[2026-05-30]` **Frozen-tail deep diagnosis** — root=DLL mapIdx clamp + `all_bars` returns history (frozen) ignoring current_bar (live). current_bar routing override exists (lines 857-882) so S4 gets live values, but **DB writes still frozen**. Fix: (1) override history[-1] with current_bar study values before DB write, (2) stale detection skips frozen duplicates, (3) 5 seed rows ts=2099 cleaned. DLL `v9_calc_cci` fallback removal = strategic stop (Michael approval).

---

## 🔴 OPEN FOR SUNDAY — לפי עדיפות

### 🔴 LIVE BLOCKER (לא ניתן ל-LIVE בלי זה)
| # | פריט | מה חסר |
|---|------|---------|
| DLL UAT | frozen-tail fix — RTH live verify | **עדיין לא מאומת.** finding: DLL mapIdx clamp still active + v9_calc_cci fallback violates SoT. Backend fix applied: current_bar overrides history[-1] studies + stale dedup. DLL fallback removal = strategic stop (Michael). verify: RTH ראשון 16:30–23:00 IL; PASS = 0 consecutive identical (cci_14,swi) pairs |

### 🟠 HIGH — לפני LIVE
| # | פריט | קובץ |
|---|------|------|
| Bug C | stop/target hit recorded at bar-open instead of actual fill price (PnL impact) | `bar_level_detector.py` |
| Item #3 (runtime) | S2 warning קיים — אבל האם hydration מגיע בזמן? לאמת live | logs ב-Phase B |
| TZ bars_5min · ✅ DONE+verified | root=aggregator `_bar_start_for` החזיר ET, נשמר +1h ב-EDT → fix: UTC + future-ts guard (`bars.py:307`,`bar_ingestion.py:74`) + consumer/five_min ZoneInfo (`c581f4d`,`b76d5e2`) → verified by Cowork 2026-05-30: 0 future-ts rows ב-`v9_bars_5min` |
| P32 (נותר) | tick_reversal +6h ts + sot_health | תיקון ה-TZ לא הוחל על stream ה-tick_reversal (~540K שורות ts עתידי). `CC_IMPLEMENT_P32_BRIDGE_SOT_2026-05-29.md` — כתוב, טרם נשלח |
| ✅ TIME_STOP (S4) | Fixed: floor bar_ts to 5-min boundary (epoch%300) + ISO-ts parser. Regression: 40 pushes same bucket → count=1. | `93a5dbf`, `e75caa6` |
| ✅ T1 not detected (S4) | Fixed: BarLevelDetector subscribes to woodies_5min + cross-channel dedup. | `9410279` |
| ✅ Footprint burst (S3) | Fixed: dedup per (level, direction, bar_ts). Needs RTH verify. | `79a7640` |
| ✅ Fake PARTIAL @5900 | Root: gateway hardcoded DB_PATH → tests write to prod DB. Fixed: DATABASE_URL + test isolation conftest. 18 rows flagged is_synthetic=1 (844-861). | `65f00e5`, `c204021` |
| ✅ 5min restart gaps | Fixed: backfill from MAX(ts) on first push after restart. | `bffad29` |
| ✅ S1 restart resets state | Fixed: day_type_seed loads opening_type/day_type/confidence from v9_day_type_history instead of forcing INDETERMINATE. | `7316289` |

### 🟡 MED — קודם LIVE (לא בלוקר)
| # | פריט |
|---|------|
| Item #6 | `min_r_t1_threshold` — parameterized test 0/0.5/1.0 |
| Item #7 | Day-type matrix A2 advisory — לא enforced |
| Item #8 | Lunch skip 12:00-13:30 ET |
| Item #9 | FOMC ±90min skip |
| ✅ Item #10 | sentinel 2099 rows cleaned from `v9_bars_5min_woodies` (5 deleted) |
| EOD 29/5 · S1 lock | confidence 0.68 < 0.70 → לא ננעל כל היום (stage B2); שקול 0.65 או forced-lock מוקדם · `state_machine.py` |
| EOD 29/5 · S1 opening | opening_type=INDETERMINATE — A2 קיבל 3 pushes ב-4 שניות (לא 3 ברים); דרוש dedup per-system ב-A2 |
| EOD 29/5 · S2 state | `v9_five_min_state` ריקה — המערכת קוראת אך לא כותבת |
| EOD 29/5 · S4 stop | stop risk 5-8 ticks צפוף ל-MES (ATR~50); שקול ATR-based stop |
| EOD 29/5 · S2 thresholds | Initiative expansion [1.5-1.75pt] לא ניתן להשגה (0/44 ברים · avg 6.12); מחקר קבוע→יחסי §7b |
| ✅ EOD 29/5 · UI pnl_r | Resolved: phantom @5900 trades had 1-tick stop → absurd R. Trades now filtered. |
| EOD 29/5 · demo open | #604 עדיין OPEN — BarLevelDetector לא מנהל עסקאות demo |

### ⏳ PENDING PHASES (Daily Reset / Demo)
| Phase | תוכן | תלות |
|-------|------|------|
| Phase 3 | Archive endpoints `/api/v9/archive/...` | prompt לא נכתב |
| Phase 4 | DemoReadiness UI panel + test chain | תלוי Phase 3 |
| Phase 5 | UAT end-to-end + sign-off | תלוי Phase 4 |
| Tiered Fire Status | Plan A++ — design ב-§13 | deployment phase TBD |
| ⏸️ Dual-machine (B=מסחר 24/7) | שכפול stack למחשב B · `CC_DUAL_MACHINE_REPLICATION_2026-05-30.md` | **דחוי — מתחיל רק על אות מ-Michael, לא היום; ולא לפני סגירת חוסמי §1** |

---

## ⚡ CC QUEUE — לשבוע הבא

| # | קובץ | סטטוס |
|---|------|--------|
| 0a | `CC_MEGA_PROMPT_BLOCKER_SWEEP_2026-05-30.md` (T1–T8 · §1.5–§1.14) | ✅ CC ביצע (uncommitted) |
| 0b | `CC_MEGA_PROMPT_BLOCKER_SWEEP_R2_2026-05-30.md` (commit+tests+fixtures+TZ) | ⏳ כתוב, מוכן לשליחה |
| 1 | `CC_IMPLEMENT_P32_BRIDGE_SOT_2026-05-29.md` | ⏳ כתוב, לא נשלח |
| 2 | Phase 3 prompt (archive endpoints) | ⏳ לא נכתב |
| 3 | Phase 4 prompt (DemoReadiness UI) | ⏳ תלוי Phase 3 |

---

## ✅ COMPLETED HANDOFFS (ארכיון)

1. ✅ `CC_HANDOFF_S4_CURRENT_BAR_ROUTING_FIX_2026-05-28.md` — DONE 20:14 28/5
2. ✅ `CC_HANDOFF_TRADE_LIFECYCLE_BUGS_2026-05-28.md` — Bugs A+D RESOLVED
3. ✅ Build Status `fired_today` from DB — DONE 21:19 28/5 (110/110 tests)
4. ✅ `CC_IMPLEMENT_P31_DAILY_RESET_2026-05-29.md` — DONE (8 tasks A-H)
5. ✅ `CC_IMPLEMENT_P31_1_FIXUP_2026-05-29.md` — DONE (T1-T6 · 101 tests)
6. ✅ DLL Frozen-Tail Parts 1+2+3 — DONE (v9.4.3-p31.1 · 4 tests · RTH UAT pending)

---

## 🔁 BRING-UP CHECKLIST (ראשון בוקר, לפני RTH)

```
□ 1. screen -r mems26_backend  (verify running)
□ 2. curl http://localhost:8000/health
□ 3. python3 scripts/sot_health.py --strict
□ 4. בדוק session rollover: v9_session_meta.last_rollover_date == היום ET
□ 5. Sierra Chart פתוח, Chart 12 (Woodies) פעיל
□ 6. DLL Input 19 = 12 ב-MES_AI_DataExport study
□ 7. הרץ Phase A מ: docs/handoff/CC_MEGA_PROMPT_SYSTEM_READINESS_CHECK_2026-05-29.md
□ 8. לאחר 09:30 ET: Phase B — אמת IB lock + CCI לא frozen
```

---

- **2026-05-30 · Michael: NEWS handling PARKED** — do not work on news (calendar/feed/options) now; finish all approved items first. Resume later. Remaining APPROVED-but-unfinished for CC: (1) **R2-8 part 2** — test-DB isolation in `tests/conftest.py` (currently missing → @5900 recurs; mark rows 847-861 `is_synthetic=1`); (2) **R2-9** — restart recovery (`day_type_seed.py` load opening_type from DB + `bars_5min_stream.py` backfill). Everything else in R2/P32 committed & verified.
- **2026-05-30 · Cowork verified CC's R2+P32 commits — 2 issues surfaced** — CC committed (git lock cleared): R2-3 ISO-ts floor (`e75caa6`), R2-4 day_type fixtures (`0ee2657`), R2-5 api conftest (`19d6456`), R2-6 TPO test (`7e80626`), R2-8 gateway DB_PATH→DATABASE_URL (`65f00e5`), + P32-I/J/K/L. **Verified:** tick_reversal future-ts = **0** (§1.10 DONE). 844-846 marked `is_synthetic=1` (§1.8 approval executed ✓). **🔴 ISSUE 1 — @5900 RECURS:** 15 NEW rows 847-861 `is_synthetic=0`. Gateway DB_PATH fix alone does NOT isolate tests — `DATABASE_URL` defaults to the live DB (`db/session.py:14`), so tests still write to it. **R2-8 part-2 (conftest temp-DB isolation) was NOT done** → still bleeding. **⚠️ ISSUE 2 — TPO TZ:** `7e80626` changed the TEST to expect UTC (not ET) for `slot_start_ts_str`, classifying as fixture-drift — needs confirm that UTC is the intended TZ (Pre-LIVE Rule 4) or it masks a regression. **R2-9 (restart recovery) NOT started.**
- **2026-05-30 · Michael APPROVED §1.15 (restart recovery — simplified)** — root: `day_type_seed.py:111` hardcodes `opening_type=INDETERMINATE` on seed instead of loading the persisted value (proof: 27/5 saved OPEN_DRIVE but seed would flip to INDETERMINATE). Approved design (no replay, no 13:00 rule): (1) MANDATORY 5min bar backfill on restart (`bars_5min_stream.py` `_first_push`); (2) S1 loads `opening_type`/`day_type`/`lock_state` from today's `v9_day_type_history` row (`date==et_today()`, not ROLLED_OVER), IB/range stay from Sierra; only if no row → real INDETERMINATE (degrades to Normal). Replay + 13:00-skip dropped as over-engineering. → mega-prompt R2-9. Plan: `RESTART_RECOVERY_PLAN_2026-05-30.md` v2.
- **2026-05-30 · Michael APPROVED §1.8** — mark rows 844-846 `is_synthetic=1` (backup first, NOT delete). CC to execute `UPDATE v9_trades SET is_synthetic=1 WHERE id IN (844,845,846)` after `cp data/mems26_local.db data/...bak`, paired with R2-8 gateway DB-path fix so it stops recurring. Verify: `COUNT(*) WHERE entry_price=5900 AND is_synthetic=0` = 0.
- **2026-05-30 · Cowork read-only diagnoses (no-decision): §1.3 + §1.14 largely resolved** — §1.3 pre_fire: verified `validate_fire` IS called in all 3 fire paths (S3 `footprint_system.py:462`, S4 `woodies/decision_tree.py` A7, S2 `five_min/setup_emitter.py:110`) before gateway route — SYSTEM_REVIEW #3 ("standalone route only") is outdated; only cosmetic docstring/dup-route cleanup left. §1.14 status enum: `status.py:_check_day_type` returns live `lock_state`; DB shows `LOCKED_LOW_CONF` (not PENDING) — mapping in place; residual stale-PENDING is a restart/hydration artifact (→ §1.15), verify live after restart-seed.
- **2026-05-30 · Cowork: @5900 root cause = TEST POLLUTION via hardcoded gateway DB path** — `gateway/trading_gateway.py:25` hardcodes `mems26_local.db`, bypassing `DATABASE_URL`; gateway tests (`test_d088`/`test_gw02`, entry=5900) write SHADOW to the LIVE DB. Evidence: 0 hits for 5900 in prod code (tests only); 12 old rows (390-401, 29/5) now `is_synthetic=1`; **3 NEW rows 844-846 created today 14:19:50 — exactly during CC's pytest run — `is_synthetic=0`**; only 3 trades created today, all 5900. Report: `FAKE_5900_SOURCE_2026-05-30.md`. Fix added to R2 (T R2-8): gateway DB path from session + test DB isolation. **Decision (Michael):** mark/delete 844-846 (backup+approval). Also confirms SYSTEM_REVIEW §4 #15 (hardcoded DB paths bypass DATABASE_URL) — gateway doesn't honor DATABASE_URL → LIVE/DEMO risk.
- **2026-05-30 · Cowork: IB-lock "regression" = FIXTURE DRIFT (not a bug) + fixed one test** — root: A4 (`state_machine.py:495-502`) deliberately refuses to lock without Sierra IB (source-of-truth cleanup 28/5); failing tests feed `bar.high/low` with no `ib_high/ib_low`. **Verified empirically in sandbox:** no Sierra IB → `ib_locked=False stage=A3`; with Sierra IB → `ib_locked=True stage=B2`. **Do NOT change the state machine** (would re-introduce the 28/5 bug). Fix = fixtures. ✅ Cowork fixed `tests/v9/systems/test_day_type_ib_live.py` (`_bar()` now defaults `ib_high/ib_low`→high/low; all 3 edge behaviors re-verified). Pending CC (needs pytest/commit): `test_day_type.py::make_bar` same fix, ISO-ts floor, api/ conftest, TPO TZ (group 5), CST test, **commit all (git lock)** → `CC_MEGA_PROMPT_BLOCKER_SWEEP_R2_2026-05-30.md`.
- **2026-05-30 · CC executed Blocker Sweep (T1–T8) — Cowork verified diffs (UNCOMMITTED)** — ⚠️ all code changes in working tree, **not committed** (`.git/index.lock` perms). (T1·§1.5) `woodies_system.py:206` floors ts to 5-min (`ts%300`) → TIME_STOP count fixed; caveat: ISO-ts fallback floors to minute not 5-min — needs regression on closed-bar count. (T2·§1.6) `bar_level_detector.py:38` now subscribes `5min`+`woodies_5min` + minute-dedup → S4 T1/Smart-BE should work; verify live. (T6·§1.7) footprint dedup `(level+dir+bar_ts)` added (`:430,489`); **RTH gate NOT added (Michael decision)**. (T3·§1.13 + @5900) added `is_synthetic` to ORM (`db/models/trades.py`) + API filter (`trades.py`) — but 12 @5900 rows still `is_synthetic=0`, not hidden; no source report → **decision: mark/delete**. (T4·§1.11) verified ALREADY FIXED (`_chicago_to_utc`, `et_today()`). (T5·§1.12) triage → `PYTEST_TRIAGE_2026-05-30.md`: 38 failed/1994 passed; **NEW regression surfaced — day_type IB-lock not firing after A4 (`session_min≥60`), vote_history not populated (groups 9-10)**. (T8·§1.14) `RESTART_RECOVERY_PLAN_2026-05-30.md` (proposal, impl pending approval). **Next:** CC must commit (resolve git lock) + write regression tests; new IB-lock regression added to ROADMAP §1.
- **2026-05-30 · Blocker-sweep mega-prompt prepared (ROADMAP §1.5–§1.14)** — `docs/handoff/CC_MEGA_PROMPT_BLOCKER_SWEEP_2026-05-30.md`. Diagnose-first (code moved — verify before fixing). No-decision tasks T1–T8: TIME_STOP dedup floor-to-5min (`woodies_system.py:206`), T1 detection (`bar_level_detector.py:38` subscribes only `5min`), status-enum verify, **TZ/DST §1.11 appears ALREADY FIXED** (verified: `key_levels` uses `et_today()` :74, `woodies_chart_routes` uses `_chicago_to_utc` — no `+5*3600`), pytest triage, footprint dedup commit, @5900 root-cause (no delete), restart-recovery plan. **Decisions flagged (not executed):** §1.2 gateway canonical (D-093.Q1), §1.4 P5-1 (Q1/Q2/re-lock), §1.7 S3 RTH gate, §1.8 trade deletion, §1.3 pre_fire wiring.
- **2026-05-30 · Cowork verification of CC work (read-only DB + git)** — verified what CC shipped against live DB. (1) **bars_5min future-ts**: root=aggregator wrote ET → fix UTC+ingest-guard (`c581f4d`,`b76d5e2`) → **verified 0 future rows** (`SELECT COUNT(*) … ts>now+2min` = 0). (2) **DLL frozen-tail**: deep-fix shipped (`ada6c88`,`cc9bd8f`) → distinct 5-min buckets show **varying** cci_14 (−40.49/−10.04/−65.39/63.46/103.02) → no frozen-tail in data; earlier "5 identical" was same-bar pushes → still OPEN pending live RTH Phase B (market closed). (3) **fake @5900**: still **12 PARTIAL** in `v9_trades`, `is_synthetic=0` → filter in `trades.py` (uncommitted) doesn't hide them → OPEN. (4) **footprint burst**: 291 firing_system=3 trades last window; `footprint_system.py` dedup **uncommitted, no RTH gate** → OPEN. ROADMAP_TO_LIVE.html updated: 1.1 note corrected, TZ item split (bars_5min done / tick_reversal open), agent-marks seeded on verified items.
- **2026-05-29 EOD · Trading-day report folded into OPEN FOR SUNDAY** — `docs/reports/END_OF_DAY_TRADING_REPORT_2026-05-29.md`. Real P&L +$137.50 (S4 12 trades). New open items moved into triage: 🟠HIGH — TIME_STOP dedup early-fire (#603/#652), T1-not-detected (BarLevelDetector wrong stream), footprint burst 550/day, fake @5900 PARTIAL, 5min restart gaps, S1 restart state-loss · 🟡MED — S1 never-locks (0.68<0.70), opening INDETERMINATE, empty `v9_five_min_state`, tight S4 stop, S2 Initiative threshold research (§7b), pnl_r UI bug, demo #604 open.
- **2026-05-29 14:00 IL · P31 + P31.1 Daily Reset / Archive backend complete** — Bug B RESOLVED. 101/101 tests. Backend recovered. See `docs/reports/P31_1_FIXUP_FINAL_2026-05-29.md`. Phase 3/4/5 pending.
- 2026-05-28 21:50 IL · W-10 TimeStopEnforcer DISABLED (Option B · Michael) — Layer 4 sole TIME_STOP authority. Commit `dispatcher_config.yaml`. 6 tests pass.

## ⚡ ACTIVE HANDOFFS (CC queue)

7. ⏳ **`docs/handoff/CC_IMPLEMENT_P32_BRIDGE_SOT_2026-05-29.md`** — written, NOT sent (Bridge tick_reversal TZ + sot_health 4 tasks)
8. ⏳ **Phase 3 prompt** — archive endpoints (`/api/v9/archive/...`) — not yet drafted
9. ⏳ **Phase 4 prompt** — DemoReadiness UI panel + test chain — depends on Phase 3
10. ⏳ **Tiered Fire Status (Plan A++)** — design done in `DAILY_RESET_AND_ARCHIVE_DESIGN.md` §13; deployment phase TBD



---

## 2026-05-29 · P31 + P31.1 Daily Reset / Archive Backend (14:00 IL)

**Bug being closed:** Bug B — frontend dashboard showed yesterday's `day_type` (`Normal · LOCKED_LOW_CONF · 0.68`) pre-market on 29/5 because:
1. Consumer wrote `UNKNOWN/PENDING` rows for 29/5 at 22:00 ET on 28/5 (TZ-naive `date.today()` in IL evening).
2. No filter on `lock_state='ROLLED_OVER'` in `/api/v9/day_type/v9/current` + `/api/v9/key_levels` + V1 compat.
3. `SessionBoundaryManager` did not exist — no daily reset/archive cycle.

| # | Action | Result |
|---|--------|--------|
| 1 | **Cursor pending fix (T1.4)** | ✅ Reset row 11 to `UNKNOWN/PENDING/conf=0` with explicit `reasoning_notes` audit trail; design doc + 5 open questions sent to Michael |
| 2 | **Michael decisions** | ✅ globex_open boundary · plus_replay archiving · all_three test chain · rely_on_existing isolation · diagnose_plus_pending_fix today |
| 3 | **Cursor design (P-T1.5)** | ✅ `docs/plans/DAILY_RESET_AND_ARCHIVE_DESIGN.md` (17 sections incl. consumer write gate · 570f10d overlap · Bug 04 hydrate · CC consult acceptance) |
| 4 | **CC audit (P31a)** | ✅ `docs/reports/CC_AUDIT_DAILY_RESET_2026-05-29.md` confirmed 9 design points + flagged 4 boundary semantics + 3 split decisions |
| 5 | **CC consult (P31b)** | ✅ `docs/reports/CC_CONSULT_P31_2026-05-29.md` advisory on §13 boundaries → adopted into §17 of design |
| 6 | **P31 implementation prompt** | ✅ `docs/handoff/CC_IMPLEMENT_P31_DAILY_RESET_2026-05-29.md` — 8 tasks A-H · CC executed + reported in `P31_DAILY_RESET_FINAL_2026-05-29.md` |
| 7 | **Cursor inquiry — 9 gaps surfaced** | ✅ `docs/handoff/CC_INQUIRY_P31_GAPS_2026-05-29.md` → CC self-assessment: working from memory, didn't run migration on live DB, prioritised shipping over verification (CLAUDE.md violations) |
| 8 | **P31.1 fix-up prompt** | ✅ `docs/handoff/CC_IMPLEMENT_P31_1_FIXUP_2026-05-29.md` — 6 tasks T1-T6 · raw UAT mandatory in commit messages |
| 9 | **CC P31.1 execution** | ✅ 6 commits (T1: ground-state-safe rollover · T2: migration on `mems26_local.db` + missing items · T3: SBM first-bar fallback + archive + truncate · T4: 2 SQLite `date('now')` + main.py path · T5: 4 missing test files · T6: final report) · `P31_1_FIXUP_FINAL_2026-05-29.md` |
| 10 | **Cursor verification (14:00 IL)** | ✅ **101/101 tests pass** (41 new P31/P31.1 + 60 regression in `day_type/`+`woodies/`+`test_time_stop`) · M19 schema applied · all 6 endpoints 200 OK · consumer write gate verified live (row 11 `last_updated_at=06:59:21` unchanged after backend ran 7h) |
| 11 | **Backend recovery** | ✅ `screen mems26_backend` started 13:40 IL · port 8000 listening · `BRIDGE_TOKEN` loaded from `.env` (was down since 28/5 19:59 — operator gap, not P31 regression) |
| 12 | **UAT 4-axis** | ✅ Quality (no UNKNOWN written by consumer) · Recency (session_date=29/5 ET) · Cardinality (no row leakage) · Latency (`/v9/current`=3ms · `/key_levels`=9ms · `/tpo/current`=5ms · `/status`=825ms) |

**Schema delta (Migration 019):**
- 4 archive tables: `v9_day_type_archive` · `v9_tpo_sessions_archive` · `v9_woodies_signals_archive` · `v9_build_status_archive`
- `v9_session_meta(last_rollover_date, ...)` — seeded with today, no reset on first run (P31.1-T1)
- 5 `is_synthetic INTEGER NOT NULL DEFAULT 0` columns: `v9_bars_5min` · `v9_woodies_signals` · `v9_trades` · `v9_audit_events` · `v9_five_min_setups`

**Code delta highlights:**
- `backend/v9/common/trading_date.py` — new `et_today()` utility (TZ-aware America/New_York)
- `backend/v9/services/session_boundary/manager.py` — new `SessionBoundaryManager` (idempotent, ground-state-safe, first-bar subscriber, archive on rollover, truncate stale state)
- `backend/v9/systems/day_type/consumer.py` — `_should_gate_write()` blocks `UNKNOWN/PENDING` writes
- `backend/v9/api/v9/day_type_v9_routes.py` + `key_levels_routes.py` + `day_type/api.py` — `lock_state != 'ROLLED_OVER'` filter
- `backend/v9/systems/five_min/five_min_system.py` — day_type hydrate moved before overnight early-return

**Open follow-ups (not blockers):**
- `backend/main.py:22` `DEFAULT_LOCAL_DB_PATH` still hardcoded (renamed but value unchanged — out of P31.1 scope)
- `backend/v9/systems/day_type/api.py:55,88` hardcoded paths remain (out of P31.1 scope)
- Pre-existing `pytest_plugins = ["tests.v9.db.conftest"]` in `tests/v9/api/conftest.py:3` — blocks running `tests/v9/api/` + `tests/v9/db/` together; workaround: run in 4 isolated groups
- CC's P31.1 final report did not paste raw UAT (CLAUDE.md Rule 5 violation, discipline-only)

**Phase plan progress:**
- ✅ **Phase 1** Diagnose + Design + Pending fix
- ✅ **Phase 2** Backend reset + archive (P31 + P31.1)
- ⏳ **Phase 3** Archive endpoints (`/api/v9/archive/sessions/{date}` etc.) — not started
- ⏳ **Phase 4** DemoReadiness UI panel + test chain — depends on Phase 3
- ⏳ **Phase 5** End-to-end UAT + sign-off

---

## 2026-05-28 · S2 VOLUME KEY MISMATCH — CRITICAL ROOT CAUSE (19:23 IL · CC report)

**Bug**: Bridge sends bars with field `"vol"`. S2 detectors read `b.get("v", 0)`. Since wiring, S2 detectors have **always seen volume=0**, silently blocking Reactive (90% vol drop) + Initiative (COT/AMT) patterns. This invalidates CC's earlier "no patterns today" conclusion.

| # | Action | Result |
|---|--------|--------|
| 1 | **CC fix (3 lines, 2 files)** | ✅ `five_min_system.py:698` adds `bar.setdefault("v", bar.get("vol", bar.get("volume", 0)))` · `s2_inspector.py:112` adds `DAY_TYPE_MODE` to trading modes · `s2_inspector.py:103` bypasses FHB gate post-first-hour |
| 2 | **Code-level verification (Cursor)** | ✅ All 3 changes confirmed in source (Read tool, lines 698 / 112 / 103) |
| 3 | **DB integrity** | ✅ 200 bars today · 0 zero-volume rows |
| 4 | **DLL export field name** | ✅ `5min.json` keys = `['ts','o','h','l','c','vol','poc_vol','vah','val','cumulative_delta']` — confirms `"vol"` is canonical |
| 5 | **Running backend = OLD CODE** | ⚠️ Backend PID 49483 started **18:34:51** · CC fix applied **~19:20** · running process has the broken in-memory module · **restart required to activate fix** |
| 6 | **UAT axes (post-restart)** | ⬜ Quality (detectors see volume>0) · ⬜ Recency (next bar feeds patterns) · ⬜ Cardinality (S2 inspector reports correct mode/FHB) · ⬜ Latency (<100ms) |
| 7 | **CC regression report** | 962 pass / 1 skip / 0 NEW failures · 11 pre-existing failures from earlier day_type + IB work (separate cleanup) |

**ACTION required from Michael / Claude Code (sandbox cannot restart services):**
1. `kill -9 49483 && cd ... && nohup python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 > /tmp/backend.log 2>&1 &`
2. Wait 10s · then probe `/api/v9/cockpit/systems-snapshot` for S2 → expect Reactive/Initiative detectors to start seeing non-zero `b1.volume` next 5-min bar.
3. Watch `/tmp/backend.log` for 5 min for any new exception.

**11 pre-existing test failures (separate ticket):** day_type state machine + IB persistence changes from today's earlier work. Not introduced by CC's fix — but blocks the "全部 green" gate. To be triaged after volume fix confirmed live.

---

## 2026-05-28 · CONVERGENCE — Woodies Data-Integrity Triangle (19:34 IL)

Three independent investigations completed within ~30 minutes; all three point at the same defective Woodies data path:

| # | Source | Bug | Layer | Status |
|---|--------|-----|-------|--------|
| 1 | CC | S2 volume key mismatch (`vol` vs `v`) → detectors saw vol=0 | S2 ingestion | ✅ Code patched (`five_min_system.py:698`) · ⚠️ needs backend restart |
| 2 | Cursor forensic subagent | DLL frozen-tail: last ~13 5-min bars share identical `cci_14 / tcci / lsma / ema_34 / swi / czi / trend_state` (confirmed on 5/26, 5/27, 5/28) | DLL → bridge | ⬜ Open · root cause in `sc_study/v9_woodies_export.h:460-475` · S4 A5 sizing rejects with frozen SWI/TCCI |
| 3 | Cursor Build Status subagent | Sentinel rows `ts='2099-01-02 0X:00:00'` poisoning `v9_bars_5min_woodies` MAX(ts) → lag=-2.29×10⁹s in inspector | Stalled stream writes | ✅ Inspector hardened (`row_helpers.latest_valid_db_ts`) · ⚠️ underlying stream still writes sentinels |

**Synthesis:** findings #2 and #3 are two views of the same illness — the Woodies stream stalls / loops, the DLL clamps to one chart index for many bars, and the bridge writes placeholder `2099-…` rows when it has nothing fresh. S4 receives frozen Sierra study values via `history[-1]` (`bars.py:223-231` prefers history over `current_bar`), A5 sizing rejects, no fire — and the build status used to show fake `Present=✓` because lex-sorted `MAX(ts)` picked the 2099 sentinel.

**Side benefit:** Build Status now exposes `Live · Required · Freshness` per row across S1/S2/S4 (`Stage | Key | Spec | Live | Required | Present | Value`); the recency pill turns red on stale data so the next time the Woodies stream stalls we'll see it immediately. +765/-35 LOC across 10 files · 81/82 tests pass (1 pre-existing failure on `bridge_inspector threshold_seconds=90 ≠ 360`).

**Deliverables produced today:**
- `docs/reports/DIAGNOSIS_S2_S4_BLOCKED_2026-05-28.md` (CC — first pass · "no patterns" verdict — **superseded**)
- `docs/reports/AUDIT_S2_S4_LIVE_FORENSICS_2026-05-28.md` (Cursor — falsified CC's verdict · ranked root cause)
- `docs/handoff/MEGA_PROMPT_CLAUDE_DESKTOP_S2_S4_AUDIT_2026-05-28.md` (independent critical-review prompt)

**Pending decision from Michael:**
1. Restart backend to activate CC's S2 volume fix → run UAT 4 axes.
2. Decide DLL frozen-tail fix path (DLL patch vs bridge-side workaround vs Sierra study reconfiguration).
3. Triage the 11 pre-existing test failures from earlier day_type/IB work.
4. Confirm bridge sentinel-row source (`2099-01-02 0X:00:00` writes — which stream and which code path).

---

## 2026-05-28 · INDEPENDENT CC REVIEW — Forensic Audit Confirmed (19:47 IL)

CC ran an independent READ-ONLY critical review of `AUDIT_S2_S4_LIVE_FORENSICS_2026-05-28.md` against source code + spec. **All 7 claims confirmed.** CC explicitly retracted his earlier "no patterns matched today" diagnosis ("I concluded 'no patterns detected' without querying `v9_woodies_signals`").

**3 NEW gaps surfaced by CC review (not in forensic audit):**

| # | Gap | Severity | File:Line | Status |
|---|-----|----------|-----------|--------|
| 1 | S2 `current_day_type=None` on mid-session restart → chart-pattern day-type gating silently skips because `None ∉ {"Neutral_Extreme","Neutral_Center","Normal","Variation"}` | MED | `five_min_system.py:728-749` | ⬜ Open |
| 2 | `woodies_chart_routes.py:43` hardcoded `ts_unix += 5*3600` is DST-unaware → under-corrects by 1h during CST (Nov-Mar) — winter-time bomb | LOW (today) / HIGH (Nov) | `woodies_chart_routes.py:43` | ⬜ Open |
| 3 | `min_r_t1_threshold >= 1.0` has no test coverage; switching to 1.0 for LIVE without regression risks silent breakage | MED | `test_pattern_dispatcher.py` (missing) | ⬜ Open |

**CC's ranked pre-LIVE blockers (independent):**

| Rank | Blocker | Status |
|------|---------|--------|
| **1 — CRITICAL** | DLL frozen-tail (`GetContainingIndexForDateTimeIndex` clamping in `v9_woodies_export.h:460-475`) — confirmed mechanically: `MES_AI_DataExport.cpp:587` uses direct `arr[idx]` (live) while history loop uses mapped index (frozen) | ⬜ Open · requires DLL patch + rebuild + Sierra study reload |
| **2 — CRITICAL** | Backend `all_bars` property (`bars.py:223-231`) prefers `history[-1]` (frozen) over `current_bar` (live) — compounds #1; CC says "no comment or docstring explains the priority… likely unintended" | ⬜ Open · ~2-line fix |
| **3 — HIGH** | S2 `"v"` vs `"vol"` key mismatch (`five_min_system.py:698`) — S2 Reactive/Initiative have NEVER seen volume since wiring | ✅ Code patched · ⚠️ needs backend restart |

**Worth quoting from CC's review (Q3):** even if S4 sizing read `studies` directly instead of `current_state`, **it would still get frozen inputs** because the routed bar itself is frozen. → Fix #1 (DLL) and Fix #2 (backend routing) are both needed; #2 alone won't help if the live `current_bar` itself doesn't carry the proper Sierra study values, but the audit confirms `current_bar` IS live (cci_14=47.21).

**Resulting strategy (recommendation for Michael's decision):**

1. **NOW** — restart backend → activates CC's S2 vol fix. 0 risk. ~30s.
2. **NEXT** — backend `all_bars` priority swap (`current_bar` first, `history` fallback) — 2-line change + 1 regression test. If `current_bar` carries live Sierra studies, this single change unblocks S4 fires immediately. Verifiable today, no DLL touch.
3. **STRATEGIC** — DLL frozen-tail fix. Architectural decision: patch DLL `mapIdx` to use `bi` directly when chart is in-progress / clamped, OR add bridge-side staleness detector that drops mapped values when they match prior bar's values. Requires DLL rebuild + Sierra study reload.
4. **DEFER** — gaps #1-3 above + 11 pre-existing test failures, after the critical-path two are clean.

CC's review also caught one item worth confirming: **`current_bar`'s study fields are live (`cci_14=47.21`)** — meaning option 2 (the backend `all_bars` swap) is the **cheapest, fastest, lowest-risk** route to actually firing S4 today. The DLL bug stays open but its blast radius is contained.

---

## 2026-05-28 · S2/S4 Live Forensics (19:00 IL · CLOSED — see Convergence + CC Review sections above)

| # | Action | Result |
|---|--------|--------|
| 1 | **CC diagnosis prompts (2)** | ✅ `docs/reports/DIAGNOSIS_S2_S4_BLOCKED_2026-05-28.md` — single combined report. CC conclusion: "no bug, no patterns today; all gates open." |
| 2 | **Cursor caveat on CC report** | ⚠️ CC claimed inspector vs live state divergence is closed — **STILL OPEN.** `/api/v9/status.day_type=PENDING/UNKNOWN/A1` while `v9_day_type_history` row IS classified (`day_type=Normal · prob=0.68 · IB=7574.0/7525.5 · WIDE · INDETERMINATE`). Root cause: legacy `status` column stuck at `PENDING` although classification fields filled — consumer.py never flips the enum. Cosmetic-but-misleading for top-bar; real bug for LIVE. |
| 3 | **Michael challenge** | ⛔ Rejected CC "no patterns" finding. Sierra Woodies UI values appear to disagree with frontend WoodiesLensContent; suspects DLL subgraph / stream-freshness / detector-drift. Requests: spec re-review · frontend↔Sierra parity · push cadence audit · 09:30→now replay through S2+S4 · Claude Desktop mega-prompt for independent critical review. |
| 4 | **Forensic audit subagent (read-only)** | ⏳ IN-FLIGHT. WS-A spec re-review · WS-B FE↔Sierra parity table · WS-C push freshness · WS-D 09:30→now replay (per-bar verdict for each detector) · WS-E ranked root-cause hypothesis. Deliverables: `docs/reports/AUDIT_S2_S4_LIVE_FORENSICS_2026-05-28.md` + `docs/handoff/MEGA_PROMPT_CLAUDE_DESKTOP_S2_S4_AUDIT_2026-05-28.md`. |
| 5 | **No code changes yet** | ✋ Strategic stop — diagnose-first per pre-LIVE protocol. Fix plan deferred until audit report + Michael go/no-go. |

**Known follow-ups queued (no work started):**
- Fix legacy `status` column rollover in `consumer.py` so `/api/v9/status.day_type` matches live machine.
- Pipe `opening_type` through S1→S2 event payload (cosmetic NA vs INDETERMINATE).
- 6-bars replay on mid-session restart in `day_type_seed.py` (so `OPEN_AUCTION_IN` recovers instead of falling back to `INDETERMINATE`).

---

## EOD 2026-05-28 · Key Levels Sierra Source-of-Truth Cleanup (17:35 IL)

| # | Action | Result |
|---|--------|--------|
| 1 | **Sierra Inputs corrected (user UI)** | ✅ In:14=1 (TPO Yest), In:16=6 (IB) — `tpo.json` now valid |
| 2 | **Step 5: `_ib_from_bars` plaster removed** | ✅ `tpo_routes.py` — Sierra is the only IB source |
| 3 | **Step 6: `/api/v9/key_levels` rewritten** | ✅ Reads `_load_sierra_tpo()`, 12/12 fields match Sierra (36ms latency) |
| 4 | **Step 7a: `tpo_system.py` IB sourced from Sierra** | ✅ Removed bar-based `_update_ib` AND second hidden accumulator in `process_bar` |
| 5 | **Step 7b: `main.py` inline IB plaster removed** | ✅ S1 BarInput.ib_h now from Sierra — `v9_day_type_history` matches Sierra |
| 6 | **Step 7c: `state_machine.py` `_stage_a3` cleaned** | ✅ No more `bar.high/low` fallback |
| 6.5 | **Step 7d: `state_machine.py` `_stage_a4` bar.low fallback removed** | ✅ A4 now drops back to A3 if Sierra IB incomplete (loud failure over silent garbage) |
| 7 | **Step 8: Future-bars bug not present** | ✅ `count(*) WHERE ts > now()` = 0; risk also closed by Steps 5-7 |
| 8 | **Step 9: Yesterday IB DLL extension** | DEFERRED · UI shows `Y IB: dll_missing` honestly |
| 9 | **Step 10: UI re-ordered to Michael's spec** | ✅ Today POC / Yest POC / IB Today / Y IB / Yest Range / Today Range |
| 10 | **Tests** | ✅ 117/117 relevant pass; 1 pre-existing unrelated failure (build_status threshold 90 vs 360) |
| 11 | **Report** | ✅ `docs/reports/PROMPT_KEY_LEVELS_SIERRA_TRUTH_2026-05-28.md` |

**Watch item:** Sierra Initial Balance Study (ID:6) reports `ib.found=false`
post-lock at ~10:34 ET. Backend correctly preserves last-known IB and does
not synthesise replacements. Sierra-side investigation needed before next
session — likely a `Number of Days to Calculate` setting on the IB study.

---

## EOD 2026-05-27 · RTH Forensic + Pipeline Fix (21:25 IL)

| # | Action | Result |
|---|--------|--------|
| 0 | **RTH Forensic Audit** | ✅ Zero signals fired — 2 structural bugs identified · full report `docs/reports/SHADOW_LIVE_BRINGUP_2026-05-27.md` |
| 0a | **Bug B1: S2 mode stuck FIRST_HOUR_TACTICAL** | ❌ `process_bar()` missing FIRST_HOUR→DAY_TYPE transition · ALL chart patterns (HNS/flags/doubles) never ran · Fix in mega-prompt |
| 0b | **Bug B2: Woodies demo disabled + shadow not persisted** | ❌ `demo_enabled_systems=[]` · shadow trades in-memory only · Fix in mega-prompt |
| 0c | **Bridge Live Feed Inspector** | ✅ `bridge_inspector.py` added to Build Status · per-stream FRESH/STALE/DEAD indicators · wired to aggregator |
| 0d | **Monitoring Script** | ✅ `scripts/bridge_monitor.py` · snapshots every 15 min · `/tmp/bridge_monitor_YYYYMMDD.log` |
| 0e | **Mega-Prompt: RTH Pipeline Fix** | ✅ `docs/handoff/MEGA_PROMPT_RTH_PIPELINE_FIX_2026-05-27.md` · 3 passes · Claude Desktop + Claude Code · Cursor verifies |
| 0f | **Table cleaned (v9_trades)** | ✅ 1 residual record deleted · fresh start for tomorrow |
| 1 | **G3 Review — Pipeline 2 S4 Woodies** | ✅ 9/10 PASS · W-9 deferred Pipeline 3 · W-10 Time Stop added · F-16 YELLOW guard fixed |
| 2 | **W-10 Time Stop Enforcer** | ✅ `TimeStopEnforcer` + 35 tests · `time_stop.py` · wired `woodies_system.py` |
| 3 | **F-16 YELLOW guard** | ✅ explicit guard instead of exception-for-control-flow |
| 4 | **F-17 RTH gate S4** | ✅ `_is_rth_bar()` + `rth_only` constructor arg · 17 tests |
| 5 | **DB cleanup** | ✅ cleared all backtest/fake trades · shadow day starts from 0 |
| 6 | **4 spec-audit meta-prompts** | ✅ S1/S2/S4/Bridge · `docs/handoff/META_PROMPT_SPEC_AUDIT_*.md` |
| 7 | **Trade filter audit S4** | ✅ AP1-9 · RTH gate · dedup · YELLOW gate · sizing · W-8 dispatcher · W-10 all verified |
| 8 | **S2 First Hour Buffer wired** | ✅ bars 1-3 ACCUMULATING (no patterns) · 4-6 EARLY (reactive only) · 7-9 DEVELOPING · 10+ MATURE |
| 9 | **S2 Choppiness wired** | ✅ `self.choppiness_score` computed live each bar in FIRST_HOUR_TACTICAL |
| 10 | **Archive S2 dead modules** | ✅ `confluence.py` · `q0_dispatcher.py` · `first_hour_matrix.py` → `five_min/archive/` |
| 11 | **Footprint SCID rollover** | ✅ `MESH26` → `MESM26` · 12/12 bridge streams healthy |
| 12 | **Tests** | ✅ 226 pass · 0 new failures |
| 13 | **S1 IB contamination bug (root cause)** | ✅ `is_rth: bool = True` added to `BarInput` · `main.py` computes `_is_rth_bar` from wall-clock ET · A2 guard + A3 guard: Globex bars skip both stages entirely |
| 14 | **S1 Globex / RTH range tracking** | ✅ `globex_h/l` + `rth_session_h/l` tracked separately in state machine · exposed via `/api/v9/day_type/state` meta · displayed in DayType lens (Now tab) |
| 15 | **DB IB cleanup** | ✅ `v9_day_type_history` row reset: `ib_h=NULL · ib_l=NULL · ib_width_class=DEVELOPING · day_type=UNKNOWN` · IB will re-lock correctly at 10:30 ET from RTH bars only |
| 16 | **Build Status enrichment — all 3 systems** | ✅ S1 +2 (ib_range_pts · trading_confidence) = 10 components · S2 +3 (mode_context · fhb_eligible · choppiness_ok) = 9/pattern · S4 +2 (rth_gate · day_type_gate) + last_fire_ts fix = 9/pattern · 71/71 tests |
| 17 | **S1 opening_run_detected** | ✅ new component distinguishes OPEN_DRIVE/OPEN_TEST_DRIVE from AUCTION types |
| 18 | **Diagnostic: systems verified ungated** | ✅ S4 CCI=50 · TCCI=45 · trend=GRAY (correct pre-RTH) · S2 buffer=0 mode=OVERNIGHT (correct pre-RTH) · both unblocked at RTH open |

**Live stack (21:25 IL):** Backend ✅ · Bridge ~10/12 streams live (woodies_5min ✅ footprint ✅ vol_profile ✅ · imbalance DEAD · tpo_bars DEAD) · Frontend ✅ · Build Status ✅ + Bridge Inspector NEW ·

**CRITICAL for next trading day:** 3 fixes pending (S2 mode transition + demo enable + shadow persist) — see `docs/handoff/MEGA_PROMPT_RTH_PIPELINE_FIX_2026-05-27.md`

---

## System Reference — Code · Spec · Decision Tree

| System | Code Path | Spec Authority | Decision Tree |
|--------|-----------|----------------|---------------|
| **S1 · Day Type** | `backend/v9/systems/day_type/` | `docs/decisions/D-091_S2_LIVE_SCOPE.md` §Day Type | `state_machine.py` stages A1→A7 · 7 Dalton types |
| **S2 · Five-Minute Patterns** | `backend/v9/systems/five_min/` | `docs/spec_authority/S2_AUTH_TABLE_V1.md` | `five_min_system.py` → FHB gate → detectors → `setup_emitter.py` |
| **S4 · Woodies CCI** | `backend/v9/systems/woodies/` | `docs/spec_authority/S4_WOODIES_TABLE_*.csv` + `D-092_S4_WOODIES_UPDATE.md` | `docs/MEMS26_WOODIES_DECISION_TREE_V1.md` (1085 LOC · 21 stages) |
| **S3 · Footprint** | `bridge/v9_streams/footprint_stream.py` | `docs/ENVIRONMENT.md` + DLL ops | `vap_recompute.py` SCID→VAP · file: `MESM26_FUT_CME.scid` |
| **Bridge** | `bridge/v9_streams/` | `CLAUDE.md` §Bridge Local-Only | `base_stream.py` → CLOUD_URL guard → 12 streams → `/api/v9/bars/*` |
| **TradeManager** | `backend/v9/systems/trade_manager/` | `docs/spec_authority/S2_TRADEMGR_HOOKS_V1.md` | `trade_manager.py` → hooks → gateway |
| **Gateway / Order Routing** | `backend/v9/services/trading_gateway/` | `docs/decisions/D-093_SIERRA_ORDER_ROUTING.md` | SHADOW: log-only · LIVE: Sierra DLL API |
| **Quality V2** | `backend/v9/systems/five_min/auth_table_v1.py` | `docs/spec_authority/S2_AUTH_TABLE_V1.md` | pattern × day_type × tier → sizing |

**Plan:** `docs/plans/PRE_LIVE_PIPELINE_2026-05-23.md` V2

מעודכן רק כש-state ממש משתנה.

---

## Pre-flight checklist


| #    | Item                                                                                                       | Owner                          | Status                                                                           |
| ---- | ---------------------------------------------------------------------------------------------------------- | ------------------------------ | -------------------------------------------------------------------------------- |
| 1    | D-090 + D-091 → `docs/decisions/`                                                                          | Michael+Cursor                 | ✅ 23/5 17:40                                                                     |
| 2    | Spec lock 1 · Zohar thresholds                                                                             | Michael                        | ✅ 23/5 17:43                                                                     |
| 3    | ~~Spec lock 2 multipliers~~ — already in Master Sheet 4                                                    | —                              | ✅ N/A                                                                            |
| 4    | Spec lock 3 · Bulkowski edge tolerances                                                                    | Michael                        | ✅ 23/5 17:43                                                                     |
| 5    | D-092 Woodies update doc                                                                                   | Michael                        | ✅ 23/5 18:00                                                                     |
| 6    | S1 Day Type verify report                                                                                  | Michael                        | ⬜                                                                                |
| 7    | S3 Footprint verify report (incl. O-4)                                                                     | Michael                        | ⬜                                                                                |
| 8    | Hybrid C model approved (chat explicit)                                                                    | Michael                        | ✅ 23/5 16:48                                                                     |
| 9    | V2 restructure approved (chat explicit)                                                                    | Michael                        | ✅ 23/5 17:30                                                                     |
| 10   | MEGA_PROMPT_TEMPLATE.md                                                                                    | Cursor                         | ✅ 23/5 16:30                                                                     |
| 11   | SPEC_LOCK_TEMPLATE.md V2 (simplified · no multipliers)                                                     | Cursor                         | ⏳ in progress                                                                    |
| 12a  | EXIT_V6 fix Stream 1 · Neutral enum split + targets_table + 6/7 state_machine hits + api.py classification | Cursor handoff · CC exec       | ✅ G3 PASS 23/5 21:00 (chain `dd9c34f` → `a58ee61` → `689ac41`)                   |
| 12a' | Stream 1.5 · prev_day hydration wiring + state_machine.py line 547 rewrite                                 | Cursor handoff · CC exec       | ✅ G3 PASS 23/5 21:18 (commit `548f1f6` · first-try clean)                        |
| 12b  | EXIT_V6 fix Stream 2 · Pkg 3a proper (day_type_targets module + wiring + NT gate)                          | Cursor handoff · CC exec       | ✅ G3 PASS 23/5 22:15 (commit `cf6383e` · first-try clean · zero new regressions) |
| 13   | STATUS_BOARD V2 (this)                                                                                     | Cursor                         | ✅ 23/5 19:05 · 23/5 20:15                                                        |
| 14   | Paste handoff to Claude Desktop · Pkg 0 mega prompt                                                        | Michael + Desktop              | ✅ pasted 23/5 17:43 · Desktop reading                                            |
| 15   | D-093 Sierra Order Routing doc                                                                             | Cursor                         | ✅ 23/5 19:00                                                                     |
| 16   | Pkg 1 handoff finalized (4 Claude Desktop fixes applied)                                                   | Cursor                         | ✅ 23/5 19:05                                                                     |
| 17   | D-093.Q1 · Gateway canonical lock                                                                          | Michael (after CC P5-0a audit) | 🟡 research recommends `backend/v9/services/trading_gateway/` (W11+W14) per `docs/research/SIERRA_ORDER_ROUTING_RESEARCH_2026-05-24.md` §3.3 · awaiting Michael lock |
| 18   | D-093.Q2 · Sierra DEMO account                                                                             | Michael                        | ⬜                                                                                |
| 19   | D-091.Q1 · NeuE vs NeuC classification                                                                     | Michael                        | ✅ 23/5 20:10 · LOCKED A (VAH/VAL vs VA-interior · fallback NeuC)                 |
| 20   | D-091.Q2 · NT NO_TRADE gate location                                                                       | Michael                        | ✅ 23/5 20:10 · LOCKED early-skip in `_check_setup` + shadow counter              |
| 21   | D-091.Q4 · Pkg 3a TradeManager wiring scope                                                                | Michael                        | ✅ 23/5 20:10 · LOCKED Emit-only · enforcement in Pkg 6                           |


---

## SHADOW gate (P-S0) — Phase A → SHADOW activation


| Criterion                                                     | Status |
| ------------------------------------------------------------- | ------ |
| Phase A all packages SHADOW-soak completed (0-3, 5, 8, 6 = 13 pkgs + Consolidation = 14 · 4a+4b deferred per D-095) | ⏳ build done · G4 UAT pending RTH 16:30 IL · meta-prompt sent to Desktop |
| pytest tests/v9/ green                                        | ✅ **WAIVER GRANTED 26/5 12:25 IL** · 1694 pass · 21 pre-existing failures in legacy/non-trading code · 4 groups: (A) 7× tpo_history_snapshotter TZ bug · (B) 8× W11 snapshot schema drift · (C) 2× legacy trade_manager DBPersistence · (D) 3× woodies_dedup isolation + 1× frontend journal file missing · none affect S2 trading path · Pkg 0–8+6 Phase A code all green |
| Pkg 5a Axis 2 (Recency)                                       | ✅ **FIXED 26/5 12:02 IL** · commit `7433d52` · setup.ts = bar timestamp · mini-G3 PASS 932/932 |
| Pkg 0 Redis decision                                          | ✅ **CLOSED 26/5 12:15 IL** · no blocking action · legacy keys dead · cleanup deferred to post-SHADOW |
| UAT 4 axes on /cockpit/systems-snapshot                       | ⬜ pending RTH 16:30 IL |
| L4-2 Recency (TPO)                                            | ⬜ pending RTH 16:30 IL |
| L4-3 Cardinality (Five-Min bars)                              | ⬜ pending RTH 16:30 IL |
| L4-4 Latency (all endpoints)                                  | ⬜ pending RTH 16:30 IL |
| G4 smoke trades (Pkgs 1, 2a, 2bc, 3a, 3b, 5a, 5b, 5c, 8, 6) | ⬜ pending RTH · CC scaffolding via Desktop meta-prompt |
| 60min ירוק · zero open warnings                               | ⬜ pending post-UAT soak |
| Michael sign-off                                              | ⬜ pending all above |


---

## Pipeline 1 · S2 D-091 · Phase A (Pre-SHADOW Build)

### Build queue (14 packages · 4a+4b DEFERRED per D-095 25/5 11:18) · **15/15 ✅ COMPLETE 25/5 15:22**


| Pkg             | Name                                                                                                                           | G0 spec                                           | G1 prompt                         | G2 CC                                                      | G3 review                                             | G4 UAT                            | G5 soak                       | G6 promote |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------- | --------------------------------- | ---------------------------------------------------------- | ----------------------------------------------------- | --------------------------------- | ----------------------------- | ---------- |
| 0               | Path B deletion + Path X rewire                                                                                                | ✅                                                 | ✅ 23/5 18:25                      | ✅ 23/5 18:42                                               | ✅ 23/5 18:47 G3 PASS                                  | ⚠️ pending Michael redis decision | n/a                           | ⬜          |
| 1               | Adaptive Stop Engine                                                                                                           | ✅ multipliers (Master Sheet 4)                    | ✅ 23/5 19:00                      | ✅ 23/5 19:27 commit `dd5e2f2`                              | ✅ 23/5 19:30 G3 PASS 12/12                            | ⬜ G4 pending Michael smoke trade  | ⬜                             | ⬜          |
| 2a              | OFA Entry signal fix                                                                                                           | ✅ Master Sheet 2 verbatim                         | ✅ handoff 23/5 19:35              | ✅ 23/5 19:51 commit `847bb40`                              | ✅ 23/5 19:55 G3 PASS 12/12                            | ⬜ G4 pending Michael smoke trade  | ⬜                             | ⬜          |
| 2bc             | OFA Config + Validators (merged 2b+2c)                                                                                         | ✅ spec locked · arch Option X (S3 forces_history) | ✅ handoff 23/5 20:30              | ✅ 23/5 20:46 commit `dfdf91f`                              | ✅ 23/5 20:50 G3 PASS 10/10                            | ⬜ G4 pending Michael smoke        | ⬜                             | ⬜          |
| 3a · Stream 1   | EXIT_V6 fix · Neutral enum split (NeuE+NeuC) + targets_table NT NO_TRADE + state_machine 6/7 hits + api.py classification      | ✅ D-091.Q1 locked + Option B 23/5 20:34           | ✅ Cursor handoff ready 23/5 20:34 | ✅ chain `dd9c34f` → `a58ee61` → `689ac41` 23/5 20:38-20:55 | ✅ 23/5 21:00 G3 PASS 14/14 (Cursor)                   | ⬜ G4 pending                      | n/a (no LIVE behavior change) | ⬜          |
| 3a · Stream 1.5 | prev_day wiring · `DayTypeStateMachine.__init__` + `_stage_a1` capture + line 547 `_rescore_from_behavior` rewrite             | ✅ D-091 Option B locked                           | ✅ Cursor handoff ready 23/5 21:05 | ✅ 23/5 21:14 commit `548f1f6`                              | ✅ 23/5 21:18 G3 PASS 10/10 (Cursor · first-try clean) | ⬜ G4 pending                      | n/a (no LIVE behavior change) | ⬜          |
| 3a · Stream 2   | Day-type targets (7 schemas) · `day_type_targets.py` + T1Setup t3_price + fix opening_type→current_day_type + D-091.Q2 NT gate | ✅ D-091.Q1+Q2+Q4 locked                           | ✅ Cursor handoff ready 23/5 21:42 | ✅ 23/5 22:14 commit `cf6383e`                              | ✅ 23/5 22:15 G3 PASS (Cursor · first-try clean · zero new regressions) | ⬜ G4 pending                      | n/a (no LIVE behavior change) | ⬜          |
| 3b · Stream 1   | Trail infrastructure · `atr_caps.py` + BE+1T fix + Pkg 3a override hook                                                        | ✅ D-094 LOCKED 23/5 23:50 + handoff §4            | ✅ Cursor handoff ready 23/5 23:50 (`DESKTOP_PKG3B_TRAIL_LOGIC_HANDOFF.md` §4) | ✅ 24/5 18:53 commit `6dfce93` (+463 / 7 files / 34 tests) | ✅ 24/5 18:57 G3 PASS 8/8 (Cursor · first-try clean · zero new regressions) | ⬜ G4 pending                      | n/a (no LIVE behavior change) | ⬜          |
| 3b · Stream 2   | TrailEngine + persistence (Layer 4 wiring deferred to 3b-3 · D-094 retrofit deferred per Michael directive)                    | ✅ D-094 LOCKED 23/5 23:50 + handoff §5 + 3 Cursor-Michael LOCKS 24/5 19:30 + 6 Claude review fixes v2 24/5 20:00 | ✅ Cursor mega-prompt v2 ready 24/5 20:00 (`MEGA_PROMPT_PKG3B_STREAM2.md`) | ✅ 24/5 20:07 commit `23c8456` (+1146 / 3 files / 29 tests) | 🔴 G3 STRATEGIC STOP 24/5 20:15 · CC wrote from scratch · 4 D-094 gap violations (Gap 2/5/11/14) · 29 tests PASS but spec-divergent · resolution: retrofit ב-3b-3 v3 per Michael directive 20:35 | ⬜ G4 pending 3b-3 | superseded by 3b-3 retrofit | ⬜ |
| 3b · Stream 3   | **D-094 retrofit + Layer 4 wiring** · 4 gap fixes from 3b-2 (LOCK 6-9) + 5 Layer 4 services (LOCK 1-5)                          | ✅ D-094 LOCKED + handoff §6 + 5 LOCKS 24/5 20:15 + 6 Claude fixes 24/5 20:30 + 4 D-094 retrofits (LOCK 6-9) per Michael directive 20:35 | ✅ Cursor mega-prompt v3 ready 24/5 20:50 (`MEGA_PROMPT_PKG3B_STREAM3.md` · ~5-6h CC · 58 tests · 28 migrated + 30 new) | ✅ 24/5 21:23 commit `6b2b7cc` → amended 21:42 to `1e01c4a` (3b-3.1 hotfix folded in via `git commit --amend`) | ✅ 24/5 21:45 G3 PASS 14/14 (Cursor · post-amend re-verify · 59/59 tests · baseline 42 failed/1114 passed identical to pre-3b-3 · zero regressions) · LOCK 1-9 + v4 Patch A + D-094 §3.B.3 order all verified | ⬜ G4 pending | ⬜ | ⬜ |
| 3c              | Contract split per pattern (emit-only · feeds Pkg 6)                                                                           | ✅ D-091 §Contract Distribution verbatim (all 10 PatternName values mapped) | ✅ Cursor handoff ready 24/5 19:45 (`DESKTOP_PKG3C_CONTRACT_SPLIT_HANDOFF.md`) | ✅ 24/5 19:45 commit `c917d42` (+163 / 6 files / 16 tests) | ✅ 24/5 19:50 G3 PASS 10/10 (Cursor · first-try clean · zero new regressions) | n/a (emit-only · implicit in Pkg 6 G4) | n/a (no LIVE behavior) | ⬜          |
| 3b · Stream 3.1 | **HOTFIX** · Layer 4 wiring order per D-094 §3.B.3 line 468 · reorder `_apply_layer4` evaluate calls to MFE→CCI→TCCI→SWI→DayType + update docstring lines 552-557 | ✅ D-094 §3.B.3 spec already locked | ✅ ad-hoc CC prompt (Michael 21:35) | ✅ 24/5 21:42 amended into `1e01c4a` (CC chose `git commit --amend` · same parent `31e493e` · +204/-119 trail_engine.py + 95/-119 tests · scope expansion beyond reorder: candidates→Dict + audit-on-move + preconditions + day_type WARN-only routing with no_trade reclass escalation gate · all legitimate improvements matching LOCK 5 part B intent) | ✅ 24/5 21:45 G3 PASS folded into 3b-3 G3 PASS | n/a (no LIVE behavior change) | n/a | ✅ folded |
| 4a              | ~~Risk Rules Critical (2 EXIT)~~ **DEFERRED · D-095 25/5 11:18** · scope absorbed by 3b-3 (TCCI cross live + NO_TRADE reclass live) | ❌ DEFERRED                                       | n/a                               | n/a                                                        | n/a                                                   | n/a                               | n/a                           | n/a        |
| 4b              | ~~Risk Rules Tightening (3)~~ **DEFERRED · D-095 25/5 11:18** · scope absorbed by 3b-3 (mfe/cci_flat/swi all live in _apply_layer4) | ❌ DEFERRED                                       | n/a                               | n/a                                                        | n/a                                                   | n/a                               | n/a                           | n/a        |
| 5a              | Inv H&S + H&S Top                                                                                                              | ✅ lock 3 + Master Sheet 2 trading spec (24/5 16:27) | ✅ Cursor handoff ready 24/5 16:35 | ✅ 24/5 17:22 commit `7ffab50`                              | ✅ 24/5 17:45 G3 PASS 10/10 (Cursor · first-try clean) | ⏳ Scaffolding G3 PASS 24/5 21:00 commit `31e493e` · Axes 1+3+4 GREEN · **Axis 2 FIXED 26/5 commit `7433d52`** · setup.ts now uses bar timestamp · mini-G3 PASS 932/932 · ready for smoke trade | ⬜                             | ⬜          |
| 5b              | Double Bottom + Top                                                                                                            | ✅ lock 3 + Master Sheet 2 trading spec (24/5 17:57) | ✅ Cursor handoff ready 24/5 18:00 (`DESKTOP_PKG5B_DBDT_HANDOFF.md`) | ✅ 24/5 18:35 commit `2c001a2`                              | ✅ 24/5 18:50 G3 PASS 10/10 (Cursor · first-try clean) | ⏳ Scaffolding G3 PASS 24/5 21:00 (shared with 5a · commit `31e493e`) | ⬜                             | ⬜          |
| 5c              | Bull Flag + Bear Flag                                                                                                          | ✅ lock 3 + D-091.Q5 Path C (24/5 18:45) + Master Sheet 2 (24/5 16:27) | ✅ Cursor v2 handoff ready 24/5 19:00 (`DESKTOP_PKG5C_FLAGS_HANDOFF.md`) | ✅ 24/5 19:19 commit `427d687`                              | ✅ 24/5 19:30 G3 PASS 12/12 (Cursor · first-try clean · Q5 Path C verbatim) | ⬜ G4 pending Michael smoke trade  | ⬜                             | ⬜          |
| 8               | Quality V2 · Auth Table V1 (pattern × day_type × tier sizing)                                                                    | ✅ 25/5 12:22 · `S2_AUTH_TABLE_V1.md` LOCKED      | ✅ 25/5 12:25 · Cursor handoff ready (`DESKTOP_PKG8_QUALITY_V2_HANDOFF.md`) | ✅ 25/5 13:00 commits `9bc3925` + `773f056` (+341/-58 · 7 files) | ✅ 25/5 13:20 G3 PASS (Cursor · 41 tests · 70 cells verified · Lock #1-8 all PASS) | ⬜ G4 pending post-RTH              | ⬜                             | ⬜          |
| **6**           | **TradeManager extensible**                                                                                                    | ✅ 25/5 13:57 · `S2_TRADEMGR_HOOKS_V1.md` LOCKED (Q9.1-Q9.4 all approved) | ✅ 25/5 14:05 · Cursor handoff ready (`DESKTOP_PKG6_TRADEMGR_HANDOFF.md`) | ✅ 25/5 14:28 commit `77dd4cf` (+887/-54 · 13 files · 39 tests) + `ed76e78` (rename fix · name collision with existing `test_trade_manager.py`) | ✅ 25/5 14:35 G3 PASS (Cursor verified · 10/10 acceptance · 39/39 new tests · D-095 zero-diff · `docs/reports/PKG6_G3_PASS_2026-05-25.md` commit `da4804b`) | ⬜ G4 pending post-RTH              | ⬜                             | ⬜          |
| **Consolidation** | **Phase A Consolidation · stale-fixture repair (LAST · 15th)**                                                              | ✅ 25/5 14:55 · `DESKTOP_PHASE_A_CONSOLIDATION_STALE_FIXTURES_HANDOFF.md` (Cursor verify-first) | ✅ 25/5 14:55 · Cursor handoff ready | ✅ 25/5 15:11 commit `799e00c` (+30/-5 · 3 test files · 18 tests · zero production diff) | ✅ 25/5 15:15 G3 PASS (Cursor verified · 7/7 acceptance · 6 originally-failing tests now PASS · regression sweep identical 30/1562) · `docs/reports/PHASE_A_CONSOLIDATION_G3_PASS_2026-05-25.md` commit `8e98010` | n/a (test-only fix · no LIVE behavior change) | n/a                           | ⬜          |


---

## Pipeline 1 · Phase C (DEMO add-ons)


| Pkg    | Name                                            | Trigger         | Status |
| ------ | ----------------------------------------------- | --------------- | ------ |
| DEMO-1 | News pause + news_countdown                     | DEMO start      | ⬜      |
| DEMO-2 | Filters (lunch skip + FOMC window)              | DEMO start      | ⬜      |
| Pkg 7  | STC/BTC time-of-day (optional · SHADOW-decided) | SHADOW analysis | ⬜      |


---

## Pipeline 2 · S4 D-092 Woodies


| Status       | Item                                                                              |
| ------------ | --------------------------------------------------------------------------------- |
| ✅ 23/5 18:00 | D-092 LOCKED · 9 patterns · ATR-14 stop arch · day-type matrix · 9 anti-patterns                                                                                                                                                                                                                  |
| ✅ 23/5 18:00 | `S4_WOODIES_PATTERN_TABLES_V1.xlsx` + 3 CSV exports in `docs/spec_authority/`                                                                                                                                                                                                                     |
| ✅ 23/5 18:00 | `D-092_S4_WOODIES_UPDATE.md` in `docs/decisions/`                                                                                                                                                                                                                                                 |
| ✅ 25/5 16:30 | **All 10 P-W locks closed** — `docs/handoff/MEGA_PROMPT_PW_DECISIONS_INTAKE.md` §Locked Decisions · audit passed (formulas direction-agnostic · no circular deps · pre-LIVE protocol compliant)                                                                                                   |
| ✅ 25/5 16:50 | **v2 FINAL · all 3 gaps resolved** — Gap 1 DTV1 saved to `docs/MEMS26_WOODIES_DECISION_TREE_V1.md` (1085 LOC · MD5-verified · matches Michael upload) · Gap 2 P-W6 typo fix `RED → CONT wins` (was `REV wins` · unreachable branch · D-092 unchanged) · Gap 3 confidence formulas code-as-truth KEEP (Registry §5 verified) · Cursor follow-ups #1+#6 ✅ DONE |
| ✅ 25/5 16:50 | Registry §5 row 9 (HFE) updated · "להחליט: DLL only או keep Python fallback" → "🔒 P-W2 lock 25/5 · B · DLL primary · Python audit-only · DLL down → no HFE"                                                                                                                                       |
| ✅ 27/5 08:58 | **G3 PASS (Cursor)** · commit `2e14400` · W-0..W-8 LOCKED (9/10) · W-9 LEGIT BLOCK (S2 Pkg 6 RiskRule + Liran doctrine missing) · 210 new tests + 912 regression · 0 new failures · PatternDispatcher wired `woodies_system.py:242` · AP8 universal wired · atr_stop wired all patterns · raw_confidence UNCHANGED |
| ✅ 27/5 09:00 | **Michael decisions locked:** W-9→defer Pipeline 3 · W-10 Time stop→add to Pipeline 2 (~1.5d CC) · W-11 Partial exit→defer Pipeline 3 · Finding #15 YELLOW edge→Phase B |
| 🟡 SHADOW     | **SHADOW: APPROVED** · paper-trading ready · 9 patterns firing via R_t1 dispatcher |
| ✅ LIVE BLOCK CLEARED | **W-10 Time stop ENFORCED** (Registry #11) · `TimeStopEnforcer` fires per-bar · WARNING log · gateway close |
| ✅ 27/5 10:18 | **W-10 DONE** · commit `210e1ca` · `time_stop.py` + wiring + 35 tests · G3 PASS · 947/947 regression |
| ⏳ pending    | **CC verification batch** (`CC_FINAL_VERIFICATION_BATCH_2026-05-26.md` · §9.2 ❓ items · WIRED layer) |
| ⏳ pending    | **SHADOW data review** ≥200 trades · Phase B R_t1 + raw_confidence distribution check |


---

## Pipeline 3 · S1 Day Type verify


| Status    | Item                       |
| --------- | -------------------------- |
| ⏳ pending | Verify report from Michael |


---

## Pipeline 4 · S3 Footprint verify


| Status    | Item                                                         |
| --------- | ------------------------------------------------------------ |
| ⏳ pending | Verify report from Michael (incl. O-4 entry/stop spec audit) |


---

## Pipeline 5 · Sierra Order Routing (D-093)

**Authority:** `docs/decisions/D-093_SIERRA_ORDER_ROUTING.md` (🔒 LOCKED 23/5 19:00)
**Discovery:** No trade has ever reached Sierra — DLL TODO + 2 unwired layers + 3 dead executor stubs.

### Sub-decisions deferred (verify-first)


| Q        | Decision                                                                | Trigger                     | Status |
| -------- | ----------------------------------------------------------------------- | --------------------------- | ------ |
| D-093.Q1 | Gateway canonical: `backend/v9/gateway/` OR `services/trading_gateway/` | After CC P5-0a audit report | ⏳ P5-0 audit in progress (Desktop meta-prompt sent) |
| D-093.Q2 | Sierra DEMO account identifier                                           | Before P5-1 execution       | ✅ **LOCKED 26/5 12:44 IL** · IronBeam · Teton CME Routing [simulation] · verify exact label before P5-1 |


### Build queue (9 packages · ~9.5 CC days)


| Pkg  | Name                                          | G0 spec       | G1 prompt | G2 CC | G3 review | G4 UAT | G5 soak | G6 promote |
| ---- | --------------------------------------------- | ------------- | --------- | ----- | --------- | ------ | ------- | ---------- |
| P5-0 | Gateway reconciliation (verify-first)         | ✅ D-093       | ⏳ meta-prompt sent to Desktop 26/5 | ⬜     | ⬜         | ⬜      | ⬜       | ⬜          |
| P5-1 | DLL `sc.BuyEntry/SellEntry` + Attached Orders (DEMO) | ✅ D-093 · Q2 LOCKED 26/5 | ⏳ meta-prompt sent to Desktop 26/5 · pending Q1 lock | ⬜     | ⬜         | ⬜      | ⬜       | ⬜          |
| P5-2 | DLL result mapping                            | ⬜ (deps P5-1) | ⬜         | ⬜     | ⬜         | ⬜      | ⬜       | ⬜          |
| P5-3 | Backend LIVE wiring                           | ⬜ (deps P5-1) | ⬜         | ⬜     | ⬜         | ⬜      | ⬜       | ⬜          |
| P5-4 | Position reconciliation                       | ⬜ (deps P5-2) | ⬜         | ⬜     | ⬜         | ⬜      | ⬜       | ⬜          |
| P5-5 | Order modification                            | ⬜ (deps P5-2) | ⬜         | ⬜     | ⬜         | ⬜      | ⬜       | ⬜          |
| P5-6 | Heartbeat + watchdog                          | ✅ D-093       | ⏳ meta-prompt sent to Desktop 26/5 | ⬜     | ⬜         | ⬜      | ⬜       | ⬜          |
| P5-7 | Bridge integration                            | ✅ D-093       | ⏳ meta-prompt sent to Desktop 26/5 | ⬜     | ⬜         | ⬜      | ⬜       | ⬜          |
| P5-8 | End-to-end UAT (SHADOW + DEMO + LIVE-on-demo) | ⬜ (deps all)  | ⬜         | ⬜     | ⬜         | ⬜      | ⬜       | ⬜          |


**Blocks:** SHADOW gate (P-S0) + DEMO gate · because without P5-1 no trade reaches a Sierra account.
**Does NOT block:** Pipeline 1 (S2) · Pipeline 2 (S4) · Pipelines 3/4 verify — those can proceed in parallel.

---

## Pipeline 2 · Shadow Data Quality Gate

**Audit 27/5 10:20 IL** — before LIVE or DEMO enable, shadow data must pass quality review.

| Date | Trades | W/L | PnL | Status |
| ---- | ------ | --- | --- | ------ |
| 2026-05-21 | 633 | 260/373 | -$6,534 | ⚠️ **SUSPECT BACKTEST** · 100 trades/hr uniform · avg_stop=1.5pts |
| 2026-05-22 | 1,830 | 736/1,094 | -$21,670 | ⚠️ **SUSPECT BACKTEST** · 100 trades/hr 24h straight · 736 zero-stop entries |
| 2026-05-23 | 9 | 9/0 | +$375 | ✅ looks real · avg_stop=0 (pre-ATR-stop code) |
| 2026-05-25 | 145 | 64/81 | -$303 | 🟡 real but high fire-rate (145/day = 12/hr) · avg_stop=1.55pts |
| 2026-05-26 | 74 | 32/42 | -$224 | 🟡 real but 74/day = 6/hr · avg_stop=1.54pts |
| 2026-05-27 | 1 | 0/1 | -$15 | ✅ · cleaned · table reset to 0 for fresh shadow start |

**Status after cleanup:** v9_trades = 0 rows. Shadow will repopulate when pipeline fixes deployed.

**Pending (Michael decision):**
- (b) 25/5-26/5 high fire-rate investigation (145/74 trades/day) — after pipeline fixes confirmed working
- (c) Minimum 200 clean post-fix SHADOW trades before LIVE quality assessment

## DEMO gate


| Criterion                                 | Status |
| ----------------------------------------- | ------ |
| All Phase A packages SHADOW passed        | ⬜      |
| D-092 (S4) done                           | ✅ Pipeline 2 complete · W-10 LIVE block cleared |
| S1 + S3 verify closed                     | ⬜      |
| ≥40 SHADOW trades on firing pattern combo | 🟡 data audit required first (see above) |
| Zero open warnings 24h                    | ⬜      |


---

## LIVE micro gate (P-L0)


| Criterion                   | Status |
| --------------------------- | ------ |
| DEMO 7 days on Sierra Sim   | ⬜      |
| Zero bugs surfaced in DEMO  | ⬜      |
| 4 pipelines fully promoted  | ⬜      |
| DEMO-1 + DEMO-2 done + soak | ⬜      |
| P-L0 Preflight 100%         | ⬜      |
| Michael sign-off explicit   | ⬜      |


---

## Risk tracker


| #   | Risk                                                     | Severity | Mitigation status                                     |
| --- | -------------------------------------------------------- | -------- | ----------------------------------------------------- |
| 1   | Spec drift mid-dev                                       | HIGH     | spec lock-once · D-XXX only                           |
| 2   | CC hallucinated APIs                                     | MED      | mega prompt whitelist enforces                        |
| 3   | Silent excepts                                           | HIGH     | mega prompt forbids · G3 adversarial scan             |
| 4   | Parallel streams stomp on shared files (manager.py)      | MED      | Pkg 3a/3b/3c sequential · scope paths whitelist       |
| 5   | Soak finds critical bug                                  | HIGH     | bug-fix budget 30-50%                                 |
| 6   | Michael overload                                         | MED      | spec locks 1+3 first                                  |
| 7   | Master Summary drift from chat                           | MED      | chat = source of truth                                |
| 8   | Pkg 6 hooks insufficient — future rule needs core change | MED      | G3 of Pkg 6 must include "future-rule" unit-test stub |


---

## Amendments log

Full log moved to [](../reports/AMENDMENTS_LOG.md) (148 KB · renderer-friendly separation).
