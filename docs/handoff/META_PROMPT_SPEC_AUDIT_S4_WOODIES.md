# META-PROMPT · SPEC AUDIT · S4 Woodies CCI System
**Version:** 1.0 · 2026-05-27
**For:** Claude Desktop → send to Claude Code (CC)
**Owner audit:** Cursor (verifies CC report)
**Scope:** System 4 — Woodies CCI full spec-compliance audit

---

## CONTEXT

Pipeline 2 (S4 Woodies CCI) was declared G3-PASS on 2026-05-27 with 9/10 packages
locked (W-9 deferred to Pipeline 3) and W-10 Time Stop wired by Cursor.

Before going LIVE, we need a comprehensive audit confirming **every filter, gate,
and spec rule is actually active in the running code** — not just present as a stub.

The audit spec authority is:
- `docs/spec_authority/S4_WOODIES_TABLE_B_DayType_Matrix.csv` (day-type matrix)
- `docs/MEMS26_WOODIES_DECISION_TREE_V1.md` (decision tree 21 stages)
- `docs/decisions/D-092_S4_WOODIES_UPDATE.md` (pattern specs)
- `docs/plans/STATUS_BOARD.md` (current locked package list)

---

## YOUR TASK (CC)

Run the following 8 checks **in order**. For each check: read the actual code,
run pytest tests if relevant, query the DB. Report PASS / FAIL / WARN for each.

---

### CHECK 1 · A1 YELLOW Gate (F-16 fix)

**Spec:** When `trend_state == YELLOW`, ALL 9 patterns must be suppressed BEFORE
reaching the dispatcher. The dispatcher must never see YELLOW.

**Verify:**
```bash
rg "YELLOW" backend/v9/systems/woodies/woodies_system.py -A 3
rg "YELLOW" backend/v9/systems/woodies/pattern_dispatcher.py -A 3
```
Expected: `woodies_system.py` has an explicit `if _ts == TrendState.YELLOW: patterns = []`
guard BEFORE calling `_pattern_dispatcher.select_winner()`.
Pattern dispatcher should still have `raise ValueError` as its own assertion.

**PASS criteria:** Guard exists in `process_bar()` before dispatcher call. Dispatcher's
`ValueError` is a safety net only — YELLOW never reaches it in normal flow.

---

### CHECK 2 · Anti-Patterns AP1–AP9 Active

**Spec:** All 9 anti-patterns must BLOCK entry when triggered. AP5 is in `hfe.py`.

**Verify:**
```bash
# Check anti_patterns.py has all 8 methods (AP5 excluded from this file)
rg "def check_ap" backend/v9/systems/woodies/anti_patterns.py
# Check AP5 lives in hfe.py
rg "AP5\|anti_pattern" backend/v9/systems/woodies/patterns/hfe.py
# Check detect_all_patterns actually calls anti-pattern checks
rg "AntiPatternChecker\|anti_pattern\|check_ap" backend/v9/systems/woodies/pattern_engine.py
```

**Critical check:** Does a BLOCKED anti-pattern actually **prevent** the pattern from
being added to the detected list? Or does it only log? Read `pattern_engine.py` logic.

**PASS criteria:** `detect_all_patterns()` returns an empty or excluded result for
any pattern where the relevant AP check returns `blocked=True`.

---

### CHECK 3 · W-8 Two-Tier R_t1 Dispatcher

**Spec (D-092):**
- BLUE/RED trend → prefer CONT family (ZLR, TLB, TT, GB100) by max(R_t1)
- GRAY trend → best R_t1 across all families
- `min_r_t1_threshold` config option (currently 0.0 — acceptable for shadow)

**Verify:**
```bash
python -c "
from backend.v9.systems.woodies.pattern_dispatcher import PatternDispatcher
d = PatternDispatcher()
print('config:', d.config)
print('source:', d.config_source)
"
cat backend/v9/systems/woodies/config/dispatcher_config.yaml
```

**PASS criteria:**
- Config loads from YAML (not Python default)
- `log_dispatch_decisions` is True (so we can see routing in logs during shadow)

**WARN criteria:** `min_r_t1_threshold == 0.0` is acceptable for shadow but note as
PENDING for LIVE (should be ≥ 0.5 per Liran's guidance once confirmed).

---

### CHECK 4 · Day-Type Matrix — Advisory vs. Blocking

**Spec:** The day-type matrix is **advisory only** (D-092). A ❌ verdict should NOT
block entry — it should log a WARNING but allow the trade.

**Verify:**
```bash
rg "DayTypeGate\|day_type_gate\|MatrixVerdict\|verdict" backend/v9/systems/woodies/ -r
```

**Critical question:** Is `day_type_gate` being called at all in `woodies_system.py`
or `decision_tree.py`? If it's not called, is that intentional per spec?

Check `decision_tree.py` evaluate_bar() — does it reference DayTypeGate?

**PASS criteria:** Either (a) gate is called and verdict is advisory/logged only,
or (b) gate is not called and spec explicitly allows this for Pipeline 2 scope.

---

### CHECK 5 · Time Stop W-10 Wiring

**Spec (Registry #11):** Every open shadow trade must be tracked. After
`time_stop_minutes` (default 90) / `tick_minutes` (default 5) = 18 bars,
the trade is forcibly closed via `trade_manager.close_trade()`.

**Verify:**
```bash
python -m pytest tests/v9/systems/test_time_stop.py -v --tb=short 2>&1 | tail -40
```

Also check wiring:
```bash
rg "_open_fire_records\|_check_time_stops\|TimeStopEnforcer" \
    backend/v9/systems/woodies/woodies_system.py
```

**PASS criteria:** All time_stop tests pass. `_open_fire_records` is populated on
shadow fire. `_check_time_stops()` is called every bar in `process_bar()`.

---

### CHECK 6 · Session / RTH Filter

**Spec:** Woodies CCI operates on 5-min bars during RTH session.
**Verify whether** `process_bar` has any session gating (RTH-only check).

```bash
rg "RTH\|session\|SessionClassifier\|session_classifier" \
    backend/v9/systems/woodies/woodies_system.py
```

If NO session filter exists, this is a **WARN** (not FAIL) for shadow, but a
**BLOCKER for LIVE** — we must not fire on overnight bars.

**PASS criteria:** RTH filter present and active.
**FAIL criteria (LIVE blocker):** No session gate at all.

---

### CHECK 7 · Dedup Gate

**Spec:** Sierra sends multiple UPDATE events per 5-min bar as it builds.
Each update must NOT fire a new shadow trade for the same bar.

**Verify:**
```bash
rg "_last_fired_bar_ts" backend/v9/systems/woodies/woodies_system.py -A 5
```

Expected: key = `"{pattern_id}_{direction}"`, value = `bar_ts`.
New fire is skipped if `float(bar_ts) <= _last_ts`.

**PASS criteria:** Dedup gate present and uses `<=` comparison (not `<`).

---

### CHECK 8 · Full pytest suite

```bash
cd /Users/michael/Downloads/mems26_web_git
python -m pytest tests/v9/systems/ -q --tb=short 2>&1 | tail -50
```

**PASS criteria:** All passing before today still pass. No new failures.

---

## REPORT FORMAT

Return a report with:

```
## S4 Woodies CCI — Spec Audit Results · [DATE]

| Check | Title | Result | Notes |
|-------|-------|--------|-------|
| 1 | A1 YELLOW Gate | ✅ PASS / ⚠️ WARN / ❌ FAIL | ... |
| 2 | AP1-9 Active | ... | ... |
| 3 | W-8 Dispatcher | ... | ... |
| 4 | Day-Type Advisory | ... | ... |
| 5 | Time Stop W-10 | ... | ... |
| 6 | RTH Session Filter | ... | ... |
| 7 | Dedup Gate | ... | ... |
| 8 | pytest suite | ... | ... |

## Findings requiring Cursor action:
[List only FAILs and LIVe-blocking WARNs]

## Shadow GREEN / RED verdict:
[One line: safe to run shadow? Y/N + why]
```

---

## STOP SIGNALS

Stop and ask Michael before proceeding if:
- Any check reveals a LIVE trade could fire without RTH gating (Check 6)
- Anti-pattern results are being ignored / only logged (Check 2)
- Time stop is not removing trades from `_open_fire_records` (Check 5)
