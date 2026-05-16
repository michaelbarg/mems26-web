# Spec Compliance — COMMIT 3.1 (Priority Hierarchy Dispatcher)

## Dispatcher — Priority Hierarchy
Spec source: Decision Tree V1 (Drive 1nuLAh8T...) § Section 1 Core Principles

Spec items:
- ✅ 9 priority classes defined → `dispatcher.py:17-25` (PriorityClass IntEnum)
- ✅ ABSOLUTE_EXIT highest (1) → `dispatcher.py:18`
- ✅ NO_ACTION lowest (9) → `dispatcher.py:25`
- ✅ Order: ABSOLUTE > STRATEGIC > ADVISORY > TIME > TARGET > TIGHTEN > PARTIAL > TRAIL > NO_ACTION → `test_dispatcher.py:145-152`
- ✅ Within same class, YAML order determines → `dispatcher.py:67` (sort by yaml_order)
- ✅ Highest-priority action wins → `dispatcher.py:69` (triggered[0] after sort)
- ✅ No other stage triggered → default HOLD → `dispatcher.py:57-63`
- ✅ Binary decisions only (no scoring) → no confidence/score fields in StageOutput

Terminal states emitted: N/A (dispatcher resolves, doesn't emit terminals)
Inputs schema: ✅ List[StageOutput] with priority_class + action + triggered + yaml_order
Outputs schema: ✅ DispatchResult with winning_stage + winning_action + winning_priority

Status: 8/8 ✅ · 0 deferred · 0 missing
