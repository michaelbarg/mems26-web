# MEGA Prompt Template — לCC

**Owner:** Claude Desktop כותב פר-package
**Consumer:** Claude Code (CC) executes
**Reviewer:** Cursor verifies output ב-G3

---

## 7 שדות חובה + Stop signal

```text
# MEGA PROMPT · Package <N> · <Name>

## Spec authority (verbatim, locked)
- D-091 §<section> — quoted verbatim, no paraphrase
- Auth Table V1 §<section> — quoted verbatim
- Bulkowski reference (if applicable): example #<num>, throwback %<num>

## Existing code (read-only · do NOT modify outside SCOPE)
- backend/v9/systems/five_min/<file>.py (attached below)
- tests/v9/systems/test_five_min/<file>.py (attached below)
[paste actual file contents inline]

## SCOPE — exactly these files
WRITE NEW:
  - backend/v9/systems/five_min/<new>.py
  - tests/v9/systems/test_five_min/<new>.py
MODIFY EXISTING (lines specified):
  - backend/v9/systems/five_min/<existing>.py · lines X-Y only
FORBIDDEN — do NOT touch:
  - backend/v9/systems/footprint/
  - backend/v9/systems/woodies/
  - backend/v9/systems/day_type/
  - frontend/
  - bridge/
  - sc_study/

## Golden tests (must pass · minimum N=15)

1. test_<canonical_case_1>: input=<fixture path or inline> → expect entry=X stop=Y T1=Z T2=W confidence=C
2. test_<canonical_case_2>: ...
3. test_<edge_case_no_detection>: input=<fixture> → expect detected=False
...
15+. cover: 4 directions × 3 day_types × edge cases

## Allowed imports (whitelist)
- from typing import ...
- from datetime import ...
- import logging
- from backend.v9.systems.five_min.<existing modules> import ...
- from backend.v9.shared.pre_fire_validator import ...
[NO imports outside this list. Hallucinated APIs = retry]

## Acceptance criteria
- `pytest tests/v9/systems/test_five_min/ -q` → all green
- `rg "<forbidden_pattern>" backend/v9/systems/five_min/` → 0 hits (if relevant)
- ReadLints clean (no new linter errors)
- All N golden tests pass

## Constraints (must not violate)
- No silent excepts. Every `except` must include `logger.warning("[<context>] <message>", ...)` rate-limited
- No `return None` without prior log
- No new dependencies (pip install / package.json)
- No "while I'm here" refactors — strict scope
- Hardcoded values forbidden — must be config constants at top of file
- T3 stays 0.0 if day-type T3 not yet implemented in dependent package
- No async I/O in `process_bar` event loop (use injected helpers)

## Deliverable format
After completion, output:
1. List of files changed (full paths · A/M/D)
2. Commit message (single line · conventional commits format)
3. Self-report:
   - Any TODOs left in code? (must be empty)
   - Any spec ambiguity encountered? (list explicitly)
   - Any forbidden constraint accidentally violated? (own up)
4. ReadLints output (paste verbatim)
5. pytest output (paste verbatim · tail 30 lines)

## Stop signal
IF any of these conditions met, STOP and report:
- Spec is ambiguous and you cannot resolve from sources cited above
- A golden test fixture is impossible to construct from input shape
- An "allowed import" doesn't exist in the codebase
- A forbidden file appears in your edit list

DO NOT guess. DO NOT add a comment "TODO: ask Michael". STOP and output STOP signal:
"STOP — <reason> · need Michael decision on <specific question>"
```

---

## דוגמה — Package 0 (Path B deletion)

```text
# MEGA PROMPT · Package 0 · Path B Deletion

## Spec authority
- D-090 §"Path A = canonical · Path B = deleted"
- D-090 §"Sync actions required (post-D-090)" — 6 actions

## Existing code (read-only)
- backend/v9/systems/chart_5min/ (entire directory — to be deleted)
- backend/v9/app.py (search for chart_5min imports)
- backend/v9/systems/__init__.py (search for chart_5min)
- tests/v9/systems/ (search for test_chart_5min directory)

## SCOPE
DELETE:
  - backend/v9/systems/chart_5min/ (entire directory)
MODIFY (lines to remove if found):
  - backend/v9/app.py · remove chart_5min imports
  - backend/v9/systems/__init__.py · remove chart_5min exports if present
DELETE TESTS:
  - tests/v9/systems/test_chart_5min/ if exists

FORBIDDEN — do NOT touch:
  - backend/v9/systems/five_min/ (the keeper · Path A)
  - any non-chart_5min file

## Allowed imports
[N/A · deletion only]

## Acceptance criteria
- `rg "chart_5min" backend/ tests/` → 0 hits
- `rg "Chart5MinSystem" backend/ tests/` → 0 hits
- `rg "Chart5MinDetector" backend/ tests/` → 0 hits
- `pytest tests/v9/ -q` → all green (no test removed unintentionally)
- ReadLints clean

## Constraints
- No new files created
- No "while I'm here" refactors outside chart_5min removal
- App boot must remain functional (don't break import chain)

## Deliverable format
1. List of files deleted (full paths · D)
2. List of files modified (full paths · M · with diff lines)
3. Commit message: "chore(s2): delete Path B chart_5min per D-090"
4. rg outputs (chart_5min/Chart5MinSystem/Chart5MinDetector) — paste 0-hit confirmation
5. pytest output tail

## Stop signal
IF `chart_5min` imports are found in production paths beyond app.py and __init__.py — STOP and report which file + which usage.
```

---

## הערות לClaude Desktop

1. **לא לפראפרז את ה-spec** — copy-paste verbatim מ-D-XXX
2. **לצרף inline את הקבצים הרלוונטיים** — לא רק paths · CC לא יכול לקרוא ללא attachment
3. **Golden tests חייבים מספרים אמיתיים** — לא placeholders. אם אין fixtures מוכנים — צריך לבקש מ-Michael
4. **Stop signal הוא חוק ברזל** — pre-LIVE protocol "no silent failures"

---

*End of template · גרסה V1 · 2026-05-23 16:30 IL*
