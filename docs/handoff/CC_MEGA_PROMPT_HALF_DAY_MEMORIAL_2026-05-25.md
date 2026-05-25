# CC Mega-Prompt · Memorial Day Half-Close · 3-Stream Fix Session

**Date:** 2026-05-25 (Memorial Day · US futures half-close 13:00 ET / 20:00 IL)
**Owner:** Claude Code
**Trigger:** Start IMMEDIATELY after Michael confirms manual trade closure + bridge/backend stop
**Fix window:** ~5 hours · re-open 18:00 ET (01:00 IL Tuesday)
**Mode:** Read-only audit (Phase 1) → gated execution (Phase 2) → UAT (Phase 3)
**Supersedes:** `docs/handoff/CC_PROMPT_S2_AUDIT_POST_EOD_2026-05-25.md` (S2-only scope · now expanded to 3 streams)

---

## 0 · Strategic context

### Why this is happening NOW (not at midnight)

Memorial Day = US futures half-close 13:00 ET. After Michael manually closes the 4 active SHORTs (#3315, #3317, #3318, #3319) and stops bridge+backend, we have a **clean 5-hour window** before Asian session resumes 18:00 ET / 01:00 IL Tuesday.

### Critical findings collected 2026-05-25 17:30-18:55 IL

**Finding A · Sierra DLL TPO export is broken (P0 · trading-data integrity)**

`~/SierraChart_Data/v9_export/tpo.json` (latest write 18:50 IL):

```json
{
  "session": {
    "poc": -88945.00,           ← GARBAGE (negative impossible)
    "vah": 7560.35,
    "val": 0.00,                ← MISSING
    "va_ok": false,             ← VA INVALID
    "session_high": 7570.00,
    "session_low": 7548.25,
    "total_volume": 0.00        ← ZERO
  },
  "ib": {
    "found": false,             ← IB NOT DETECTED (despite Sierra UI showing IB clearly)
    "high": 0.00, "mid": 0.00, "low": 0.00
  },
  "previous_session": {
    "found": false              ← Friday TPO not detected
  }
}
```

Sierra Chart UI (truth) shows:
- Today POC 7559.75 · VAH 7565.00 · VAL 7556.75
- IB High 7570.00 · IB Mid 7562.00 · IB Low 7554.00
- Friday TPO POC 7501.50 · VAH 7517.50 · VAL 7485.50

DB (`v9_tpo_sessions` row `CASH_2026-05-25`) shows:
- POC 7558.25 · VAH 7569.50 · VAL 7558.25 (= POC ?!)
- IB high 7558.75 · IB low 7557.75 (IB width 1.0pt vs Sierra's 16.0pt)
- Friday DB POC 7505.50 · VAL 7505.00 (vs Sierra Friday POC 7501.50 · VAL 7485.50)

**Finding B · Backend synthesizes TPO when DLL is invalid (CLAUDE.md violation)**

When DLL emits `poc=-88945, val=0, va_ok=false, ib.found=false`, the backend writes **non-garbage but wrong** values to `v9_tpo_sessions`. This means there is a synthesis path that:
- Rejects the impossible (negative POC, zero VAL)
- Replaces them with computed values (likely rolling mean / last-good fallback)
- Writes to DB as if authoritative
- Violates CLAUDE.md "Forbidden: synthesizing OHLC/TPO when DLL omits them"

**Finding C · S2 wiring drift (already documented in STATUS_BOARD 17:50 amendment)**

- B1: `_on_day_type_update` (`backend/v9/systems/five_min/five_min_system.py:252-264`) updates `current_day_type` but NOT `opening_type` from event payload. UI shows `pending` forever.
- B2: mode transition `FIRST_HOUR_TACTICAL → DAY_TYPE_MODE` (lines 244-246) gated on processed bar's `bar_time`. bar_router backlog grew to 13,199 (from 12,263 → +936 in 20 min). Processed bars stuck before 10:30 ET. 3/5 detectors disabled (H&S Top/Inverse · DB/DT · Bull/Bear Flag).

**Finding D · S1 DayType still DEVELOPING at 11:45 ET**

`v9_day_type_state` last row at 15:45 UTC = 11:45 ET = stage B2 · DEVELOPING · confidence 0.38 · classification empty. By spec S1 should have locked DayType by 10:30 ET (IB close).

**Finding D ownership · UNDECIDED · Phase 1 MUST classify:**

| Possibility | Implication |
|---|---|
| **D = sub-symptom of Stream A** | DLL emits `ib.found=false` → backend cannot detect IB close → S1 cannot transition stage B2 → C1 (lock) · fix Stream A is sufficient. No new stream. |
| **D = sub-symptom of Stream B** | DLL emits valid data but backend ingest fails to propagate IB to S1 (synthesizes around it but S1 reads raw) · Stream B fix needed for D too. |
| **D = independent (new Stream D)** | S1 state machine itself has a bug (lines 535 / Stream 1.5 area · Q1 fallback) · independent of DLL/backend ingest. Needs its own audit + fix. |
| **D = race condition** | S1 hydration completed AFTER today's IB lock window · hydration replays history but live IB event was missed. Requires hydration ordering audit. |

Phase 1 deliverable section "Finding D classification" MUST resolve which of the 4 applies (or D = combination).

**Phase 1 MUST verify D's classification with Layer 3 evidence BEFORE assuming relationship to A.**

Layer 3 commands to run specifically for D:

```bash
rg -n 'DayType|day_type|DEVELOPING|_rescore|stage B' /tmp/backend.err.log | head -50
sqlite3 data/mems26_local.db 'SELECT ts, stage, confidence, ib_high, ib_low FROM v9_day_type_state WHERE ts >= date("now") ORDER BY ts'
```

- If logs show S1 received valid IB event but failed to transition → D is independent (Stream D needed).
- If logs show S1 never received IB event → D is downstream of A (no Stream D).

---

## 0.5 · Cross-impact map (per Michael 19:00 IL feedback)

The TPO/DLL chain is upstream of more than just S2. Phase 1 audit MUST surface these dependencies in the deliverable's "Cross-Impact" section:

| Dependent surface | Consumes from TPO/DLL | Today's blast radius | Future blast (if not fixed) |
|---|---|---|---|
| **S4 Woodies (live)** | POC for HFE/ZLR/HTLB/VEGAS confidence math · VA edges for ZLR | 142 trades today fired against wrong POC=7558.25 (real 7559.75 · 1.5pt drift) · 4 SHORTs entered above real POC instead of below | Tomorrow's fires use same bad levels until DLL/B fixed |
| **Pipeline 2 G0 audit (NEXT)** | A4 + B4 touch-points reference POC/VA per DTV1 + P-W7 lock | None tonight (G0 not started) | **G0 audit will produce wrong KEEP/ADAPT/REPLACE/DEFER decisions** if it classifies Woodies code against unreliable TPO baseline · entire Pipeline 2 build queue at risk |
| **S2 D-091 Pkg 5b (Double Bottom/Top)** | Adam&Adam / Eve&Eve geometry uses POC/VAL/VAH for context filters | None today (S2 blocked by B2) | Pkg 5b SHADOW soak invalid if TPO untrusted |
| **S2 D-091 Pkg 5c (Bull/Bear Flag) Path C** | Day-type conditional T2 reads VAH/VAL/POC for NeuE/Norm targets (D-091.Q5.B) | None today (mode-blocked) | Path C T2 wrong on every Flag fire post-fix until A clean |
| **S1 NeuE/NeuC classification** | Reads prev_day VAH/VAL (D-091.Q1 fallback) | Today's `opening_type` may be misclassified | Every neutral day misclassified until DLL `previous_session.found=true` reliably |
| **S3 Footprint** | Aligns to TPO POC for setup filters | TBD (footprint stream stuck `pushes=0`) | Independent issue (see Phase 1 Layer 3 logs) |
| **UI cockpit POC/VA strip** | Reads `v9_tpo_sessions` | Trader sees wrong levels in UI | Continues until B fixed |

**Sequencing implication:** Stream A blocks future Pipeline 2 G0. Stream A blocks Pkg 5b/5c SHADOW. Stream A is on the critical path for **all** post-Phase-A Pre-LIVE work · not just tonight's bug. Phase 1 deliverable must make this explicit so Michael decides whether to slip Pipeline 2 G0 start until A is GREEN.

---

## 1 · Mission · 3 streams · 3 phases

### Streams

| ID | Stream | Priority | Files | Risk |
|---|---|---|---|---|
| **A** | Sierra DLL TPO export | P0 | `sc_study/MES_AI_DataExport.cpp` (+ headers) | HIGH (requires Sierra Remote Build) |
| **B** | Backend TPO synthesis hardening | P0 | TBD (find via Phase 1 audit) likely under `backend/v9/services/tpo/` or `backend/v9/api/v9/tpo/` | MED (pure Python) |
| **C** | S2 wiring (B1 + B2) | P1 | `backend/v9/systems/five_min/five_min_system.py` | LOW (3-line + investigation) |

### Phases

| Phase | Scope | Duration target | Hard deadline | Output |
|---|---|---|---|---|
| **1 · Audit** | 5-layer audit per stream (read-only) | ~90 min target · 120 min ceiling | start NLT 19:30 IL · end NLT 21:30 IL | `docs/reports/MEMORIAL_DAY_AUDIT_2026-05-25.md` |
| **2 · Execute** | Per-stream fix · gated by Michael approval after Phase 1 | ~2.5h target · expandable | end NLT 00:00 IL (1h pre-reopen) | Per-stream commit + regression tests |
| **3 · UAT** | Restart services · verify all 4 axes (Quality/Recency/Cardinality/Latency) | **as-needed before 18:00 ET / 01:00 IL reopen** · no fixed cap | **MUST complete before 18:00 ET reopen** | `docs/reports/MEMORIAL_DAY_UAT_2026-05-25.md` |

**Time budget escalation triggers (per Michael 19:00 IL feedback):**
- If Phase 1 exceeds 120min ceiling → strategic stop · checkpoint to Michael · decide which streams to defer.
- If Phase 2 fix #N exceeds 90min wall-clock → checkpoint that fix · skip to next stream · revisit at end.
- **If reopen <90min away and Phase 3 not started → ABORT execution · revert ALL fixes via `git revert HEAD~N..HEAD` · restart services on pre-fix code · report and wait.** Better no fix than half-fix in production.

**Real budget reality check:** if Stream A diagnosis reveals session-boundary refactor (HA-3) or deep study-handle plumbing — that ALONE eats Phase 2. In that case: Stream A enters "diagnosis-only" tonight · ship Stream B (warning-only mode) + Stream C (B1 only) · defer Stream A patch + B2 fix to next-day window.

---

## 2 · Phase 1 · 5-Layer audit (READ-ONLY)

### Layer 1 · Spec-vs-Code

**Read all of these BEFORE proposing any finding:**

| Doc | Path | Use for |
|---|---|---|
| Sierra DLL ops | `docs/runbooks/SIERRA_DLL_OPS.md` | DLL deploy mechanics · what NOT to touch |
| P30 inbox §7a | `docs/handoff/P30_AGENT_INBOX_PRE_LIVE.md` (search §7a) | DLL+time-axis anti-regression baseline |
| P30.8 report | `docs/reports/PROMPT30_8_5MIN_JSON_EXPORT.md` | 5min JSON export precedent |
| CLAUDE.md | `CLAUDE.md` | Source-of-truth rules · forbidden synthesis · polling floors |
| D-091 S2 LIVE Scope | `docs/decisions/D-091_S2_LIVE_SCOPE.md` (416 LOC) | S2 spec for Stream C |
| EXIT_V6 | `docs/spec_authority/S2_EXIT_DEFINITION_V6.md` | Time stop windows |
| Auth Table V1 | `docs/spec_authority/S2_AUTH_TABLE_V1.md` | OFA entry signals |
| Registry §S2 | `docs/reports/MEMS26_SYSTEMS_DECISIONS_REGISTRY_2026-05-23.md` §S2 | Locks history |
| STATUS_BOARD amendment 17:50 | `docs/plans/STATUS_BOARD.md` (line ~219) | B1 + B2 documented findings |
| ENVIRONMENT | `docs/ENVIRONMENT.md` | Paths · LaunchAgent · build commands |

Then walk the code surface:

- **Stream A:** `sc_study/MES_AI_DataExport.cpp` + headers + any `*.cpp` referenced from there. Map: which function writes `tpo.json` · what study references are used · how IB/POC/VAL/VAH are extracted from Sierra's TPO study.
- **Stream B:** Find the ingest path. Search keys: `v9_tpo_sessions`, `tpo.json`, `poc_price`, `vah_price`, `va_ok`, `ib.found`. Likely candidates: `backend/v9/services/tpo/`, `backend/v9/bridges/`, `bridge/v9_streams/tpo*.py`.
- **Stream C:** `backend/v9/systems/five_min/` (40 files · already classified in the superseded prompt · keep that classification work).

### Layer 2 · Live database evidence

```sql
-- Stream A: TPO DB rows for today
SELECT * FROM v9_tpo_sessions WHERE trading_date='2026-05-25';
SELECT * FROM v9_tpo_sessions WHERE trading_date='2026-05-22';
SELECT * FROM v9_tpo_history WHERE ts >= datetime('now','-2 days') ORDER BY ts DESC LIMIT 30;

-- Verify the 142-trade impact claim · Stream A blast radius
SELECT COUNT(*) AS fires_today,
       SUM(CASE WHEN direction='SHORT' AND entry_price > 7559.75 THEN 1 ELSE 0 END) AS shorts_above_real_poc,
       SUM(CASE WHEN direction='LONG' AND entry_price < 7559.75 THEN 1 ELSE 0 END) AS longs_below_real_poc
  FROM v9_trades
 WHERE date(entry_ts) = date('now') AND firing_system = 4;  -- S4 Woodies

-- Stream B: when did TPO synthesis last update? (catch the ingest cadence)
SELECT id, session_id, opened_ts, closed_ts FROM v9_tpo_sessions ORDER BY id DESC LIMIT 10;
SELECT created_at, COUNT(*) AS rows FROM v9_tpo_history WHERE ts >= datetime('now','-1 day') GROUP BY date(created_at);

-- Stream C: S2 fires 7d / 30d
SELECT date(entry_ts) AS day, COUNT(*) AS fires FROM v9_trades
  WHERE firing_system=2 AND entry_ts >= date('now','-30 days') GROUP BY day ORDER BY day DESC;
SELECT * FROM v9_five_min_setups ORDER BY id DESC LIMIT 20;  -- check schema first
SELECT * FROM v9_five_min_state ORDER BY id DESC LIMIT 10;

-- DayType (Finding D)
SELECT * FROM v9_day_type_state WHERE ts >= datetime('now','-1 day') ORDER BY id DESC LIMIT 30;
SELECT * FROM v9_day_type_history WHERE date='2026-05-25';
```

### Layer 3 · Runtime logs

```bash
LOGS="/tmp/backend.err.log /tmp/backend.out.log /tmp/bridge.err.log /tmp/bridge.out.log"
# Stream A
rg -n 'tpo\.json|poc=-?|va_ok|ib\.found|previous_session|TPOExport' $LOGS | tail -200
# Stream B
rg -n 'tpo|TPO|synthesiz|fallback|invalid_poc|rolling|MISSING' backend/v9 --type py | head -100
rg -n 'TPO|poc|vah|val' $LOGS | tail -200
# Stream C
rg -n 'five_min|FiveMin|S2 |_detect_|NT skip|mode=|DAY_TYPE_MODE|FIRST_HOUR_TACTICAL|opening_type|_on_day_type_update|_check_setup|setup_emitter' $LOGS | tail -200
# Finding D
rg -n 'DayType|day_type|DEVELOPING|stage B|_stage_a|_rescore' $LOGS | tail -200
# bar_router (Finding C B2 root cause)
rg -n 'bar_router|backlog|footprint|pushes=0|dispatch' $LOGS | tail -200
```

### Layer 4 · Replay/Backtest

**Stream A · counterfactual:** if DLL had emitted correct POC/VAH/VAL/IB for today, what would each S4 Woodies trade look like? Recompute Reactive/Initiative entries against Sierra-truth POC=7559.75/VAH=7565/VAL=7556.75/IB=7554-7570. Compare to 142 actual trades. Report: `trades_correctly_setup vs trades_misfired_due_to_bad_levels`.

**Stream C · S2 counterfactual:** run today's `v9_bars_5min` (RTH only) through `FiveMinSystem` with three scenarios:
- A current (FIRST_HOUR_TACTICAL stuck · opening_type=None)
- B fix B1 only (opening_type wired · mode still stuck)
- C fix B1+B2 (both unstuck)

Output: counterfactual fire count for Reactive×2 · Initiative×2 · Flag×2 · H&S×2 · DB/DT×2.

### Layer 5 · Cross-system snapshot

| Field | Producer | Consumer | Expected | Today's actual |
|---|---|---|---|---|
| DLL `tpo.json.session.poc` | Sierra DLL | ingest | matches Sierra UI POC | **-88945** ❌ |
| DB `v9_tpo_sessions.poc_price` | ingest | S2/S4/UI | matches DLL or rejects | **7558.25** (synthesized) ❌ |
| API `/api/v9/tpo` | DB | UI | matches DB | TBD |
| UI cockpit POC | API | trader | matches Sierra UI | **drift confirmed** |
| DLL `tpo.json.ib.found` | DLL | ingest | true after 10:30 ET | **false** ❌ |
| `v9_day_type_history.ib_width` | ingest | S1 classifier | matches DLL IB | DB 11.5 · DLL 0 · Sierra 16.0 — **3-way drift** |
| `current_day_type` | S1 | S2 | locked by 10:30 ET | **DEVELOPING at 11:45 ET** ❌ |

Each drift = a finding. Trace each to root cause (DLL · ingest · S1 · S2 · UI · snapshot service).

---

## 3 · Stream A · Sierra DLL diagnostic (Phase 1 read-only details)

### Hypothesis tree (verify each in Phase 1)

| H | Hypothesis | How to verify (read-only) |
|---|---|---|
| **HA-1** | Wrong study reference IDs in DLL inputs | Read `MES_AI_DataExport.cpp` · find `sc.GetStudyArrayUsingID()` calls for TPO study · compare to actual study slot in Sierra Chart |
| **HA-2** | Chart not reloaded after Sierra restart · study handles invalid | `ls -la ~/SierraChart_Data/v9_export/woodies_diag.json` · check timestamp (last 18:50 vs older?) · diff today's tpo.json vs yesterday's tpo.json structure |
| **HA-3** | Memorial Day partial session triggers session-boundary bug | Check `Session->IsCurrentSessionEnd()` / `sc.RTHSettings` usage in DLL · look for session-day-type guards |
| **HA-4** | Recent DLL deploy regression (check git log under `sc_study/`) | `cd sc_study && git log --oneline -30` · find last deploy · diff vs deployed timestamp `~/SierraChart/ACS_Source/MES_AI_DataExport.cpp` |
| **HA-5** | DLL is fine · Sierra Chart's TPO study itself is misconfigured (wrong VA percentage · wrong time bracket · etc.) | Check Sierra Chart `Study Settings` for the TPO study Input slot (Input 4 = `V9 Export Directory` per CLAUDE.md) · request Michael to screenshot study settings |

**Output of Stream A Phase 1:** `docs/reports/STREAM_A_DLL_DIAGNOSIS_2026-05-25.md` with confirmed/refuted hypotheses + root-cause statement + proposed patch scope.

**DO NOT in Phase 1:**
- Modify `sc_study/*.cpp`
- Run `./scripts/build_monolithic_cpp.sh --deploy`
- Touch `~/SierraChart/ACS_Source/`
- Modify Sierra Chart study settings (requires Michael in Sierra UI)

---

## 4 · Stream B · Backend TPO synthesis hardening (Phase 1 read-only details)

### What we know

Backend transforms broken DLL (`poc=-88945, val=0, va_ok=false`) into DB rows with non-garbage but **wrong** values. Find where this synthesis happens.

### Search vectors

```bash
# Find ingest entry point for tpo.json
rg -n 'tpo\.json|tpo_data|TpoExport|TPOExport' backend/ bridge/ --type py
rg -n 'va_ok|previous_session|prior_day' backend/ bridge/ --type py
# Find where v9_tpo_sessions is written
rg -n 'v9_tpo_sessions|V9TpoSession|v9_tpo_history' backend/ --type py
# Find synthesis / fallback / rolling
rg -n 'fallback|synthesiz|rolling|last_good|previous_poc|interpolat' backend/v9 --type py
```

### Expected fix scope (Phase 2)

Reject-and-warn pattern:

```python
# Pseudo-code · authoritative implementation in Phase 2 tests
def ingest_tpo_export(tpo: dict) -> None:
    session = tpo.get("session", {})
    ib = tpo.get("ib", {})
    if (
        session.get("poc", 0) <= 0
        or session.get("val", 0) <= 0
        or session.get("vah", 0) <= 0
        or not session.get("va_ok", False)
    ):
        logger.warning(
            "[TPO ingest] rejecting invalid DLL export · poc=%s val=%s vah=%s va_ok=%s · DB not updated",
            session.get("poc"), session.get("val"), session.get("vah"), session.get("va_ok"),
        )
        metrics_counter("tpo_dll_reject_total").inc()
        return  # do NOT write to DB · do NOT synthesize
    if not ib.get("found", False):
        # IB not yet locked · acceptable pre-10:30 ET · suspicious after
        if is_post_ib_window():
            logger.warning("[TPO ingest] IB not found post-10:30 ET · DLL state suspicious")
    # write to DB only when DLL output is valid
    write_tpo_session(session, ib)
```

**Tests required (Phase 2):**
- Reject when `poc < 0` (today's case)
- Reject when `val == 0`
- Reject when `va_ok == false`
- Reject when `vah == 0`
- Accept when all valid
- Warning-only when `ib.found == false` pre-10:30 ET
- Warning + reject when `ib.found == false` post-10:30 ET

**Caveat for Phase 2 sequencing:** if Stream B ships before Stream A is fixed, the DB will stop receiving TPO updates entirely. All S2/S4 logic that depends on POC/VA/IB will block. To avoid trading halt:
- Option 1: ship Stream B in **warning-only mode** first (log + metric, no DB block) · then upgrade to reject mode after Stream A is fixed.
- Option 2: ship Stream A first · then ship Stream B reject mode.
- **Recommendation:** Option 2 if Stream A diagnosis is confident · Option 1 if Stream A needs more time.

---

## 5 · Stream C · S2 wiring (Phase 1 read-only details)

### B1 audit (cosmetic · LOW risk fix)

Read `backend/v9/systems/five_min/five_min_system.py:252-264` (`_on_day_type_update`). Verify:

- The event payload has an `opening_type` field
- The handler does NOT extract it
- `self.opening_type` is read elsewhere in the file (find consumers)
- Determine if any code path uses `self.opening_type` for trading logic (search for `self.opening_type` outside `_on_day_type_update`)

Fix scope (Phase 2): add 1-2 lines to extract `opening_type` from event payload. Add 2 unit tests:
1. `_on_day_type_update` updates both `current_day_type` and `opening_type`
2. Snapshot includes correct `opening_type` after event received

### B2 audit (HIGH-impact · root-cause investigation)

Read `backend/v9/systems/five_min/five_min_system.py:244-246`. Verify:

- mode transition is gated on `event.ts.time() >= 10:30 ET`
- the `event.ts` comes from currently-processed bar (not real wall-clock)
- with bar_router backlog 13K+, processed bars lag the wall clock

Investigate bar_router backlog root cause:

```bash
rg -n 'class BarRouter|bar_router|dispatch|backlog|subscribers' backend/v9 --type py
# Check footprint stream that has pushes=0 for 5 days
rg -n 'footprint.*push|pushes=0|footprint_stream' bridge/ backend/ --type py
```

Hypothesis: footprint subscriber blocks the dispatch loop · slow ingest · all other subscribers (S2, S4 woodies, tick_reversal) get backed up.

Fix scope (Phase 2):
- B1: 3-line wiring
- B2: depends on root cause · could be:
  - 1-line: switch mode transition gate to wall-clock instead of bar-time
  - small: skip footprint subscriber on backlog > N
  - large: async-queue refactor for bar_router

**B2 fix in Phase 2 MUST be the smallest correct change.** No "while I'm here" refactor.

### Stream C scope NOT covered tonight

D-091 has 10 patterns · today S2 fired 3 in 7 days. Even after B1+B2 fix, 6/10 patterns (chart patterns) need build verification. That's Pipeline 1 Phase A 15/15 build queue (already complete per STATUS_BOARD) · UAT only.

Do NOT add new patterns tonight. Only restore the wiring.

---

## 6 · Phase 1 deliverable · `docs/reports/MEMORIAL_DAY_AUDIT_2026-05-25.md`

```markdown
# Memorial Day Audit · 2026-05-25 · 3-Stream Read-Only Findings

## Executive summary
- **Stream A status:** RED/YELLOW/GREEN · top finding · proposed fix scope
- **Stream B status:** ...
- **Stream C status:** ...
- **Recommended Phase 2 sequencing:** A → B → C (or as analysis dictates)

## Stream A · Sierra DLL
- Hypothesis verification table (HA-1 to HA-5)
- Root cause statement
- Proposed patch scope (file:line · LOC estimate · risk class)
- DOES IT REQUIRE Sierra Remote Build? YES/NO

## Stream B · Backend TPO synthesis
- Found ingest path? YES/NO · file:line
- Synthesis logic identified? YES/NO · file:line
- Proposed reject-and-warn patch
- Tests planned

## Stream C · S2 wiring
- B1 confirmed · file:line · patch scope
- B2 root cause? confirmed/refuted · investigation summary
- Tests planned

## Cross-stream drifts (Layer 5 findings)
- TPO drift (DLL vs DB vs UI vs Sierra)
- IB drift (DLL false vs DB 1pt vs Sierra 16pt)
- DayType drift (UNKNOWN vs PENDING vs DEVELOPING)
- bar_router backlog (13K+ growing)

## Finding D classification (MANDATORY · per §0)
- Verdict: D = sub-symptom of Stream A / Stream B / independent Stream D / race condition / combination
- Evidence per Layer 1 / 3 / 5
- If independent: ownership statement · proposed audit scope
- If sub-symptom: confirm Stream A or B fix WILL resolve D · acceptance criterion

## Cross-impact map (MANDATORY · per §0.5)
- For each consumer of TPO/DLL (S4 Woodies · Pipeline 2 G0 · Pkg 5b/5c · S1 NeuE/NeuC · S3 Footprint · UI):
  - Today's blast: trade/UAT count affected
  - Future blast: which Pre-LIVE packages slip if Stream A defers
- Recommendation: should Pipeline 2 G0 start slip until Stream A GREEN? · Should Pkg 5b/5c SHADOW gate require Stream A pass?

## Component classification (40 files under five_min/ + ~10 files under bridges/tpo/ + sc_study/)
| File | Stream | Classification | Notes |
|---|---|---|---|
| ... | ... | KEEP / ADAPT / REPLACE / DEFER / MISSING | ... |

## Recommended Phase 2 fix sequence
| # | Stream | Fix | Estimated CC time | Depends on | Risk | Notes |
|---|---|---|---|---|---|---|
| 1 | C | B1 opening_type wiring | 15min | none | LOW | |
| 2 | B | TPO reject-and-warn (warning-only mode initially) | 30min | none | MED | **Conditional:** B warning-only · ONLY if Phase 1 Stream A confidence <80% · else skip directly to fix #4 after A (per §4 Option 2 recommendation). |
| 3 | A | DLL root-cause patch | ~1h CC + Michael Sierra deploy | Sierra running | HIGH | |
| 4 | B | upgrade B to reject mode | 10min | A passing UAT | MED | If fix #2 was skipped: this becomes the full B-reject ship. |
| 5 | C | B2 root cause fix | TBD by Phase 1 finding | none | MED-HIGH | |

## Open questions for Michael
1. ...
2. ...
3. ...

## Stop conditions hit during audit
[record any layer that hard-stopped]

## Sign-off
CC · 2026-05-25 ~XX:XX IL · audit took XX minutes
```

---

## 7 · Phase 2 · Execution (gated)

**Rule:** CC does NOT touch code in Phase 2 until:
1. Phase 1 audit report exists at `docs/reports/MEMORIAL_DAY_AUDIT_2026-05-25.md`
2. Michael reads and approves the per-stream fix scope (chat reply: "approved · execute fix #N")
3. CC executes ONE fix · adds tests · runs `pytest backend/v9/systems/<area>/tests/ -q`
4. CC commits with descriptive message · returns control to Michael
5. Repeat for next fix only after Michael approval

**Pre-LIVE protocol mandatory per fix:**
- [ ] Diagnosed across ≥3 layers (per §2)
- [ ] Read current code (no edits from memory)
- [ ] Smallest correct fix
- [ ] Regression test added under appropriate `tests/` directory
- [ ] Four UAT axes considered (Quality / Recency / Cardinality / Latency)
- [ ] No silent failures (use `logger.warning` rate-limited, not `logger.debug`)

---

## 8 · Phase 3 · UAT (before 18:00 ET / 01:00 IL reopen)

### Service restart sequence

```bash
# 1. Confirm bridge + backend stopped
launchctl list | grep mems26 || echo "LaunchAgent not loaded"
lsof -i :8000 -i :3000 || echo "no listeners · safe to start"

# 2. Sierra Chart (if Stream A deployed)
# Michael action: open Sierra · reload study · verify v9_export/tpo.json clean

# 2.5. Wait for Sierra to emit fresh tpo.json (5s polling · 30s timeout)
while [ $(($(date +%s) - $(stat -f %m ~/SierraChart_Data/v9_export/tpo.json))) -gt 10 ]; do
    sleep 1
done

# 3. Cat the export file
cat ~/SierraChart_Data/v9_export/tpo.json
# Expect: poc>0, val>0, vah>0, va_ok=true, ib.found=true (if post-10:30 ET on next session)

# 4. Start backend (LaunchAgent)
launchctl load ~/Library/LaunchAgents/com.mems26.backend.plist
sleep 5
curl -s http://localhost:8000/api/v9/status | python3 -m json.tool | head -30

# 5. Start bridge (LaunchAgent)
launchctl load ~/Library/LaunchAgents/com.mems26.bridge.plist
sleep 10
tail -30 /tmp/bridge.err.log
# Expect: NO "API push FAILED to https://*" (must be localhost only per CLAUDE.md)
```

### Four UAT axes per stream

**Stream A (DLL):**
- Quality: `tpo.json.session.poc > 0` · `val > 0` · `vah > 0` · `va_ok = true`
- Recency: `mtime(tpo.json)` within 5s of wall clock
- Cardinality: `previous_session.found = true` after at least one prior session in the export window
- Latency: writeback cycle <5s (existing perf budget per P30)

**Stream B (backend synthesis):**
- Quality: `v9_tpo_sessions.poc_price` matches DLL output exactly (no synthesis)
- Recency: `v9_tpo_sessions.opened_ts` within 60s of DLL `export_ts`
- Cardinality: 1 row per session_id (CASH + GLOBEX) per day
- Latency: ingest <100ms p99

**Stream C (S2 wiring):**
- Quality: `current_day_type` and `opening_type` both reflect S1's classification
- Recency: snapshot fields update within 1 bar of S1 event
- Cardinality: mode transitions exactly once per session (FIRST_HOUR_TACTICAL → DAY_TYPE_MODE at 10:30 ET)
- Latency: bar_router backlog <100 (not 13K+)

### Regression test suite

**Per-stream targeted suites (run after each Phase 2 commit):**

```bash
cd /Users/michael/Downloads/mems26_web_git

# Stream C (S2 wiring)
pytest backend/v9/systems/five_min/tests/ -q
pytest tests/v9/systems/test_five_min/test_auth_table_v1.py -q  # S2 OFA Auth Table V1 (existing · Pkg 1 surface)
# NOTE: Pkg 8 (Quality V2 Auth Table) not yet implemented · MEGA prompt pending
pytest tests/v9/systems/test_day_type/ -q                # Stream 1 / 1.5 day type tests

# Stream B (backend TPO synthesis)
pytest backend/v9/services/tpo/tests/ -q                 # if exists · Phase 1 confirms
pytest tests/v9/api/test_chart_bars5min_integrity.py -q  # P27.5a regression guard
# Stream A (DLL · no Python tests · UAT only)

# Pkg 6 TradeManager rewrite (committed today · da4804b) — MUST not regress
pytest backend/v9/services/trade_manager/tests/ -q
pytest tests/v9/services/test_trade_manager/ -q          # if duplicate location exists

# Pkg 3a Day Type targets (committed cf6383e)
pytest tests/v9/systems/test_day_type_targets/ -q
pytest backend/v9/systems/five_min/tests/test_day_type_targets.py -q  # if symlinked

# Pkg 3b BE+1T trail
pytest tests/v9/services/test_trade_manager/test_be_plus_one_tick.py -q

# Woodies S4 (Pipeline 2 surface · must not regress · 142 trades today depend on this)
pytest backend/v9/systems/woodies/tests/ -q
pytest tests/v9/systems/test_woodies/ -q

# S1 Day Type · S3 Footprint · S5 TPO · S6 (cross-system regression)
pytest tests/v9/systems/test_day_type/ -q
pytest tests/v9/systems/test_footprint/ -q
pytest tests/v9/systems/test_tpo/ -q

# Full backend suite (budget-permitting · run LAST)
pytest backend/v9/ -q --tb=short -x
pytest tests/v9/ -q --tb=short -x
```

**Discovery first:** before running, CC does `find tests/v9/services/test_trade_manager backend/v9/services/trade_manager/tests -type d 2>/dev/null` to confirm which paths exist · skip non-existent paths · do NOT fail Phase 3 over missing test directories (note in UAT report instead).

**Acceptance:** 0 test failures · 0 new warnings · all 12 axes (4 × 3 streams) GREEN · **0 regressions in Pkg 3a/3b/6/8 tests** (these shipped this week and are the primary risk surface).

### Test-failure triage rules

- A test fails that was passing in `git log -1 --before='2026-05-25 17:00'`'s state → BLOCKER · revert this Phase 2 fix.
- A test fails that was already failing per `backend/v9/systems/five_min/tests/test_time_stop_mapper.py` git diff (pre-existing modification) → note in UAT report · do not block.
- A new test added in this session fails on first run → expected during TDD · iterate until green.

---

## 9 · Hard constraints (apply to all phases)

- **LIVE-only bridge:** `CLOUD_URL=http://localhost:8000` · `bridge/v9_streams/base_stream.py` refuses non-local. Do not change.
- **LaunchAgent:** do NOT change `~/Library/LaunchAgents/com.mems26.bridge.plist` back to `KeepAlive=true`.
- **No bytecode commits:** add `*.pyc` and `__pycache__/` to ignore if they appear.
- **No frontend polling change:** floors per CLAUDE.md table are NOT to be touched.
- **Smallest correct fix:** no "while I'm here" refactors. Each commit addresses ONE bug.
- **Diagnose first:** verify hypothesis with data before touching code.
- **Strategic stop:** at any contradiction with D-091 / EXIT_V6 / Auth Table V1 / CLAUDE.md.
- **2× failure rule:** if same diagnostic command fails 2× · change tactic · do not thrash.
- **Budget guidance (per Michael 19:05 IL feedback):** Phase 1 target 90min · ceiling 120min hard (per §1 escalation). Phase 2 target 150min · **expandable · checkpoint to Michael if exceeded** · subject to reopen deadline. Phase 3 as-needed before 18:00 ET / 01:00 IL reopen · no fixed cap. See §1 escalation triggers for ABORT rules.

---

## 10 · Reporting workflow

Per CLAUDE.md §Reporting Workflow:

- After Phase 1: `docs/reports/MEMORIAL_DAY_AUDIT_2026-05-25.md`
- After each Phase 2 fix: chat summary + `git log` confirmation · ask Michael for next-fix approval
- After Phase 3: `docs/reports/MEMORIAL_DAY_UAT_2026-05-25.md`
- Final: update `docs/plans/STATUS_BOARD.md` amendment log with summary

Do not advance to next phase until current phase's report exists.

---

## 11 · Sign-off checklist before first commit

- [ ] Phase 1 audit complete · report committed
- [ ] Michael approval received in chat for fix #N
- [ ] Pre-LIVE protocol checklist passed for this fix
- [ ] Regression tests added
- [ ] `pytest` passes locally
- [ ] No silent-failure paths introduced
- [ ] Commit message describes WHY (not just WHAT)

---

**End of mega-prompt · Cursor · 2026-05-25 18:55 IL.**

---

## Appendix · Quick-start command for CC

```
Read this entire file end-to-end. Confirm understanding by listing: (1) the 3 streams, (2) the 3 phases, (3) the 5 layers, (4) the 4 UAT axes. Then begin Phase 1 audit. Output Phase 1 deliverable to docs/reports/MEMORIAL_DAY_AUDIT_2026-05-25.md. Wait for Michael's per-stream approval before Phase 2.
```
