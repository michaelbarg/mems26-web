# MEGA PROMPT · Package W-0 · S4 Codebase Audit

**Produced by:** Claude Desktop · 2026-05-25 IL · for CC · reviewed by CD (Claude Desktop self-report review · per INDEX §6)
**Final reviewer:** Cursor (batch · after all 10 packages CD_PASSED)
**Spec authority:** D-092 LOCKED 2026-05-23 + INTAKE v2 LOCKED 2026-05-25 16:50 + DTV1 v1.0 (2026-05-09)

---

## ⚠️ Read this before starting

You are Claude Code (CC). You execute this prompt single-shot. **No code changes in W-0** — this is an audit-only package. You produce one report file and that is the entire deliverable.

After completion, submit your self-report (per §8 below) to Michael. Michael forwards to Claude Desktop (CD) for 5-phase review. Wait for CD verdict before moving on.

---

## §1 · Spec authority (verbatim, locked)

### §1.1 · D-092 LOCKED 2026-05-23 · Scope · 9 Patterns

> **CONT (Continuation) · 4 patterns**
>
> | # | Name | Group | Source | Stats | Wood-doctrine notes |
> |---|---|---|---|---|---|
> | 1 | **ZLR** Zero Line Reject | CONT | Wood (def) · Rensink · Liran | 🔴 NO_STATS | "could be the only Woodies trade for your career" (Gannon) · 39 test failures (P-W3) |
> | 2 | **TLB** Trend Line Break | CONT | Wood · Liran | 🔴 NO_STATS | "rarely standalone, usually combined" (Liran) |
> | 3 | **TT** Tony Trade / Turbo Touch | CONT | Wood · Rensink (>5 CCI gap) · Liran (3-9 bar) | 🔴 NO_STATS | BLUE/RED only · never GRAY/YELLOW (Wood) |
> | 4 | **GB100** Ghost Bar at ±100 | CONT | Wood · Liran (CZI + 6-bar rule) | 🔴 NO_STATS | Deeper-pullback variant of ZLR |
>
> **REV (Reversal) · 5 patterns**
>
> | # | Name | Group | Source | Stats | Wood-doctrine notes |
> |---|---|---|---|---|---|
> | 5 | **VEGAS** Divergence / Cup-and-Handle | REV | Wood · Liran · Bulkowski (analog) | 🔴 NO_STATS | Min bar 20 · NeuE/NeuC/Norm only |
> | 6 | **GHOST** CCI Head-and-Shoulders | REV | Wood · Liran (head-size irrelevant) · Bulkowski (analog) | 🔴 NO_STATS | "you gotta love a Ghost" (Wood) |
> | 7 | **FAMIR** Failed ZLR at ±200 | REV | Wood · Liran ("mentally hardest pattern") | 🔴 NO_STATS | LSMA agreement mandatory |
> | 8 | **HTLB** Horizontal Trend Line Break | REV-ish | Wood · Liran (zone definition) | 🔴 NO_STATS | Long-line [−100,−200] · short-line [+100,+200] |
> | 9 | **HFE** Hook From Extreme | REV | Community · MEMS26-internal · Liran (level-confluence) | 🔴 NO_STATS | NO Wood doctrine · ~50% success but R>>L (Gannon anecdote) |

### §1.2 · D-092 LOCKED · Stop Architecture · ATR-14 based

> | Layer | Rule | Notes |
> |---|---|---|
> | **א · Primary CONT** | 2-3 ticks beyond entry-bar low/high | Liran's "momentum trade" rule |
> | **א · Primary REV** | Beyond last swing extreme | per-pattern anchor (cup low · right shoulder · failed-ZLR bar · horizontal bar · extreme bar) |
> | **ב · ATR cap CONT** (ZLR/TLB/TT) | **1.0× ATR-14** ≈ 8-16 ticks | normal vol |
> | **ב · ATR cap medium** (GB100/HTLB) | **1.2× ATR-14** ≈ 10-20 ticks | |
> | **ב · ATR cap REV** (VEGAS/GHOST/FAMIR/HFE) | **1.5× ATR-14** ≈ 12-24 ticks | |
> | **ג · Floor** | **4 ticks** (MES tick-noise floor) | 1T = 0.25pt = $1.25 |

### §1.3 · D-092 LOCKED · Trend State Handling (4 states)

> | State | Rule | CONT | REV |
> |---|---|---|---|
> | **BLUE** uptrend | CCI > 50 + prev > 0 + SWI > 20 · Liran: ≥6 bars above ZL with ≥1 bar >+100 | ✅ FIRE | ❌ BLOCK |
> | **RED** downtrend | Mirror of BLUE | ✅ FIRE | ❌ BLOCK |
> | **YELLOW** transition (5th opposite bar) | **P-W5 LOCKED A · BLOCK ALL 9** (Wood WSI · Liran "next bar flip") | ❌ | ❌ |
> | **GRAY** chop / no trend | BLOCK or require confidence > 0.55 (current code) | ❌ | ❌ |

### §1.4 · D-092 LOCKED · Day-Type Matrix Summary (Sheet B detail · 63 cells)

> | Day Type | CONT (1-4) | REV (5-9) |
> |---|---|---|
> | **TN** Trend Normal | ✅ ZLR/TLB/TT/GB100 fire | ❌ trend persistence overwhelms |
> | **TDD** Trend DD | ✅ at 2nd distribution | ❌ extension dominates |
> | **NV** Normal Variation (~70%) | ⚠️ IB-extension direction only | ⚠️ late-session IB-exhaustion only |
> | **NeuE** Neutral Extreme | ❌ CCI extremes clipped | ✅ fade IB-extreme (home) |
> | **NeuC** Neutral Center | ⚠️ mini-trend in VA only | ✅ range edges = ideal |
> | **Norm** Normal rotation | ⚠️ scalp only | ✅ fade VA edges |
> | **NT** Non-Trend | ❌ no Stage-1 trend lock | ❌ no swing structure |
>
> **Rule:** ALL 9 fail in NT (~6.81% of days). CONT fail in NeuE/NT. REV fail in TN/TDD.

### §1.5 · D-092 LOCKED · 9 Anti-patterns

> | # | Trigger |
> |---|---|
> | AP1 | ZLR after >12-bar pullback (CCI memory fades · Rensink) |
> | AP2 | GB100 in YELLOW state (fake breakout · Wood) |
> | AP3 | VEGAS without 5+ bars between swings (noise · Liran) |
> | AP4 | HTLB with <2 touches (single bounce ≠ level) |
> | AP5 | HFE without bars_since_extreme ∈ [2,12] (MEMS26 constraint) |
> | AP6 | GB100 where CCI stays >6 bars opposite ZL during pullback (trend flipped · Liran) |
> | AP7 | TT with TCCI gap < 5 CCI (incomplete cross · Rensink) |
> | AP8 | Any pattern when CCI flat (range < 50) ≥3 bars (Raschke) |
> | AP9 | FAMIR without LSMA agreement (Wood + Liran) |

### §1.6 · INTAKE v2 LOCKED 2026-05-25 16:50 · Relevant P-W decisions for audit

> **P-W3 · LOCK A:** "39 ZLR test failures · diagnose first · no code changes until per-fixture probe report. CC runs probe on all 39 fixtures · reports per fixture whether ≥1 bar has CCI >+200 (Liran Stage-1 requirement) · only then decide fixture-bug vs detector-bug."
>
> **P-W7 · LOCK doc-reconciliation:** "6 touch-points = **A2** (Day Type · Entry) · **A4** (POC + Suffering Side · Entry) · **A5** (OTF Clarity · Entry) · **B4** (POC migration · Active) · **B5** (OTF Clarity mid-trade · Active) · **B9** (Market State · Active). All ADVISORY · none blocks/exits. Canvas A4 list (`day_type / tpo / veto / killzone / layer0`) confused S2 vocab. Master Index '6 total' is correct."
>
> **P-W8 · LOCK hybrid v2:** "The 9 `raw_confidence` formulas in `backend/v9/systems/woodies/patterns/*.py` are **code-as-truth** · classify **KEEP** in G0 audit · they feed `v9_trades.raw_confidence` for SHADOW analysis · they do **NOT** participate in V1 dispatcher decisions."
>
> **Registry §5 raw_confidence formulas (verified per INTAKE v2 Gap 3):**
>
> | Pattern | Formula | Type |
> |---|---|---|
> | ZLR | `min(0.9, 0.5 + cci/400)` | dynamic |
> | TLB | `min(0.85, 0.4 + abs(curr-pred)/200)` | dynamic |
> | TT | `0.7` | fixed |
> | GB100 | `min(0.85, 0.5 + (curr-100)/200)` | dynamic |
> | VEGAS | `0.75` | fixed |
> | GHOST | `0.7` | fixed |
> | FAMIR | `min(0.8, 0.5 + (200-max)/100)` | dynamic |
> | HTLB | `0.65` | fixed |
> | HFE | `min(0.8, 0.5 + hook/400)` | dynamic |

### §1.7 · DTV1 v1.0 · 21 Stages reference (full file at `docs/MEMS26_WOODIES_DECISION_TREE_V1.md` · committed per P-W1)

> **Entry Phase (A1-A7):** A1 Strategic Gate · A2 Day Type Query (touch-point) · A3 Pattern Detection · A4 POC+Suffering Side Query (touch-point) · A5 OTF Clarity Query (touch-point) · A6 Entry Classification · A7 Universal Pre-Entry Checks
>
> **Active Phase (B1-B14):** B1 Stop Check · B2 EOD Check · B3 Color Flip · B4 POC Migration Query (touch-point) · B5 OTF Clarity Mid-Trade (touch-point) · B6 News Window · B7 Time Stop · B8 Counter-Pattern · B9 Market State Query (touch-point) · B10 T1 Milestone · B11 T2 Milestone · B12 T3 Milestone · B13 Trail Check · B14 Hold

---

## §2 · Existing code surfaces (READ-ONLY in this package)

CC reads each path below using the Read tool and analyzes content. **No file is modified, created, or deleted in W-0 (except the one output report).**

### §2.1 · Woodies subsystem · 50 files under `backend/v9/systems/woodies/`

```
Core orchestration (16 files):
  woodies_system.py
  decision_tree.py
  pattern_engine.py
  dispatcher.py
  yaml_loader.py
  terminal_states.py
  entry_phase.py
  active_phase.py
  execution_bridge.py
  direction_change_detector.py
  cci_calc.py
  cci.py
  schemas.py
  api.py
  detector.py
  __init__.py

9 patterns (10 files):
  patterns/zlr.py
  patterns/tlb.py
  patterns/tt.py
  patterns/gb100.py
  patterns/vegas.py
  patterns/ghost.py
  patterns/famir.py
  patterns/htlb.py
  patterns/hfe.py
  patterns/__init__.py

21 DTV1 stages (22 files):
  stages/a1_strategic_gate.py
  stages/a2_day_type_query.py
  stages/a3_pattern_detection.py
  stages/a4_poc_suffering_query.py
  stages/a5_otf_clarity_query.py
  stages/a6_entry_classification.py
  stages/a7_universal_checks.py
  stages/b1_stop_check.py
  stages/b2_eod_check.py
  stages/b3_color_flip.py
  stages/b4_poc_migration_query.py
  stages/b5_otf_clarity_mid_trade.py
  stages/b6_news_window.py
  stages/b7_time_stop.py
  stages/b8_counter_pattern.py
  stages/b9_market_state_query.py
  stages/b10_t1_milestone.py
  stages/b11_t2_milestone.py
  stages/b12_t3_milestone.py
  stages/b13_trail_check.py
  stages/b14_hold.py
  stages/__init__.py

Helpers (2 files):
  helpers/ema_calculator.py
  helpers/__init__.py

Config (2 files):
  config/woodies_config.yaml
  compliance_manifest.yaml
```

*Exact filenames may differ in the live tree — use `view` on the directory to discover. The above is the EXPECTED inventory per Cursor's 2026-05-25 21:30 audit. If discrepancies, document them in §3.4 Drift list.*

### §2.2 · Test files (14 files)

```
tests/atomic/test_woodies_runtime_contract.py
tests/atomic/test_woodies_decision_tree.py
tests/atomic/test_woodies_fire_endpoint.py
tests/atomic/test_woodies_direction_change.py
tests/v9/systems/test_woodies.py
tests/v9/systems/test_woodies_dedup.py
tests/v9/systems/test_woodies_patterns.py
tests/v9/systems/test_woodies_process_bar_perf.py
tests/v9/compliance/test_woodies_compliance.py
tests/v9/frontend/test_woodies_build_data_texts.py
tests/v9/api/test_woodies_5min_payload.py
tests/v9/api/test_woodies_chart_routes.py
backend/v9/tests/test_woodies_system.py
backend/v9/tests/integration/test_woodies_e2e.py
backend/v9/tests/integration/fixtures/woodies_bar_sequences.py
```

### §2.3 · Cross-system contact points (READ-ONLY · map only · do NOT modify)

Map where S4 (woodies) touches other systems. **Do not change anything outside woodies/.**

```
backend/v9/systems/five_min/                    [S2 · touched only if S4 imports from it]
backend/v9/systems/day_type/                    [S1 · S4 reads day_type via touch-point A2/B?]
backend/v9/services/bar_router/                 [S4 likely subscribes via bar_router]
backend/v9/db/                                  [S4 writes to v9_trades · check raw_confidence column existence]
```

For each cross-system touch found, record in §3.3.

---

## §3 · Audit deliverable structure

Produce ONE markdown file: `docs/reports/PIPELINE_2_S4_AUDIT.md`

The report has 6 sections:

### §3.1 · Per-pattern table (9 rows)

For each of the 9 patterns (ZLR / TLB / TT / GB100 / VEGAS / GHOST / FAMIR / HTLB / HFE), produce one row:

| Column | What goes in |
|---|---|
| `pattern_id` | ZLR / TLB / etc. |
| `file` | `patterns/zlr.py` etc. |
| `LOC` | line count of the file |
| `uses_dll` | yes / no — does the pattern read a DLL-provided field (e.g., `hfe_detected`)? |
| `uses_python_fallback` | yes / no — does it have a Python-computed alternative path? |
| `confidence_formula` | the exact line of code that computes raw_confidence (verbatim from file:line) |
| `confidence_type` | dynamic / fixed (per §1.6 Registry §5 table) |
| `formula_matches_registry` | ✅ / ❌ — does the file's actual formula match the registered formula in §1.6? |
| `referenced_anti_patterns` | which AP1-AP9 IDs (from §1.5) does this pattern's code call? Cite file:line for each |
| `day_type_sensitivity_comments` | quote any comment in the file referencing day_type — file:line |

**Every cell must cite file:line.** No claim from memory. If a file doesn't exist, mark `MISSING` and record in §3.4.

### §3.2 · Per-stage table (21 rows · A1-A7, B1-B14)

For each of the 21 DTV1 stages, one row:

| Column | What goes in |
|---|---|
| `stage_id` | A1 / A2 / ... / B14 |
| `file` | `stages/a1_strategic_gate.py` etc. |
| `LOC` | line count |
| `is_touch_point` | yes/no (touch-points per P-W7 LOCK: A2/A4/A5/B4/B5/B9) |
| `priority_class` | one of: ABSOLUTE_EXIT / STRATEGIC_EXIT / ADVISORY_EXIT / TIME_EXIT / TARGET / TIGHTEN / PARTIAL / TRAIL / NO_ACTION / Entry (for A-stages) |
| `gateway_TODOs_found` | grep `TODO|FIXME|XXX|HACK` in file · list with file:line |
| `wires_correctly_to_pattern_engine` | yes/no/unclear — does the stage's output flow correctly into A3/A6 or B-priority dispatch? |

### §3.3 · Cross-cut analysis

Four specific cross-cut questions:

**(a) ATR-14 calculation: does it exist anywhere?**
- Search `backend/v9/systems/woodies/` for ATR-14 computation
- Search `backend/v9/systems/five_min/` for shared ATR-14 module
- Search `backend/v9/shared/` for any indicator utility module
- Cite file:line for each match · classify as KEEP / ADAPT / REPLACE / DEFER for W-1
- If nothing exists: state "W-1 is fully greenfield · no ATR-14 calc in repo"

**(b) Day-Type Matrix — touched anywhere?**
- Search woodies/ for "day_type" / "DayType" / Sheet B usage
- Identify whether the 63-cell matrix is encoded anywhere (YAML / Python dict / SQL table)
- Cite file:line for each match · classify

**(c) Anti-patterns — checked anywhere?**
- Search woodies/ for each of AP1-AP9 (any of the 9 trigger patterns from §1.5)
- For each AP found, cite the file:line that implements it
- For each AP NOT found, list as "AP-X missing"
- This drives W-7 scope decision

**(d) Confidence normalization status**
- How does `dispatcher.py` currently compare confidences from 5 dynamic + 4 fixed patterns?
- Quote the exact code that picks a winner when multiple patterns fire (file:line)
- Does it normalize? Does it use raw values? Does it use R_t1?
- This drives W-8 scope. Per P-W8 v2 LOCK, V1 will use R_t1 · do not propose changes here, just document current state

### §3.4 · Drift list

Every disagreement found between code and (D-092 / Sheets / DTV1 / INTAKE v2). Each entry has:

```
Drift #N:
  Location:      file:line
  Code says:     "<verbatim quote from code>"
  Spec says:     "<verbatim quote from spec section §X.Y>"
  Severity:      LOW / MED / HIGH (HIGH = trading logic affected)
  W-X to fix:    which package addresses this drift
```

**Seed drift items from Cursor's 25/5 21:30 audit (CC verifies each against live code):**

> 1. `__init__.py` reportedly says "8 patterns on 30-min bars" · D-092 says 9 patterns on 5-min bars · location `backend/v9/systems/woodies/__init__.py:1` (CC verifies line number)
> 2. `hfe.py` GROUP comment reportedly says "REVERSAL (NEW_TREND per spec → mapped to REVERSAL group)" · D-092 calls it REV · DTV1 calls it NEW_TREND · location `patterns/hfe.py:18` (CC verifies)
> 3. Two CCI calc files coexist: `cci.py` + `cci_calc.py` · classify which is canonical · recommend deletion of stale one
> 4. `dispatcher.py` priority enum reportedly 9-class at lines 21-31 · verify matches DTV1 + P-W6 v2 rule
> 5. `a1_strategic_gate.py` reportedly has 5 colors incl. YELLOW at line 23 · per P-W5 LOCK A, A1 must extend to BLOCK ALL 9 patterns in YELLOW · verify current state and document delta
> 6. ATR-14 stop engine MISSING per Cursor audit · confirm absence
> 7. Day-Type Matrix gate MISSING per Cursor audit · confirm absence
> 8. Anti-patterns module MISSING per Cursor audit · confirm absence
> 9. Confidence normalization status UNKNOWN · resolve per §3.3(d)

CC must verify each drift against the live tree and add NEW drifts found during audit.

### §3.5 · Per-package readiness verdict

For W-1 through W-9, classify the existing code as one of:

- **KEEP** — file/module exists and matches spec · no change needed
- **ADAPT** — file/module exists but needs targeted modification · refit, not rewrite
- **REPLACE** — file/module exists but is wrong direction · rewrite from scratch
- **DEFER** — file/module doesn't exist · greenfield in W-X

For each package, also estimate effort delta vs Pipeline V2 §10 baseline:

```
W-1 (ATR-14 Stop Engine):
  Baseline estimate: 1 day CC
  Audit-adjusted:    [N days based on audit findings]
  Reason:            "audit confirmed no ATR-14 calc exists · greenfield as planned" OR
                     "audit found existing ATR-N calc in five_min/ that can be adapted · 0.5d instead"

W-2 (Trend State Machine):
  Baseline:          1 day CC
  Audit-adjusted:    [N days]
  Reason:            verify A1 gate current state + needed delta per P-W5

W-3 (Day-Type Matrix Gate):
  ...

W-4 (HFE divergence logger):
  ...

W-5 (ZLR 39 fix):
  ...

W-6 (8 patterns refit):
  ...

W-7 (Anti-patterns gate):
  ...

W-8 (R_t1 dispatcher + YAML loader):
  ...

W-9 (LiranExitLadderRule):
  ...
```

### §3.6 · P-W3 ZLR test failure root-cause hypothesis

Per P-W3 LOCK A (audit-first · diagnose before fix), CC reads `backend/v9/tests/integration/fixtures/woodies_bar_sequences.py` AND inspects the 39 failing test bodies. For each failing test:

```
test_name: tests/v9/.../test_woodies_X::test_Y
classification: FIXTURE_BUG | DETECTOR_BUG | SPEC_DRIFT | UNCLEAR
evidence:       "<quote from fixture or detector showing root cause>"
```

**Specific deliverable:** quote 3 concrete failing test names + 1 fixture chunk that CC believes is missing Stage-1 condition (BLUE declared without ≥1 bar >+200 touch).

This becomes the input to W-5 Step 1. **NO test changes or code changes here.**

Additionally check `v9_trades` table schema for `raw_confidence` column existence (drives W-8 scope decision per P-W8 v2):

```bash
sqlite3 data/mems26_local.db ".schema v9_trades" | grep -i raw_confidence
```

Report yes/no and column type if present.

---

## §4 · Acceptance criteria

The audit is complete only when ALL of these hold:

- [ ] `docs/reports/PIPELINE_2_S4_AUDIT.md` exists with all 6 sections (§3.1-§3.6)
- [ ] Every claim in §3.1-§3.5 backed by `file:line` citation (no claim from memory)
- [ ] Zero code files modified outside the report
- [ ] Zero test files modified
- [ ] `pytest tests/v9/ -q` runs (sanity check that audit didn't break repo) · tail pasted in self-report
- [ ] `git status` shows ONLY the new audit report as Added (no unintended M/D)
- [ ] `git diff --stat HEAD` shows no source file changes
- [ ] Drift list (§3.4) has all 9 seed items verified or refuted, plus any new drifts CC found
- [ ] Per-package readiness verdict (§3.5) has KEEP/ADAPT/REPLACE/DEFER + effort estimate for all 9 packages (W-1..W-9)
- [ ] P-W3 ZLR section (§3.6) names 3 specific failing tests + 1 fixture chunk + classification
- [ ] `raw_confidence` column existence in `v9_trades` schema confirmed yes/no

---

## §5 · Allowed imports

**N/A** — W-0 is audit-only. No code is written. No imports added.

The audit may use bash tools (`rg`, `grep`, `wc`, `sqlite3`) and the Read tool only. No Python execution required for this package.

---

## §6 · Constraints (must not violate)

### §6.1 · Memorial Day §5 lessons (MANDATORY)

```text
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

**Application to W-0:** the audit DOCUMENTS current state of wiring (per §3.2 `wires_correctly_to_pattern_engine`) but does NOT fix any wiring in W-0. The §5 lessons apply when subsequent packages (W-2, W-3, W-4, W-6, W-9) modify wiring.

### §6.2 · Pre-LIVE protocol (per `.cursor/rules/mems26-pre-live-protocol.mdc`)

- **Read the current code.** Audit using Read tool · no claims from memory.
- **Audit what already exists.** This package IS the audit · classify everything KEEP/ADAPT/REPLACE/DEFER.
- **Verify the hypothesis with data.** When confirming a drift, paste the line that shows it.
- **Confirm the fix is not already there.** Particularly for items §3.3(a), (b), (c), (d) · "MISSING per Cursor audit" must be verified, not assumed.
- **Bound the blast radius.** This package is audit-only — zero code change, zero test change.

### §6.3 · No code changes

```text
- DO NOT modify any .py file under backend/v9/systems/woodies/
- DO NOT modify any test file
- DO NOT modify compliance_manifest.yaml or woodies_config.yaml
- DO NOT modify __init__.py to "fix the 30-min comment" — that's W-6 scope
- DO NOT add a TODO comment to any source file
- The ONLY file Added in git status is docs/reports/PIPELINE_2_S4_AUDIT.md
```

### §6.4 · Forbidden surface (do NOT touch)

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

For audit purposes the above paths are READ-only (CC may grep them as part of §3.3 cross-system analysis), but no modifications.

### §6.5 · No invented findings

If a file mentioned in §2.1/§2.2 doesn't exist in the live tree, document it as `MISSING` in §3.4 — do NOT pretend it exists. Do NOT cite line numbers from memory. Do NOT extrapolate behavior from the spec to claim code behavior — only quote what the code actually says.

---

## §7 · Deliverable format

After completion, CC submits a structured self-report to Michael (Michael forwards to CD).

```text
# CC Self-Report · W-0 · S4 Codebase Audit

## 1. Files changed (A/M/D)
A docs/reports/PIPELINE_2_S4_AUDIT.md

## 2. Commit message
docs(woodies): W-0 codebase audit report · 50 files · 9 patterns · 21 stages · drift list

## 3. Audit report self-check
- §3.1 per-pattern table: 9/9 rows with file:line citations
- §3.2 per-stage table: 21/21 rows with file:line citations
- §3.3 cross-cut: ATR/DayType/AntiPatterns/Confidence — N findings each
- §3.4 drift list: 9 seed items verified · N new drifts added
- §3.5 per-package readiness: 9/9 packages with KEEP/ADAPT/REPLACE/DEFER + effort delta
- §3.6 P-W3 hypothesis: 3 failing tests classified + 1 fixture chunk + raw_confidence column = YES/NO

## 4. Spec ambiguity encountered
[list any case where D-092 / Sheets / DTV1 / INTAKE v2 contradicted each other in a way the audit could not resolve · do NOT pick a side · flag for Michael]

## 5. Forbidden constraint violations
[must be empty · if violated, own up]

## 6. Pytest output (tail 30 lines)
```
[paste verbatim]
```

## 7. Git status check
```
$ git status
$ git diff --stat HEAD
```
[paste verbatim · only the new audit report should appear as Added]

## 8. ReadLints output
N/A · audit-only · no source files modified

## 9. Live Python repro
N/A · W-0 is audit-only · no wiring change · §5 lessons recorded but not applied in this package
```

---

## §8 · Stop signal

STOP and report to Michael (do NOT continue, do NOT guess) if any of these occur:

- A file in §2.1/§2.2 doesn't exist AND its absence changes the audit's overall conclusion (e.g., if `pattern_engine.py` is missing entirely)
- Cursor's seed drift items (§3.4 seed list) cannot be verified — neither confirmed nor refuted — because the live tree differs more substantially than expected
- A FORBIDDEN file (per §6.4) appears unavoidable to read for the audit (this should not happen · only READ is needed, never modify)
- A claim in D-092 / Sheets / DTV1 / INTAKE v2 directly contradicts another claim in those documents in a way the audit must resolve (e.g., D-092 says 9 patterns but a Sheet says 10)
- A test fixture or test body in §2.2 is corrupted/unreadable so P-W3 hypothesis (§3.6) cannot proceed
- A new drift is found that suggests a previous P-W decision should be re-opened (this is significant · do NOT silently note it · STOP and flag explicitly)

Output format if STOP triggered:
```
STOP — <reason> · need Michael decision on <specific question>
```

Do NOT leave a `TODO: ask Michael` in the audit report. Either the audit section is COMPLETE or the STOP signal is the next action.

---

**End of MEGA PROMPT · W-0 · S4 Codebase Audit · 2026-05-25 IL · Claude Desktop**

*Audit-only · no code change · single deliverable: `docs/reports/PIPELINE_2_S4_AUDIT.md` · self-report to Michael → CD review per INDEX §6 → next package starts on 🟢 PASS.*
