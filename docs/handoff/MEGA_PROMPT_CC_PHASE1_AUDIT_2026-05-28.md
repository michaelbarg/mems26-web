# MEGA PROMPT · CC Phase 1 — Unified Audit & Consult
## IB + W-10 TimeStop + CC's 7-Fixes Critique · 2026-05-28

**Author of handoff:** Cursor agent (Claude Opus 4.7)
**Owner (CC):** Claude Code
**Supersedes:** `MEGA_PROMPT_CC_AUDIT_IB_TIMESTOP_2026-05-28.md` + `CC_MEGA_PROMPT_7_FIXES_2026-05-28.md` (both retained for evidence; this is the canonical Phase 1).
**Implementation follow-up:** `MEGA_PROMPT_CC_PHASE2_INTEGRATED_FIX_2026-05-29.md`
**Mode:** **AUDIT (read-only) → CONSULT → STOP for Michael green-light.** No code patches in Phase 1.
**Severity:** 🔴 LIVE blocker family — IB data integrity + trade-lifecycle correctness + TZ data path
**Pre-LIVE protocol:** `.cursor/rules/mems26-pre-live-protocol.mdc` (re-read — Mistakes #1-#11, Source-of-Truth Discipline Rules 1-5 added 2026-05-28).

---

## §0 · TL;DR for CC

Three independent investigations converged on 2026-05-28:

1. **Cursor's IB diagnosis** (worker `ece40e5e`, report `DIAGNOSIS_IB_GROUND_TRUTH_DIVERGENCE_2026-05-28.md`) — 4 root-cause bugs in the IB pipeline.
2. **W-10 TimeStop subagent** (worker `d954ada6`) — already disabled W-10 enforcer via YAML kill switch; landed code + tests + reports; **awaits backend restart to activate**.
3. **CC's own 7-fixes prompt** (`CC_MEGA_PROMPT_7_FIXES_2026-05-28.md`) — proposes fixes for 7 bugs under 4 root causes (Chicago TS, TIME_STOP push counter, S2 hydrate, DLL frozen-tail).

These three investigations **partially contradict each other**. Your Phase 1 job is to audit ALL THREE independently against live code/DB/spec, identify the contradictions, and write a single consultation document Michael can use to green-light Phase 2.

**Do NOT patch anything in Phase 1.** Do NOT trust the proposed diffs in any of the three sources. Re-verify every claim from raw code/data.

---

## §1 · Required reading (in this exact order)

### Discipline (newly tightened today)
1. `.cursor/rules/mems26-pre-live-protocol.mdc` — Mistakes Log §2026-05-17 (#1-#6) and §**2026-05-28 (#7-#11, NEW)**, plus **Source-of-Truth Discipline Rules 1-5 (NEW)**. Heed every rule.
2. `CLAUDE.md` — § *Source-of-Truth Discipline (added 2026-05-28)* with Rules 1-5 condensed for CC.

### What I (Cursor agent) already did
3. **`docs/reports/CURSOR_AGENT_SELF_CRITIQUE_AND_CHANGE_LOG_2026-05-28.md`** — **mandatory read.** Lists every file I modified today and what NOT to undo. Includes my own confessed mistake (re-adding `_ib_from_bars()` synthesis) — your IB Fix #2 will undo that, agree with the undo.

### Today's three primary diagnostic reports
4. `docs/reports/DIAGNOSIS_IB_GROUND_TRUTH_DIVERGENCE_2026-05-28.md` — **the IB authority.** 4 bugs + 5 ranked fixes.
5. `docs/reports/DIAGNOSIS_TRADE_LIFECYCLE_BUGS_2026-05-28.md` — your own diagnosis of the 5 lifecycle bugs.
6. `docs/reports/AUDIT_S2_S4_LIVE_FORENSICS_2026-05-28.md` — Cursor's forensic that falsified your initial "no patterns" claim.
7. `docs/reports/CRITICAL_REVIEW_FORENSIC_AUDIT_2026-05-28.md` — your own self-review confirming the forensic audit.
8. `docs/reports/FIX_REPORT_S2_VOLUME_KEY_2026-05-28.md` — the S2 `"v"` vs `"vol"` fix you already landed.

### Today's three handoff prompts (the inputs being unified here)
9. `docs/handoff/MEGA_PROMPT_CC_AUDIT_IB_TIMESTOP_2026-05-28.md` — Cursor's IB+TimeStop audit prompt (now superseded by this Phase 1 doc).
10. `docs/handoff/CC_MEGA_PROMPT_7_FIXES_2026-05-28.md` — your self-authored 7-fixes prompt (now superseded by this Phase 1 doc — but its content is being audited HERE).
11. `docs/handoff/OPEN_ITEMS_PRE_LIVE_2026-05-28.md` — the canonical backlog. Rows 14-18 added today.
12. `docs/reports/AMENDMENTS_LOG.md` § *2026-05-28 · W-10 TimeStopEnforcer disabled (Option B)* — what landed.

### Code currently under audit
13. `backend/v9/api/v9/tpo_routes.py` (`_normalize_sierra_tpo` + `_ib_from_bars`)
14. `backend/v9/systems/day_type/state_machine.py` (`_stage_a3` lines 413-427)
15. `backend/v9/systems/woodies/woodies_system.py` (`_bar_count++` line ~201, `_check_time_stops` ~533)
16. `backend/v9/systems/woodies/config/dispatcher_config.yaml` (kill switch `time_stop_minutes: null`)
17. `backend/v9/services/trade_manager/bar_level_detector.py` (Layer 4 TIME_STOP, `_check_time_stop`, `_parse_ts`)
18. `backend/v9/api/v9/woodies_chart_routes.py` (line 43, hardcoded `+5*3600`)
19. `bridge/v9_streams/base_stream.py` (`_chicago_to_utc`, line ~283)
20. `sc_study/v9_exports.h` (`v9_sc_datetime_to_unix` line ~147)
21. `sc_study/MES_AI_DataExport.cpp` (IB read lines 717-730)
22. `backend/main.py` (`_day_type_on_bar` lines 195-260)
23. `backend/v9/systems/five_min/five_min_system.py` (hydrate lines 187-213; process_bar 660-700; volume fix at line 698)

---

## §2 · Audit subjects

Phase 1 has **three independent audit subjects**. Audit each separately, then surface cross-contradictions in §3.

### §2.1 · Audit subject A — W-10 TimeStopEnforcer disable (Option B)

The subagent claims W-10 is disabled and the trade lifecycle bugs A + D are moot. Verify the following 11 concrete claims:

| # | Claim | How to verify |
|---|---|---|
| A1 | `dispatcher_config.yaml::time_stop.time_stop_minutes` is now `null` with documenting comments. | Read the YAML. |
| A2 | `TimeStopEnforcer.check()` returns `fired=False` unconditionally when minutes is `None`. | Read `time_stop.py:71`. |
| A3 | `load_time_stop_config()` coerces falsy to `None` at `time_stop.py:134-135`. | Read directly. |
| A4 | `woodies_system.py` has documenting comments at ~line 96 and ~line 533 — **no logic deleted**. | `git diff backend/v9/systems/woodies/woodies_system.py`. |
| A5 | 6 new tests pass (`test_w10_time_stop_disabled.py` + `test_layer4_time_stop_authority.py`). | `pytest <both> -v`. |
| A6 | 7 pre-existing tests carry explicit `@pytest.mark.skip(reason=...)` citing 2026-05-28. No silent fixture rewrites. | Read each `@pytest.mark.skip` line. |
| A7 | Full woodies-adjacent suite: 293 passed / 7 skipped / 0 failed. | `pytest tests/v9/systems/woodies/ tests/v9/services/trade_manager/ tests/v9/systems/test_time_stop.py tests/v9/systems/test_woodies_rth_gate.py -q`. |
| A8 | Constitution V3 Layer 4 IS the canonical TIME_STOP authority (not Registry #11). | Grep `docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt` for "TIME_STOP", "Layer 4", "time-based exit". If V3 contradicts (e.g. mandates W-10), STOP. |
| A9 | Bug A (`_bar_count++` per push at `woodies_system.py:201`) is **latent — not fixed**. Re-enabling YAML re-fires it. | Read line 201. |
| A10 | Layer 4 (`bar_level_detector.py:117-124`) sets `refreshed.exit_price = bar_close` BEFORE `close_trade(trade.id, "TIME_STOP")`. This anti-regresses Bug D. | Read directly. |
| A11 | Layer 4 uses **wall-clock minutes** `(bar_ts - entry_ts).total_seconds() / 60` at line 164 — NOT a per-push counter. | Read `_check_time_stop`. |

Pushback opportunities:
- Does anything OUTSIDE `_check_time_stops` call `enforcer.check()`?
- Could a stale `_open_fire_records` entry cause issues even with the enforcer inert?
- Is Layer 4's wall-clock semantics consistent with spec, or should it be bar-count?

### §2.2 · Audit subject B — IB Ground-Truth Diagnosis (4 root causes)

Re-verify each of the 4 root causes against live code/DB. Do NOT trust the diagnosis text alone.

#### B-Bug #1 — DLL silent IB
**Subagent claim:** `sc_study/MES_AI_DataExport.cpp:717-730` reads ACSIL idx 6 / 8 at `sc.Index` only; returns 0 post-lock; `ib_found=false` flows downstream.

**Verify:**
- Read cited lines verbatim.
- `python3 -c "import json,os; print(json.dumps(json.load(open(os.path.expanduser('~/SierraChart_Data/v9_export/tpo.json')))['ib'], indent=2))"` → confirm `ib.found=false`.
- Check `docs/forensics/SIERRA_UI_EVIDENCE_2026-05-25.md` (if exists) for prior SG mapping evidence.
- Sanity-check earlier-today `ib_high=7543.75, ib_low=7522.00` against possible Sierra IB subgraphs (IB Mid = 7549.75, 2× Above = 7622.5, etc.). None of these match — strongly suggests wrong subgraph indices.

**Pushback:** Wrong-subgraphs hypothesis vs "Extend Lines Forward = No" — what's the discriminator? Both produce the same symptom post-lock. Bar-math for the 09:30-10:30 ET window (whichever TZ) should produce different results from Sierra's IB study.

#### B-Bug #2 — Backend `_normalize_sierra_tpo` synthesis with `ib_found=true` lie
**Subagent claim:** `tpo_routes.py:380-396` synthesises IB from `MAX(high)/MIN(low)` over bars when DLL silent, **flags `ib_found=ib_locked=True`**, fools every downstream consumer. Produces 7583.5 / 7575.0.

**Verify:**
- Read `_normalize_sierra_tpo` + `_ib_from_bars` verbatim.
- `curl -s http://localhost:8000/api/v9/tpo/current | jq '{ib_high,ib_low,ib_source,ib_locked}'` → confirm response.
- Cross-check violation against CLAUDE.md § *Sierra real-time data* AND the new § *Source-of-Truth Discipline* Rule 1.

**This is the single biggest amplifier.** Every other store consumes this synthetic value.

#### B-Bug #3 — State machine cumulative `min`/`max`
**Subagent claim:** `state_machine.py:413-427` (`_stage_a3`) does cumulative `max(ib_high, bar.ib_high)` / `min(ib_low, bar.ib_low)`. Once a low synthetic `ib_low` (7553.25) flows through, latched forever.

**Verify:**
- Read `_stage_a3` body.
- Mentally simulate: bar 1 (h=7583.5, l=7575.0); bar 2 (h=7583.5, l=7553.25). After bar 2: `ib_low = min(7575, 7553.25) = 7553.25`. Matches DB.
- Verify `_stage_a4`/`_stage_b*` do NOT re-read IB post-lock.

**Pushback:** Proposed fix is verbatim assignment. Agree, OR keep `min/max` for A3 evolution and adopt verbatim only at lock (A4)? My take: verbatim is correct per the new Source-of-Truth Rule 3 ("Sierra is the aggregator, not us"). Confirm.

#### B-Bug #4 — Seed accepts synthesised IB
**Subagent claim:** `day_type_seed.py:70` guards on `tpo_ib_locked` boolean only. Bug #2 sets `ib_locked=True` on synthesis → seed adopts synthetic on restart → destroyed the originally-correct `7574 / 7525.5` snapshot.

**Verify:**
- Read `maybe_seed_ib_from_tpo` body.
- Check `v9_day_type_state` table for MEDIUM→WIDE transition timestamp (claimed between 14:30-17:00 UTC):
  ```sql
  SELECT timestamp, ib_width_class FROM v9_day_type_state
  WHERE date(timestamp)='2026-05-28' AND ib_width_class IS NOT NULL
  ORDER BY timestamp;
  ```
- Correlate with backend restart timestamp (`/tmp/backend.log` or process start).

#### B-Bug #5 — `_persist_ib_to_session` no COALESCE (latent)
**Subagent claim:** Once Bug #2 is fixed, transient Sierra silence could fall through with `ib_high/low = None`. Defense-in-depth COALESCE warranted.

**Verify:**
- Read `_persist_ib_to_session` + line 387 guard.

**Pushback:** Ship in same batch as Fix #2, or defer 24h?

### §2.3 · Audit subject C — CC's 7-fixes prompt (`CC_MEGA_PROMPT_7_FIXES_2026-05-28.md`)

**This is the new section. CC's prompt was authored before the W-10 disable landed and before the IB diagnosis report was written.** Therefore several of its claims are now obsolete or contradicted. Audit each claim:

#### C-Bug #1 (DLL frozen-tail) — DEFERRED in CC's prompt
- **Status:** ✅ Correctly deferred. Same conclusion as IB Bug #1 (requires Sierra Remote Build + Subgraphs screenshot).
- **Audit task:** Confirm that the `current_bar` routing mitigation Michael landed via `bars.py` is sufficient for S4 (Trade #155 fired) — yes per UAT. Update prompt cross-ref to IB Bug #1.

#### C-Bug #2 (Chicago TS, `woodies_chart_routes.py:43`) — REAL but UNDER-SPECIFIED
- **Status:** ⚠️ The fix is real, but CC's prompt under-scopes it.
- **Audit tasks:**
  1. CC's prompt asks Michael: "Is Sierra ET or CT?". **First answer this with code evidence, not just Michael's assertion.** Read `sc_study/v9_exports.h:147` (`v9_sc_datetime_to_unix`) — it's a pure Excel-serial conversion with NO TZ. So the timestamps land in whatever TZ Sierra encodes them in. If Sierra is in ET and `_chicago_to_utc` (`base_stream.py:283`) interprets them as CT and adds 5h, we have a +1h drift in EDT (and 0h or -1h in EST).
  2. Per the new Source-of-Truth Rule 4 (TZ ambiguity is forbidden), this is exactly the discipline failure we're trying to prevent. The TZ MUST be confirmed before any patch.
  3. **Bar-math verification (DO THIS):**
     ```sql
     -- If bridge timezone is correct, the 09:30 ET = 13:30 UTC bars should
     -- be the first bars of the day with rising volume (RTH open):
     SELECT ts, high, low, volume FROM v9_bars_5min
     WHERE symbol='MES' AND date(ts)='2026-05-28' AND ts BETWEEN '2026-05-28 13:00:00' AND '2026-05-28 15:30:00'
     ORDER BY ts;
     ```
     If the volume jump appears at `14:30 UTC` instead of `13:30 UTC`, the TZ is shifted by +1h (Sierra in ET, bridge interpreting as CT).
  4. **If TZ shift confirmed:** the bridge's `_chicago_to_utc` is wrong — it should be `_eastern_to_utc` using `America/New_York`. THIS IS A LARGER SCOPE than CC's prompt admits. Every timestamp written by the bridge since this code landed is off by 1h (in EDT).
- **Pushback:** CC's proposed fix (call `BaseV9Stream._chicago_to_utc` from `woodies_chart_routes.py:43`) is a band-aid. The deeper fix is to correct the bridge TZ. This affects EVERY downstream consumer.

#### C-Bug #3 (TIME_STOP push counter) — ✅ MOOT per W-10 disable
- **Status:** ✅ **RESOLVED already.** W-10 enforcer is disabled (Option B, YAML kill switch). `_bar_count` continues to increment per push but `enforcer.check()` returns `fired=False` unconditionally. Bug A is latent.
- **Audit task:** **DO NOT apply CC's proposed fix** to `woodies_system.py:204`. Doing so would be wasted work and would also modify code Michael wants kept inert as a future telemetry path. Cite `docs/reports/AMENDMENTS_LOG.md` § *2026-05-28 · W-10 TimeStopEnforcer disabled (Option B)*.
- **Note in consultation:** Mark Bug #3 as ✅ already resolved.

#### C-Bug #4 (IB window auto-fix) — ❌ FALSE CLAIM
- **Status:** ❌ **CC's claim that Bug #4 is auto-fixed by Bug #2 is wrong.**
- **Why:** Even if TZ is corrected and the IB window shifts to the correct 09:30-10:30 ET range, `_ib_from_bars()` will still produce a value that **does not match Sierra UI** (7574 / 7525.5):
  - Window 1 (13:30-14:30 UTC if Sierra is in ET): MAX/MIN = 7583.5 / 7575.0 (8.5pt NARROW)
  - Window 2 (14:30-15:30 UTC if Sierra is in CT): MAX/MIN = 7581.75 / 7553.25 (28.5pt)
  - **Neither matches Sierra UI** (7574 / 7525.5 = 48.5pt WIDE).
  - 7525.5 is the overnight Globex low (06:45 UTC bar) — outside any plausible RTH IB window.
- **Implication:** Even with TZ fixed, `_ib_from_bars()` is the WRONG approach. **The IB synthesis itself must be deleted** (per IB diagnosis Bug #2 / new Source-of-Truth Rule 1).
- **Audit task:** Replace CC's "auto-fix by #2" claim with: *"Fix #4 (IB synthesis removal) is INDEPENDENT of TZ fix and must be implemented separately. After TZ fix, `_ib_from_bars()` still returns wrong values; delete the function entirely per IB Diagnosis Fix #2."*

#### C-Bug #5 (TIME_STOP exit_price NULL) — ✅ MOOT per W-10 disable
- **Status:** ✅ **RESOLVED already.** The Woodies-side `_check_time_stops` path no longer runs (kill switch). Layer 4 (`bar_level_detector.py:117-124`) sets `refreshed.exit_price = bar_close` BEFORE `close_trade` — anti-regression test at `tests/v9/services/trade_manager/test_layer4_time_stop_authority.py`.
- **Audit task:** **DO NOT apply CC's proposed fix** to `woodies_system.py:556`. The path is dead code now.
- **Note in consultation:** Mark Bug #5 as ✅ already resolved.

#### C-Bug #6 (S2 current_day_type=None lazy-load) — REAL but proposed fix VIOLATES discipline
- **Status:** ⚠️ Real bug, but CC's proposed fix uses `except Exception: pass` (line 261 of CC's prompt).
- **Violation:** Pre-LIVE protocol § *Mindset* — *"Silent error handling (debug-level logs on failure paths, swallowed exceptions) is forbidden between now and LIVE."* This is also CLAUDE.md § *Pre-LIVE Discipline* — *"No silent failures."*
- **Audit task:** Replace `except Exception: pass` with `except Exception as e: logger.warning("[FiveMin] Late hydrate failed: %s", e)`. Otherwise endorse the fix.
- **Cross-coupling:** The lazy-load reads `V9DayTypeState` table. Verify there's no overlap with `maybe_seed_ib_from_tpo` (which will be modified per IB Fix #4) — both should NOT race.

#### C-Bug #7 (exit_ts uses raw bar_ts) — PARTIALLY auto-fixed by #2
- **Status:** ⚠️ Partially auto-fixed by Bug #2 IF the bridge TZ is corrected at source.
- **Audit task:** Verify `BarLevelDetector._parse_ts` at lines 167-178 does NOT apply its own TZ conversion that would compound the fix. If `_parse_ts` is naive (no TZ added), then yes, fixing the bridge TZ propagates correctly. If `_parse_ts` does its own conversion, additional work needed.
- **Cross-check:** This is also OPEN_ITEMS #18 (Bug E from `DIAGNOSIS_TRADE_LIFECYCLE_BUGS_2026-05-28.md`). Don't duplicate the fix.

---

## §3 · Cross-contradiction matrix

This is what makes Phase 1 critical. The three sources contradict each other in subtle places:

| Topic | Source 1 says | Source 2 says | Resolution |
|---|---|---|---|
| **Bug #3 TIME_STOP push counter** | CC prompt: fix at line 204 | Subagent: already moot (W-10 disabled) | Side with subagent — DO NOT TOUCH `woodies_system.py:201/204`. Cite AMENDMENTS_LOG. |
| **Bug #5 TIME_STOP exit_price** | CC prompt: fix at line 556 | Subagent: already moot | Side with subagent — Layer 4 already correct. |
| **Bug #4 IB synthesis fix** | CC prompt: auto-fixed by TZ correction | IB diagnosis: delete `_ib_from_bars()` entirely | Side with IB diagnosis — synthesis is the deeper issue; TZ alone doesn't help (bar-math proves it). |
| **IB ground truth** | Michael's screenshot: 7574 / 7525.5 | Our bars (any TZ window): 7583.5 / 7575.0 or 7581.75 / 7553.25 | Neither matches. Sierra UI is plotting something different (study config or DLL bug). Hold for Sierra Subgraphs screenshot before any IB-store update. |
| **Bridge TZ** | CC prompt: maybe ET, ask Michael | CLAUDE.md / Mistake #10: TZ must be confirmed with chart settings | Confirm with chart settings screenshot first. |
| **Silent error handling** | CC Bug #6 fix: `except Exception: pass` | Pre-LIVE protocol: forbidden | Side with protocol — replace with `logger.warning`. |

---

## §4 · Consultation document format

Write **`docs/reports/CC_AUDIT_CONSULTATION_2026-05-28.md`** with:

### §0 · Audit summary table
| Subject | Claims verified | Claims falsified | Confidence |
|---|---|---|---|
| W-10 disable (11 claims) | … | … | HIGH/MED/LOW |
| IB Bug #1 (DLL) | … | … | … |
| IB Bug #2 (synthesis) | … | … | … |
| IB Bug #3 (min/max) | … | … | … |
| IB Bug #4 (seed) | … | … | … |
| IB Bug #5 (COALESCE) | … | … | … |
| CC Bug #1 (deferred) | … | … | … |
| CC Bug #2 (Chicago TZ) | … | … | … |
| CC Bug #3 (TIME_STOP push) — moot? | … | … | … |
| CC Bug #4 (IB window) — false auto-fix? | … | … | … |
| CC Bug #5 (exit_price) — moot? | … | … | … |
| CC Bug #6 (S2 lazy-load) | … | … | … |
| CC Bug #7 (exit_ts) | … | … | … |

### §1 · Pushback
- One bullet per area where you disagree with any source.
- Include alternative root cause hypotheses or alternative fix sketches.

### §2 · Missed concerns
- Anything none of the three sources addressed. Examples to consider:
  - "Does the bridge TZ fix require backfilling all historical bars in `v9_bars_5min`?"
  - "How does the UI gracefully degrade when `ib_high=None`?"
  - "Does Bug #6 lazy-load create a race with `maybe_seed_ib_from_tpo`?"
  - "If Sierra UI's 7574/7525.5 is a different study entirely, what study is it?"

### §3 · Spec authority cross-check
- Constitution V3 Layer 4 IS / IS NOT canonical TIME_STOP authority.
- Sierra IB Study IS / IS NOT canonical IB source per CLAUDE.md.
- Registry #11 IS / IS NOT superseded.

### §4 · Recommended integrated fix order
Re-rank ALL fixes (IB Bugs #1-#5 + CC Bugs #2, #6, #7; CC Bugs #3, #5 marked moot) in a single dependency-aware list. Surface any dependencies (e.g. "Sierra TZ confirmation must precede Bug #2").

### §5 · Open questions for Michael
- Sierra chart TZ (ET or CT) — confirmed with chart settings screenshot.
- Sierra IB Study Subgraphs tab screenshot (for DLL Fix #1).
- Sierra IB Study Date Reference (today vs yesterday).
- Whether to backfill historical bars after TZ fix.
- Any concerns Michael has with the integrated fix order.

### §6 · Phase 2 readiness checklist
List the prerequisites that MUST be met before Phase 2 starts:
- [ ] Audit complete (this doc).
- [ ] Michael green-lights the fix order.
- [ ] Sierra TZ confirmed.
- [ ] Sierra Subgraphs screenshot received.
- [ ] Backend restart timing decided.

---

## §5 · Hard constraints (Phase 1)

- **READ-ONLY.** No `git add` / `git commit` / `git restore` / file edits.
- **No `except Exception: pass`** — anywhere, ever, including in your audit-time test probes.
- **No `bash scripts/start_all.sh`** — no service spawning.
- **No backend restart** without Michael coordination.
- **Strategic stop** if:
  - Constitution V3 turns out NOT to be the TIME_STOP authority — STOP.
  - Sierra Subgraphs screenshot reveals a 4th study being plotted — STOP (different scope).
  - Sierra TZ turns out to be something other than ET/CT (e.g. UTC) — STOP.
  - Cross-contradiction matrix expands beyond the 6 entries above — STOP and report.
- **Pre-LIVE Mistakes Log applies:**
  - Mistake #4 (don't trust CC/Subagent reports at face value — re-verify from raw evidence)
  - Mistake #7 (no synthesis fallbacks)
  - Mistake #9 (verification quote, not assertion — paste raw command + output for every claim)
  - Source-of-Truth Rule 5 (verification quote, not assertion)

---

## §6 · Deliverables (Phase 1)

1. **`docs/reports/CC_AUDIT_CONSULTATION_2026-05-28.md`** — per §4 above.
2. A summary message back to Cursor + Michael with:
   - Pass/fail for each of the 11 W-10 claims.
   - Confirmed/falsified for each of the 5 IB bugs.
   - Confirmed/falsified for each of the 7 CC-prompt bugs.
   - Cross-contradiction resolutions (matrix in §3).
   - Re-ranked integrated fix order.
   - Open questions for Michael.

**Then STOP.** Do not patch anything. Phase 2 implementation prompt is `MEGA_PROMPT_CC_PHASE2_INTEGRATED_FIX_2026-05-29.md` — gated on Michael's green-light based on your consultation.

---

## §7 · Process

- Cursor agent (me) keeps: code reading, strategic stop/go gating, verification of CC's audit against the 4 UAT axes, routing to Michael for Sierra UI / DLL interaction.
- CC (you) keeps: audit execution, consultation doc, conditional Phase 2 implementation, regression tests, UAT, reports.
- **One thread at a time.** Don't open Phase 2 until Phase 1 closes.

---

## Acknowledgement template

```
Acknowledged MEGA_PROMPT_CC_PHASE1_AUDIT_2026-05-28.md.
Phase 1 (audit) starting now. READ-ONLY mode confirmed.
Pre-LIVE protocol: confirmed reading Mistakes #1-#11 + Source-of-Truth Discipline Rules 1-5.
ETA Phase 1: 60-90 min (3 audit subjects + cross-contradiction matrix + consultation doc).
Will paste raw command+output for every claim verification (per Mistake #9 / Rule 5).
```

Go.
