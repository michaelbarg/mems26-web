# MEGA PROMPT · Pipeline 2 (S4 Woodies CCI) · INDEX

**Produced by:** Claude Desktop · 2026-05-25 IL
**For:** Claude Code (CC) — executes each `MEGA_PROMPT_PIPELINE_2_W-X.md` single-shot, one at a time
**Reviewed by (pre-final):** Claude Desktop (CD) — per-package self-report review
**Reviewed by (final):** Cursor — adversarial review + UAT 4 axes on the assembled Pipeline 2 system, **once at the end**, after all 10 packages reach CD_PASSED

---

## §0 · TL;DR

10 mega-prompts (`W-0` audit through `W-9` TradeManager hooks) covering the full Pipeline 2 build for S4 Woodies CCI per D-092 (locked 23/5) + INTAKE v2 P-W decisions (locked 25/5 16:50). All 10 P-W questions are **closed** per `MEGA_PROMPT_PW_DECISIONS_INTAKE.md` v2 — **no skeleton packages, no STOP-on-P-W signals**.

Each package follows the 7-field MEGA_PROMPT_TEMPLATE.md format with Memorial Day §5 lessons injected into every Constraints section, and the forbidden surface (§7 of this INDEX) injected into every FORBIDDEN block.

Execution per package: CC code → CC self-report → Michael forwards to CD → CD review → CD verdict → next package starts. **Cursor batch review happens once, at the end.**

---

## §1 · Provenance + version note

| Field | Value |
|---|---|
| Meta-prompt source | Cursor agent · 2026-05-25 21:30 IL (post-Memorial-Day emergency fix session) |
| Spec authority used | D-092 LOCKED 23/5 18:00 + Sheets A/B/C 23/5 + DTV1 v1.0 (9/5) + INTAKE v2 25/5 16:50 |
| Lock authority for P-W series | `MEGA_PROMPT_PW_DECISIONS_INTAKE.md` v2 final · 25/5 16:50 IL · Cursor audit ✅ |
| Pipeline plan source | `PRE_LIVE_PIPELINE_2026-05-23.md` §10 Pipeline 2 |
| Pre-LIVE protocol | `.cursor/rules/mems26-pre-live-protocol.mdc` + `CLAUDE.md` Pre-LIVE Discipline |
| Memorial Day fix session lessons | `NEXT_CHAT_CONTINUATION_2026-05-26_AM.md` §5 (live-repro + payload-vs-data) |

**Resolution of meta-prompt vs INTAKE v2 contradiction:** Meta-prompt §5 treated P-W2/W-3/W-5/W-6/W-8 as ⏳ open and mandated STOP skeletons for W-2/W-4/W-5/W-8. INTAKE v2 (16:50 same day · ~5 hours earlier) had already locked all 10 P-W with Cursor audit ✅. Per Michael's rule "האחרון בזמן קובע" the INTAKE v2 lock set is the operative authority. All 10 packages are full prompts, zero skeletons.

---

## §2 · Status banner (write-state at INDEX generation)

```
Pipeline 2 · S4 Woodies CCI
P-W locks:         ✅ 10/10 closed per INTAKE v2 (25/5 16:50 IL)
Spec authority:    ✅ D-092 LOCKED + Sheets A/B/C + DTV1
Existing code:     ⚠️ 50 files under backend/v9/systems/woodies/ · 9 patterns exist · conformance-to-spec refit
Memorial Day fix:  ✅ Stream A GREEN (DLL TPO) · Pipeline 2 unblocked
P-W blockers:      ✅ none (all skeletons converted to full prompts)
Forbidden surface: ✅ enumerated §7 below · injected into every prompt
Ready to ship:     ✅ 10 prompts ready · CC can pick up W-0 immediately
```

---

## §3 · 10-package table

| Pkg | Name | Spec authority (verbatim) | Est CC days | Pkg deps | Commit prefix |
|---|---|---|---|---|---|
| **W-0** | S4 Codebase Audit | D-092 + 50 files under `backend/v9/systems/woodies/` | ~1 day | — | `docs(woodies): W-0 codebase audit report` |
| **W-1** | ATR-14 Stop Engine | D-092 §Stop Architecture + Sheet C §6.1 | ~1 day | W-0 | `feat(woodies): W-1 ATR-14 stop engine` |
| **W-2** | Trend State Machine (4 states + YELLOW block) | D-092 §Trend State + Sheet C §6.3 + INTAKE v2 P-W5 lock A | ~1 day | W-0 | `feat(woodies): W-2 trend state machine + YELLOW block` |
| **W-3** | Day-Type Matrix Gate (63 cells verbatim) | D-092 §Day-Type Matrix + Sheet B (63 cells) | ~1.5 days | W-0, W-1, W-2 | `feat(woodies): W-3 day-type matrix gate` |
| **W-4** | HFE dual-path divergence logger | D-092 §Patterns row 9 + INTAKE v2 P-W2 lock B | ~2 days | W-0 | `feat(woodies): W-4 HFE divergence logger` |
| **W-5** | ZLR 39 test failures · audit-first | D-092 §Caveats #7 + INTAKE v2 P-W3 lock A | ~1-2 days (audit Step 1) + ~1 day (fix Step 2 after Michael approval) | W-0 | `docs(woodies): W-5 ZLR audit report` (Step 1) + `fix(woodies): W-5 ZLR ...` (Step 2) |
| **W-6** | 8 patterns refit (CONT + REV) — adds R_t1 field, keeps raw_confidence | D-092 Sheet A + Sheet C + INTAKE v2 P-W8 v2 | ~3 days | W-1, W-2, W-3, W-7 | `feat(woodies): W-6 8 patterns refit + R_t1 emit` |
| **W-7** | 9 Anti-patterns gate (AP1-AP9) | D-092 §9 Anti-patterns + Sheet C §6.5 | ~1 day | W-0 | `feat(woodies): W-7 anti-patterns gate` |
| **W-8** | Dispatcher (R_t1 two-tier) + YAML loader | D-092 + INTAKE v2 P-W6 v2 + P-W8 v2 + P-W9 E | ~2 days | W-6 | `feat(woodies): W-8 R_t1 dispatcher + YAML loader` |
| **W-9** | LiranExitLadderRule + bridge integration | D-092 §Target Strategy + Sheet C §6.2 + S2 Pkg 6 RiskRule interface | ~1.5 days (after Pkg 6 landed) | ALL S4 + S2 Pkg 6 | `feat(woodies): W-9 Liran exit ladder` |

**Total CC effort:** ~16-19 days · 4 weeks calendar with parallel streams per Pipeline V2 §10 sequencing.

---

## §4 · Execution order (DAG flattened linearly)

Recommended execution order respecting dependencies:

```
W-0  (audit · 1d · standalone)
 ↓
W-1  (ATR engine · 1d) ────────┐  parallel-eligible after W-0
W-7  (anti-patterns · 1d) ─────┤  parallel-eligible after W-0
 ↓                              ↓
W-2  (trend states · 1d · YELLOW block per P-W5)
 ↓
W-3  (day-type matrix · 1.5d · consumes Sheet B)
 ↓
W-5  (ZLR audit Step 1 · 1d · NO CODE · per P-W3 A) → Michael review → W-5 Step 2 fix (1d)
 ↓
W-4  (HFE divergence logger · 2d · per P-W2 B)
 ↓
W-6  (8 patterns refit · 3d · requires W-1+W-2+W-3+W-7)
 ↓
W-8  (R_t1 dispatcher · 2d · requires W-6 output shape)
 ↓
W-9  (Liran exit ladder · 1.5d · ALSO requires S2 Pkg 6 RiskRule interface landed)
```

**Parallelism opportunities:**

- W-1 and W-7 can run in parallel after W-0 (different files, no shared state)
- W-2 and W-5 Step 1 can overlap (different scope)
- W-4 and other packages can interleave (independent file)

**Sequential constraints (do NOT violate):**

- W-6 cannot start before W-1, W-2, W-3, W-7 all CD_PASSED (it consumes their outputs)
- W-8 cannot start before W-6 CD_PASSED (it consumes PatternResult shape including R_t1)
- W-9 has TWO predecessors: (a) all S4 packages CD_PASSED AND (b) S2 Pkg 6 TradeManager RiskRule interface committed. Pkg 6 status per `STATUS_BOARD.md` is "LAST · absorbs 4a+4b · waits on Pkg 8 Auth Table". W-9 STOP-signals at runtime if Pkg 6 interface missing.

---

## §5 · Per-package P-W lock reference (verbatim from INTAKE v2)

The locks closed in INTAKE v2 final (25/5 16:50 IL) drive specific behavior in 6 of the 10 packages. Verbatim citations below — every W-X prompt re-quotes the relevant lock in its Spec Authority section.

### P-W1 · LOCK B — drives W-0 (audit references DTV1)

> "DTV1 source · file uploaded as `MEMS26_WOODIES_DECISION_TREE_V1.md` (1085 LOC · v1.0 · 2026-05-09 · STANDALONE architecture · Entry A1-A7 + Active B1-B14)."

### P-W2 · LOCK B — drives W-4

> "HFE detection · DLL primary · Python audit-only · DLL down → no HFE (8 patterns continue). DLL exports `hfe_detected` via bridge · Python `hfe.py` runs in parallel and logs divergences to SHADOW events · trade decisions consume DLL signal only."

### P-W3 · LOCK A — drives W-5

> "39 ZLR test failures · diagnose first · no code changes until per-fixture probe report. CC runs probe on all 39 fixtures · reports per fixture whether ≥1 bar has CCI >+200 (Liran Stage-1 requirement) · only then decide fixture-bug vs detector-bug."

### P-W4 · LOCK A — drives optional W-0 follow-up

> "`gateway._persist_trade` 18s latency · verify-first · measure before fix. CC runs one-shot probe over last 100 trades · measures p50/p95/max latency of `_persist_trade` · if max >1s → bug confirmed · if max <100ms → close P-W4 no-action."

(Not in Pipeline 2 main W-X scope. W-0 audit may surface it as a noted follow-up; resolution is post-Pipeline 2.)

### P-W5 · LOCK A — drives W-2

> "YELLOW trend state (5th opposite bar) · BLOCK ALL 9 patterns · both CONT and REV. DTV1 Stage A1 (Strategic Gate) extended with `if trend_state == 'YELLOW': reject_all_patterns`. No pass-through · no reduced-confidence override. Wood 'WSI' + Liran 'next bar flip' doctrine."

### P-W6 · LOCK B extended (v2 typo fix) — drives W-8

> "Two-tier dispatcher: (1) within same family (CONT vs CONT · REV vs REV) → `max(R_t1)` per P-W8 · (2) cross-family (CONT + REV) → Stage-1 trend gate breaks: **BLUE → CONT wins · RED → CONT wins · GRAY → `max(R_t1)` cross-family fallback**. YELLOW already blocks all per P-W5 (not reached). Direction follows trend (BLUE → CONT-LONG · RED → CONT-SHORT)."

### P-W7 · LOCK doc-reconciliation — drives W-0 (audit identifies compliance manifest update)

> "6 touch-points = A2 (Day Type · Entry) · A4 (POC + Suffering Side · Entry) · A5 (OTF Clarity · Entry) · B4 (POC migration · Active) · B5 (OTF Clarity mid-trade · Active) · B9 (Market State · Active). All ADVISORY · none blocks/exits. Canvas A4 misattributed (used S2 vocab). Master Index '6 total' is correct."

### P-W8 · LOCK hybrid prose v2 — drives W-6, W-8

> "V1 dispatcher comparator = **R_t1 = (t1_price − entry) / (entry − stop)**. Within-family (CONT vs CONT · REV vs REV) → `max(R_t1)`. Cross-family → P-W6 trend gate breaks (BLUE → CONT · RED → CONT · GRAY → `max(R_t1)` cross-family fallback). SHADOW logs `raw_confidence` + `realized_R per leg` (T1/T2/T3 hit/miss/stopped) for all 9 patterns to enable Phase B re-decision. The 9 `raw_confidence` formulas in `backend/v9/systems/woodies/patterns/*.py` are **code-as-truth** · classify **KEEP** in G0 audit · they feed `v9_trades.raw_confidence` for SHADOW analysis · they do **NOT** participate in V1 dispatcher decisions."

### P-W9 · LOCK E — drives W-8

> "Python detector files (`patterns/*.py`) define `THRESHOLDS = {...}` as default constants. Optional `backend/v9/systems/woodies/config/thresholds.yaml` loaded at init · merged on top of Python defaults (YAML wins). If YAML missing/corrupt → fall back to Python defaults (no silent failure · no init crash · WARN log). SHADOW experiments can load alternate YAML via env var without touching baseline. All YAML diffs Git-tracked."

### P-W10 · LOCK A — informs SHADOW thresholds post-Pipeline 2

> "All 9 patterns active through V1 SHADOW. **Drop threshold:** `N≥500 AND E[R]<0 AND hit-rate T1<35%`. **Promote 🔴→🟢:** `N≥500 AND E[R]>0 AND hit-rate T1>40%`. Non-blocking for build · decision happens post-SHADOW launch."

---

## §6 · CD Review Protocol (for every package CC submits)

When CC submits a self-report, Michael forwards it to Claude Desktop (CD). CD runs **5 phases** before emitting a verdict. All findings recorded in `docs/handoff/CD_REVIEW_W-X.md`.

### Phase 1 · Spec compliance check

- [ ] Spec authority quoted verbatim (no paraphrase of D-092 / Sheets / DTV1 / INTAKE v2)
- [ ] Files changed match SCOPE — no FORBIDDEN files touched, no "while I'm here" additions
- [ ] Golden tests count ≥ minimum specified in prompt
- [ ] `pytest` tail GREEN (paste-evidence in self-report, not just claim)
- [ ] Allowed imports respected — no imports outside the whitelist
- [ ] All Acceptance Criteria bullets ticked with concrete evidence
- [ ] Constraints respected (no silent excepts · no `logger.debug` on failure paths · no hardcoded constants)

### Phase 2 · §5 lessons enforcement (Memorial Day · for wiring packages: W-2, W-3, W-4, W-6, W-9)

- [ ] **Live Python repro present** — imports REAL production class (not FakeBarEvent / mock) and proves production-visible side effect. Format: `python3 -c "from <real module> import <real class>; ev = <real class>(...); asyncio.run(<handler>(ev)); assert <side effect>"`. Output pasted in self-report. **Missing live repro → 🔴 FAIL.**
- [ ] **Source dataclass line numbers quoted** before any new attribute access on event/dataclass. CC must Read the source and cite line range in self-report. **Cited from memory → 🟡 NEEDS_FIX.**
- [ ] **Tests do NOT use FakeBarEvent / mock event** with `.data` attribute (the §5 fix #4A.1 root cause). **Mock with .data → 🔴 FAIL.**

### Phase 3 · INTAKE v2 P-W lock compliance

Package-specific checks per §5 above. Examples:

- W-2: A1 gate blocks ALL 9 patterns in YELLOW (both CONT and REV) per P-W5 A
- W-4: Python `hfe.py` ONLY logs divergence to SHADOW · does NOT influence trade decisions per P-W2 B
- W-5: Step 1 produces probe report ONLY · NO code change · per P-W3 A audit-first
- W-6: 9 raw_confidence formulas UNCHANGED in code · R_t1 added as new field · per P-W8 v2 KEEP
- W-8: dispatcher rule verbatim two-tier from P-W6 v2 (BLUE→CONT · RED→CONT · GRAY→max(R_t1)) · YAML loader per P-W9 E
- W-9: Liran exit ladder verbatim from Sheet C §6.2 (8 rungs from T1 4T to TCCI cross)

### Phase 4 · Pre-LIVE protocol compliance

Per `.cursor/rules/mems26-pre-live-protocol.mdc`:

- [ ] Smallest correct change (no scope creep beyond prompt SCOPE block)
- [ ] Regression test added for every bug fix under `tests/v9/...`
- [ ] `pytest tests/v9/... -q` passes (paste tail)
- [ ] No new `logger.debug` on failure paths — bridge/backend errors must be `warning` or `error` with rate-limit
- [ ] Report reflects post-execution reality (not pre-execution plan)
- [ ] If wiring change: bridge/backend/DB state recorded in self-report

### Phase 5 · Verdict output

```
## CD Review · W-X · <Name> · <ISO timestamp>

Verdict: 🟢 PASS | 🟡 NEEDS_FIX | 🔴 FAIL

Phase 1 (Spec compliance):      ✅ / ❌
Phase 2 (§5 lessons):            ✅ / ❌ / n/a
Phase 3 (INTAKE v2 locks):      ✅ / ❌
Phase 4 (Pre-LIVE protocol):    ✅ / ❌

Findings:
1. [severity] description with file:line citation
2. ...

Recommendation:
- if 🟢 PASS: move to next package
- if 🟡 NEEDS_FIX: short retry prompt (CD will draft)
- if 🔴 FAIL: stop world · Michael decides retry-CC or revision-of-prompt

Cursor handoff items (for batch review at end):
- specific live repro to re-run
- specific integration point to verify
```

**🔴 FAIL = stop world.** Michael decides next action.

---

## §7 · Forbidden surface (locked · injected into every prompt's FORBIDDEN block)

Per meta-prompt §4.4 + Memorial Day fix session locked commits. No package may touch:

```text
- sc_study/MES_AI_DataExport.cpp                       [Stream A · locked 037b6a7]
- bridge/v9_streams/*                                   [bridge local-only · mems26-stability.mdc]
- ~/Library/LaunchAgents/com.mems26.bridge.plist        [stability rule]
- backend/v9/api/v9/tpo_routes.py:343-360               [Stream B reject-and-warn · locked 73a6acf]
- backend/v9/systems/five_min/five_min_system.py:on_day_type_event  [Fix #4A.1 · locked 9e698aa]
- backend/main.py:89 (bar_router.subscribe day_type_classification)  [locked 598b3a9]
- backend/v9/db/session.py (WAL + busy_timeout settings)             [already configured · D-074]
- frontend/                                              [Pipeline 2 is backend-only]
- backend/v9/systems/{five_min,day_type,footprint,layer0}/  [other systems · S2/S1/S3/S5]
- docs/spec_authority/*                                  [LOCKED · only D-XXX changes them]
- docs/decisions/D-*.md                                  [LOCKED · only new D-XXX changes them]
- MEGA_PROMPT_PW_DECISIONS_INTAKE.md                     [LOCKED 25/5 16:50]
```

---

## §8 · Memorial Day §5 lessons (verbatim · injected into every prompt's Constraints block)

From `NEXT_CHAT_CONTINUATION_2026-05-26_AM.md` §5 + meta-prompt §2:

```text
## Constraints (Memorial Day §5 lessons · MANDATORY)

a. For any new event subscription or wrapper that reads attribute X from an event,
   FIRST open the source dataclass with the Read tool and quote the field list with
   line numbers in your self-report (Deliverable §3). Do NOT cite from memory.

b. For any wiring fix (subscribe/dispatch/hook), include a live Python repro in
   the deliverable that imports the REAL production class (NOT a FakeEvent mock)
   and proves the production-visible side effect. Format:
     python3 -c "from <real module> import <real class>; ev = <real class>(...);
                 asyncio.run(<handler>(ev)); assert <side effect>"

c. Unit tests using fake/mock events are NOT sufficient proof that wiring works.
   Production-import repro is mandatory before claiming a wiring fix is GREEN.

d. Do NOT trust commit messages or status lines that say "GREEN" without seeing
   the live repro evidence inline in the report.
```

**Root cause of these lessons (do not repeat):**

- Fix #1 (`bbf30a6`): `_on_day_type_update` modified correctly but never subscribed to bar_router. Tests called the method directly so didn't catch.
- Fix #4A (`598b3a9`): wrapper subscribed correctly but read `event.data` while real `BarEvent` has `.payload`. Tests used FakeBarEvent with `.data` so passed; production no-op'd.

Cursor caught both via live Python repro using the REAL `BarEvent` class.

---

## §9 · Hand-off workflow (per package)

```
1. Michael picks up MEGA_PROMPT_PIPELINE_2_W-X.md
   ↓
2. Michael pastes the prompt to Claude Code (CC)
   ↓
3. CC executes single-shot:
   - Read spec authority sections inlined in the prompt
   - Read existing code files cited (CC uses its Read tool)
   - Implement per SCOPE block
   - Write tests per Golden Tests block
   - Verify per Acceptance Criteria
   - Emit self-report per Deliverable Format block
   ↓
4. CC submits self-report to Michael
   ↓
5. Michael forwards self-report to Claude Desktop (CD)
   ↓
6. CD runs CD Review Protocol §6 (5 phases)
   ↓
7. CD verdict: 🟢 PASS | 🟡 NEEDS_FIX | 🔴 FAIL
   ↓
8. CD updates docs/handoff/PIPELINE_2_SPRINT_CHECKLIST.md status column
   ↓
9. If 🟢 PASS → next package starts
   If 🟡 NEEDS_FIX → CD drafts retry prompt → CC retries → loop to step 4
   If 🔴 FAIL → STOP · Michael decides retry-CC or revision-of-prompt
   ↓
10. (After all 10 packages CD_PASSED) Michael requests PIPELINE_2_CURSOR_HANDOFF.md
    CD generates handoff doc summarizing all 10 packages
    Cursor batch-reviews: adversarial + UAT 4 axes on assembled system
    Cursor emits Final Green Light → Pipeline 2 LOCKED
```

---

## §10 · File manifest (this Pipeline 2 batch)

11 files under `docs/handoff/`:

| File | Purpose | When generated |
|---|---|---|
| `MEGA_PROMPT_PIPELINE_2_INDEX.md` | This file · navigation map | NOW |
| `PIPELINE_2_SPRINT_CHECKLIST.md` | Live sprint status board · 10-row package table + burndown + Cursor readiness | NOW (init state) |
| `MEGA_PROMPT_PIPELINE_2_W-0.md` | Codebase audit prompt | NOW |
| `MEGA_PROMPT_PIPELINE_2_W-1.md` | ATR-14 stop engine | NOW |
| `MEGA_PROMPT_PIPELINE_2_W-2.md` | Trend state machine + YELLOW block | NOW |
| `MEGA_PROMPT_PIPELINE_2_W-3.md` | Day-type matrix gate (63 cells) | NOW |
| `MEGA_PROMPT_PIPELINE_2_W-4.md` | HFE divergence logger | NOW |
| `MEGA_PROMPT_PIPELINE_2_W-5.md` | ZLR 39 fix · audit-first | NOW |
| `MEGA_PROMPT_PIPELINE_2_W-6.md` | 8 patterns refit · R_t1 emit | NOW |
| `MEGA_PROMPT_PIPELINE_2_W-7.md` | Anti-patterns gate (AP1-AP9) | NOW |
| `MEGA_PROMPT_PIPELINE_2_W-8.md` | R_t1 dispatcher + YAML loader | NOW |
| `MEGA_PROMPT_PIPELINE_2_W-9.md` | LiranExitLadderRule | NOW |
| `CD_REVIEW_W-X.md` (10 files · one per package) | CD review verdicts | per-package · when CC self-report arrives |
| `PIPELINE_2_CURSOR_HANDOFF.md` | Cursor batch review handoff doc | ON-DEMAND when Michael requests, after all 10 CD_PASSED |

---

## §11 · Quick navigation

| Section | Where |
|---|---|
| Provenance + version note | §1 above |
| Status banner | §2 above |
| 10-package table | §3 above |
| Execution order (DAG) | §4 above |
| Per-package P-W lock reference (verbatim) | §5 above |
| CD Review Protocol | §6 above |
| Forbidden surface | §7 above |
| Memorial Day §5 lessons | §8 above |
| Hand-off workflow | §9 above |
| File manifest | §10 above |

10 mega-prompts open in the same folder as this INDEX:
```
docs/handoff/MEGA_PROMPT_PIPELINE_2_W-0.md  ← start here
docs/handoff/MEGA_PROMPT_PIPELINE_2_W-1.md
docs/handoff/MEGA_PROMPT_PIPELINE_2_W-2.md
docs/handoff/MEGA_PROMPT_PIPELINE_2_W-3.md
docs/handoff/MEGA_PROMPT_PIPELINE_2_W-4.md
docs/handoff/MEGA_PROMPT_PIPELINE_2_W-5.md
docs/handoff/MEGA_PROMPT_PIPELINE_2_W-6.md
docs/handoff/MEGA_PROMPT_PIPELINE_2_W-7.md
docs/handoff/MEGA_PROMPT_PIPELINE_2_W-8.md
docs/handoff/MEGA_PROMPT_PIPELINE_2_W-9.md
docs/handoff/PIPELINE_2_SPRINT_CHECKLIST.md  ← live status
```

---

**End of INDEX · Pipeline 2 (S4 Woodies CCI) · 2026-05-25 IL · Claude Desktop**

*All 10 P-W locks verified against INTAKE v2 final · zero skeleton packages · zero STOP-on-P-W signals · ready for CC pickup of W-0.*
