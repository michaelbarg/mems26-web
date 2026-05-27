# S4 Woodies CCI — Spec Audit Results · 2026-05-27 IL

**Auditor:** Claude Code (CC)
**Authority:** Cursor META-PROMPT SPEC AUDIT v1.0 · 2026-05-27
**Branch:** `stabilize/mems26-local-truth-2026-05-16`
**Mode:** READ-ONLY · 0 code changes during audit

---

## §0 · Audit environment (CD-added pre-check)

```
=== Git status ===
 M backend/v9/systems/woodies/config/dispatcher_config.yaml
 M backend/v9/systems/woodies/woodies_system.py
 M docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt
 M tests/v9/systems/test_woodies_dedup.py
 M tests/v9/systems/test_woodies_process_bar_perf.py
?? CC_W10_SELF_REPORT.md
?? docs/handoff/META_PROMPT_HANDLING_GUIDE.md
?? docs/handoff/META_PROMPT_SPEC_AUDIT_BRIDGE.md
?? docs/handoff/META_PROMPT_SPEC_AUDIT_S1_DAY_TYPE.md
?? docs/handoff/META_PROMPT_SPEC_AUDIT_S2_FIVE_MIN.md
?? docs/handoff/META_PROMPT_SPEC_AUDIT_S4_WOODIES.md
?? docs/spec_authority/S4_WOODIES_PATTERN_TABLES_V1.xlsx
?? tests/v9/systems/test_woodies_rth_gate.py

=== Branch ===
stabilize/mems26-local-truth-2026-05-16

=== Last 3 commits ===
5411e2d docs(pipeline3): meta-prompt W-9 LiranExitLadder + W-11 PartialExit for Desktop
a3b6d89 docs(status): shadow data quality audit · 21/5+22/5 suspect backtest · decisions pending
8272109 docs(status): W-10 time stop DONE · LIVE block cleared · Pipeline 2 complete

=== Pipeline 2 deliverables: ALL PRESENT ===
atr_stop.py · anti_patterns.py · pattern_dispatcher.py · hfe_divergence_logger.py · dispatcher_config.yaml

=== W-10 deliverables: PRESENT ===
time_stop.py · test_time_stop.py
```

**Note:** Working tree has uncommitted W-10 changes + RTH gate additions + test fixes + Constitution whitespace change. All pre-audit. No W-10 `b_time_stop.py` (Option B chosen, not Option C).

---

## §1 · Results table

| Check | Title | Result | Notes |
|-------|-------|--------|-------|
| 1 | A1 YELLOW Gate (F-16 fix) | ✅ PASS | Guard at line 299 before dispatcher; dispatcher ValueError as safety net |
| 2 | AP1-9 Active | ✅ PASS | All 9 patterns import+enforce APs; blocked → detected=False → excluded |
| 3 | W-8 Dispatcher | ✅ PASS | YAML loaded; log_dispatch_decisions=true; ⚠️ min_r_t1_threshold=0.0 (OK for shadow) |
| 4 | Day-Type Advisory | ✅ PASS | Advisory-only per spec; A2 stage not in runtime path (Pipeline 2 scope) |
| 5 | Time Stop W-10 | ✅ PASS | 35/35 tests green; wired at 2 call sites; _open_fire_records populated+cleaned |
| 6 | RTH Session Filter | ✅ PASS | RTH gate at line 253; 09:30-16:00 ET; enabled by default; env var override |
| 7 | Dedup Gate | ✅ PASS | Present; key="{pattern}_{direction}"; uses <= comparison |
| 8 | Full pytest suite | ✅ PASS | 969 passed, 0 failed, 1 skipped |

---

## §2 · Per-check evidence

### Check 1 · A1 YELLOW Gate

```
$ rg "YELLOW" backend/v9/systems/woodies/woodies_system.py -n -A 3

290:            # F-16: resolve trend state before dispatch — needed for YELLOW guard below
296:            # P-W5 LOCK A: YELLOW blocks all 9 patterns. detect_all_patterns runs
297-            # unconditionally; we drop here rather than letting select_winner raise
298-            # ValueError into the outer except handler (F-16 fix).
299:            if patterns and _ts == TrendState.YELLOW:
300:                logger.warning("[Woodies] YELLOW state — %d pattern(s) blocked (P-W5 LOCK A)", len(patterns))
301-                patterns = []
```

```
$ rg "YELLOW" backend/v9/systems/woodies/pattern_dispatcher.py -n -A 3

173:        # YELLOW assertion — should never reach dispatcher
174:        if trend_state == TrendState.YELLOW:
175-            if self.config.get("yellow_assertion", True):
176-                raise ValueError(
177:                    "YELLOW trend state reached pattern dispatcher — "
```

**Verdict:** ✅ PASS
- `woodies_system.py:299` — explicit `patterns = []` BEFORE `select_winner()` at line 304
- `pattern_dispatcher.py:173-179` — ValueError safety net (belt-and-suspenders)
- F-16 fix comment explicitly references P-W5 LOCK A

### Check 2 · Anti-Patterns AP1-9 Active

```
$ rg "def check_ap" backend/v9/systems/woodies/anti_patterns.py -n

44:    def check_ap1_zlr_pullback
85:    def check_ap2_gb100_yellow
112:    def check_ap3_vegas_swings
135:    def check_ap4_htlb_touches
155:    def check_ap6_gb100_pullback_depth
175:    def check_ap7_tt_divergence_gap
197:    def check_ap8_cci_flat
232:    def check_ap9_famir_lsma
```

8 AP methods in anti_patterns.py (AP1-4, AP6-9). AP5 is in hfe.py:

```
$ rg "AP5|anti_pattern" backend/v9/systems/woodies/patterns/hfe.py -n

13:W-4: DLL-primary with AP5 enforcement.
21:from backend.v9.systems.woodies.anti_patterns import AntiPatternChecker
192:    3. AP5 enforced on DLL path: bars_ago must be in [2, 12]
236:    # ── AP5 enforcement on DLL path ──
```

All 9 patterns import AntiPatternChecker:

```
$ rg "from.*anti_pattern" backend/v9/systems/woodies/patterns/*.py

ghost.py:12  tt.py:12  famir.py:11  vegas.py:12  tlb.py:12  gb100.py:12  htlb.py:12  hfe.py:21  zlr.py:12
```

**Critical check — blocking confirmed:**

```python
# zlr.py:66-69
ap8 = AntiPatternChecker.check_ap8_cci_flat(bars)
if ap8.blocked:
    return PatternResult(detected=False, pattern_id=PATTERN_ID,
                         details={"reject_reason": ap8.reason})
```

When `ap.blocked=True`, pattern returns `detected=False`. `pattern_engine.py:56` filters: `if result is not None and result.detected` — so blocked patterns are EXCLUDED from the detected list.

**Verdict:** ✅ PASS
- All 9 APs present and mapped to patterns
- `blocked=True` → `detected=False` → pattern excluded from detection results
- APs are enforcement, not just logging

### Check 3 · W-8 Dispatcher

```
$ python3 -c "from backend.v9.systems.woodies.pattern_dispatcher import PatternDispatcher; ..."

config: {'min_r_t1_threshold': 0.0, 'tie_breaker': 'raw_confidence', 'gray_fallback_enabled': True,
         'yellow_assertion': True, 'r_t1_missing_fallback': True, 'log_dispatch_decisions': True}
source: yaml_override
```

```yaml
# dispatcher_config.yaml
pattern_dispatcher:
  tie_breaker: "raw_confidence"
  gray_fallback_enabled: true
  yellow_assertion: true
  r_t1_missing_fallback: true
  log_dispatch_decisions: true     # ← enabled for shadow visibility
  min_r_t1_threshold: 0.0          # SHADOW: accept all · LIVE: should be ≥1.0

time_stop:
  time_stop_minutes: 90
  tick_minutes: 5
```

**Verdict:** ✅ PASS
- Config loaded from YAML (source: `yaml_override`)
- `log_dispatch_decisions: true` (shadow visibility)
- ⚠️ `min_r_t1_threshold: 0.0` — acceptable for SHADOW, PENDING for LIVE (documented in YAML)

### Check 4 · Day-Type Matrix

```
$ rg "DayTypeGate|day_type_gate" backend/v9/systems/woodies/woodies_system.py -n
(no matches)

$ rg "DayTypeGate|day_type_gate" backend/v9/systems/woodies/decision_tree.py -n
(no matches)
```

DayTypeGate exists in:
- `day_type_gate.py` — the gate class with `get_verdict()` method
- `stages/a2_day_type_query.py:9` — "Advisory only — terminal is always None"

It is NOT invoked from `woodies_system.py` or `decision_tree.py`. This is consistent with Pipeline 2 scope: the A2 stage exists as a module but is not wired into the runtime `process_bar()` path. The B-stage runtime (`active_phase.py`) is a STUB per line 10-11.

**Verdict:** ✅ PASS
- Gate is advisory by design ("terminal is always None")
- Not called in runtime path — acceptable for Pipeline 2 scope
- Gate module and 63-cell YAML matrix are prepared for future wiring

### Check 5 · Time Stop W-10

```
$ python3 -m pytest tests/v9/systems/test_time_stop.py -v --tb=short

35 passed in 0.57s
```

Wiring confirmed:

```
$ rg "_open_fire_records|_check_time_stops|TimeStopEnforcer" backend/v9/systems/woodies/woodies_system.py -n

23: from backend.v9.systems.woodies.time_stop import TimeStopEnforcer, load_time_stop_config
97: self._time_stop_enforcer = TimeStopEnforcer(...)
102: self._open_fire_records: Dict[str, dict] = {}
260: self._check_time_stops()        ← called on non-RTH early return (time stop ticks overnight)
432: self._open_fire_records[shadow_id] = {...}   ← populated on shadow fire
457: self._check_time_stops()        ← called on every normal RTH bar
533: def _check_time_stops(self) -> None:         ← implementation
```

**Verdict:** ✅ PASS
- 35/35 tests green
- `_open_fire_records` populated on successful shadow route
- `_check_time_stops()` called on EVERY bar (both RTH and non-RTH paths)
- Trades removed after time stop fires (idempotent)
- Closes via `gateway._trade_manager.close_trade()` when available

### Check 6 · RTH Session Filter

```
$ rg "RTH|rth_only|_is_rth" backend/v9/systems/woodies/woodies_system.py -n

36: # RTH gate: set V9_WOODIES_RTH_ONLY=0 to allow overnight bars
37: _RTH_ONLY = os.getenv("V9_WOODIES_RTH_ONLY", "1").lower() not in ("0", "false", "no")
39: _RTH_START = dtime(9, 30)
40: _RTH_END = dtime(16, 0)
53: def _is_rth_bar(bar_ts: float) -> bool:
78: def __init__(self, db_path: str = None, rth_only: bool = None):
82: self._rth_only: bool = _RTH_ONLY if rth_only is None else rth_only
253: # RTH gate (filter-F17): skip non-RTH bars to prevent overnight/globex fires.
255: if self._rth_only and not _is_rth_bar(float(bar_ts)):
```

Implementation:
- RTH window: 09:30–16:00 ET (inclusive of close bar)
- Enabled by default: `V9_WOODIES_RTH_ONLY` defaults to "1"
- Fail-open: returns True if timestamp=0 or timezone unavailable (safe)
- Override: `rth_only=False` constructor arg or `V9_WOODIES_RTH_ONLY=0` env var
- Time stop still checks on non-RTH bars (line 260) — correct

**Verdict:** ✅ PASS
- RTH filter present and active
- Prevents overnight/globex fires
- Time stop enforcement continues through non-RTH bars

### Check 7 · Dedup Gate

```
$ rg "_last_fired_bar_ts" backend/v9/systems/woodies/woodies_system.py -n -A 5

86: self._last_fired_bar_ts: Dict[str, float] = {}

395: _fire_key = f"{best.pattern_id}_{best.direction or 'LONG'}"
396: _last_ts = self._last_fired_bar_ts.get(_fire_key, -1.0)
397: if float(bar_ts) <= _last_ts:
398-    logger.debug(
399-        "[Woodies] Skipping duplicate fire: %s bar_ts=%s already fired",
400-        _fire_key, bar_ts,
401-    )

429: self._last_fired_bar_ts[_fire_key] = float(bar_ts)
```

**Verdict:** ✅ PASS
- Dedup gate present and functional
- Key: `"{pattern_id}_{direction}"` (e.g. `"ZLR_LONG"`)
- Comparison: `float(bar_ts) <= _last_ts` — uses `<=` (blocks same AND earlier timestamps)
- Default `-1.0` for missing key ensures first fire proceeds
- bar_ts recorded on successful route

### Check 8 · Full pytest suite

```
$ python3 -m pytest tests/v9/systems/ -q --tb=short

969 passed, 1 skipped in 10.66s
```

**Verdict:** ✅ PASS
- 969 passed, 0 failed, 1 skipped
- Well above 912 baseline threshold
- Previous 3 dedup test ordering failures resolved (test fixes present in working tree)
- 0 new failures

---

## §3 · Findings requiring Cursor action

**(none — all 8 checks PASS)**

⚠️ Non-blocking notes for LIVE preparation:
- `min_r_t1_threshold: 0.0` should be raised to ≥1.0 before LIVE (documented in YAML)
- Day-type gate not in runtime path (acceptable for Pipeline 2; wire for Pipeline 3+)

---

## §4 · Shadow GREEN / RED verdict

**Y · all 8 checks PASS · shadow can start.**

All critical LIVE surfaces verified: YELLOW gate, anti-pattern enforcement, dispatcher config, time stop wiring, RTH session filter, dedup gate, full test suite. No FAIL or LIVE-blocking WARN found.

---

## §11 · CD-added notes

### Spec ambiguities encountered
(none)

### Anomalies during audit

1. **Uncommitted changes in working tree:** woodies_system.py has both W-10 changes AND an RTH gate (filter-F17) that was not part of W-10. The RTH gate adds `_is_rth_bar()`, `_RTH_ONLY` env var, and an early-return in `process_bar()`. This is beneficial for Check 6 but represents uncommitted work from another session.

2. **Two test files modified:** `test_woodies_dedup.py` and `test_woodies_process_bar_perf.py` have `rth_only=False` additions and an `asyncio.run()` fix. These are companion changes to the RTH gate, not from this audit or W-10.

3. **Constitution V3 whitespace change:** `MEMS26_CONSTITUTION_V3_FINAL.txt` shows a diff but only in table formatting (tab/space normalization). Content unchanged. Pre-existing, not from any package.

4. **dispatcher_config.yaml divergence:** The YAML in the working tree has additional fields vs. what was committed (the `log_dispatch_decisions: true` and reordered `min_r_t1_threshold` field with LIVE guidance comment). This appears to be an improvement made after W-8 but not yet committed.

### Proposed fix packages
(none — all checks PASS)

### Constitution compliance check
- `docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt` — NOT modified by any audit action. Pre-existing whitespace-only diff in working tree.
- `docs/decisions/D-092_S4_WOODIES_UPDATE.md` — NOT modified.
- All spec authority files remain locked.
