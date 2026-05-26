# META-PROMPT · Claude Desktop → Generate 10 Mega-Prompts for Pipeline 2 (S4 Woodies CCI)

**Producer:** Cursor agent · 2026-05-25 21:30 IL (Memorial Day evening · post-emergency-fix session)
**Consumer:** Claude Desktop (you)
**Final consumer of your output:** Claude Code (CC) — executes each mega-prompt; one at a time
**Reviewer of CC's work:** Cursor (G3 adversarial review · G4 4-axis UAT)

---

## §0 · 30-second briefing

Tonight (Memorial Day half-close) we closed an emergency 3-stream fix session
(13 commits, all pushed). Stream A (DLL TPO) is now GREEN, which **unblocks
Pipeline 2 — the S4 Woodies CCI build**. Spec was locked 23/5 18:00 as D-092
with 10 packages (`W-0` audit through `W-9` TradeManager hooks). Your job is
to draft those 10 mega-prompts, one per package, each ready for CC to execute
single-shot per `MEGA_PROMPT_TEMPLATE.md`.

**Critical:** the Woodies codebase already has 50 files including all 9
patterns and 21 decision-tree stages. Pipeline 2 is mostly **conformance-to-spec
refit**, NOT greenfield. Treat each pattern/stage as KEEP/ADAPT/REPLACE/DEFER —
do not let CC rewrite working code.

---

## §1 · Your role (and what you must NOT do)

| You DO | You DO NOT |
|---|---|
| Read all source-of-truth files attached by the user verbatim | Paraphrase the spec — copy/paste verbatim into the prompt |
| Produce 10 mega-prompts as separate markdown files | Combine packages into one prompt — CC must execute single-shot per package |
| Embed inline code attachments per package (paths from §4 audit) | Tell CC "read X" without attaching — CC sometimes cannot |
| Include a STOP signal at the top of any prompt blocked on a P-W question | Guess a P-W answer · invent stats · paraphrase Liran/Wood doctrine |
| Cite line numbers when ADAPTing existing code | Cite line numbers from memory · always quote from the attached file |
| Follow §5 lessons (live-repro · payload-vs-data attribute checks) | Skip §5 — it was written tonight after we caught two dead-code bugs |

---

## §2 · §5 lessons from tonight (MANDATORY · read before drafting any prompt)

Tonight CC introduced TWO bugs that passed all unit tests but were dead in production:

1. **Fix #1** (`bbf30a6`): `_on_day_type_update` was wired in `five_min_system.py`
   correctly, but the method was **never subscribed** to bar_router. Tests called
   the method directly so the wiring gap was invisible.
2. **Fix #4A** (`598b3a9`): wrapper subscribed correctly but read `event.data`
   while the real `BarEvent` dataclass has `.payload`. Tests used a FakeBarEvent
   with `.data` so passed; production silently no-op'd.

**Cursor caught both via live Python repro using the REAL `BarEvent` class.**

Inject these RULES into the **Constraints** section of every prompt you write:

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

---

## §3 · Source-of-truth attachments the user will paste with this meta-prompt

The user (Michael) will paste these files in a single Claude Desktop conversation
along with this meta-prompt. If any are MISSING when you start drafting, **STOP**
and output the missing list before proceeding.

| # | Path | Role |
|---|------|------|
| 1 | `docs/decisions/D-092_S4_WOODIES_UPDATE.md` | spec authority · 9 patterns · ATR-14 stop arch · day-type matrix · 9 anti-patterns · 10 P-W open |
| 2 | `docs/spec_authority/S4_WOODIES_TABLE_A_Pattern_Setup.csv` | Sheet A · 9 patterns × 13 cols |
| 3 | `docs/spec_authority/S4_WOODIES_TABLE_B_DayType_Matrix.csv` | Sheet B · 9 patterns × 7 day types = 63 cells |
| 4 | `docs/spec_authority/S4_WOODIES_TABLE_C_Strategy_Caveats.csv` | Sheet C · stops · trend states · anti-patterns · P-W · caveats |
| 5 | `docs/MEMS26_WOODIES_DECISION_TREE_V1.md` | DTV1 · 21 stages (A1-A7, B1-B14) · 6 advisory touch-points |
| 6 | `docs/research/S4_WOODIES_RESEARCH_DELIVERABLE_2026-05-23.md` | Researcher narrative + source citations behind D-092 |
| 7 | `docs/plans/PRE_LIVE_PIPELINE_2026-05-23.md` (§10 Pipeline 2) | 10 packages W-0..W-9 · spec deps · P-W blockers |
| 8 | `docs/templates/MEGA_PROMPT_TEMPLATE.md` | 7-field format you must follow per prompt |
| 9 | `docs/handoff/NEXT_CHAT_CONTINUATION_2026-05-26_AM.md` | Memorial Day session closure · §5 lessons · current commit state |
| 10 | `.cursor/rules/mems26-pre-live-protocol.mdc` | Pre-LIVE discipline · 4-step verification · 4-axis UAT |
| 11 | `CLAUDE.md` | Sierra source authority · Bridge local-only · Frontend polling floors |

If a file is missing, write:
> **STOP — meta-prompt missing attachment(s):** [list]. Cursor to provide before drafting.

---

## §4 · Existing Woodies code audit (Cursor · 2026-05-25 21:30 IL)

This was done with the Read tool against the live tree. CC will Read the actual
files when executing each prompt; your job is to use this audit to **scope each
package as NEW / EXISTS-needs-conformance / EXISTS-needs-drift-fix**.

### §4.1 · File inventory (50 files under `backend/v9/systems/woodies/`)

| Layer | Files | Status |
|---|---|---|
| Core orchestration | `woodies_system.py`, `decision_tree.py`, `pattern_engine.py`, `dispatcher.py`, `yaml_loader.py`, `terminal_states.py`, `entry_phase.py`, `active_phase.py`, `execution_bridge.py`, `direction_change_detector.py`, `cci_calc.py`, `cci.py`, `schemas.py`, `api.py`, `detector.py`, `__init__.py` | EXISTS · refit per spec |
| 9 patterns | `patterns/{zlr, tlb, tt, gb100, vegas, ghost, famir, htlb, hfe}.py` + `__init__.py` | EXISTS · all 9 wired in `pattern_engine.detect_all_patterns()` |
| 21 DTV1 stages | `stages/{a1..a7}.py` (Entry) + `stages/{b1..b14}.py` (Active) + `__init__.py` | EXISTS · one file per stage, names match DTV1 |
| Helpers | `helpers/ema_calculator.py`, `helpers/__init__.py` | EXISTS |
| Config | `config/woodies_config.yaml`, `compliance_manifest.yaml` | EXISTS · YAML matches DTV1 stage map exactly |
| Tests | 14 files across `tests/atomic/`, `tests/v9/systems/`, `tests/v9/api/`, `tests/v9/compliance/`, `tests/v9/frontend/`, `backend/v9/tests/`, `backend/v9/tests/integration/` | EXISTS · 39 ZLR failures per P-W3 |

### §4.2 · Drift findings (must be addressed in W-0 audit and/or W-6 refit)

| Drift | Where | Fix |
|---|---|---|
| `__init__.py` says **"8 patterns on 30-min bars"** | `backend/v9/systems/woodies/__init__.py:1` | Spec says **9 patterns on 5-min bars**. Fix docstring + verify no 30-min subscription. |
| `hfe.py` GROUP comment says "REVERSAL (NEW_TREND per spec → mapped to REVERSAL group)" | `patterns/hfe.py:18` | DTV1 calls it NEW_TREND (REV per D-092). Verify category map in `pattern_engine.py` matches D-092 §Scope · 9 Patterns. |
| Two CCI calc files coexist | `cci.py` + `cci_calc.py` | W-0 must classify which is canonical and recommend deletion of the stale one. |
| `dispatcher.py` priority enum is 9-class | `dispatcher.py:21-31` | Matches DTV1. Verify YAML order is read for same-class tiebreak (P-W6 spec). |
| `a1_strategic_gate.py` has 5 colors incl. YELLOW | `stages/a1_strategic_gate.py:23` | Verify P-W5 BLOCK semantics: does A3 honor YELLOW as veto? CC must trace the flow. |
| ATR-14 stop engine **MISSING** | no `atr_stop.py` under `woodies/` | W-1 is NEW · per D-092 Stop Architecture (CONT 1.0× · MED 1.2× · REV 1.5× · floor 4T) |
| Day-Type Matrix gate **MISSING** | no `day_type_gate.py` under `woodies/` | W-3 is NEW · consumes Sheet B 63 cells |
| Anti-patterns module **MISSING** | no `anti_patterns.py` under `woodies/` | W-7 is NEW · AP1-AP9 from Sheet C |
| Confidence normalization status **UNKNOWN** | likely scattered across patterns | W-8 must audit and unify (P-W8 spec gated) |

### §4.3 · Test inventory (14 files · 39 ZLR failures per Master Index 16/5)

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

W-5 (ZLR fix) must audit fixtures in `woodies_bar_sequences.py` for Stage-1
completeness (BLUE declared but no >+200 touch — researcher hypothesis).

### §4.4 · Forbidden surface (DO NOT touch in any Pipeline 2 package)

Inject this into the **FORBIDDEN — do NOT touch** section of every prompt:

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
```

---

## §5 · P-W blocker policy

4 of the 10 packages are spec-blocked on P-W open questions that only Michael
can resolve. Your handling:

| Pkg | Blocked on | Your action |
|---|---|---|
| **W-2** Trend State Machine | P-W5 (YELLOW = BLOCK ALL 9?) | Produce a **skeleton** mega-prompt with STOP signal at top: `STOP — blocked on P-W5 · need Michael decision before this package can run. Researcher rec: BLOCK ALL 9 in YELLOW (Wood WSI). Until locked, this package does not start.` Body still drafts scope so it's ready to ship the instant Michael decides. |
| **W-4** HFE dual-path | P-W2 (DLL canonical? Python fallback?) | Same as W-2 · skeleton + STOP. Researcher rec: DLL=primary, Python=audit/fallback, log divergences for SHADOW. Note `patterns/hfe.py` already has primary DLL + Python fallback wired — package is **conformance audit + divergence logging**, not greenfield. |
| **W-5** ZLR 39 test fix | P-W3 (root cause: fixtures or detector?) | Same · skeleton + STOP. Researcher hypothesis: Stage-1 incomplete fixtures (BLUE declared but no >+200 touch). Audit fixtures BEFORE assuming detector regression. |
| **W-8** Dispatcher + Confidence + YAML | P-W6 (priority rule) + P-W8 (normalize?) + P-W9 (YAML schema?) | Same · skeleton + STOP. Researcher recs: P-W6 = DTV1-spec hierarchical · same-direction max conf · opposite-direction Stage-1 tiebreak · CONT wins BLUE/RED · P-W8 = YES normalize to [0,1] via z-score or min-max · P-W9 = YAML-driven, current defaults locked as "Liran baseline". |

For unblocked packages (**W-0, W-1, W-3, W-6, W-7, W-9**), produce the full
mega-prompt ready for CC to execute.

---

## §6 · Per-package scope skeletons

Each entry below is the **minimum** content for the mega-prompt body — you may
add per-spec golden tests, allowed imports, etc. per `MEGA_PROMPT_TEMPLATE.md`.

### §6.1 · W-0 · S4 Codebase Audit (Day 1 · UNBLOCKED · `~1 day CC`)

**Spec authority:** D-092 (locked) + Pipeline V2 §10 §W-0.

**SCOPE — CC reads, classifies, writes one report. NO code changes.**

WRITE NEW:
- `docs/reports/PIPELINE_2_S4_AUDIT.md`

READ-ONLY (audit subjects):
- All 50 files under `backend/v9/systems/woodies/`
- All 14 test files listed in §4.3
- `backend/v9/systems/five_min/` (only to map S4↔S2 cross-system contact points — DO NOT modify)

**Deliverable structure for the audit report:**

1. Per-pattern table (9 rows): pattern_id · file · LOC · uses DLL? · uses Python fallback? · confidence formula type (fixed vs dynamic) · referenced anti-patterns · day-type sensitivity comments found
2. Per-stage table (21 rows · A1-A7, B1-B14): stage_id · file · LOC · touch_point yes/no · priority_class · gateway TODOs found
3. Cross-cut analysis: ATR-14 calc — does it exist anywhere? Day-Type Matrix — touched anywhere? Anti-patterns — checked anywhere? Confidence normalization — how does dispatcher compare 5 dynamic vs 4 fixed today?
4. Drift list: every disagreement found between code and D-092 / Sheets / DTV1 (use §4.2 of the meta-prompt as a seed; CC must verify and extend)
5. Per-package readiness verdict: for W-1..W-9 — is the existing code KEEP / ADAPT / REPLACE / DEFER · estimate effort delta vs Pipeline V2 §10 (e.g., "W-6 was estimated 3d; audit confirms the 8 patterns share signature so refit is 1.5d")
6. Test failure root-cause hypothesis for the 39 ZLR failures (P-W3) — fixture issue or detector? Quote 3 concrete failing test names + 1 fixture chunk that CC believes is missing Stage-1 condition.

**Golden gate (CC self-check before report submission):** every claim in §1-5
must be backed by a code citation (path:line range). No claim from memory.

**No imports needed** (audit only).

---

### §6.2 · W-1 · ATR-14 Stop Engine (Day 2 · UNBLOCKED · `~1 day CC`)

**Spec authority:** D-092 §Stop Architecture + Sheet C §6.1.

**SCOPE — single new module + tests:**

WRITE NEW:
- `backend/v9/systems/woodies/atr_stop.py`
- `tests/v9/systems/test_atr_stop.py`

MODIFY (only the imports + helper call site):
- TBD per W-0 audit (e.g., `pattern_engine.py` if patterns currently hard-code stop ticks · audit MUST confirm)

FORBIDDEN — do NOT touch any pattern detection logic in `patterns/*.py` yet.
W-6 will wire the stop engine to patterns; W-1 only builds the engine + tests.

**Required API:**

```python
def compute_stop(
    direction: Literal["LONG", "SHORT"],
    entry_bar: WoodiesBar,                  # for ±3T primary rule (CONT)
    swing_anchor: Optional[float] = None,    # for REV per-pattern (None for CONT)
    pattern_group: Literal["CONT_TIGHT", "CONT_MED", "REV"],  # ATR cap selector
    atr_14: float,                           # 5-min ATR-14, ticks
    tick_size: float = 0.25,
    floor_ticks: int = 4,
) -> StopResult:
    """Returns StopResult(stop_price, stop_ticks, layer_applied, cap_applied)."""
```

**Caps per D-092:**
- CONT_TIGHT (ZLR/TLB/TT): `1.0 * atr_14`
- CONT_MED (GB100/HTLB): `1.2 * atr_14`
- REV (VEGAS/GHOST/FAMIR/HFE): `1.5 * atr_14`
- Floor: `max(4 ticks, computed_stop_ticks)`

**15+ golden tests:**
1. Each of 9 patterns × 2 directions × normal vol (24T ATR → expect cap hit)
2. Floor test: tiny ATR (3T) → 4T floor wins for CONT
3. Cap test: huge ATR (50T) → cap hits at 1.0/1.2/1.5×
4. REV with swing anchor far → cap clamps before swing rule
5. Tie-breaker test: primary == cap exactly
6. tick_size variation (0.5 → ES instead of MES)
7. Negative ATR → raise ValueError (no silent default)

**ATR-14 input source:** the engine accepts `atr_14: float`. The CALLER provides
it (so this module has no side-effect read). W-6 will wire a feed.

**No new dependencies. No imports outside `backend.v9.systems.woodies.schemas`,
`typing`, `dataclasses`, `enum`.**

---

### §6.3 · W-2 · Trend State Machine (BLOCKED on P-W5)

**Status:** STOP at top of prompt.

```text
STOP — blocked on P-W5 · need Michael decision before this package can run.

Question: In YELLOW state (5th opposite bar · transition), block ALL 9 patterns
(researcher rec per Wood WSI) or allow REV patterns to fire?

Researcher rec (D-092 §P-W5): BLOCK ALL 9. Wood transcripts: "WSI = Wait, Sit,
Inspect." Liran: "next bar will flip" — neither old trend nor new trend is
actionable.

Until locked, W-2 does NOT start.
```

**Drafted scope (post-decision):**

WRITE NEW:
- `backend/v9/systems/woodies/trend_state.py` (state machine: BLUE/RED/YELLOW/GRAY · Stage-1 gate per Liran 6 bars + 1 bar >±100)
- `tests/v9/systems/test_trend_state.py`

MODIFY:
- `stages/a1_strategic_gate.py` — extend to honor BLOCK for YELLOW once decision is in

Note `a1_strategic_gate.py` ALREADY emits 5 colors; the package extends BLOCK semantics, not adds colors.

**Tests:** ≥10 golden including 4-state transitions, Stage-1 lock confirmation, YELLOW BLOCK verification.

---

### §6.4 · W-3 · Day-Type Matrix Gate (Day 3-4 · UNBLOCKED · `~1.5 day CC`)

**Spec authority:** D-092 §Day-Type Matrix + Sheet B (63 cells).

**SCOPE — new module that consumes Sheet B:**

WRITE NEW:
- `backend/v9/systems/woodies/day_type_gate.py`
- `backend/v9/systems/woodies/config/day_type_matrix.yaml` (Sheet B encoded · 63 cells · ✅/⚠️/❌ + per-cell condition strings)
- `tests/v9/systems/test_day_type_gate.py`

MODIFY:
- `stages/a2_day_type_query.py` — currently emits day_type as touch-point advisory.
  Extend it to compute the matrix verdict per (pattern, day_type) and pass it
  forward to A3 — but per DTV1 §3 touch-points are advisory ONLY (NEVER veto).
  → The gate produces a `MatrixVerdict` object that A3/A6/A7 may consume but
    cannot be auto-converted to a veto without a configurable flag (per DTV1
    §A2 edit notes: `convert_advisory_to_veto: false` default).

FORBIDDEN — do not auto-veto · do not block in degraded mode (per DTV1 §1 Degraded Mode).

**Sheet B canonicalization:** the YAML must encode all 63 cells with exact text
from the CSV cells (Cursor will attach `S4_WOODIES_TABLE_B_DayType_Matrix.csv`).
Verbatim — no paraphrase.

**Required API:**

```python
class DayTypeGate:
    def __init__(self, matrix_yaml_path: str): ...
    def get_verdict(
        self,
        pattern_id: PatternId,        # one of ZLR/TLB/TT/GB100/VEGAS/GHOST/FAMIR/HTLB/HFE
        day_type: DayType,            # TN, TDD, NV, NeuE, NeuC, Norm, NT
    ) -> MatrixVerdict:
        """Returns (verdict: '✅' | '⚠️' | '❌', entry_hint: str, t1_ref: str)."""
```

**63-cell verbatim test:** parse the CSV directly in a test fixture · assert
every YAML cell matches the source CSV cell. (Prevents future drift.)

**Degraded mode test:** if `day_type` is `UNAVAILABLE` (S1 offline), return
verdict='⚠️' across all patterns · NEVER block.

---

### §6.5 · W-4 · HFE dual-path (BLOCKED on P-W2)

**Status:** STOP at top.

```text
STOP — blocked on P-W2 · need Michael decision before this package can run.

Question: Is the DLL HFE detection the canonical source, or should Python
fallback remain co-equal? If Python is fallback only, what triggers it (DLL
field missing, or DLL field stale)?

Researcher rec (D-092 §P-W2): DLL=primary, Python=audit/fallback, log
divergences for SHADOW analysis.

Note: `patterns/hfe.py` ALREADY implements primary DLL path + Python fallback
(see lines 45-50). Package is conformance audit + divergence logger, not
greenfield.

Until locked, W-4 does NOT start.
```

**Drafted scope:**

WRITE NEW:
- `backend/v9/systems/woodies/hfe_divergence_logger.py`
- `tests/v9/systems/test_hfe_divergence.py`

MODIFY:
- `patterns/hfe.py` — minor · log divergence whenever DLL says HFE_detected=true but Python fallback disagrees (or vice versa) · log at WARNING level rate-limited.

FORBIDDEN — do not change DLL detection threshold values; do not change Python lookback window.

**Tests:** divergence detection (DLL=True, Python=False · DLL=False, Python=True · agreement cases · DLL field missing → fallback kicks in).

---

### §6.6 · W-5 · ZLR fixtures audit + 39 test repair (BLOCKED on P-W3)

**Status:** STOP at top.

```text
STOP — blocked on P-W3 · need Michael decision before this package can run.

Question: 39 ZLR test failures (Master Index 16/5) — root cause = fixture bug
or detector bug?

Researcher hypothesis (D-092 §P-W3 + Caveats #7): fixtures declared BLUE state
without a >+200 touch in their lookback. Liran's Stage-1 requires ≥6 bars above
ZL with ≥1 bar past +100 (ideally >+200). If the fixtures violate this, the
detector's correct refusal to fire was logged as a failure.

Required first step (audit before fix): CC reads
`backend/v9/tests/integration/fixtures/woodies_bar_sequences.py` and the 39
failing test bodies, classifies each as FIXTURE_BUG / DETECTOR_BUG /
SPEC_DRIFT, BEFORE proposing any code change.

Until locked, W-5 does NOT start.
```

**Drafted scope:**

WRITE NEW:
- `docs/reports/W5_ZLR_FAILURE_AUDIT.md` (must be produced and reviewed before any code/fixture changes)

MODIFY (after Michael approves audit):
- Either fixtures in `woodies_bar_sequences.py` (if FIXTURE_BUG) OR
- `patterns/zlr.py` (if DETECTOR_BUG)

NEVER both in the same commit · two PR-style commits split by root cause.

**Tests:** all 39 must pass post-fix · regression test added in a NEW
`tests/v9/systems/test_zlr_stage1_completeness.py` that fails ANY fixture
declaring BLUE without a >+200 touch (so the bug class is permanently caught).

---

### §6.7 · W-6 · 8 patterns refit (Day 5-8 · UNBLOCKED but deps W-1/W-2/W-3/W-7/W-8 · `~3 day CC`)

**Spec authority:** D-092 + Sheet A + Sheet C.

**Status if started before W-1/W-3/W-7 land:** dependencies block this from
running. Note in the prompt that this package executes ONLY after W-0+W-1+W-3+W-7
land (W-2, W-5, W-8 may still be P-W-blocked; the refit can proceed with
defaults until those land · CC must STOP at runtime if a missing dep is detected).

**SCOPE — wire each of 8 existing patterns to ATR-14 + Day-Type + Trend State + Anti-patterns + Targets:**

MODIFY:
- `patterns/zlr.py`
- `patterns/tlb.py`
- `patterns/tt.py`
- `patterns/gb100.py`
- `patterns/vegas.py`
- `patterns/ghost.py`
- `patterns/famir.py`
- `patterns/htlb.py`
- `pattern_engine.py` (orchestration)

NEW test per pattern: `tests/v9/systems/test_woodies_pattern_<name>_refit.py`

FORBIDDEN — do not modify `patterns/hfe.py` in this package (it's W-4 scope).

**Per-pattern checklist (each of 8):**
1. Import `atr_stop.compute_stop` and replace any hard-coded stop tick constant
2. Read pattern's day-type verdict via `DayTypeGate.get_verdict(pattern_id, day_type)` — if `❌`, return `PatternResult(detected=False, reason="day_type_block_X")`
3. Read trend state and gate per Sheet C §6.3 (BLUE/RED for CONT · BLOCK in NT)
4. Apply 9 anti-patterns from `anti_patterns.py` · short-circuit if any fires
5. Targets per Sheet A column "T1/T2/T3" exactly — CCI-scaffold or pattern-measure or R-multiples
6. Confidence formula → emit via `normalize_confidence()` (provided by W-8 once unblocked; until then patterns emit raw float and a TODO is logged · CC must add a "TODO::W-8" inline)

**Golden tests:** per-pattern · ≥3 happy path + ≥3 anti-pattern-blocks + ≥2 day-type-block · 8 patterns × 8 tests = 64 tests minimum.

---

### §6.8 · W-7 · Anti-patterns module (Day 3 · UNBLOCKED · `~1 day CC`)

**Spec authority:** D-092 §9 Anti-patterns + Sheet C §6.5.

**SCOPE — single new module + 9 unit gates:**

WRITE NEW:
- `backend/v9/systems/woodies/anti_patterns.py`
- `tests/v9/systems/test_anti_patterns.py`

**Required API:**

```python
class AntiPatternGate:
    def check(
        self,
        pattern_id: PatternId,
        context: PatternContext,  # bars, cci, day_type, trend_state, etc.
    ) -> AntiPatternResult:
        """Returns AntiPatternResult(blocked: bool, rule_id: Optional[str], reason: str)."""
```

**9 gates verbatim from Sheet C §6.5:**
- AP1: ZLR after >12-bar pullback (Rensink)
- AP2: GB100 in YELLOW state (Wood)
- AP3: VEGAS without 5+ bars between swings (Liran)
- AP4: HTLB with <2 touches
- AP5: HFE without bars_since_extreme ∈ [2, 12]
- AP6: GB100 with >6 bars opposite ZL during pullback (Liran)
- AP7: TT with TCCI gap < 5 CCI units (Rensink)
- AP8: Any pattern when CCI flat (range < 50) ≥3 bars (Raschke)
- AP9: FAMIR without LSMA agreement (Wood + Liran)

**One unit test per AP (positive + negative case · 18 tests minimum).**

FORBIDDEN — do not call patterns from this module; this is a pure rule library
queried BY patterns in W-6.

---

### §6.9 · W-8 · Dispatcher + Confidence + YAML (BLOCKED on P-W6 + P-W8 + P-W9)

**Status:** STOP at top.

```text
STOP — blocked on P-W6 + P-W8 + P-W9 · need Michael decisions before this
package can run.

Questions:
- P-W6: priority when 2 patterns fire same bar — max(confidence) plain, or
        DTV1-spec hierarchical (same-dir max conf · opposite-dir Stage-1
        tiebreak · CONT wins BLUE/RED)?
- P-W8: confidence normalization — none, z-score, min-max, or per-pattern
        multiplier? (Mixing 5 dynamic vs 4 fixed today creates dispatcher bias.)
- P-W9: YAML schema for thresholds — V1 static or YAML-driven · current
        defaults locked as "Liran baseline" profile?

Researcher recs (D-092):
- P-W6: DTV1-spec hierarchical
- P-W8: YES normalize all-9 to [0,1] via z-score or min-max
- P-W9: YAML-driven loader · current defaults locked as "Liran baseline"

Until locked, W-8 does NOT start.
```

**Drafted scope:**

MODIFY:
- `dispatcher.py` — switch from raw-max to hierarchical rule
- `yaml_loader.py` — extend to load per-pattern thresholds from a new profile schema

WRITE NEW:
- `backend/v9/systems/woodies/confidence_normalizer.py`
- `backend/v9/systems/woodies/config/thresholds_liran_baseline.yaml`
- `tests/v9/systems/test_dispatcher_hierarchy.py`
- `tests/v9/systems/test_confidence_normalize.py`

**Tests:** dispatcher cases · same-direction (max wins) · opposite-direction
(Stage-1 BLUE → CONT wins · GRAY → tiebreak rule) · normalization (verify all
9 patterns produce comparable [0,1] confidences from raw inputs at different
scales).

---

### §6.10 · W-9 · S4 TradeManager hooks (FINAL · UNBLOCKED but deps Pipeline 1 Pkg 6 · `~1.5 day CC`)

**Spec authority:** D-092 §Target Strategy + Pipeline V2 §5 (Pkg 6 hook architecture).

**Status:** depends on S2 Pkg 6 (TradeManager rewrite) being landed. Pkg 6 is
"NEXT" per the status board — verify before starting · STOP if Pkg 6 RiskRule
interface not yet committed.

**SCOPE — add S4-specific RiskRule subclasses:**

WRITE NEW:
- `backend/v9/systems/woodies/risk_rules/liran_exit_ladder.py` (LiranExitLadderRule)
- `backend/v9/systems/woodies/risk_rules/__init__.py`
- `tests/v9/systems/test_liran_exit_ladder.py`

MODIFY:
- `execution_bridge.py` — register the new RiskRule with TradeManager via existing public API · zero changes to TradeManager core (per D-067 Hybrid Architecture).
- `woodies_system.py` — instantiate the rule and pass to bridge.

FORBIDDEN — do NOT modify `backend/v9/systems/five_min/trade_manager*` (or
wherever Pkg 6's `TradeManager` lives) · the entire point of Pkg 6 is that S4
adds hooks without touching it.

**LiranExitLadderRule logic (verbatim from Sheet C §6.2 Liran's exit ladder):**

```
T1 = 4T (or 5T if net-vol confirms)
→ ±200 cross opposite (close 1)
→ ±100 cross opposite (close 1)
→ ZL cross opposite (close all)
→ SWI turns red (close all)
→ contradicting/new-trend pattern fires (close all)
→ CCI-14 flat ≥3 bars (close all)
→ TCCI crosses CCI-14 against (trail to last-bar low/high)
```

**Memorial Day §5 lessons applied here:**
- The rule must subscribe to bar events via a REAL `BarEvent` (NOT a FakeEvent
  mock). CC's report must include a live Python repro that imports the real
  TradeManager rules registry and proves a `LiranExitLadderRule` instance is
  registered and `evaluate()` is called when a real bar arrives.
- Before adding any `event.payload[...]` access in the rule, CC must Read the
  `BarEvent` dataclass and quote line numbers in the self-report.

**Tests:** golden trades through each rung of the ladder · ≥12 cases (8 rungs × 1-2 entry scenarios).

---

## §7 · Per-prompt deliverable format (you must produce 10 of these)

Each of your 10 mega-prompts must be a separate markdown file at:

```
docs/handoff/MEGA_PROMPT_PIPELINE_2_W-0.md
docs/handoff/MEGA_PROMPT_PIPELINE_2_W-1.md
docs/handoff/MEGA_PROMPT_PIPELINE_2_W-2.md   [skeleton + STOP]
docs/handoff/MEGA_PROMPT_PIPELINE_2_W-3.md
docs/handoff/MEGA_PROMPT_PIPELINE_2_W-4.md   [skeleton + STOP]
docs/handoff/MEGA_PROMPT_PIPELINE_2_W-5.md   [skeleton + STOP]
docs/handoff/MEGA_PROMPT_PIPELINE_2_W-6.md
docs/handoff/MEGA_PROMPT_PIPELINE_2_W-7.md
docs/handoff/MEGA_PROMPT_PIPELINE_2_W-8.md   [skeleton + STOP]
docs/handoff/MEGA_PROMPT_PIPELINE_2_W-9.md
```

Plus one index file:

```
docs/handoff/MEGA_PROMPT_PIPELINE_2_INDEX.md
```

The index must contain:
- Table of all 10 packages with: name · status (READY / BLOCKED) · P-W blockers · dependency chain · estimated CC days · expected commit prefix (e.g., `feat(woodies): W-1 ATR-14 stop engine`)
- Recommended execution order (a DAG flattened to a linear sequence respecting deps)
- G3 review checklist for Cursor (per-package adversarial review hooks)

Each individual `MEGA_PROMPT_PIPELINE_2_W-X.md` file MUST follow
`docs/templates/MEGA_PROMPT_TEMPLATE.md` exactly:

1. **Spec authority** (verbatim quotes from D-092 / Sheets / DTV1 with section refs)
2. **Existing code** (paths CC must Read + inline snippets if a quote is referenced)
3. **SCOPE** (WRITE NEW + MODIFY + FORBIDDEN with line ranges)
4. **Golden tests** (≥15 named, with input fixture pointers · numeric expectations from spec)
5. **Allowed imports** (whitelist)
6. **Acceptance criteria** (pytest + ReadLints + rg grep checks)
7. **Constraints** (no silent excepts · §5 lessons · no while-I'm-here · no new deps)
8. **Deliverable format** (files changed · commit msg conventional commits · self-report · pytest tail · live-repro for any wiring)
9. **Stop signal** (when CC should halt and ask Cursor)

---

## §8 · Output style guidance

- Markdown for each prompt · CC-readable · self-contained · single-shot.
- Quote D-092 / Sheets / DTV1 verbatim where you cite — never paraphrase a
  locked spec.
- Use code blocks for code references; do NOT use line numbers inside the
  block content.
- Add a header to each prompt: `# MEGA PROMPT · Package W-X · <Name>` + a
  one-line "produced by Claude Desktop · {date} · for CC · reviewed by Cursor".
- For BLOCKED packages, the STOP signal must be the FIRST section of the body
  (above Spec authority) so CC sees it before reading anything else.

---

## §9 · STOP signal for YOU (Claude Desktop)

Stop and report back to Cursor/Michael (not CC) if any of these:

- A required attachment from §3 is missing
- A spec citation produces an internal contradiction (e.g., D-092 vs Sheet A
  disagree on a number) — flag the contradiction; do NOT pick a side
- A required golden test fixture is impossible to construct from the spec
  alone (CC will need Michael to supply data)
- A FORBIDDEN file appears unavoidable to modify for a given package — flag
  and ask before drafting
- You are tempted to cite a P-W answer that is still 🟡 OPEN — output `STOP`
  in the prompt body and quote the researcher's recommendation only

Do NOT silently leave a `TODO: ask Michael` in any prompt body. Either the
prompt is COMPLETE and ready for CC, or it is STOP-signaled at the top with
the exact question for Michael.

---

## §10 · Quick reference · what Cursor will check at G3 review

When CC returns each package's output, Cursor will:

1. Verify every claim in CC's self-report against the actual diff (no
   "reports green without diff evidence" · §5 lessons)
2. Run the live Python repro from the report (for any wiring change)
3. Run `pytest tests/v9/systems/ -q` (or scoped path) and confirm GREEN
4. Run `ReadLints` on the changed files · confirm zero new warnings
5. Adversarial scan for:
   - silent excepts (any `except: pass` or `logger.debug` on a failure path)
   - hardcoded constants (D-092 numbers must reference YAML/config)
   - dead-code wiring (subscribe-but-never-called · §5 #1)
   - mock-vs-real-event mismatch (§5 #2)
   - while-I'm-here refactors outside SCOPE
   - mass-rewrite of EXISTS code where ADAPT was sufficient
6. UAT 4 axes if the package touches a live endpoint (Quality / Recency /
   Cardinality / Latency)
7. Cross-check `docs/spec_authority/` files were not modified (those are
   LOCKED · only D-XXX changes them)

Each mega-prompt should make Cursor's G3 job easier by including the exact
adversarial checks CC must pass IN ADVANCE so CC self-checks before submitting.

---

## §11 · Final sanity check before you start drafting

Before writing W-0 mega-prompt, confirm to the user (Michael) that you have:

- [ ] All 11 attachments from §3 (or list missing)
- [ ] Understood the §5 lessons (live-repro · payload-vs-data)
- [ ] Read the §4 audit findings
- [ ] Understood the P-W blocker policy in §5 (skeleton + STOP)
- [ ] Will produce 10 files + 1 index per §7

If any uncertainty, ask BEFORE drafting. Drafting based on a partial
understanding wastes a CC pass.

---

**End of META-PROMPT · Cursor agent · 2026-05-25 21:30 IL**

*After Claude Desktop returns the 10 mega-prompts + index, Cursor will G3-review
the meta-package as a whole (consistency · spec verbatim · §5 traps) before
Michael hands them to CC one at a time per the dependency order in the index.*
