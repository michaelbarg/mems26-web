# Pkg 3a · Stream 1.5 · prev_day wiring + line 547 rewrite

**Authority:** D-091 §Pkg 3a sub-decisions · Option B (Michael 23/5 20:34)
**Predecessor:** Stream 1 G3 PASS commit chain `dd9c34f` → `a58ee61` → `689ac41`
**Status:** Spec ready · Cursor handoff for Claude Desktop mega-prompt → CC exec.
**Estimated CC time:** 1-2 hours.
**Independent of:** Stream 2 (can run in parallel).

---

## §1 · Why this exists (the unfinished bit from Stream 1)

In Stream 1 (Option B), `backend/v9/systems/day_type/state_machine.py::_rescore_from_behavior`
(currently at line 537, returning `DayType.Neutral` at line 547) was preserved **byte-identical**
because the corrected NeuE/NeuC classification needs `prev_vah`/`prev_val`/`session_open_price`/
`session_date` and **those fields don't exist on `DayTypeStateMachine` yet**.

Today's reality:
- The `api.py` path (`_classify_v1_from_tpo`) already calls `classify_neutral_subtype()` correctly
  → S2 receives `NeuE`/`NeuC` from the API.
- The state-machine path still returns `DayType.Neutral` (the deprecated alias).
- `targets_table.get_targets("Neutral")` maps it to `Neutral_Center` config (30min · HALF · safe
  default) and emits a 1-shot DEPRECATED warning → **no live regression**, but the warning is
  noise and the deprecated path should be retired.

Stream 1.5 wires `prev_day_summary` into the state machine and rewrites line 547 to call
`classify_neutral_subtype` directly. After this ships, the deprecated `Neutral` enum value is
only reachable via legacy DB rows.

---

## §2 · Scope · ONE module + 1 production caller + 1 new test file

### 2.1 · Modified · `backend/v9/systems/day_type/state_machine.py`

**Three surgical edits. Nothing else.**

#### Edit A · `__init__` signature (additive · backward compatible)

Current (lines 195-201):

```python
def __init__(
    self,
    config: Optional[DayTypeConfig] = None,
    zohar_engine: Optional[ZoharRulesEngine] = None,
    extension_tracker: Optional[ExtensionTracker] = None,
    decision_matrix: Optional[object] = None,
):
```

New (add 1 kwarg at the end):

```python
def __init__(
    self,
    config: Optional[DayTypeConfig] = None,
    zohar_engine: Optional[ZoharRulesEngine] = None,
    extension_tracker: Optional[ExtensionTracker] = None,
    decision_matrix: Optional[object] = None,
    prev_day_summary: Optional[Dict[str, Any]] = None,
):
```

Then inside `__init__`, **after** `self.missing_pd_fields: List[str] = []` (currently line 212),
add a new block:

```python
        # Stream 1.5 · prev_day context for NeuE/NeuC classification (D-091.Q1)
        _pds = prev_day_summary or {}
        self.prev_vah: Optional[float] = _pds.get("vah")
        self.prev_val: Optional[float] = _pds.get("val")
        self.session_date: Optional[str] = _pds.get("session_date")
        self.session_open_price: Optional[float] = None  # captured in _stage_a1
```

#### Edit B · `_stage_a1` captures session_open_price (1 line)

At the **very top** of `_stage_a1` (currently line 291-292, just after the `def`/docstring,
before the `missing_pd = ...` block), insert:

```python
        if self.session_open_price is None:
            self.session_open_price = bar.open
```

This captures the open of the first bar processed by `_stage_a1`. Subsequent A1 calls (re-runs
on the same bar after restart, or repeated A1 if pd_context degrades) leave it unchanged.

#### Edit C · `_rescore_from_behavior` line 547 rewrite (THE point of Stream 1.5)

Current (lines 545-547):

```python
        if self.behavior == Behavior.COMPRESSED:
            if self.range_category == RangeCategory.COMPRESSED:
                return DayType.Nontrend
            return DayType.Neutral
```

Replace line 547 ONLY (`return DayType.Neutral`) with:

```python
            from backend.v9.systems.day_type.neutral_classifier import classify_neutral_subtype
            return classify_neutral_subtype(
                session_open_price=self.session_open_price,
                prev_vah=self.prev_vah,
                prev_val=self.prev_val,
                session_date=self.session_date,
            )
```

**Keep** the inline import (same pattern Stream 1 used in `api.py`). Reason: avoids a top-of-file
import cycle risk and matches the existing convention.

### 2.2 · Modified · `backend/main.py` (P5.1.2 block · 1 surgical edit)

Current (lines 147-150):

```python
        from backend.v9.api.v9.day_type_seed import maybe_seed_ib_from_tpo

        day_type_machine = DayTypeStateMachine()
        app.state.day_type_machine = day_type_machine
```

New:

```python
        from backend.v9.api.v9.day_type_seed import maybe_seed_ib_from_tpo
        from backend.v9.systems.day_type.prev_day import load_tpo_previous_day_summary
        from backend.v9.services.market_clock import now_et

        try:
            _prev_day_tpo = load_tpo_previous_day_summary()
            _prev_day_summary_for_machine = {
                "vah": _prev_day_tpo.get("vah"),
                "val": _prev_day_tpo.get("val"),
                "session_date": now_et().date().isoformat(),
            }
        except Exception as _pds_err:
            _logger.warning("[DayType] prev_day_summary load failed: %s · NeuE/NeuC will fall back to NeuC", _pds_err)
            _prev_day_summary_for_machine = None

        day_type_machine = DayTypeStateMachine(prev_day_summary=_prev_day_summary_for_machine)
        app.state.day_type_machine = day_type_machine
```

Note: `session_date` is the **current** trading day (today) — it's the key the rate-limited
fallback log uses to suppress duplicates within a session. Not the previous day.

### 2.3 · New · `tests/v9/systems/test_day_type/test_rescore_neutral_subtype.py`

8 tests minimum. Use existing `make_bar()` helper from
`tests/v9/systems/test_day_type/test_day_type.py` (or replicate locally).

Required tests:

1. `test_constructor_backward_compat_no_args` — `DayTypeStateMachine()` works, all 4 new fields are None.
2. `test_constructor_accepts_prev_day_summary` — passes `{"vah":4500,"val":4480,"session_date":"2026-05-23"}`, asserts fields populated.
3. `test_stage_a1_captures_session_open_price` — feed 1 bar with `open=4490`, assert `machine.session_open_price == 4490`.
4. `test_stage_a1_does_not_overwrite_session_open` — feed 2 bars with different opens, assert `session_open_price` equals the FIRST bar's open.
5. `test_rescore_returns_neue_when_open_at_vah` — construct with prev_day VAH=4500/VAL=4480, set `session_open_price=4500`, drive machine into Behavior.COMPRESSED + RangeCategory.NORMAL, call `_rescore_from_behavior(bar)`, assert returns `DayType.Neutral_Extreme`.
6. `test_rescore_returns_neue_when_open_at_val` — same setup with `session_open_price=4480`, expect `Neutral_Extreme`.
7. `test_rescore_returns_neuc_when_open_inside_va` — `session_open_price=4490`, expect `Neutral_Center`.
8. `test_rescore_falls_back_to_neuc_without_prev_day_summary` — construct with `prev_day_summary=None`, drive to compressed/normal, expect `Neutral_Center` (fallback path).

Optional but recommended:

9. `test_rescore_falls_back_with_only_vah_missing` — prev_day with `val` but `vah=None`, expect NeuC.

For tests 5-9: the easiest way to drive `_rescore_from_behavior` is to directly set
`machine.behavior = Behavior.COMPRESSED` and `machine.range_category = RangeCategory.NORMAL`,
then call `machine._rescore_from_behavior(bar)` with any non-failed-extension bar.
Imports needed at top:

```python
from backend.v9.systems.day_type.state_machine import DayTypeStateMachine
from backend.v9.systems.day_type.schemas import (
    DayType, BarInput, Behavior, RangeCategory, FailedExtensionType,
)
```

---

## §3 · API contract · `prev_day_summary` dict shape

```python
{
    "vah": Optional[float],            # previous day TPO VAH (Value Area High)
    "val": Optional[float],            # previous day TPO VAL (Value Area Low)
    "session_date": Optional[str],     # today's date in ISO format (YYYY-MM-DD)
}
```

`None` for any field is acceptable. The downstream `classify_neutral_subtype()` already handles
missing VAH/VAL by falling back to `Neutral_Center` with a rate-limited log. Already tested in
Stream 1.

---

## §4 · Forbidden zone (G3 will verify byte-identical)

The following must NOT change:

- `backend/v9/systems/day_type/state_machine.py` lines OUTSIDE the 3 surgical edits above.
  Specifically: `_rescore_from_behavior` body lines 538-546 + line 549 (`return self.day_type`)
  must be byte-identical to HEAD (`689ac41`).
- `backend/v9/systems/day_type/neutral_classifier.py` — NO modifications. Shipped in Stream 1.
- `backend/v9/systems/day_type/api.py` — NO modifications. Stream 1 already wired this path.
- `backend/v9/systems/day_type/targets_table.py` — NO modifications.
- `backend/v9/systems/day_type/schemas.py` — NO modifications.
- `backend/v9/services/layer4/day_type_targets_verify.py` — NO modifications.
- Any other test file under `tests/` or `backend/v9/tests/` — read-only reference; do not edit.
- `backend/v9/systems/day_type/prev_day.py` — read-only reference; do not edit.

Cursor G3 will run `git diff 689ac41..HEAD -- backend/v9/systems/day_type/state_machine.py`
and verify the diff touches exactly the 3 edit regions defined in §2.1, with the same line counts.

---

## §5 · Acceptance criteria (G3 will check ALL)

1. `pytest tests/v9/systems/test_day_type/ -q` → all green (existing tests + new test file).
2. `pytest tests/v9/systems/ -q` → ≥545 passed, 0 new failures vs HEAD `689ac41`.
3. `pytest backend/v9/tests/test_state_machine_v9.py backend/v9/tests/e2e/test_day_type_e2e.py -q` → all green.
4. `pytest tests/v9/compliance/test_day_type_compliance.py -q` → all green.
5. Boot smoke: `python3 -c "from backend.main import app; print('OK')"` exits 0.
6. Backward-compat smoke: `python3 -c "from backend.v9.systems.day_type.state_machine import DayTypeStateMachine; m = DayTypeStateMachine(); print(m.prev_vah, m.prev_val, m.session_date, m.session_open_price)"` prints `None None None None` and exits 0.
7. Wired smoke: construct `DayTypeStateMachine(prev_day_summary={"vah":4500,"val":4480,"session_date":"2026-05-23"})`, set `session_open_price=4500`, force `behavior=COMPRESSED + range_category=NORMAL`, call `_rescore_from_behavior(bar)`, assert returns `DayType.Neutral_Extreme`.
8. `ReadLints` on `state_machine.py` + `main.py` + the new test file → 0 errors.
9. No `logger.debug` on failure paths anywhere in the 2 modified files (pre-LIVE protocol).
10. No `logger.warning` rate-limit regression (the existing one in `main.py:158` for pd_context stays).

---

## §6 · Constraints (mega-prompt MUST include)

- Use the inline-import pattern (`from backend.v9.systems.day_type.neutral_classifier import classify_neutral_subtype` INSIDE `_rescore_from_behavior`). Do NOT add a top-of-file import to `state_machine.py` for this — matches the Stream 1 convention.
- The new `prev_day_summary` parameter is **the last kwarg** in `__init__`. Do not reorder existing kwargs.
- Do NOT add new instance fields beyond the 4 listed in §2.1 Edit A. No "while I'm here" refactors.
- Do NOT modify `BarInput` schema. The 4 fields live on the machine, not on the bar.
- Do NOT modify the deprecated `DayType.Neutral` enum member. It stays as a back-compat alias for legacy DB rows.
- Do NOT touch `_check_reeval`, `_behavior_agrees_with_type`, `_range_aligns_with_type`. Stream 1 already updated those.
- Do NOT touch the `PLAYBOOK_TEMPLATES`, `DAY_TYPE_LOOKUP` constants. Stream 1 already updated.
- `main.py` edit must wrap the `load_tpo_previous_day_summary()` call in `try/except` with a `logger.warning` (not debug) on failure. Production protocol — never silent-fail on a startup load.
- Use `now_et().date().isoformat()` for `session_date` to match the canonical clock pattern (matches Stream 1 fix-up `a58ee61` in `api.py`).

---

## §7 · Stop signals (CC must abort and ask Michael)

1. If `prev_day` module signature has changed since `689ac41` (i.e., `load_tpo_previous_day_summary` no longer returns dict with `vah`/`val`).
2. If `DayTypeStateMachine.__init__` already has a `prev_day_summary` parameter (already wired by another commit).
3. If `_rescore_from_behavior` body has shifted off lines 537-549 (any non-Stream-1.5 commit landed between this handoff and exec).
4. If line 547 currently is something OTHER than `return DayType.Neutral` (Stream 1 deferred this; if it's already changed, something is wrong).
5. If `backend/main.py` `_load_previous_day_context` no longer exists or moved (suggests recent refactor not accounted for).
6. If the existing test suites already had `prev_day_summary` fixtures (suggests duplicate work).

---

## §8 · Out of scope · explicitly deferred

- **Hydration of `session_open_price` from existing DB** for mid-session restarts. The new code captures from the first bar of the current process; if FastAPI restarts mid-session, `session_open_price` will be the open of whatever bar arrives first post-restart, NOT the true 09:30 open. This is a known limitation matching the existing IB seeding pattern (`maybe_seed_ib_from_tpo`). **Defer to a follow-up Pkg** if/when SHADOW UAT shows this mattering. Document as a known limitation in the commit message.
- **Removing the deprecated `DayType.Neutral` enum value.** Stays as alias for legacy DB rows.
- **Changing the `targets_table` alias mapping.** `"Neutral"` → `"Neutral_Center"` stays as-is.
- **Stream 2 work** (day_type_targets module, T1Setup t3_price, opening_type→day_type fix). Independent. Different handoff.

---

## §9 · Mega-prompt sanity checklist (for Claude Desktop)

Before generating the mega-prompt, Desktop must verify the handoff contains:

- [x] Exact line numbers and file paths for all edits
- [x] Forbidden zone clearly defined with git diff verification recipe
- [x] Backward-compat acceptance criterion (constructor with no args)
- [x] Inline-import constraint (matches Stream 1 convention)
- [x] try/except on `load_tpo_previous_day_summary` in `main.py` (no silent startup fail)
- [x] Canonical clock for `session_date` (`now_et().date().isoformat()`)
- [x] 8 minimum tests with concrete numerics (VAH=4500, VAL=4480, opens 4500/4480/4490)
- [x] No BarInput schema change (4 fields on machine, not on bar)
- [x] Mid-session-restart limitation explicitly out-of-scope + acknowledged

---

## §10 · After exec

CC commits locally with message:

```
feat(s1.5): wire prev_day summary + rewrite line 547 NeuE/NeuC classification

- Add prev_day_summary kwarg to DayTypeStateMachine.__init__ (additive, optional)
- Add 4 instance fields: prev_vah, prev_val, session_date, session_open_price
- Capture session_open_price from first bar in _stage_a1
- Replace `return DayType.Neutral` in _rescore_from_behavior with
  classify_neutral_subtype() call (D-091.Q1 logic, fallback to NeuC)
- Wire main.py P5.1.2 to load TPO prev_day summary at startup
- 8+ new tests under tests/v9/systems/test_day_type/test_rescore_neutral_subtype.py

Known limitation: session_open_price not hydrated from DB on mid-session restart
(captures from first post-restart bar). Defer to follow-up if SHADOW UAT flags.

Pkg 3a Stream 1.5 · D-091 Option B · unblocks deprecating `DayType.Neutral` path.
```

Then Cursor G3 reviews per §5 acceptance criteria.

---

*Drafted by Cursor agent · 2026-05-23 21:05 IL · post-Stream-1 G3 PASS*
