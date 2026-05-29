# MEGA PROMPT · CC Phase 2 — Integrated Fix Implementation
## IB Cleanup + TZ Fix + Trade Lifecycle Bugs · 2026-05-29

**Author of handoff:** Cursor agent (Claude Opus 4.7)
**Owner (CC):** Claude Code
**Prerequisite:** `MEGA_PROMPT_CC_PHASE1_AUDIT_2026-05-28.md` completed AND Michael green-lit the consultation (`CC_AUDIT_CONSULTATION_2026-05-28.md`).
**Mode:** **Implement → Test → Restart → UAT → Report.** One group at a time. Stop and consult Michael between groups.
**Severity:** 🔴 LIVE blocker family — IB data integrity + TZ correctness + trade lifecycle.
**Pre-LIVE protocol:** `.cursor/rules/mems26-pre-live-protocol.mdc` (Mistakes #1-#11, Source-of-Truth Rules 1-5).

---

## §0 · TL;DR

Phase 1 produced a re-ranked, integrated fix order. This Phase 2 prompt executes that list in **dependency-safe groups**. Each group has its own UAT (4 axes) before the next group starts.

**Forbidden actions** (Phase 2 specifically):
- Do NOT undo W-10 disable (`time_stop_minutes: null`). Bugs A + D from `DIAGNOSIS_TRADE_LIFECYCLE_BUGS_2026-05-28.md` are resolved by this kill switch.
- Do NOT apply CC's original 7-fixes prompt diffs for Bugs #3 (TIME_STOP push counter) and #5 (TIME_STOP exit_price). Those paths are now dead code.
- Do NOT add `except Exception: pass` ANYWHERE. Every catch must log at `logger.warning` or `logger.error`.
- Do NOT touch the DLL (`sc_study/*`) without Michael's explicit go-ahead AND a fresh Sierra Subgraphs screenshot.
- Do NOT rebuild the DLL without `docs/runbooks/SIERRA_DLL_OPS.md` ritual.

**Must read before any edit:**
1. `MEGA_PROMPT_CC_PHASE1_AUDIT_2026-05-28.md` + your own `CC_AUDIT_CONSULTATION_2026-05-28.md` (Phase 1 output).
2. `docs/reports/CURSOR_AGENT_SELF_CRITIQUE_AND_CHANGE_LOG_2026-05-28.md` — what NOT to undo.
3. `.cursor/rules/mems26-pre-live-protocol.mdc` and `CLAUDE.md` — full Source-of-Truth Discipline.
4. `docs/reports/DIAGNOSIS_IB_GROUND_TRUTH_DIVERGENCE_2026-05-28.md` — Bugs #1-#5 fix sketches.
5. `docs/reports/DIAGNOSIS_TRADE_LIFECYCLE_BUGS_2026-05-28.md` — Bugs A-E. A + D resolved; B + C + E remain.

---

## §1 · Pre-implementation gates (block start of Phase 2)

| Gate | Status before Phase 2 starts | Owner |
|---|---|---|
| Phase 1 audit consultation doc written (`CC_AUDIT_CONSULTATION_2026-05-28.md`) | Must be complete | CC |
| Michael has green-lit the integrated fix order | Must be confirmed (verbal or message) | Michael |
| Sierra Chart TZ confirmed (ET or CT) via chart settings screenshot | Required for Group B | Michael |
| Sierra Initial Balance Study Subgraphs tab screenshot received | Required for Group F (DLL fix) | Michael |
| Backend restart slot decided | Required for Group A → C transitions | Michael |
| `git status` shows expected files only (no surprise uncommitted work) | Required at start | CC |

If any gate fails, STOP and message Michael.

---

## §2 · Fix groups (in strict dependency order)

Execute groups A → G sequentially. **One group at a time.** After each group: run targeted pytest, then proceed only if green.

### Group A — TZ investigation & confirmation (Michael-led, no code yet)

**Goal:** Establish definitively whether Sierra Chart emits timestamps in ET or CT, so the bridge TZ fix doesn't ship on a wrong assumption (Pre-LIVE Mistake #10 / Rule 4).

**Steps:**
1. Request from Michael: screenshot of `Sierra Chart → Chart Settings → Time Zone` for the MES chart.
2. Re-verify with bar-math:
   ```sql
   -- If bridge TZ is correct, RTH open (09:30 ET) volume jump should appear at 13:30 UTC.
   -- If bridge interprets ET-encoded ts as CT (over-adds 5h instead of 4h), volume jump shifts to 14:30 UTC.
   SELECT
     strftime('%H:%M', ts) AS hhmm_utc,
     SUM(volume) AS vol,
     COUNT(*) AS bar_count
   FROM v9_bars_5min
   WHERE symbol='MES' AND date(ts)='2026-05-28'
   GROUP BY hhmm_utc
   ORDER BY hhmm_utc;
   ```
   Find the first time bucket with `vol > 2× overnight_avg`. If it's `13:30 UTC` → bridge TZ correct. If `14:30 UTC` → bridge interprets as CT, Sierra is ET, +1h drift confirmed.
3. Cross-check Sierra IB Study Inputs: `Start Time = 09:30:00`. In whichever TZ Sierra uses, this should equal the RTH open. The bar-math above tells you which TZ that is.
4. Document conclusion in `docs/reports/SIERRA_TZ_CONFIRMATION_2026-05-29.md`.

**Deliverable:** TZ confirmed in writing + Michael's screenshot attached.

**Exit gate:** Michael confirms the TZ conclusion. Do NOT proceed to Group B until this is done.

---

### Group B — IB Backend cleanup (no DLL, no TZ change yet)

**Goal:** Remove the synthesis lies from the IB pipeline. After this group, the API will return `ib_high=None, ib_low=None, ib_source="missing"` whenever Sierra DLL is silent — honest failure (Source-of-Truth Rule 1).

**Spec authority:** `docs/reports/DIAGNOSIS_IB_GROUND_TRUTH_DIVERGENCE_2026-05-28.md` § *Fix #2, #3, #4, #5*.

**Fixes in this group (4 fixes):**

#### B.1 — IB Bug #2: Delete `_ib_from_bars()` synthesis
**File:** `backend/v9/api/v9/tpo_routes.py:380-396` + helper at 322-356.

**Sketch (subject to your Phase 1 pushback):**
```python
ib_found = bool(ib.get("found"))
if ib_found:
    ib_high, ib_low, ib_mid = ib.get("high"), ib.get("low"), ib.get("mid")
    ib_source = "sierra_live"
else:
    ib_high = ib_low = ib_mid = None
    ib_source = "missing"
```
Delete `_ib_from_bars()` function entirely. Update `key_levels_routes.py` `sources.ib` string accordingly.

**Regression test:** `tests/v9/api/test_tpo_routes_no_ib_synthesis.py`:
- Patch `_load_sierra_tpo` to return `{"ib": {"found": False, "high": 0, "low": 0}}`.
- Assert `/api/v9/tpo/current` returns `ib_high=None`, `ib_low=None`, `ib_found=False`, `ib_source="missing"`.

**UAT (4 axes):**
- Quality: `curl -s http://localhost:8000/api/v9/tpo/current | jq '.ib_source'` returns `"missing"` (or `"sierra_live"` if DLL recovers).
- Recency: `latest_ts` matches DB `MAX(ts)`.
- Cardinality: response includes all expected fields (just with `null` for IB).
- Latency: < 200ms for `/api/v9/tpo/current`.

#### B.2 — IB Bug #4: Seed rejects non-`sierra_live` IB
**File:** `backend/v9/api/v9/day_type_seed.py:70` + parameter plumbing in `backend/main.py:_day_type_on_bar`.

**Sketch:**
```python
# day_type_seed.py
def maybe_seed_ib_from_tpo(..., tpo_ib_source: Optional[str] = None) -> bool:
    if not tpo_ib_locked:
        return False
    if tpo_ib_source != "sierra_live":
        logger.warning("[day_type_seed] Rejecting non-sierra_live IB source: %s", tpo_ib_source)
        return False
    ...

# main.py
tpo_ib_source = sierra_tpo.get("ib_source")
maybe_seed_ib_from_tpo(..., tpo_ib_source=tpo_ib_source)
```

**Regression test:** `tests/v9/api/test_day_type_seed_rejects_synthetic.py`.

#### B.3 — IB Bug #3: State machine adopts Sierra IB verbatim
**File:** `backend/v9/systems/day_type/state_machine.py:413-427`.

**Sketch:**
```python
def _stage_a3(self, bar: BarInput):
    if not bar.is_rth:
        return
    if bar.ib_high is not None and bar.ib_low is not None:
        # Per Source-of-Truth Rule 3: Sierra is the aggregator, not us.
        # Adopt verbatim — do NOT min/max across bars.
        self.ib_high = bar.ib_high
        self.ib_low = bar.ib_low
    if bar.session_min >= self.config.ib_period_min:
        self.stage = Stage.A4
```

**Regression test:** `tests/v9/systems/test_day_type_ib_no_accumulate.py`:
- Feed two A3 bars: (`ib_high=7574, ib_low=7525.5`) then (`ib_high=7574, ib_low=7560`).
- Assert `state.ib_low == 7560` (latest Sierra value), NOT 7525.5.

#### B.4 — IB Bug #5 (optional defense-in-depth): COALESCE on `_persist_ib_to_session`
**File:** `backend/v9/systems/tpo/tpo_system.py:444-451`.

**Sketch:** Already in IB diagnosis report § Fix #5.

**Note:** Ship in same batch as B.1-B.3 unless your Phase 1 audit ranked it differently.

**Post-Group-B manual UPDATE:**
```sql
UPDATE v9_day_type_history
SET ib_high = NULL, ib_low = NULL, ib_width = NULL, ib_width_class = NULL
WHERE date = '2026-05-28';
```
This clears the stuck synthetic IB. Engine will re-populate from Sierra on tomorrow's session. **Confirm exact SQL with Michael before running.** Document the UPDATE in `AMENDMENTS_LOG.md`.

**Group B exit criteria:**
- 4 new regression tests pass.
- Full backend test suite: targeted + unaffected (no new failures).
- Backend restart clean.
- 4 UAT axes pass for `/api/v9/tpo/current`, `/api/v9/key_levels`, `/api/v9/day_type/v9/current`.
- DB row updated, response shows `null` IB.

---

### Group C — Chicago TZ fix (only after Group A confirmed TZ)

**Goal:** Fix the +1h timestamp drift if Group A confirmed Sierra emits ET-encoded timestamps but bridge interprets as CT.

**Spec authority:** CC's 7-fixes prompt § Fix #2 (corrected scope) + OPEN_ITEMS #2.

**⚠️ Conditional:** If Group A concludes Sierra IS in CT (no drift), SKIP this group entirely. If Sierra is in ET, execute below.

**Fixes:**

#### C.1 — Bridge TZ correction (LARGER SCOPE than CC's original prompt)
**File:** `bridge/v9_streams/base_stream.py:73` (and any other reference to `America/Chicago`).

**Sketch:**
```python
# BEFORE (if TZ was incorrectly Chicago):
_EXCHANGE_TZ = ZoneInfo("America/Chicago")

# AFTER (if Sierra is ET, confirmed via Group A):
_EXCHANGE_TZ = ZoneInfo("America/New_York")
```

Rename `_chicago_to_utc` to `_eastern_to_utc` (or keep the name and document the inversion — your call, but PICK ONE consistently).

**Cross-impact: this affects EVERY timestamp the bridge writes.** Before deploying:
1. Document expected impact: every new bar will have correct UTC ts going forward. Historical bars (last N days) will REMAIN shifted +1h.
2. Decide with Michael: backfill historical bars, OR leave history as-is and tag a discontinuity in the data.

#### C.2 — `woodies_chart_routes.py:43` DST-aware
**File:** `backend/v9/api/v9/woodies_chart_routes.py:43`.

**Sketch:**
```python
# BEFORE:
ts_unix += 5 * 3600

# AFTER (after C.1 lands):
ts_unix = _eastern_to_utc(ts_unix)   # or equivalent helper
```

Add regression test that runs in winter (mock `datetime.now(tz=ZoneInfo("America/New_York"))` for a Dec date) — verifies no double-correction.

#### C.3 — `BarLevelDetector._parse_ts` (audit, may not need change)
**File:** `backend/v9/services/trade_manager/bar_level_detector.py:167-178`.

If Phase 1 audit found `_parse_ts` is naive (no TZ added) → no change needed; C.1 propagates correctly.
If `_parse_ts` applies its own TZ → audit and adjust.

This is also OPEN_ITEMS #18 / Trade Lifecycle Bug E. Resolves both.

**Regression test:** `tests/v9/services/trade_manager/test_bar_level_detector_tz.py`:
- Feed a bar with ET-encoded ts.
- Assert `fill_ts` stored in UTC matches expected.
- Assert no `09:30:00` defaults appear.

**Group C exit criteria:**
- New tests pass.
- Backend restart clean.
- 4 UAT axes for any endpoint that reads bar timestamps (e.g. `/api/v9/chart/bars_5min`, `/api/v9/woodies/chart`).
- `SELECT MAX(ts) FROM v9_bars_5min` matches wall clock UTC (delta < 10 min, not +1h).
- `SELECT COUNT(*) FROM v9_trades WHERE exit_ts < entry_ts` returns 0.

---

### Group D — S2 lazy-load current_day_type (no TZ dependency)

**Goal:** Make S2 self-heal when `current_day_type` is None after mid-session restart, **without violating no-silent-failures rule** (Pre-LIVE Mistake #6 of CC's original prompt).

**Spec authority:** CC's 7-fixes prompt § Fix #6 (with discipline correction) + OPEN_ITEMS #3.

**File:** `backend/v9/systems/five_min/five_min_system.py:660-700` (`process_bar`).

**Sketch — REVISED from CC's original prompt to comply with discipline:**
```python
# In process_bar(), early — after mode checks, before NT skip:
if self.current_day_type is None:
    try:
        from backend.v9.db.session import SessionLocal
        from backend.v9.systems.day_type.models import V9DayTypeState
        from sqlalchemy import func
        db = SessionLocal()
        try:
            row = db.query(V9DayTypeState).filter(
                func.date(V9DayTypeState.ts) == func.current_date()
            ).order_by(V9DayTypeState.id.desc()).first()
            if row and row.day_type:
                self.current_day_type = row.day_type
                logger.info("[FiveMin] Late hydrate current_day_type=%s", row.day_type)
            else:
                logger.warning("[FiveMin] Late hydrate found no V9DayTypeState row for today")
        finally:
            db.close()
    except Exception as e:
        # Per Pre-LIVE protocol: no silent failures
        logger.warning("[FiveMin] Late hydrate failed: %s", e, exc_info=True)
```

Note differences from CC's original:
- `except Exception as e: logger.warning(...)` (NOT `pass`).
- Logs both success and miss cases.

**Race condition check:** Does this conflict with `maybe_seed_ib_from_tpo` (which was modified in Group B.2)? Both read recent day_type state on restart. Verify no double-write to `self.current_day_type`.

**Regression test:** `tests/v9/systems/test_five_min_lazy_load.py`:
- Set `current_day_type = None`.
- Insert a V9DayTypeState row for today.
- Call `process_bar(...)`.
- Assert `current_day_type` populated AND `"Late hydrate"` log line emitted.

**Group D exit criteria:**
- New test passes.
- `/api/v9/five_min/current` returns non-null `current_day_type` after a restart simulation.

---

### Group E — Remaining trade lifecycle bugs (B + C + E from `DIAGNOSIS_TRADE_LIFECYCLE_BUGS_2026-05-28.md`)

**Goal:** Close the remaining trade lifecycle bugs after the W-10 disable resolved A + D.

#### E.1 — Bug B (Smart BE+1T verification)
**Status:** Classified as "working as designed" but needs live re-verification.

**Steps:**
1. Wait for a clean LONG fire post-restart.
2. Verify lifecycle: T1 hit → Smart BE+1T sets stop = entry + tick → stop hit (if hit) sets `exit_price`, `pnl_usd`.
3. Confirm `tests/v9/services/trade_manager/test_smart_be_after_t1.py` exists or write one.

#### E.2 — Bug C (`t1_hit_ts == stop_hit_ts` on wide-range bar)
**File:** `backend/v9/services/trade_manager/bar_level_detector.py:88-114`.

**Sketch:** When bar straddles both T1 and the post-BE stop, write T1 hit, defer Smart BE setup to NEXT bar. Distinct timestamps.

**Regression test:** synthetic wide-range bar covering both levels; assert `t1_hit_ts != stop_hit_ts`.

#### E.3 — Bug E (`stop_hit_ts = 09:30:00` default)
**Status:** Likely auto-fixed by Group C.3 (`_parse_ts` TZ correction). Verify with `SELECT COUNT(*) FROM v9_trades WHERE exit_ts = '... 09:30:00.000000'` = 0.

If still failing after Group C, dig into the source — `_parse_ts` may still have a fallback that defaults to a session-open time.

**Group E exit criteria:**
- 0 trades with `exit_ts < entry_ts` in `v9_trades`.
- 0 trades with `exit_ts = '09:30:00'` literal.
- Bug B verified on a live LONG fire OR explicitly punted to next SHADOW day.

---

### Group F — DLL fix (Sierra-side, BLOCKED on Sierra Subgraphs screenshot)

**Goal:** Make the DLL read the correct IB subgraphs and use a persistent lookup so locked values survive post-RTH.

**Spec authority:** `DIAGNOSIS_IB_GROUND_TRUTH_DIVERGENCE_2026-05-28.md` § *Fix #1* + OPEN_ITEMS #1.

**File:** `sc_study/MES_AI_DataExport.cpp:717-730`.

**Prerequisites:**
1. Michael's Sierra UI screenshot of "Initial Balance Study → Subgraphs" tab.
2. Map UI SG number → ACSIL idx (UI numbers start at 1, ACSIL at 0).
3. `docs/runbooks/SIERRA_DLL_OPS.md` ritual.

**Sketch:**
```cpp
// Add helper for persistent lookup (handles "Extend Lines Forward = No")
int _v9_last_nonzero(SCFloatArray& arr, int idx) {
    for (int i = idx; i >= 0; --i) {
        if (arr[i] != 0.0f) return i;
    }
    return -1;
}

// Replace the IB read block at MES_AI_DataExport.cpp:717-730:
sc.GetStudyArrayFromChartUsingID(chart_num, ib_study_id, H_IDX, ib_high_arr);
sc.GetStudyArrayFromChartUsingID(chart_num, ib_study_id, L_IDX, ib_low_arr);
int last_h = _v9_last_nonzero(ib_high_arr, idx);
int last_l = _v9_last_nonzero(ib_low_arr, idx);
if (last_h >= 0 && last_l >= 0) {
    ib_h = ib_high_arr[last_h];
    ib_l = ib_low_arr[last_l];
    ib_found = (ib_h > 0 && ib_l > 0 && ib_h > ib_l);
}
```

Where `H_IDX` and `L_IDX` come from Michael's Subgraphs screenshot.

**Build & deploy:** `./scripts/build_monolithic_cpp.sh --deploy` per `docs/runbooks/SIERRA_DLL_OPS.md`. Sierra UI Remote Build + study reload.

**Regression test:** `tests/v9/sierra/test_tpo_export_ib.py` — load a recorded post-lock `tpo.json` fixture and assert `ib.found=True, ib.high=<expected>, ib.low=<expected>`.

**Group F exit criteria:**
- `tpo.json.ib.found == True` post-RTH.
- `tpo.json.ib.high` / `ib.low` match Sierra UI 1:1.
- `/api/v9/tpo/current.ib_source == "sierra_live"` (not `"missing"`).

---

### Group G — Final report

After all groups (or those Michael approved) land:

**Write:** `docs/reports/INTEGRATED_FIX_BATCH_REPORT_2026-05-29.md`

Structure:
```
§0 · TL;DR (which groups landed, which deferred)
§1 · Per-group summary
    - Files changed (file:line)
    - Tests added/modified
    - UAT 4 axes results
§2 · Group A — TZ confirmation
§3 · Group B — IB Backend cleanup
§4 · Group C — Chicago TZ fix (or N/A)
§5 · Group D — S2 lazy-load
§6 · Group E — Trade lifecycle bugs B/C/E
§7 · Group F — DLL fix (or DEFERRED to next session)
§8 · OPEN_ITEMS update — which rows close, which remain open
§9 · AMENDMENTS_LOG entries added
§10 · STATUS_BOARD entries added
§11 · Self-assessment per the Source-of-Truth Discipline (which rule applied where)
```

Update:
- `docs/reports/AMENDMENTS_LOG.md` — one entry per group.
- `docs/plans/STATUS_BOARD.md` — one line per group.
- `docs/handoff/OPEN_ITEMS_PRE_LIVE_2026-05-28.md` — mark closed items.

---

## §3 · Per-fix UAT (4 axes, mandatory after each group)

For each group, run:

| Axis | Question | Pass condition |
|---|---|---|
| **1. Quality** | Is the specific bug condition gone? | `bad_count = 0` (or equivalent per group) |
| **2. Recency** | Does `endpoint.latest_ts == DB MAX(ts)`? | Yes |
| **3. Cardinality** | Does `len(rows) == requested_limit`? | Yes — no silent truncation (P27.5a regression class) |
| **4. Latency** | Response time under threshold? | Yes (consult endpoint's documented threshold) |

If ANY axis fails: STOP, do not proceed to next group, report to Michael.

---

## §4 · Hard constraints (Phase 2)

- **One group at a time.** Confirm exit criteria + UAT before next group.
- **Smallest correct change.** No "while I'm here" refactors.
- **No `except Exception: pass`** — anywhere. Every catch logs at `warning` or `error`.
- **No `logger.debug` on failure paths** — anything that hides bridge/backend errors must be `warning` or `error`.
- **No backend restart without Michael coordination.**
- **Do NOT touch `frontend/`** in this batch — Michael's UI work is locked.
- **Do NOT touch `~/Library/LaunchAgents/com.mems26.bridge.plist`.**
- **Do NOT change `V9_DISABLE_WATCHDOG`.**
- **Do NOT set `CLOUD_URL` to anything other than `http://localhost:8000`.**
- **Strategic stop** at any of:
  - Group A reveals TZ is something other than ET/CT → STOP.
  - Group B reveals a downstream consumer that doesn't gate on `ib_source` → STOP.
  - Group F reveals DLL Subgraphs are arranged differently than expected → STOP.
  - Any group's UAT 4 axes fail → STOP.
- **Pre-LIVE Mistakes Log applies:**
  - #1 (don't slice-bug)
  - #2 (verify before patching)
  - #4 (don't trust subagent at face value — paste raw output)
  - #6 (don't promote hypothesized fix before confirming)
  - #7 (no synthesis fallbacks)
  - #9 (verification quote, not assertion)
- **Source-of-Truth Discipline applies:**
  - Rule 1 (honest failure > synthetic value) — Group B is the main embodiment.
  - Rule 2 (verify before you trust) — Group A is the main embodiment.
  - Rule 3 (min/max amplifies upstream bugs) — Group B.3 must succeed.
  - Rule 4 (TZ ambiguity forbidden) — Group A + C.
  - Rule 5 (verification quote) — every group's UAT must paste raw command + output.

---

## §5 · Per-fix anti-regression list (do NOT undo)

Cross-reference `docs/reports/CURSOR_AGENT_SELF_CRITIQUE_AND_CHANGE_LOG_2026-05-28.md` § *Things CC Must NOT Re-Touch* before each group:

1. **W-10 YAML kill switch** (`time_stop_minutes: null` in `dispatcher_config.yaml`) — DO NOT REVERT.
2. **7 skipped tests** in `test_time_stop.py` + `test_woodies_rth_gate.py` — DO NOT un-skip.
3. **6 new W-10 anti-regression tests** (`test_w10_time_stop_disabled.py` + `test_layer4_time_stop_authority.py`) — DO NOT delete.
4. **`bar.setdefault("v", ...)`** at `five_min_system.py:698` — DO NOT delete.
5. **`current_bar` routing** in `bars.py` — DO NOT undo (S4 first-fire depended on it).
6. **`latest_valid_db_ts` + `fires_today` helpers** in `row_helpers.py` — DO NOT delete.
7. **Build Status `Live`/`Required`/`Freshness` columns + `FireSummary` chip** in frontend — DO NOT modify.
8. **`KeyLevelsStrip` / `KeyLevelsCard` UI order** — DO NOT reorder.

---

## §6 · Deliverables (Phase 2)

1. Per-group commits (or grouped if Michael prefers).
2. Per-group regression tests under `tests/v9/`.
3. Per-group UAT results (4 axes, raw output pasted).
4. `docs/reports/INTEGRATED_FIX_BATCH_REPORT_2026-05-29.md` — final report.
5. Updated `AMENDMENTS_LOG.md`, `STATUS_BOARD.md`, `OPEN_ITEMS_PRE_LIVE_2026-05-28.md`.
6. Self-assessment: which Source-of-Truth Rule was demonstrated by which group's work.

---

## §7 · Cross-references (read these alongside Phase 2)

- `docs/handoff/MEGA_PROMPT_CC_PHASE1_AUDIT_2026-05-28.md` — Phase 1 prompt.
- `docs/reports/CC_AUDIT_CONSULTATION_2026-05-28.md` — Phase 1 output (your audit).
- `docs/reports/CURSOR_AGENT_SELF_CRITIQUE_AND_CHANGE_LOG_2026-05-28.md` — anti-regression guide.
- `docs/reports/DIAGNOSIS_IB_GROUND_TRUTH_DIVERGENCE_2026-05-28.md` — IB Fix #1-#5 sketches.
- `docs/reports/DIAGNOSIS_TRADE_LIFECYCLE_BUGS_2026-05-28.md` — Bugs A-E.
- `docs/handoff/OPEN_ITEMS_PRE_LIVE_2026-05-28.md` — backlog.
- `docs/runbooks/SIERRA_DLL_OPS.md` — DLL rebuild ritual.
- `.cursor/rules/mems26-pre-live-protocol.mdc` — Mistakes #1-#11 + Source-of-Truth Rules 1-5.
- `CLAUDE.md` — workspace conventions + Source-of-Truth Rules (CC-facing).

---

## Acknowledgement template (paste at top of your Phase 2 start message)

```
Acknowledged MEGA_PROMPT_CC_PHASE2_INTEGRATED_FIX_2026-05-29.md.
Phase 1 audit consultation reviewed; Michael green-lit on <date/time>.
TZ confirmation status: <ET/CT, confirmed via chart settings screenshot>.
Sierra Subgraphs screenshot status: <received / pending — Group F deferred if pending>.
Backend restart slot: <coordinated for after Group <X>>.

Pre-LIVE protocol: re-confirmed Mistakes #1-#11 + Source-of-Truth Rules 1-5.
Anti-regression list reviewed: 8 items in §5 will not be touched.

Starting Group A — TZ investigation.
```

Go.
