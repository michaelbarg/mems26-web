# META-PROMPT · SPEC AUDIT · S1 Day Type System
**Version:** 1.0 · 2026-05-27
**For:** Claude Desktop → send to Claude Code (CC)
**Owner audit:** Cursor (verifies CC report)
**Scope:** System 1 — Day Type state machine + classification publishing

---

## CONTEXT

S1 Day Type classifies the current trading day into one of 7 Dalton types:
`TN · TDD · NV · NeuE · NeuC · Norm · NT`

This classification is the **upstream dependency** for both S2 and S4.
If S1 is wrong, all downstream trading decisions are wrong.

Spec authority:
- `backend/v9/systems/day_type/state_machine.py` — 13-stage machine (canonical)
- `backend/v9/systems/day_type/zohar_rules.py` — ZoharRulesEngine
- `backend/v9/systems/day_type/decision_matrix.py` — DECISION_MATRIX
- `docs/spec_authority/S2_AUTH_TABLE_V1.md §3` — day type → enum mapping

---

## YOUR TASK (CC)

Run the following 5 checks. Report PASS/FAIL/WARN for each.

---

### CHECK 1 · All 7 Day Types Classified

**Spec:** The state machine must be capable of producing all 7 types.
Verify the `DayType` enum and decision matrix cover all 7.

```bash
python -c "
from backend.v9.systems.day_type.schemas import DayType
print([d.value for d in DayType])
"
```

Expected output includes: `Trend_Normal, Trend_DD, Variation, Neutral_Extreme,
Neutral_Center, Normal, Nontrend`

**PASS criteria:** All 7 types present in enum.

---

### CHECK 2 · State Machine Transitions

**Spec:** The 13-stage machine (A1→C3) must process a bar and eventually
lock a classification.

```bash
python -c "
from backend.v9.systems.day_type.state_machine import DayTypeStateMachine
from backend.v9.systems.day_type.schemas import BarInput, PreOpenContext
sm = DayTypeStateMachine()
print('State machine created OK, stage:', sm.stage if hasattr(sm, 'stage') else 'N/A')
"
```

Also run:
```bash
python -m pytest tests/v9/systems/day_type/ -q --tb=short 2>&1 | tail -30
```

**PASS criteria:** State machine instantiates cleanly. Tests pass.

---

### CHECK 3 · ZoharRulesEngine Active

**Spec:** ZoharRules override day-type classifications in specific conditions
(e.g. NeuE inside-VA opener → downgrade classification).

```bash
rg "ZoharRulesEngine\|zohar_rules\|RuleVerdict" \
    backend/v9/systems/day_type/state_machine.py -A 3 | head -30
```

**PASS criteria:** `ZoharRulesEngine` is called within `state_machine.py`
and its verdict modifies the classification output.

**WARN:** If Zohar rules are instantiated but never called, flag as PENDING.

---

### CHECK 4 · Classification Published to Event Bus

**Spec:** After locking a classification, S1 must publish
`mems26:events:system.day_type.classification` so S2 and S4 can consume it.

```bash
rg "day_type.classification\|publish.*day_type\|emit.*day_type" \
    backend/v9/ -r | head -20
```

Also check who consumes it:
```bash
rg "day_type.classification\|current_day_type" \
    backend/v9/systems/ -r | head -20
```

**PASS criteria:** S1 publishes the event. S2 (`five_min_system.py`) subscribes
and updates `current_day_type`. S4 (Woodies) either subscribes or queries S1.

---

### CHECK 5 · NT → NO_TRADE broadcast

**Spec:** When day type is NT, a global NO_TRADE signal must propagate.
Verify this is either broadcast or that all consuming systems check for NT.

```bash
rg "Nontrend\|NT\b\|no_trade\|NO_TRADE" \
    backend/v9/systems/ -r | grep -v "test_" | head -30
```

**PASS criteria:** NT state is handled explicitly downstream (S2 guard confirmed
in S2 audit, S4 advisory confirmed in S4 audit).

---

## REPORT FORMAT

```
## S1 Day Type — Spec Audit Results · [DATE]

| Check | Title | Result | Notes |
|-------|-------|--------|-------|
| 1 | 7 Day Types Classified | ✅ / ⚠️ / ❌ | ... |
| 2 | State Machine Transitions | ... | ... |
| 3 | ZoharRules Active | ... | ... |
| 4 | Classification Published | ... | ... |
| 5 | NT → NO_TRADE | ... | ... |

## Downstream dependencies confirmed:
- S2 consumes S1: YES / NO
- S4 consumes S1: YES / NO

## Shadow GREEN / RED verdict:
[Safe? Y/N + reason]
```

---

## STOP SIGNALS

Stop immediately if:
- Day type classification is NOT published to event bus (Check 4 FAIL)
- NT does NOT reach S2 or S4 as a trade-blocking signal
- State machine is producing wrong classifications (run a quick sanity test)
