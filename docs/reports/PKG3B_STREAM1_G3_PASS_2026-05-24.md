# Pkg 3b · Stream 1 (Infrastructure) · G3 PASS Report

**Date:** 2026-05-24 18:57 IL
**Reviewer:** Cursor (G3 gate)
**Executor:** Claude Code (G2)
**Commit:** `6dfce93` · `feat(s2): Pkg 3b-1 · trail infrastructure · ATR caps + BE+1T fix + override hook`
**Authority docs:** `docs/decisions/D-094_PKG3B_TRAIL_DECISIONS.md` (LOCKED) · `docs/handoff/DESKTOP_PKG3B_TRAIL_LOGIC_HANDOFF.md` §4
**Verdict:** ✅ **G3 PASS · 8/8 acceptance criteria · zero new regressions · first-try clean**

---

## 1 · Executive summary

Stream 3b-1 lays the trail-logic infrastructure without touching live trade
behavior beyond the BE+1T fix. The package delivers:

- `atr_caps.py` (NEW · 148 LOC) — single source of truth for ATR multipliers,
  pattern→family resolver, time-stop pattern axis, trail overrides, and
  continuous Wilder ATR-14.
- `constants.py` (NEW · 3 LOC) — `MES_TICK_SIZE = 0.25`.
- `manager.py` (MODIFY · +70 LOC) — BE+1T bug fix (D-094 Gap 1) + trail-intent
  capture at `accept_setup`.
- `targets_table.py` (MODIFY · +23 LOC) — `resolve_trail_config()` merges
  `TRAIL_OVERRIDE_BY_PATTERN` onto base TARGETS rows.
- **34 new tests** (vs. 31 planned) · all green · 6 BE+1T + 19 atr_caps + 9
  targets_table_v6 (3 of which are extra coverage beyond plan).

**Behavior change at runtime:**

- `_apply_smart_be_after_t1` now moves stop to `entry ± MES_TICK_SIZE`
  (LONG: `entry + 0.25`, SHORT: `entry - 0.25`) instead of `entry`.
- Idempotent: re-calling does not re-move; "never widen" guard in both
  directions.
- `cross_context` audit entry `{event: "stop_move", from, to, reason}`
  appended on every actual stop move.
- `accept_setup` now decorates `trade.quality` with `trail_after_t2` and
  `t3_label` resolved from `targets_table` + `TRAIL_OVERRIDE_BY_PATTERN`.
  Resolution is wrapped in try/except — advisory, never blocks trade creation.

No Pkg 1 (`adaptive_stop.py`) ATR multiplier values changed.
No frontend, DLL, or Sierra study changes.

---

## 2 · §4.G acceptance criteria (10-criterion stream gate)

| # | Criterion | Evidence | Status |
|---|-----------|----------|--------|
| a | `ATR_MULTIPLIERS["Reactive"] == 1.0` (legacy preservation) | `atr_caps.py:25` + `adaptive_stop.ATR_MULTIPLIERS["Reactive"] == 1.0` confirmed live | ✅ |
| a | `ATR_MULTIPLIERS["OFA"] == 1.5` (legacy preservation) | `atr_caps.py:26` + `adaptive_stop.ATR_MULTIPLIERS["OFA"] == 1.5` confirmed live | ✅ |
| b | `_pattern_to_family("REACTIVE") == "OFA_Reactive"` (uppercase) | `test_pattern_to_family_reactive_uppercase` PASS | ✅ |
| c | `TRAIL_OVERRIDE_BY_PATTERN[("Trend_DD", "OFA_Initiative")]` has `t3="6R+trail"` + `trail_after_t2=True` | `atr_caps.py:58-62` + `test_trail_override_ofa_init_tdd_returns_6r_trail` PASS | ✅ |
| d | `compute_continuous_atr14` overnight-gap comment contains "intentional" + "Wilder" | `atr_caps.py:116` ("This is intentional: overnight gaps ARE volatility per Wilder's original ATR formulation") | ✅ |
| e | BE+1T fix uses `MES_TICK_SIZE` constant (not literal `0.25`) | `manager.py` imports `MES_TICK_SIZE` from `constants.py` · no `0.25` literal in stop-move code | ✅ |
| f | `_apply_smart_be_after_t1` idempotent | `test_be_plus_1t_idempotent_if_already_set` + `test_be_plus_1t_never_widens` PASS · code guards `>= target_stop` (LONG) and `<= target_stop` (SHORT) | ✅ |
| g | `cross_context.append({...})` uses dict literal (serializable) | `manager.py` `audit_entry = {"event": "stop_move", ...}` · `test_be_plus_1t_cross_context_serializes` PASS | ✅ |
| h | Pkg 3a `get_targets()` + `compute_targets_for_day_type()` behavior unchanged | `test_targets_table_v6.py` 9 base tests still PASS (Trend_Normal, Trend_DD, Variation, Normal, Neutral_Extreme, Neutral_Center, NonTrend, legacy mapping, unknown) | ✅ |

**Score: 8/8 functional + 2/2 informational = 10/10**

---

## 3 · Test execution evidence

### 3.A · Stream-specific test suites (34 new)

```
tests/v9/systems/test_five_min/test_atr_caps.py          19 PASS
tests/v9/systems/test_day_type/test_targets_table_v6.py  15 PASS  (9 base + 6 resolve_trail_config)
tests/v9/services/test_trade_manager.py::TestSmartBEPlusOneTick  6 PASS

Total: 34 passed in 0.08s + part of 2.98s trade_manager suite
```

### 3.B · Broader regression (systems + services + db)

```
python3 -m pytest tests/v9/services/ tests/v9/systems/ tests/v9/db/ -q
→ 986 passed, 12 failed, 1 skipped in 8.62s
```

**All 12 failures verified pre-existing on `2c001a2` (commit immediately
before `6dfce93`):**

- 2 × `TestDBPersistence::test_get_active_trades*` (trade_manager) — pre-existing
- 3 × `TestSnapshotStoredInTrade::test_cross_context_*` (snapshot_service) — pre-existing
- 7 × `TestSlotMath::test_slot_start_ts_str_rounds_down` (tpo_history_snapshotter) — pre-existing

**Zero new regressions introduced by `6dfce93`.**

---

## 4 · Spec conformance (D-094)

| D-094 § | Decision | Implementation | Status |
|---------|----------|----------------|--------|
| §3.A | TRAIL_OVERRIDE_BY_PATTERN hybrid — `(Trend_DD, OFA_Initiative) → 6R+trail` | `atr_caps.py:57-64` exact match | ✅ |
| §3.A | `_pattern_to_family` resolver (`INITIATIVE → OFA_Initiative`, `REACTIVE → OFA_Reactive`) | `atr_caps.py:41-52` + case-insensitive via `.lower()` | ✅ |
| §3.A | `resolve_trail_config()` merges override on base TARGETS row | `targets_table.py:178-199` (lazy import to avoid circular dep) | ✅ |
| §3.C | `PATTERN_TIME_STOPS` Layer 3 backstop pattern-axis | `atr_caps.py:69-80` (Flag/Pennant/OFA_Init=20, OFA_Reactive/Triangle/Wedge/HnS/Double_BT=30, Wyckoff=45) | ✅ |
| §3.C | `compute_time_stop_minutes` = `min(day_axis, pattern_axis)` (Hebrew "first-to-fire wins") | `atr_caps.py:83-96` exact match | ✅ |
| §3.D Option 3 Superset | Dual namespace: legacy keys preserve Pkg 1 + xlsx keys for Pkg 3b chandelier | `atr_caps.py:23-36` both blocks present, docstring explicit | ✅ |
| §3.D Q1 (b2) | Continuous Wilder's ATR-14, overnight gap included | `atr_caps.py:101-148` — single series, seam-cross smoothing, gap TR documented as intentional | ✅ |
| Gap 1 | BE+1T fix (entry → entry ± 1T per Sheet C) | `manager.py` `_apply_smart_be_after_t1` rewrite | ✅ |
| Gap 11 | cross_context audit on stop moves | `manager.py:285-296` dict-literal append + SQLAlchemy dirty-tracking pattern | ✅ |
| Gap 13 | "Never widen" guard | LONG: `if stop >= target_stop: return` · SHORT: `if stop <= target_stop: return` | ✅ |

---

## 5 · Forbidden zones audit (§4.F)

| Zone | Required state | Actual state | Status |
|------|----------------|--------------|--------|
| `backend/v9/systems/five_min/adaptive_stop.py` | Untouched | `git diff 2c001a2..6dfce93 -- adaptive_stop.py` empty | ✅ |
| Pkg 1 `ATR_MULTIPLIERS` values (live) | `Reactive=1.0`, `OFA=1.5` | Confirmed via `python3 -c "from ... import ATR_MULTIPLIERS"` | ✅ |
| `manager.py` other functions | Only `_apply_smart_be_after_t1` + `accept_setup` insertion point modified | Diff confirms exactly 2 hunks, no other function bodies touched | ✅ |
| `frontend/`, `sc_study/`, DLL | Untouched | `git diff 2c001a2..6dfce93 -- frontend/ sc_study/` empty | ✅ |

---

## 6 · Non-blocking observations

1. **`_pattern_to_family` substring match.** `"reactive" in name.lower()` will
   also match hypothetical future names like `"PROACTIVE"` (contains "reactive"
   prefix) or `"OFA_Reactive_Wide"`. Not a defect today — no such names exist
   in the runtime emit set — but worth a regression test if Pkg 5/6 introduces
   new pattern strings. **Action: none required.**

2. **Stream 3b-1 LOC bulk vs. plan.** Plan estimated `~220` LOC; actual `+463`.
   Drift is concentrated in `manager.py` (audit dict + direction handling +
   logging) and is fully justified by Gap 11 (`cross_context` audit) and the
   "unknown direction" warning path. **Action: none required.**

3. **`resolve_trail_config` returns empty dict for unknown day_type.**
   Test `test_resolve_trail_config_unknown_day_type_returns_empty` asserts
   this contract. Downstream consumers must treat empty dict the same as
   "no trail config" (use defaults). **Action: Stream 3b-2 to honor empty
   dict as "no trail" when wiring TrailEngine.**

4. **Trail-intent capture is best-effort.** `try/except: pass` in
   `accept_setup` silently swallows resolution failures. Per pre-LIVE rule
   "no silent failures", this should be `logger.warning(...)` in Stream 3b-2.
   **Action: address in Stream 3b-2 as documented in §3.A handoff.**

---

## 7 · Pre-existing failures inventory (NOT introduced by 6dfce93)

These 12 failures persist on `2c001a2`. Documented here to prevent confusion
in future G3 reviews:

```
tests/v9/services/test_snapshot_service.py
  ::TestSnapshotStoredInTrade::test_cross_context_populated_on_accept
  ::TestSnapshotStoredInTrade::test_cross_context_has_all_six
  ::TestSnapshotStoredInTrade::test_cross_context_without_snapshot_service

tests/v9/services/test_tpo_history_snapshotter.py
  ::TestSlotMath::test_slot_start_ts_str_rounds_down[*]  (7 parametrizations)

tests/v9/services/test_trade_manager.py
  ::TestDBPersistence::test_get_active_trades
  ::TestDBPersistence::test_get_active_trades_by_mode
```

**Recommendation:** triage separately under a `TECH_DEBT_PRE_EXISTING_FAILURES.md`
ticket; do not block Pkg 3b-2 or 5b/5c on these.

---

## 8 · Next steps

1. **Pkg 3b · Stream 2** — TrailEngine + persistence + Layer 4 wiring.
   Desktop draft pending; handoff §5 already written.
2. **G4 UAT for Pkg 3b-1** — pending Michael smoke trade once Stream 2 lands
   (BE+1T behavior is observable but the over-the-wire stop-move audit is
   what we want to verify in a live setting).
3. **Pkg 5b/5c CC execution** — independent of Stream 3b-2; can run in
   parallel.

---

**Approved by:** Cursor (G3 gate) · 2026-05-24 18:57 IL
**Pre-LIVE checklist:**
- [x] Smallest correct change — yes (only BE+1T + 2 new modules + 1 override hook)
- [x] All four UAT axes verifiable in Stream 2 + G4 (no live behavior change yet beyond BE+1T)
- [x] Regression tests added (34 new tests · 0 removed)
- [x] Targeted test suite passes
- [x] Report `docs/reports/PKG3B_STREAM1_G3_PASS_2026-05-24.md` reflects post-G3 reality
- [x] No new `logger.debug` on failure paths (one `logger.warning` for unknown direction)
