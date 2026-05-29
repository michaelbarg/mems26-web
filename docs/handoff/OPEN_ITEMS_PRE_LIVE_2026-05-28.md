# Open Items — Pre-LIVE Backlog · 2026-05-28 21:50 IDT

**Compiled by:** Cursor agent
**Purpose:** Single canonical list of every known issue that must be addressed
before MEMS26 reaches LIVE futures trading. Sorted by severity. Each row links
back to the source diagnosis so context never gets lost.

This list assumes the **S4 `current_bar` routing fix**
(`CC_HANDOFF_S4_CURRENT_BAR_ROUTING_FIX_2026-05-28.md`) has been applied and
UAT-verified. If it hasn't, that item is #0 — do it first.

Status legend: 🔴 BLOCKER · 🟠 HIGH · 🟡 MED · 🟢 LOW · ✅ DONE (today's work) ·
⛔ DEFERRED (Pipeline 3+)

---

## §1 · LIVE blockers (must close before LIVE)

| # | Item | Owner | Severity | Source | Notes |
|---|------|-------|----------|--------|-------|
| 1 | **DLL frozen-tail bug** — `sc.GetContainingIndexForDateTimeIndex(woodies_chart, …)` clamps the last ~13 5-min bars of every session to a single Woodies-chart index, freezing `cci_14 / cci_6_tcci / lsma_value / ema_34 / swi_value / czi_value / trend_state`. The S4 `current_bar` workaround papers over this for routing but **the frontend Woodies CCI panel still shows the frozen tail**, and any future consumer that reads `history` (replay, charts, audit) gets stale data. | CC + Michael (Sierra-side) | 🔴 | `AUDIT_S2_S4_LIVE_FORENSICS_2026-05-28.md` §1, §3, §6 rank-1 · CC review Claim 1 | Two paths:<br>(a) DLL patch — fix `mapIdx` in `sc_study/v9_woodies_export.h:460-475` to use `bi` directly when `GetContainingIndexForDateTimeIndex` clamps (detect by `mi == prev_mi` for ≥2 consecutive bars). Requires DLL rebuild + Sierra study reload.<br>(b) Sierra config — set `WoodiesChartNumber` DLL input #18 to the **same chart number** as the DLL's host chart, eliminating the cross-chart fetch entirely. Verify this is acceptable for the Woodies study setup with Michael. |
| 2 | **`woodies_chart_routes.py:43` hardcoded `ts_unix += 5*3600`** — over-corrects by 1h in CST (Nov–Mar). Winter-time bomb. Bridge's `_chicago_to_utc` is DST-aware (`zoneinfo.ZoneInfo("America/Chicago")`), this endpoint is not. | CC | 🟠 | CC review §4 / forensic audit §3 "Timestamp drift" sub-finding | Replace the hardcoded constant with a DST-aware conversion using `zoneinfo`. Add a regression test that runs in CST (mock `datetime.now(tz=ZoneInfo("America/Chicago"))` for a Dec date) and asserts no double-correction. |
| 3 | **S2 `current_day_type=None` silent skip** — chart-pattern day-type gating at `five_min_system.py:728-749` checks `current_day_type in {"Neutral_Extreme", …, "Variation"}`. When `current_day_type` is `None` (mid-session restart before any S1 event arrives), the check is silently False and chart patterns are skipped without logging. | CC | 🟠 | CC review §4 gap #2 | Either: (a) explicitly log a warning when `current_day_type is None`, or (b) seed `current_day_type` from `v9_day_type_history` on startup (similar to the IB seed we did today). Option (b) is cleaner. |
| 4 | **Status enum sync — `/api/v9/status.day_type` reports `PENDING/UNKNOWN/A1`** while `v9_day_type_history` row IS classified (`Normal · 0.68 · IB locked · INDETERMINATE`). Inspector reads from a different field than the live state machine writes. | CC | 🟠 | `STATUS_BOARD.md` 19:00 §1 row 2 / live verify at 19:00 IDT | Read `backend/v9/systems/day_type/consumer.py` — find where the classification is persisted and add a `status='CLASSIFIED'` write next to the fields update. Plus a regression test on the inspector. |
| 5 | **11 pre-existing pytest failures** introduced by today's day_type + IB persistence changes. CC's volume fix report flagged them. They block the "全部 green" gate before LIVE. | CC | 🟠 | CC volume fix report §Regression / Cursor verification at 19:23 IDT | Run `pytest tests/v9/systems/day_type/ tests/v9/api/test_tpo_routes_sierra_contract.py -q` — list every failure with file:line. Triage each: real regression vs test-fixture drift. |
| 14 | **✅ RESOLVED — Bug A · TIME_STOP fires after 52s (shadow #155).** Root cause: `WoodiesSystem._bar_count` increments per bridge push (~3s), not per closed 5-min bar; 18 pushes ≈ 54s triggered the W-10 enforcer. **Fix (Option B · Michael 2026-05-28 21:50 IL):** disabled the Woodies-side W-10 TimeStopEnforcer via YAML kill switch (`dispatcher_config.yaml::time_stop.time_stop_minutes = null`). Constitution V3 Layer 4 (`bar_level_detector._check_time_stop` + `TIME_STOP_BY_DAY_TYPE`) is now the sole authority, with Day-Type-dependent limits (TREND_NORMAL=none · VARIATION=60 · NORMAL=30 · TREND_DD=90 · NEUTRAL=45 · NONTREND=20). Regression: `tests/v9/systems/woodies/test_w10_time_stop_disabled.py`. | Michael / Cursor | ✅ | `docs/reports/DIAGNOSIS_TRADE_LIFECYCLE_BUGS_2026-05-28.md` §1 / `AMENDMENTS_LOG.md` 2026-05-28 W-10 entry | Awaits backend restart to activate (paired with parallel IB worker restart). |
| 15 | **Bug B · Demo stop "inverted" for LONG (#156, stop above entry).** CC classified as *WORKING AS DESIGNED* — Smart BE+1T fired after T1 hit per `manager.py::_apply_smart_be_after_t1` (LONG: `target_stop = entry + tick`). The "inversion" is the post-T1 BE stop that then got hit on the same bar. Verify post-restart that with Bug A gone, the LONG path consistently reaches T1 → Smart BE → stop without the early TIME_STOP confusing the picture. | CC / Michael | 🟡 | `DIAGNOSIS_TRADE_LIFECYCLE_BUGS_2026-05-28.md` §2 | Not strictly a bug; tag as verified once a clean LONG fire goes T1 → BE → stop end-to-end with correct PnL. |
| 16 | **Bug C · `t1_hit_ts == stop_hit_ts` (demo #156, identical 18:45:00).** Wide-range bar covered both T1 and the post-Smart-BE stop; `BarLevelDetector` writes both events with the same `fill_ts = bar_ts`. Cosmetic in shadow, but for LIVE the priority should be tightened so a T1+stop straddle records T1 hit but defers Smart BE until the next bar close. | CC | 🟢 | `DIAGNOSIS_TRADE_LIFECYCLE_BUGS_2026-05-28.md` §3 | Fix in `bar_level_detector.py:88-114` — when bar straddles both, suppress Smart BE on the same bar and write distinct timestamps. Regression: synthetic wide-range bar covering both levels. |
| 17 | **✅ RESOLVED — Bug D · pnl=0.0 and exit_price=NULL on TIME_STOP (shadow #155).** Root cause: Woodies `_check_time_stops()` called `tm.close_trade(int(trade_id), "TIME_STOP")` without setting `exit_price` first → `manager._calculate_pnl()` fell back to `exit_price or entry_price = entry_price` → `pnl=0.0`. **Fix (Option B):** Woodies path no longer runs (W-10 disabled). Layer 4's TIME_STOP branch at `bar_level_detector.py:117-124` sets `refreshed.exit_price = bar_close` BEFORE `close_trade(trade.id, "TIME_STOP")`, so PnL computes correctly. Regression: `tests/v9/services/trade_manager/test_layer4_time_stop_authority.py` source-inspects `BarLevelDetector.on_bar` to pin the ordering. | Michael / Cursor | ✅ | `DIAGNOSIS_TRADE_LIFECYCLE_BUGS_2026-05-28.md` §4 / `AMENDMENTS_LOG.md` 2026-05-28 W-10 entry | Awaits backend restart to activate. |
| 18 | **Bug E · `stop_hit_ts` / `exit_ts` defaults to 09:30:00 (trades #14, #15).** Stop hit recorded as 09:30:00 ET while entry was 13:35:01 — exit before entry. Likely cause: BarLevelDetector subscribes to the `5min` channel and `_parse_ts` does not apply the same Chicago-to-UTC correction the bridge applies for `woodies_5min`. `09:30:00.000000` without TZ suggests a naive datetime written through. | CC | 🟡 | `DIAGNOSIS_TRADE_LIFECYCLE_BUGS_2026-05-28.md` §5 | Fix `BarLevelDetector._parse_ts` to apply DST-aware Chicago→UTC conversion (mirror `_chicago_to_utc` in bridge). Add regression: mock a bar with Chicago-encoded ts, verify `fill_ts` stored is UTC. |

---

## §2 · Pre-LIVE quality items (close before P-L0 sign-off)

| # | Item | Owner | Severity | Source |
|---|------|-------|----------|--------|
| 6 | **`min_r_t1_threshold = 0.0` (shadow) → `>= 1.0` (LIVE) has no test coverage**. Switching to 1.0 without a parameterized test (covering 0.0, 0.5, 1.0) risks silent breakage on LIVE. | CC | 🟡 | CC review §4 gap, forensic audit §2 D-4 |
| 7 | **Day-type matrix gate A2 is advisory-only** (terminal is always None per `stages/a2_day_type_query.py:9`). For LIVE, the Table B per-day-type allowed-patterns matrix should actually gate fires, not just advise. | CC + Michael | 🟡 | Forensic audit §2 D-3 |
| 8 | **Lunch skip (12:00–13:30 ET) not enforced.** Spec `S4_WOODIES_TABLE_A_Pattern_Setup.csv` says "skip 12:00–13:30 ET" for all 9 patterns. No `lunch` check in `woodies_system.py`. | CC | 🟡 | Forensic audit §2 D-1 |
| 9 | **FOMC ±90min skip not enforced.** Spec mandates it; no calendar wired. | CC | 🟡 | Forensic audit §2 D-2 |
| 10 | **`v9_bars_5min_woodies` sentinel rows `ts='2099-01-02 0X:00:00'`** — placeholder writes from a stalled stream. Build Status inspector hardened today (skips them via `latest_valid_db_ts`), but the **underlying stream still writes them**. Find the bridge / persistence path that emits the sentinel and stop it at source. | CC | 🟡 | Build Status subagent finding · `row_helpers.latest_valid_db_ts` |
| 11 | **`v9_bars_5min_woodies` stores push timestamps, not bar timestamps** — 3,193 rows/day for ~6h of trading (~14 inserts/min). The column is `(ts, …, cci_14, …)` but the same bar gets multiple rows with different `ts` values. Table is OK as a debug log but should NOT be used as a source of truth for replay. | CC | 🟡 | Forensic audit §6 rank-5 |
| 12 | **`opening_type` event payload missing the field S1→S2** — S2's `self.opening_type` is `None`, displayed as "NA" while S1 has `INDETERMINATE`. Cosmetic, zero impact on classification (both map to Normal/WIDE), but Build Status now exposes the divergence loudly via the new Live/Required columns. | CC | 🟢 | CC original diagnosis §3 / forensic audit |
| 13 | **6-bar S1 replay on mid-session restart** — `day_type_seed.py:104-114` falls back to `INDETERMINATE` when the machine missed RTH open. Could be made to replay the first 6 bars from `v9_bars_5min` to recover the correct opening type (e.g. `OPEN_AUCTION_IN`). Cosmetic for trading (Decision Matrix maps both to Normal/WIDE) but helps reproducibility. | CC | 🟢 | CC original diagnosis §3 |

---

## §3 · Closed today (for the record)

| ✅ | Item | Where it landed |
|---|------|-----------------|
| ✅ | Sierra Inputs corrected (In:14=1, In:16=6) | Michael via Sierra UI (17:30 IDT) |
| ✅ | `_ib_from_bars` plaster removed → Sierra-only IB | `tpo_routes.py` |
| ✅ | `/api/v9/key_levels` rewritten — 12/12 fields match Sierra | `key_levels_routes.py` |
| ✅ | TPO system IB sourced from Sierra (no internal accumulator) | `tpo_system.py` |
| ✅ | `state_machine._stage_a3 / a4` cleaned (no bar.high/low fallback) | `state_machine.py` |
| ✅ | `main.py` inline IB plaster removed (BarInput.ib_h from Sierra) | `main.py` |
| ✅ | UI re-ordered to Michael's spec — `Today POC / Y POC / IB Today / Y IB / Y Range / Today Range` | `KeyLevelsStrip.tsx`, `KeyLevelsCard.tsx` |
| ✅ | **S2 volume key mismatch fix** (`"vol"` vs `"v"`) — applied to code, awaits restart | `five_min_system.py:698` (CC) |
| ✅ | **Inspector mode + FHB gate** — `DAY_TYPE_MODE` allowed; FHB bypassed post-first-hour | `s2_inspector.py:103, 112` (CC) |
| ✅ | **Build Status `Live / Required / Freshness` columns** across S1+S2+S4 — DB sentinel-2099 lex-sort lag fixed in inspector via `latest_valid_db_ts` | `types.py`, `row_helpers.py`, `*_inspector.py`, `ComponentTable.tsx` (Cursor subagent) |
| ✅ | **Forensic audit + Claude Desktop mega-prompt + CC critical review** — three converging investigations falsified "no patterns today" and identified DLL frozen-tail as primary root cause | `docs/reports/AUDIT_S2_S4_LIVE_FORENSICS_2026-05-28.md`, `docs/handoff/MEGA_PROMPT_CLAUDE_DESKTOP_S2_S4_AUDIT_2026-05-28.md` |

---

## §4 · Strategic / deferred to Pipeline 3+

| ⛔ | Item | Why deferred |
|---|------|--------------|
| ⛔ | DLL `WoodiesChartNumber` redesign / monolithic export refactor | Architectural — Pipeline 3 scope |
| ⛔ | DEMO-1 (news pause) / DEMO-2 (FOMC filter) | Trigger: DEMO start (post-SHADOW) |
| ⛔ | Pkg 7 STC/BTC time-of-day | Trigger: SHADOW analysis ≥200 trades |
| ⛔ | Pipeline 5 P5-1..P5-8 Sierra Order Routing | Blocks LIVE; Q1 (gateway canonical) pending Michael lock |
| ⛔ | Yesterday IB from DLL extension | UI shows `Y IB: dll_missing` honestly; not critical for LIVE |
| ⛔ | Pipeline 1 G4 UAT on 10 packages | Trigger: post-RTH 16:30 IL (pending) |
| ⛔ | 60-min "zero open warnings" soak | Post-UAT |

---

## §5 · Open questions for Michael (next decision points)

1. After CC applies the `current_bar` routing fix and UAT passes, **how do
   you want to address DLL frozen-tail**? Two paths in §1 item #1 — DLL
   patch vs Sierra config (`WoodiesChartNumber` = host chart).
2. **11 pre-existing test failures** — triage now or after the routing fix
   is verified live? My suggestion: after, so we don't conflate signals.
3. **Status enum sync (#4)** — fix in same CC session as the routing fix
   (cheap, 2-line change) or queue separately?
4. **Should we restart the bridge** after the backend restart? The bridge
   reads from disk and pushes to localhost — its state is independent of
   backend reloads. But if the bridge has been running since pre-volume-fix,
   it may have stale internal buffers (unlikely but worth checking).

---

## §6 · Source-of-truth pointers (so context never gets lost)

- **Master plan:** `docs/plans/PRE_LIVE_PIPELINE_2026-05-23.md` V2
- **Status board:** `docs/plans/STATUS_BOARD.md`
- **Amendments log:** `docs/reports/AMENDMENTS_LOG.md`
- **Spec authority:** `docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt`
- **Pre-LIVE protocol:** `.cursor/rules/mems26-pre-live-protocol.mdc`
- **Stability rules:** `.cursor/rules/mems26-stability.mdc`, `CLAUDE.md`
- **Bridge ops runbook:** `docs/runbooks/SIERRA_DLL_OPS.md`
- **Today's three convergent reports:**
  - `docs/reports/DIAGNOSIS_S2_S4_BLOCKED_2026-05-28.md` (CC first pass — superseded)
  - `docs/reports/AUDIT_S2_S4_LIVE_FORENSICS_2026-05-28.md` (Cursor falsified CC)
  - `docs/handoff/MEGA_PROMPT_CLAUDE_DESKTOP_S2_S4_AUDIT_2026-05-28.md` (independent review prompt)
- **CC handoff for the immediate fix:**
  - `docs/handoff/CC_HANDOFF_S4_CURRENT_BAR_ROUTING_FIX_2026-05-28.md`
