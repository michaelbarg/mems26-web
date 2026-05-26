# S2 TradeManager RiskRule Hooks V1

**Status:** ✅ LOCKED (Michael approved 2026-05-25 13:56 IL)
**Date:** 2026-05-25 13:56 IL
**Authority:** D-095 (defer 4a/4b · absorb into Pkg 6) + D-094 (Layer 4 service architecture)
**Source:** Q1-Q5 + Q9.1-Q9.4 chat 25/5 13:45-13:56 IL (Cursor recommendations · Michael approved all)
**Consumed by:** Pkg 6 (TradeManager extensible · LAST Phase A package)
**Scope:** Wrap 5 existing layer4 services into `RiskRule` subclasses · **zero functional change · refactor only**

---

## 1 · Q1-Q5 Decisions (Michael approved 25/5 13:49 chat)

| Q | Decision | Rationale |
|---|---|---|
| Q1 · base signature | `evaluate(trade: dict, ctx: Layer4Context) -> Optional[dict]` | Unifies 5 different layer4 signatures into one |
| Q2 · registration | `@register_rule(order=N)` explicit decorator | Discoverable · preserves D-094 ordering · auditable |
| Q3 · file location | `backend/v9/services/trade_manager/rules/` NEW subdir | Separation: `layer4/` = pure functions · `rules/` = wrappers |
| Q4 · TrailEngine integration | `_apply_layer4()` loops over `get_registered_rules()` | Minimal change · TrailEngine ownership preserved |
| Q5 · future-rule test stub | register + integration + cleanup (no test pollution) | Risk #8 G3 mandatory · cleanup learned from `get_event_loop()` |

---

## 2 · API Contracts (verbatim · CC must implement exact signatures)

### 2.1 · `Layer4Context` (immutable runtime context)

```python
# backend/v9/services/trade_manager/rules/base.py
from dataclasses import dataclass
from typing import List, Optional

@dataclass(frozen=True)
class Layer4Context:
    """Aggregated runtime context for risk rules.

    Extensible: new fields can be added without breaking existing rules
    (rules ignore fields they don't use). MUST stay immutable.
    """
    cci_history: Optional[List[float]] = None
    direction_change_event: Optional[dict] = None
    swi: Optional[dict] = None
    current_day_type: Optional[str] = None
```

### 2.2 · `RiskRule` abstract base

```python
from abc import ABC, abstractmethod
from typing import Literal, Optional

Phase = Literal["PRE_TIGHTEN", "POST_TIGHTEN"]


class RiskRule(ABC):
    """Base class for risk rules. Subclasses wrap a layer4.<svc>.evaluate() call.

    Contract:
    - `name` is a class-level constant string (e.g., "TCCI_CROSS")
    - `phase` controls when the rule runs vs _apply_tightest_stop:
        - "PRE_TIGHTEN" (default · 4 of 5 rules): result may TIGHTEN_STOP
          (buffered into candidate_stops) or EXIT (short-circuits whole chain)
        - "POST_TIGHTEN" (only DAY_TYPE_TARGETS): runs AFTER tightest_stop is
          applied · result routes to _handle_day_type_action (WARN/CLOSE_ALL escalation)
    - `evaluate()` returns an action dict {action, rule, ...} or None
    - Action types: "EXIT" | "TIGHTEN_STOP" | "WARN" | "CLOSE_ALL"
    - On exception · TrailEngine catches and logs.warning · rule is skipped
    - EXIT short-circuits ALL subsequent rules + _apply_tightest_stop
    """
    name: str = ""  # MUST override in subclass
    phase: Phase = "PRE_TIGHTEN"  # MAY override (only DAY_TYPE_TARGETS sets POST_TIGHTEN)

    @abstractmethod
    def evaluate(self, trade: dict, ctx: Layer4Context) -> Optional[dict]:
        ...
```

### 2.3 · Rate-limited skip logger (Q9.4 LOCKED)

```python
# backend/v9/services/trade_manager/rules/base.py (continued)
import logging
from threading import Lock
from time import monotonic

logger = logging.getLogger(__name__)


class _SkipLogLimiter:
    """Rate-limits ctx-missing warnings · one per (rule_name, ctx_field) per interval.

    Pre-LIVE requirement (Q9.3 LOCKED): we MUST surface when a risk rule is
    silently skipped due to missing context (e.g., S4 outage → cci_history is None).
    But we cannot flood logs every 5-min bar × N trades. Default interval = 300s
    (one warning per rule-context pair per 5 minutes per process).
    """

    def __init__(self, interval_seconds: float = 300.0):
        self._last: dict[tuple[str, str], float] = {}
        self._lock = Lock()
        self._interval = interval_seconds

    def should_log(self, rule_name: str, missing_field: str) -> bool:
        key = (rule_name, missing_field)
        now = monotonic()
        with self._lock:
            last = self._last.get(key)
            if last is None or (now - last) >= self._interval:
                self._last[key] = now
                return True
            return False

    def reset(self) -> None:
        """For tests only."""
        with self._lock:
            self._last.clear()


_skip_limiter = _SkipLogLimiter()


def log_skipped_rule(rule_name: str, missing_field: str) -> None:
    """Called by wrappers when ctx is missing required field.
    Rate-limited to 1 warning per (rule, field) per 5 min.
    """
    if _skip_limiter.should_log(rule_name, missing_field):
        logger.warning(
            "[RiskRule] %s skipped · ctx.%s is None",
            rule_name, missing_field,
        )
```

### 2.4 · Registry

```python
from typing import List, Tuple, Type

_REGISTRY: List[Tuple[int, RiskRule]] = []  # (order, instance)

def register_rule(*, order: int):
    """Decorator. Registers a RiskRule subclass with an ordering key.

    Raises:
        TypeError if `cls` is not a RiskRule subclass
        ValueError if `cls.name` is empty
        ValueError if `cls.name` is already registered (duplicate name)
    """
    def _wrap(cls: Type[RiskRule]) -> Type[RiskRule]:
        if not isinstance(cls, type) or not issubclass(cls, RiskRule):
            raise TypeError(f"register_rule expects RiskRule subclass, got {cls!r}")
        if not getattr(cls, "name", ""):
            raise ValueError(f"{cls.__name__}.name must be a non-empty string")
        for _, r in _REGISTRY:
            if r.name == cls.name:
                raise ValueError(f"RiskRule name={cls.name!r} already registered")
        _REGISTRY.append((order, cls()))
        _REGISTRY.sort(key=lambda x: x[0])
        return cls
    return _wrap


def get_registered_rules() -> List[RiskRule]:
    """Returns rules in ascending order of `order=N` key."""
    return [r for _, r in _REGISTRY]


def unregister_rule(cls: Type[RiskRule]) -> None:
    """For tests only. Removes the instance whose type matches `cls`."""
    global _REGISTRY
    _REGISTRY = [(o, r) for o, r in _REGISTRY if not isinstance(r, cls)]
```

### 2.5 · The 5 Rule Classes (wrappers · order matches D-094 lines 553-557)

```python
# rules/mfe_peak.py
from backend.v9.services.trade_manager.rules.base import RiskRule, Layer4Context, register_rule
from backend.v9.services.layer4 import mfe_peak_tighten

@register_rule(order=1)
class MFETightenRule(RiskRule):
    name = "MFE_PEAK"
    def evaluate(self, trade, ctx):
        # No ctx fields needed · always runs
        return mfe_peak_tighten.evaluate(trade)


# rules/cci_flat.py
from backend.v9.services.trade_manager.rules.base import (
    RiskRule, Layer4Context, register_rule, log_skipped_rule,
)
from backend.v9.services.layer4 import cci_flat_tighten

@register_rule(order=2)
class CCIFlatRule(RiskRule):
    name = "CCI_FLAT"
    def evaluate(self, trade, ctx):
        if ctx.cci_history is None:
            log_skipped_rule(self.name, "cci_history")  # Q9.3 LOCKED · rate-limited
            return None
        return cci_flat_tighten.evaluate(trade, ctx.cci_history)


# rules/tcci_cross.py
from backend.v9.services.layer4 import tcci_cross_exit

@register_rule(order=3)
class TCCIExitRule(RiskRule):
    name = "TCCI_CROSS"
    def evaluate(self, trade, ctx):
        # Note: layer4.tcci_cross_exit.evaluate() already handles None
        # internally (returns None). No explicit short-circuit here —
        # matches D-095 zero-diff requirement. No skip log needed.
        return tcci_cross_exit.evaluate(trade, ctx.direction_change_event)


# rules/swi.py
from backend.v9.services.trade_manager.rules.base import (
    RiskRule, Layer4Context, register_rule, log_skipped_rule,
)
from backend.v9.services.layer4 import swi_tighten

@register_rule(order=4)
class SWITightenRule(RiskRule):
    name = "SWI"
    def evaluate(self, trade, ctx):
        if ctx.swi is None:
            log_skipped_rule(self.name, "swi")  # Q9.3 LOCKED · rate-limited
            return None
        return swi_tighten.evaluate(trade, ctx.swi)


# rules/day_type_targets.py
from backend.v9.services.trade_manager.rules.base import (
    RiskRule, Layer4Context, register_rule, log_skipped_rule,
)
from backend.v9.services.layer4 import day_type_targets_verify

@register_rule(order=5)
class DayTypeTargetsVerifyRule(RiskRule):
    name = "DAY_TYPE_TARGETS"
    phase = "POST_TIGHTEN"  # runs AFTER _apply_tightest_stop · routes to _handle_day_type_action
    def evaluate(self, trade, ctx):
        if ctx.current_day_type is None:
            log_skipped_rule(self.name, "current_day_type")  # Q9.3 LOCKED
            return None
        return day_type_targets_verify.evaluate(trade, ctx.current_day_type)
```

### 2.6 · `rules/__init__.py` auto-import

```python
# backend/v9/services/trade_manager/rules/__init__.py
from .base import (
    RiskRule, Layer4Context,
    register_rule, get_registered_rules, unregister_rule,
    log_skipped_rule, _skip_limiter,
)

# Auto-register all 5 rules at package load
from . import mfe_peak  # noqa: F401  · order=1
from . import cci_flat  # noqa: F401  · order=2
from . import tcci_cross  # noqa: F401  · order=3
from . import swi  # noqa: F401  · order=4
from . import day_type_targets  # noqa: F401  · order=5

__all__ = [
    "RiskRule", "Layer4Context",
    "register_rule", "get_registered_rules", "unregister_rule",
    "log_skipped_rule",
]
```

---

## 3 · TrailEngine integration

Current `_apply_layer4()` (`backend/v9/services/trail_engine.py:553-` approx) calls 5 hardcoded layer4 services in fixed order with try/except. Pkg 6 replaces the body with a registry loop.

### 3.1 · Before Pkg 6 (current)

```python
def _apply_layer4(self, trade, ...):
    from backend.v9.services.layer4 import tcci_cross_exit
    from backend.v9.services.layer4 import mfe_peak_tighten
    from backend.v9.services.layer4 import cci_flat_tighten
    from backend.v9.services.layer4 import swi_tighten
    from backend.v9.services.layer4 import day_type_targets_verify

    # 1. mfe_peak_tighten
    try:
        result = mfe_peak_tighten.evaluate(trade_dict)
        if result and result.get("action") == "TIGHTEN_STOP":
            self._tighten_stop(trade, result)
    except Exception as exc:
        logger.warning("[TrailEngine] mfe_peak_tighten failed trade=%s: %s", trade.id, exc)

    # 2. cci_flat_tighten (S4 only)
    if cci_history is not None:
        try:
            result = cci_flat_tighten.evaluate(trade_dict, cci_history)
            ...
        except Exception as exc:
            ...

    # 3. tcci_cross_exit (S4 only · EXIT short-circuits)
    if direction_change_event is not None:
        try:
            result = tcci_cross_exit.evaluate(trade_dict, direction_change_event)
            if result and result.get("action") == "EXIT":
                self._close_trade(trade, result)
                return
            ...
        except Exception as exc:
            ...

    # 4. swi_tighten
    ...

    # 5. day_type_targets_verify
    ...
```

### 3.2 · After Pkg 6 (target)

```python
from backend.v9.services.trade_manager.rules import (
    get_registered_rules, Layer4Context
)

def _apply_layer4(self, trade, ...):
    ctx = Layer4Context(
        cci_history=cci_history,                      # already computed above
        direction_change_event=direction_change_event,
        swi=swi_snapshot,
        current_day_type=getattr(trade, 'current_day_type', None),
    )
    trade_dict = self._trade_to_dict(trade)

    for rule in get_registered_rules():
        try:
            result = rule.evaluate(trade_dict, ctx)
        except Exception as exc:
            logger.warning(
                "[TrailEngine] %s.evaluate failed trade=%s: %s",
                rule.name, trade.id, exc,
            )
            continue

        if result is None:
            continue

        action = result.get("action")
        if action in ("EXIT", "CLOSE_ALL"):
            self._close_trade(trade, result)
            return  # short-circuit
        elif action == "TIGHTEN_STOP":
            self._tighten_stop(trade, result)
        elif action == "WARN":
            self._handle_warn(trade, result)
```

### 3.3 · Compliance with D-095 "zero functional change"

| Behavior | Before | After | Same? |
|---|---|---|---|
| Order: mfe → cci_flat → tcci → swi → day_type | hardcoded | order=1..5 | ✅ |
| EXIT short-circuit (TCCI) | `return` after close | `return` after close | ✅ |
| cci_flat skip when `cci_history is None` | guard before call | rule returns None | ✅ |
| tcci skip when `direction_change_event is None` | guard before call | layer4 still returns None on None input | ✅ |
| Per-rule try/except + logger.warning | per-call | per-iteration | ✅ |
| Action handling: TIGHTEN_STOP / EXIT / WARN | unchanged | unchanged | ✅ |

---

## 4 · File Layout

```
backend/v9/services/trade_manager/rules/              ← NEW (Pkg 6)
├── __init__.py                          ~18 LOC · exports + auto-import
├── base.py                              ~130 LOC · RiskRule + Layer4Context + registry + _SkipLogLimiter
├── mfe_peak.py                          ~10 LOC · order=1 · no skip log (no ctx field needed)
├── cci_flat.py                          ~14 LOC · order=2 · skip log on cci_history=None
├── tcci_cross.py                        ~12 LOC · order=3 · no skip log (layer4 handles None)
├── swi.py                               ~14 LOC · order=4 · skip log on swi=None
└── day_type_targets.py                  ~14 LOC · order=5 · skip log on current_day_type=None

backend/v9/services/layer4/                            UNCHANGED
└── *.py · 5 files · 336 LOC · ZERO DIFF

backend/v9/services/trail_engine.py                    MODIFIED (Pkg 6)
└── _apply_layer4 method only · 5 hardcoded calls → 1 registry loop · ~30 lines changed

tests/v9/services/test_trade_manager/                  NEW (Pkg 6)
├── __init__.py
├── test_rules_registry.py               ~10 tests
├── test_rules_wrappers.py               ~15 tests (3 per rule)
├── test_layer4_context.py               ~5 tests
└── test_future_rule_stub.py             ~3 tests · Risk #8 mandatory
```

Total LOC: ~200 NEW production · ~30 modified · ~270 new tests.

---

## 5 · Test Plan (Pkg 6 G3 mandatory)

### 5.1 · Registry (10 tests · `test_rules_registry.py`)

1. `test_register_rule_adds_to_registry`
2. `test_register_rule_respects_order` (order=5 then order=1 → registry order [1,5])
3. `test_register_rule_rejects_non_RiskRule_class`
4. `test_register_rule_rejects_empty_name`
5. `test_register_rule_rejects_duplicate_name` (Q9.1 lock)
6. `test_get_registered_rules_returns_ordered_list`
7. `test_unregister_rule_removes_from_registry`
8. `test_unregister_rule_idempotent` (calling twice doesn't error)
9. `test_registry_loads_5_rules_at_import` (after `from rules import ...`)
10. `test_5_rules_names_match_d094` (names: MFE_PEAK, CCI_FLAT, TCCI_CROSS, SWI, DAY_TYPE_TARGETS)

### 5.2 · Wrappers (18 tests · `test_rules_wrappers.py`)

For each of 5 RiskRule subclasses · 3 tests each (15):
- `test_<name>_wraps_layer4_service` — wrapper output == layer4 service output for canonical inputs
- `test_<name>_returns_none_when_required_ctx_missing` — e.g., CCIFlatRule with `ctx.cci_history=None`
- `test_<name>_class_attr_name_correct` — class.name == expected D-094 string

Plus 3 Q9.3-specific tests (rate-limited skip log):
- `test_skip_log_first_call_emits_warning` — CCIFlatRule(ctx.cci_history=None) emits 1 warning
- `test_skip_log_within_interval_silent` — 2nd call within 300s does NOT emit (rate-limited)
- `test_skip_log_after_interval_re_emits` — after `_skip_limiter.reset()`, next call emits again

**Test setup:** use `caplog` fixture · `_skip_limiter.reset()` in `setup_method` / fixture teardown to avoid pollution across tests. MFETightenRule and TCCIExitRule MUST NOT emit skip logs (no required ctx field).

### 5.3 · Layer4Context (5 tests · `test_layer4_context.py`)

1. `test_layer4_context_default_all_None`
2. `test_layer4_context_accepts_all_fields`
3. `test_layer4_context_immutable_raises_on_mutation` (FrozenInstanceError)
4. `test_layer4_context_equality_by_value`
5. `test_layer4_context_extensible_new_field` (forward-compat smoke)

### 5.4 · Future-rule stub (3 tests · `test_future_rule_stub.py` · Risk #8 mandatory)

```python
def test_future_rule_can_register_without_core_change():
    """Risk #8 G3 mandatory · proves extensibility contract via registry only."""
    from backend.v9.services.trade_manager.rules import (
        register_rule, RiskRule, get_registered_rules, unregister_rule, Layer4Context,
    )

    @register_rule(order=99)
    class _TestFutureRule(RiskRule):
        name = "TEST_FUTURE"
        def evaluate(self, trade, ctx):
            return {"action": "TIGHTEN_STOP", "rule": "TEST_FUTURE", "new_stop": 100.0}

    try:
        names = [r.name for r in get_registered_rules()]
        assert "TEST_FUTURE" in names
        assert names[-1] == "TEST_FUTURE"  # order=99 → last
    finally:
        unregister_rule(_TestFutureRule)  # MANDATORY cleanup · no test pollution


def test_future_rule_integration_via_loop():
    """End-to-end: TrailEngine-like loop calls the registered future rule."""
    ... (similar pattern)


def test_future_rule_cleanup_idempotent():
    """unregister_rule called twice doesn't raise · prevents test ordering bugs."""
    ...
```

### 5.5 · No-regression sweep

- All existing TrailEngine tests must pass unchanged
- All `tests/v9/services/test_layer4/` tests (if any) pass unchanged
- `pytest backend/v9/services/ tests/v9/services/ -q` → no NEW failures vs HEAD pre-Pkg6

---

## 6 · FORBIDDEN zones (CC must not touch)

| File | Reason |
|---|---|
| `backend/v9/services/layer4/*.py` (all 5) | Source of truth · D-095 "zero functional change" |
| `backend/v9/services/trade_manager/manager.py` | TradeManager core · not scope of Pkg 6 (only TrailEngine integration) |
| `backend/v9/services/trade_manager/state_machine.py` | Stable state machine · no rule logic here |
| `backend/v9/services/trade_manager/events.py` | Event emitter · separate concern |
| `backend/v9/systems/` (all subdirs) | Out of scope |
| `backend/v9/db/models/` | No schema changes |
| `frontend/` `sc_study/` | Out of scope |

**Allowed touch:** ONLY the 7 new files in `rules/` + `trail_engine.py::_apply_layer4` method + 4 new test files.

---

## 7 · Constitution V3 amendment (after Pkg 6 G3 PASS)

Constitution V3 §D-094 / §Trail / §Layer 4 mentions the 5 services by function name. Add amendment note:

> **Pkg 6 amendment (2026-05-25):** Layer 4 services are now wrapped by RiskRule subclasses in `backend/v9/services/trade_manager/rules/`. Functions in `layer4/*.py` remain byte-identical · invoked via the wrappers. New risk rules can be added without modifying TrailEngine core. See `S2_TRADEMGR_HOOKS_V1.md`.

Cursor drafts after Pkg 6 G3 PASS.

---

## 8 · Q9.1-Q9.4 Final decisions (Michael LOCKED 25/5 13:56 IL)

| # | Question | DECISION | Rationale |
|---|---|---|---|
| Q9.1 | `register_rule` raises on duplicate `name`? | **YES** · `ValueError` | pre-LIVE "no silent failures" · 1 LOC · prevents silent override of MFE_PEAK / TCCI_CROSS by typo'd duplicate. Risk #4 catch. |
| Q9.2 | `Layer4Context` validates types at construction? | **NO** · frozen dataclass only | consistent with codebase (no runtime type validation elsewhere) · type hints + tests sufficient · negligible perf gain not worth pattern divergence |
| Q9.3 | Wrappers log when ctx is None (CCIFlatRule / SWITightenRule / DayTypeTargetsVerifyRule)? | **YES · rate-limited** · 1 warning per `(rule, field)` per 300s | pre-LIVE "no silent failures" protocol REQUIRES observability of a disabled risk rule. Rate limit prevents log flood (12 trades × 5-min bars). `_SkipLogLimiter` provided in §2.3 |
| Q9.4 | Singletons or per-call instances? | **SINGLETON** · stored in `_REGISTRY` at registration | stateless rules · matches current layer4 function pattern · zero overhead · stateful future rules must store state in `trade` dict, not `self` |

**Constraint locked:** MFETightenRule and TCCIExitRule do NOT call `log_skipped_rule` (no required ctx field · cannot be silently skipped).

---

## 9 · Audit trail

| Date | Event |
|---|---|
| 2026-05-23 17:30 | V2 plan added Pkg 6 (TradeManager hook-based · LAST Phase A package) |
| 2026-05-25 11:18 | D-095 LOCKED · Pkg 4a/4b deferred · scope absorbed by Pkg 6 |
| 2026-05-25 13:20 | Pkg 8 G3 PASS · 13/15 Phase A done |
| 2026-05-25 13:35 | B2 test cleanup partial done · 17+2 failures fixed · 6 deferred |
| 2026-05-25 13:49 | Michael approves Q1-Q5 (chat) |
| 2026-05-25 13:55 | Cursor writes S2_TRADEMGR_HOOKS_V1_DRAFT.md · Q9.1-Q9.4 defaults proposed |
| 2026-05-25 13:56 | **Michael LOCKS Q9.1-Q9.4** (Q9.3 upgraded from default NO → YES+rate-limited per pre-LIVE protocol) |
| 2026-05-25 13:57 | **DRAFT → V1 LOCKED · spec authoritative for Pkg 6 G0** |
| TBD | Cursor writes DESKTOP_PKG6_TRADEMGR_HANDOFF.md · CC implements |
| TBD | Pkg 6 G3 PASS · LAST Phase A · 14/15 done (4a/4b stay deferred) |
