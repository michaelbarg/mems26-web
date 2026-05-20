# Sierra Study Data Protocol — MANDATORY

**Date:** 2026-05-20
**Status:** ACTIVE — applies to ALL agents (Cursor, Claude Code, Cloud)
**Authority:** Michael Barg (system owner)

---

## RULE #1: Sierra Is The Single Source of Truth

ALL Woodies CCI and TPO indicator values MUST come from Sierra Chart native studies via `GetStudyArrayFromChartUsingID`. **Never** compute these values independently when Sierra data is available.

**Why:** Independent computation drifts from Sierra's display. The trader makes decisions based on what Sierra shows. Any discrepancy between the cockpit and Sierra is a trading risk.

### Protected Values (Sierra-sourced)

| Value | Sierra Study ID | Subgraph | Notes |
|-------|----------------|----------|-------|
| CCI-14 | 4 | SG0 | Main CCI |
| CCI-6 (TCCI) | 10 | SG0 | Turbo CCI |
| EMA-34 | 3 | SG0 | Woodies EMA |
| LSMA-25 | 2 | SG0 | Linear Regression MA |
| Sidewinder | 6 | **SG5** | NOT SG0 (SG0=±200 ref line) |
| ChopZone | 7 | **SG2** | NOT SG0 (SG0=±100 ref line) |
| ProjHigh | 9 (Woodies Panel) | **SG1** | NOT from Pivot Points study |
| ProjLow | 9 (Woodies Panel) | **SG2** | NOT from Pivot Points study |
| CCIDiff | computed | CCI14 - CCI6 | From Sierra CCI values |
| Y-POC | TPO Study (ID set in input) | SG0 | Yesterday session |
| Y-VAH | TPO Study (ID set in input) | SG1 | Yesterday session |
| Y-VAL | TPO Study (ID set in input) | SG2 | Yesterday session |
| Today POC | TPO Study (ID set in input) | SG0 | Developing session |
| Today VAH | TPO Study (ID set in input) | SG1 | Developing session |
| Today VAL | TPO Study (ID set in input) | SG2 | Developing session |

### Chart Numbers (configured in DLL study inputs)

| Input | Current Value | Purpose |
|-------|--------------|---------|
| Woodies Chart Number | 12 | Chart with all Woodies studies |
| TPO Chart Number | (set per session) | Chart with TPO Value Area Lines |

---

## RULE #2: No Changes Without Approval

Any change to the following requires **explicit approval from Michael**:

1. **Study IDs or Subgraph indices** — changing which Sierra study/SG we read from
2. **Computed fallback logic** — changing when/how we fall back from Sierra to computed values
3. **DLL export fields** — adding, removing, or renaming JSON fields in the export
4. **Indicator formulas** — changing how CCIDiff, predictor, trend state etc. are calculated
5. **Time boundaries** — changing RTH (09:30-16:00 ET) or Globex (18:00 ET) windows
6. **TPO line behavior** — colors, styles, time ranges, visibility rules

### What Agents CAN Do Without Approval

- Read existing Sierra values and display them
- Fix rendering bugs (CSS, SVG, chart library issues)
- Fix crashes, errors, hydration issues
- Add logging/diagnostics (temporary, must be removed after)
- Update documentation

---

## RULE #3: DLL Build Protocol

1. Edit modular files in `sc_study/` (NOT the merged file directly)
2. Run `bash scripts/build_monolithic_cpp.sh --deploy`
3. Also copy to `~/SierraChart2/ACS_Source/`
4. Sierra Remote Build compiles on **Windows** — use `localtime_s` not `localtime_r`
5. Headers are inlined by the monolith script — never raw `#include` in the `.cpp`
6. Two Sierra installations exist: `~/SierraChart/` and `~/SierraChart2/`

---

## RULE #4: Validation

- TPO prices: reject outside 3000-10000 (MES range)
- If Sierra returns 0 for a study value: keep computed fallback
- `sierra_source: true` in JSON = Sierra values active
- `va_ok: true` in TPO = Sierra has calculated valid value area

---

## Diagnostic Reference

To re-run the subgraph scan (if study IDs change):
1. Uncomment the diagnostic block in `MES_AI_DataExport.cpp` (search "DIAGNOSTIC")
2. Build + deploy
3. Read `woodies_diag.json` — shows SG0-SG15 for all 13 studies
4. Remove diagnostic after use

**Verified subgraph mapping date:** 2026-05-20
