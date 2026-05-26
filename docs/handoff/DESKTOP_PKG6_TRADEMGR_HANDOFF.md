# DESKTOP_PKG6_TRADEMGR_HANDOFF · Cursor → Claude Desktop → CC

**Date:** 2026-05-25 14:05 IL · **Owner draft:** Cursor · **Reviewer:** Michael Barg (Q9.1-Q9.4 approved 25/5 13:56)
**Authority for this handoff:** `docs/spec_authority/S2_TRADEMGR_HOOKS_V1.md` (🔒 LOCKED 25/5 13:57)
**Package:** Pkg 6 · TradeManager extensible (RiskRule registry) · **LAST Phase A package** (per D-095)
**Branch:** `stabilize/mems26-local-truth-2026-05-16` · HEAD `12edadc`
**Phase A status:** 13/15 done · Pkg 6 = 14th + LAST · 4a/4b stay deferred
**Estimated CC time:** ~3-4h (registry + 5 wrappers + TrailEngine refactor + 30+ tests)

---

## 0 · Cursor-Michael LOCKS (Q9.1-Q9.4 chat 25/5 13:56)

CC MUST treat these as authoritative on top of the spec doc.

| # | Lock | Where it matters |
|---|---|---|
| 1 | **Q9.1 · YES** · `register_rule` raises `ValueError` on duplicate `name` | `base.py` registry · pre-LIVE "no silent failures" |
| 2 | **Q9.2 · NO** · `Layer4Context` is `@dataclass(frozen=True)` only · no runtime type validation | `base.py` Layer4Context |
| 3 | **Q9.3 · YES + rate-limited** · `log_skipped_rule(rule_name, missing_field)` emits 1 warning per `(rule, field)` per 300s (`_SkipLogLimiter` in `base.py`) | 3 wrappers: CCIFlatRule (cci_history) · SWITightenRule (swi) · DayTypeTargetsVerifyRule (current_day_type) |
| 4 | **Q9.4 · Singleton** · `_REGISTRY` stores instances · `@register_rule(order=N)` registers once at import | `base.py` registry |
| 5 | **D-095 zero functional change** · all 5 layer4 services UNTOUCHED (zero diff) · refactor is pure architectural | `backend/v9/services/layer4/*.py` FORBIDDEN |
| 6 | **2 phases** · 4 rules `phase="PRE_TIGHTEN"` (order 1-4) · 1 rule `phase="POST_TIGHTEN"` (DAY_TYPE_TARGETS · order 5) · `_apply_tightest_stop` runs BETWEEN phases | `trail_engine.py::_apply_layer4` |
| 7 | **EXIT short-circuits ALL** · including `_apply_tightest_stop` + POST_TIGHTEN rules | matches current TCCI_CROSS behavior at `trail_engine.py:619-620` |
| 8 | **Rule.name → close_trade reason** · `self._tm.close_trade(trade.id, f"{rule.name}_AGAINST_TRADE")` · matches current `"TCCI_CROSS_AGAINST_TRADE"` literal at `trail_engine.py:619` | `trail_engine.py::_apply_layer4` |

---

## 1 · Spec authority (read this first)

**Single source of truth:** `docs/spec_authority/S2_TRADEMGR_HOOKS_V1.md` (LOCKED 25/5 13:57).

Read ALL of §1-§9 before writing code. Critical sections:

- §2.1 · `Layer4Context` dataclass shape (4 Optional fields)
- §2.2 · `RiskRule` ABC + `phase: Literal["PRE_TIGHTEN", "POST_TIGHTEN"]`
- §2.3 · `_SkipLogLimiter` + `log_skipped_rule` (Q9.3 rate-limited warnings)
- §2.4 · `register_rule(order=N)` decorator · MUST raise `ValueError` on duplicate name (Q9.1)
- §2.5 · The 5 wrapper rule classes (verbatim · names + phase + ctx field guards)
- §2.6 · `rules/__init__.py` auto-import order
- §3 · TrailEngine integration (target behavior · 2 phases + tightest_stop between)
- §6 · FORBIDDEN zones
- §8 · Q9.1-Q9.4 final decisions

**If the spec doc and this handoff disagree on any detail, the SPEC doc wins.** Flag the disagreement in §11 self-report.

---

## 2 · Existing code (read-only · do NOT modify · read to understand)

### 2.1 · `backend/v9/services/trail_engine.py` lines 546-644 (the target of the refactor)

The current `_apply_layer4(trade, bar, bar_ts)` method has 3 distinct phases:

**Phase A · PRE_TIGHTEN** (lines 591-631):
- 1. `mfe_peak_tighten.evaluate(trade_dict)` → TIGHTEN_STOP → `candidate_stops`
- 2. `cci_flat_tighten.evaluate(trade_dict, cci_history)` → TIGHTEN_STOP → `candidate_stops` (guarded by `cci_history and len(cci_history) >= 3`)
- 3. `tcci_cross_exit.evaluate(trade_dict, direction_change_event)` → EXIT → `close_trade + return` SHORT-CIRCUIT (guarded by `direction_change_event`)
- 4. `swi_tighten.evaluate(trade_dict, swi)` → TIGHTEN_STOP → `candidate_stops` (guarded by `swi and swi.get("value") is not None`)

**Phase B · _apply_tightest_stop** (lines 633-635):
- If `candidate_stops`: `self._apply_tightest_stop(trade, candidate_stops, bar_ts)`

**Phase C · POST_TIGHTEN** (lines 637-644):
- 5. `day_type_targets_verify.evaluate(trade_dict, current_day_type)` → `self._handle_day_type_action(trade, result, bar_ts)` (guarded by `current_day_type`)

Helpers CC must preserve (called from refactored method · NO CHANGES to these):
- `self._adapt_trade_for_layer4(trade, bar_close)` → trade_dict (line 567)
- `self._tm.is_fill_locked(trade.id)` early return (line 560)
- `self._woodies_provider()` → woodies_ctx (lines 571-575)
- `self._fetch_current_day_type()` → current_day_type (line 580)
- `self._append_cross_context(trade, {...})` (lines 613-618)
- `self._tm.close_trade(trade.id, reason)` (line 619)
- `self._apply_tightest_stop(trade, candidate_stops, bar_ts)` (lines 646-685) · DO NOT MODIFY
- `self._handle_day_type_action(trade, result, bar_ts)` (lines 687-728) · DO NOT MODIFY

CC reads this method end-to-end before writing the refactor. The target behavior is byte-identical externally (D-095 zero functional change).

### 2.2 · `backend/v9/services/layer4/*.py` (FROZEN · zero diff)

5 pure functions · current signatures:

```python
mfe_peak_tighten.evaluate(trade: Dict) -> Optional[Dict]
cci_flat_tighten.evaluate(trade: Dict, cci_history: List[float]) -> Optional[Dict]
tcci_cross_exit.evaluate(trade: Dict, direction_change_event: Optional[Dict]) -> Optional[Dict]
swi_tighten.evaluate(trade: Dict, swi: Dict) -> Optional[Dict]
day_type_targets_verify.evaluate(trade: Dict, current_day_type: str) -> Optional[Dict]
```

Wrappers in `rules/*.py` call these byte-identically (only routing context fields).

### 2.3 · `backend/v9/services/trade_manager/` (existing structure · do NOT touch outside `rules/`)

```
backend/v9/services/trade_manager/
├── manager.py          # TradeManager core · FORBIDDEN
├── state_machine.py    # FORBIDDEN
├── events.py           # FORBIDDEN
└── rules/              # NEW · the only allowed write target inside trade_manager/
```

---

## 3 · SCOPE — exactly these files

### WRITE NEW (8 files)

- `backend/v9/services/trade_manager/rules/__init__.py` (~18 LOC · exports + auto-import 5 rule modules)
- `backend/v9/services/trade_manager/rules/base.py` (~130 LOC · Layer4Context + RiskRule + registry + _SkipLogLimiter + log_skipped_rule)
- `backend/v9/services/trade_manager/rules/mfe_peak.py` (~10 LOC · order=1 · phase=PRE_TIGHTEN · no skip log)
- `backend/v9/services/trade_manager/rules/cci_flat.py` (~14 LOC · order=2 · phase=PRE_TIGHTEN · skip log on `cci_history`)
- `backend/v9/services/trade_manager/rules/tcci_cross.py` (~12 LOC · order=3 · phase=PRE_TIGHTEN · no skip log · layer4 handles None internally)
- `backend/v9/services/trade_manager/rules/swi.py` (~14 LOC · order=4 · phase=PRE_TIGHTEN · skip log on `swi`)
- `backend/v9/services/trade_manager/rules/day_type_targets.py` (~14 LOC · order=5 · phase=POST_TIGHTEN · skip log on `current_day_type`)
- `tests/v9/services/test_trade_manager/__init__.py` (empty marker)

### WRITE NEW TESTS (4 files)

- `tests/v9/services/test_trade_manager/test_layer4_context.py` (5 tests · §5.3 of spec)
- `tests/v9/services/test_trade_manager/test_rules_registry.py` (10 tests · §5.1)
- `tests/v9/services/test_trade_manager/test_rules_wrappers.py` (18 tests · §5.2 · includes 3 rate-limit log tests)
- `tests/v9/services/test_trade_manager/test_future_rule_stub.py` (3 tests · §5.4 · Risk #8 mandatory · cleanup MUST be idempotent)

### MODIFY (1 file · narrow change · `_apply_layer4` method only)

- `backend/v9/services/trail_engine.py` lines 546-644:
  - Replace the 5 hardcoded layer4 import + try/except blocks with:
    1. Build `ctx = Layer4Context(cci_history=..., direction_change_event=..., swi=swi_snapshot, current_day_type=current_day_type)` from `woodies_ctx` + `_fetch_current_day_type()`
    2. Loop 1 over `[r for r in get_registered_rules() if r.phase == "PRE_TIGHTEN"]`:
       - try/except → `logger.warning("[TrailEngine] %s.evaluate failed trade=%s: %s", rule.name, trade.id, exc)` · continue
       - if `result is None`: continue
       - if `result.get("action") == "EXIT"`: `_append_cross_context` + `close_trade(trade.id, f"{rule.name}_AGAINST_TRADE")` + `return` (short-circuit)
       - if `result.get("action") == "TIGHTEN_STOP"` and `new_stop is not None`: append to `candidate_stops`
    3. After loop: `if candidate_stops: self._apply_tightest_stop(trade, candidate_stops, bar_ts)`
    4. Loop 2 over `[r for r in get_registered_rules() if r.phase == "POST_TIGHTEN"]`:
       - try/except → `logger.warning(...)` · continue
       - if `result is None`: continue
       - `self._handle_day_type_action(trade, result, bar_ts)`
  - **DELETE** the 5 hardcoded import lines (`from backend.v9.services.layer4 import ...`) at lines 583-587
  - **ADD** one import at the top of trail_engine.py: `from backend.v9.services.trade_manager.rules import get_registered_rules, Layer4Context`

### FORBIDDEN — do NOT touch

```text
backend/v9/services/layer4/*.py                      # 5 layer4 services · D-095 zero diff
backend/v9/services/trade_manager/manager.py         # TradeManager core
backend/v9/services/trade_manager/state_machine.py
backend/v9/services/trade_manager/events.py
backend/v9/services/trail_engine.py LINES OUTSIDE 546-644 (including helpers _apply_tightest_stop · _handle_day_type_action · _adapt_trade_for_layer4 · _fetch_current_day_type · _move_stop_tighter_only · _append_cross_context)
backend/v9/systems/                                   # all subdirs · out of scope
backend/v9/db/                                        # no schema changes
frontend/ sc_study/ bridge/                          # out of scope
```

---

## 4 · Golden tests (must pass · minimum N=36)

### 4.1 · `test_layer4_context.py` (5 tests)

```text
test_layer4_context_default_all_None
test_layer4_context_accepts_all_fields
test_layer4_context_immutable_raises_on_mutation (FrozenInstanceError on setattr)
test_layer4_context_equality_by_value
test_layer4_context_extensible_new_field (forward-compat smoke · pseudo-extra-field)
```

### 4.2 · `test_rules_registry.py` (10 tests)

```text
test_register_rule_adds_to_registry
test_register_rule_respects_order (register order=5 then order=1 → registry list ordered [1,5])
test_register_rule_rejects_non_RiskRule_class (TypeError)
test_register_rule_rejects_empty_name (ValueError)
test_register_rule_rejects_duplicate_name (ValueError · Q9.1 LOCKED)
test_get_registered_rules_returns_ordered_list
test_unregister_rule_removes_from_registry
test_unregister_rule_idempotent (no error on double-call)
test_registry_loads_5_rules_at_import (after `from backend.v9.services.trade_manager.rules import ...`)
test_5_rules_names_match_d094 (names: MFE_PEAK, CCI_FLAT, TCCI_CROSS, SWI, DAY_TYPE_TARGETS)
```

### 4.3 · `test_rules_wrappers.py` (18 tests)

For each of 5 RiskRule subclasses · 3 tests (15):
```text
test_<name>_wraps_layer4_service (wrapper output == layer4 service output · canonical fixture)
test_<name>_returns_none_when_required_ctx_missing (CCIFlatRule(ctx.cci_history=None) → None · etc.)
test_<name>_class_attr_name_and_phase_correct
```

Plus 3 Q9.3 skip-log tests:
```text
test_skip_log_first_call_emits_warning (CCIFlatRule + caplog · 1 warning recorded)
test_skip_log_within_interval_silent (same call within 300s · 0 new warnings)
test_skip_log_after_reset_re_emits (`_skip_limiter.reset()` · next call emits again)
```

**Test setup MANDATORY:** `_skip_limiter.reset()` in fixture teardown (or `setup_method` per-class) · NO POLLUTION. MFETightenRule and TCCIExitRule MUST NOT call `log_skipped_rule` (verify via caplog: 0 records on None ctx).

### 4.4 · `test_future_rule_stub.py` (3 tests · Risk #8 G3 mandatory)

Each test wraps register → assert → `unregister_rule(...)` in `try/finally`. CLEANUP IS NON-NEGOTIABLE — learned from `get_event_loop()` test pollution (commit bbf5044).

```text
test_future_rule_can_register_without_core_change (extensibility contract via registry only)
test_future_rule_integration_via_loop (TrailEngine-like loop calls registered future rule · checks result routing)
test_future_rule_cleanup_idempotent (unregister twice does not raise)
```

---

## 5 · Acceptance criteria

| # | Criterion | Verify |
|---|---|---|
| 1 | `pytest tests/v9/services/test_trade_manager/ -v` → all 36 green | run + paste tail |
| 2 | `pytest tests/v9/services/ -q` → no new regressions vs HEAD `12edadc` (compare before/after counts) | run + paste tail |
| 3 | `pytest tests/v9/ -q` → full suite · zero new failures vs baseline `40 failed / 1116 passed` at HEAD `12edadc` | run + paste tail |
| 4 | `pytest backend/v9/ tests/atomic/ -q` → green · no atomic regression | run + paste tail |
| 5 | ReadLints clean on all 8 new files + `trail_engine.py` | paste output |
| 6 | `rg "from backend.v9.services.layer4 import" backend/v9/services/trail_engine.py` → **0 hits** (5 hardcoded imports removed) | rg |
| 7 | `rg "get_registered_rules\|Layer4Context" backend/v9/services/trail_engine.py` → **2+ hits** (import + usage) | rg |
| 8 | `git diff backend/v9/services/layer4/` → empty (zero diff · D-095 lock) | git diff |
| 9 | Wrapper instance count: `len(get_registered_rules())` == **5** at import · names == `["MFE_PEAK", "CCI_FLAT", "TCCI_CROSS", "SWI", "DAY_TYPE_TARGETS"]` · phases `["PRE_TIGHTEN"]*4 + ["POST_TIGHTEN"]*1` | report inline |
| 10 | D-095 zero-functional-change UAT (manual): pick 3 representative bars from previous SHADOW run · run `_apply_layer4` pre-Pkg6 vs post-Pkg6 · `candidate_stops` set + final `trade.stop` + `cross_context` events MUST be identical | report inline · note if any drift |

---

## 6 · Constraints (must not violate · pre-LIVE protocol)

- **No silent excepts.** Every `except` includes `logger.warning("[TrailEngine] <rule_name>.evaluate failed trade=%s: %s", trade.id, exc)`. Match current trail_engine logging exactly.
- **No `return None` without prior log** at info/warning level explaining why · EXCEPT for the rate-limited `log_skipped_rule` path (which already logs at WARN intervals).
- **No new dependencies** (pip / package.json).
- **No "while I'm here" refactors** outside SCOPE files. If you notice anything wrong in a FORBIDDEN file, document in §11 self-report and STOP if it blocks the work.
- **No hardcoded sleeps / `time.sleep()` in tests.** Rate limiter tests use `_skip_limiter.reset()` or monkeypatch `_skip_limiter._interval` to 0.
- **No `asyncio.get_event_loop()`** in any new test (learned from commit bbf5044 · use `asyncio.run()` if async needed).
- **D-095 zero-diff for `layer4/*.py`** is non-negotiable. If you find a bug in a layer4 service, STOP and report — DO NOT fix it in Pkg 6.
- **Commit message MUST include Phase A flag** verbatim: `Phase A mechanical · DEMO+ parametric calibration`.

---

## 7 · Allowed imports (whitelist)

```python
# base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Dict, List, Literal, Optional, Tuple, Type
import logging

# mfe_peak.py / cci_flat.py / tcci_cross.py / swi.py / day_type_targets.py
from backend.v9.services.trade_manager.rules.base import (
    RiskRule, Layer4Context, register_rule, log_skipped_rule,
)
from backend.v9.services.layer4 import (
    mfe_peak_tighten,  # mfe_peak.py
    cci_flat_tighten,  # cci_flat.py
    tcci_cross_exit,   # tcci_cross.py
    swi_tighten,       # swi.py
    day_type_targets_verify,  # day_type_targets.py
)
# (each wrapper imports ONLY the one layer4 module it wraps · not all)

# rules/__init__.py
from .base import (
    RiskRule, Layer4Context,
    register_rule, get_registered_rules, unregister_rule,
    log_skipped_rule,
)
from . import mfe_peak, cci_flat, tcci_cross, swi, day_type_targets  # noqa: F401

# trail_engine.py (NEW import only)
from backend.v9.services.trade_manager.rules import (
    get_registered_rules, Layer4Context,
)

# tests
import pytest
import logging
from backend.v9.services.trade_manager.rules import (
    RiskRule, Layer4Context, register_rule, get_registered_rules,
    unregister_rule, log_skipped_rule,
)
from backend.v9.services.trade_manager.rules.base import _skip_limiter  # for reset() in tests only
```

**NO imports outside this list.** Hallucinated APIs = retry.

---

## 8 · Deliverable format (CC self-report)

After completion, CC outputs:

1. **Files changed** (full paths · A=add / M=modify / D=delete):
   - A · `backend/v9/services/trade_manager/rules/__init__.py`
   - A · `backend/v9/services/trade_manager/rules/base.py`
   - A · `backend/v9/services/trade_manager/rules/mfe_peak.py`
   - A · `backend/v9/services/trade_manager/rules/cci_flat.py`
   - A · `backend/v9/services/trade_manager/rules/tcci_cross.py`
   - A · `backend/v9/services/trade_manager/rules/swi.py`
   - A · `backend/v9/services/trade_manager/rules/day_type_targets.py`
   - A · `tests/v9/services/test_trade_manager/__init__.py`
   - A · `tests/v9/services/test_trade_manager/test_layer4_context.py`
   - A · `tests/v9/services/test_trade_manager/test_rules_registry.py`
   - A · `tests/v9/services/test_trade_manager/test_rules_wrappers.py`
   - A · `tests/v9/services/test_trade_manager/test_future_rule_stub.py`
   - M · `backend/v9/services/trail_engine.py` (lines 546-644 + 1 new import)

2. **Commit message** (verbatim · single line · conventional commits):
   ```
   feat(s2): Pkg 6 · TradeManager extensible · RiskRule registry + 5 wrappers · D-095 zero functional change · Phase A mechanical · DEMO+ parametric calibration
   ```

3. **Self-report:**
   - Any TODOs left in code? (must be empty)
   - Any spec ambiguity encountered? (list explicitly · STOP signal if blocked)
   - Any forbidden constraint accidentally violated? (own up — Cursor catches in G3 anyway)
   - LOC count breakdown (base.py / 5 wrappers / __init__.py / 4 test files / trail_engine.py diff)
   - **Functional invariants** (verify and report inline):
     - `len(get_registered_rules()) == 5` at import time
     - Names + phases match locks #6
     - `git diff backend/v9/services/layer4/` is empty
     - `rg "from backend.v9.services.layer4 import" backend/v9/services/trail_engine.py` → 0 hits

4. **ReadLints output** (paste verbatim · all 8 new files + trail_engine.py)

5. **pytest outputs** (paste verbatim · tail 30 lines for each):
   - `pytest tests/v9/services/test_trade_manager/ -v`
   - `pytest tests/v9/services/ -q`
   - `pytest tests/v9/ -q` (full suite · before/after counts must match baseline `40 failed / 1116 passed` at HEAD `12edadc`)
   - `pytest backend/v9/ tests/atomic/ -q` (no atomic regression)

---

## 9 · Stop signal

IF any condition met, STOP and output `STOP — <reason> · need Michael decision on <specific question>`:

- Any FORBIDDEN file (§3) appears in your edit list · STOP
- `git diff backend/v9/services/layer4/` is non-empty · STOP (D-095 zero-diff violation)
- An allowed import (§7) doesn't resolve · STOP and report
- `_apply_layer4` refactor changes the order of rule execution observable from the outside (audit events `layer4_tighten` / `layer4_exit` / `layer4_warn` differ in count or order vs pre-refactor on the same input) · STOP
- A golden test scenario (§4) is impossible to construct from current code shape · STOP
- `pytest tests/v9/ -q` baseline drifts (was `40 failed / 1116 passed` at HEAD `12edadc`) · STOP and inspect
- Test pollution detected (registry leak after test · `_skip_limiter` accumulated entries from prior test) · STOP — cleanup is mandatory per Risk #8
- D-095 zero-functional-change UAT (§5 #10) shows ANY drift in `candidate_stops` set · final `trade.stop` · or `cross_context` events · STOP

**DO NOT guess. DO NOT add a comment "TODO: ask Michael".**

---

## 10 · Authority & references

- **Spec:** `docs/spec_authority/S2_TRADEMGR_HOOKS_V1.md` (🔒 LOCKED 2026-05-25 13:57)
- **D-095:** `docs/decisions/D-095_DEFER_4A_4B_SCOPE_ABSORBED.md` (defer 4a/4b · absorb into Pkg 6)
- **D-094:** Constitution V3 §Layer 4 (5 services + order)
- **Constitution V3:** `docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt` (§Layer 4 amendment 2026-05-25)
- **Pre-LIVE protocol:** `.cursor/rules/mems26-pre-live-protocol.mdc`
- **Pkg 8 G3 PASS report** (most recent successful refactor): `docs/reports/PKG8_G3_PASS_2026-05-25.md`
- **Risk #8 mandate** (cleanup discipline · pollution): commit `bbf5044` for asyncio.run pattern · commit `12edadc` for time_stop_mapper fix

---

## 11 · Phase A completion note (Cursor will update after Pkg 6 G3 PASS)

After Pkg 6 G3 PASS:
- Phase A: 14/15 done · 4a + 4b stay deferred per D-095
- Constitution V3 §Layer 4 amendment confirmed live
- Phase A → Phase B transition (per `PRE_LIVE_PIPELINE_2026-05-23.md`)

Cursor will write G3 report `docs/reports/PKG6_G3_PASS_2026-05-25.md` after CC delivers.

---

*End of handoff · ready for Claude Desktop to convert into final CC mega-prompt · 2026-05-25 14:05 IL Cursor*
