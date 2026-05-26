# Pkg 3b · Trail Logic (Post-T2 Trade Management)

**Authority:** D-094 (LOCKED 2026-05-24) · D-091 (S2 LIVE) · Master Sheet 2 (S2_Master_Summary.xlsx) Sheet C STOP STRATEGY · Sheet D 8 PRIORITIES · Constitution V3 PART 5 B11+B12
**Predecessor:** Phase A bundle complete (Pkg 0+1+2a+2bc+3a Streams 1/1.5/2 all G3 PASS) · HEAD = `cf6383e`
**Status:** Spec LOCKED · Cursor handoff ready for Claude Desktop to convert to CC MEGA-prompt(s)
**Estimated CC time:** ~6-8 hours total · suggested split across 3 streams (~2-3h each)
**Phase classification:** Phase A mechanical · DEMO+ parametric calibration (per D-094 §4 commit message flag)

---

## §1 · Why this exists

Pkg 3b ships the **post-T2 trade management mechanics** that were deferred from Pkg 3a (which only shipped target-table + day-type wiring). After T1/T2 are hit, the trade currently has no active trail — Pkg 3b adds:

1. **BE+1T fix** at T1 hit (bug fix · Pkg 3a's existing `_apply_smart_be_after_t1` puts stop at BE, not BE+1T)
2. **HL/LH trail** post-T2 (5-bar lookback · structural)
3. **ATR chandelier** post-T2 (continuous Wilder's ATR-14 · volatility-aware)
4. **Pattern override hook** (OFA Initiative on TDD → 6R+trail per Sheet A row 14)
5. **5 Layer 4 service wires** (MFE peak · CCI24 flat · TCCI cross · SWI · day_type_targets_verify · all exist as dead code today)
6. **3-layer defense in depth**: MFE tighten (L1) → HL/LH trail (L2) → time_stop backstop (L3 · `min(day, pattern)`)
7. **Persistence + audit trail**: `trade.quality["trail_state"]` JSON + `cross_context` events with `json.dumps(default=str)`
8. **Restart recovery + concurrency** (Sierra tick fills always win over trail compute)

D-094 §1-§4 contains the full decision rationale and ALL specs (verbatim xlsx + Michael's locks). **Read D-094 first.** This handoff focuses on the executable scope.

---

## §2 · Spec authority hierarchy

1. **D-094** (locked decisions · supersedes earlier docs where they conflict)
2. **`MEMS26_V9_Pattern_Tables_Enhanced.xlsx`** Sheet C (STOP STRATEGY · ATR caps) + Sheet D (8 PRIORITIES · exit triggers · time_stop)
3. **Constitution V3 PART 5 B11+B12** (MFE peak 80% tighten · day-type targets verify)
4. **Pkg 3a code outputs** (`targets_table.py` · DO NOT REGRESS · only ADD `TRAIL_OVERRIDE_BY_PATTERN` + `resolve_trail_config()`)
5. **Pkg 1 code outputs** (`adaptive_stop.py` · 3 ATR functions + `ATR_MULTIPLIERS` · keep legacy keys per D-094 §3.D ripple Option 3 Superset)

---

## §3 · SCOPE · Stream-organized

Pkg 3b is large (~1115 LOC + ~87 tests). Suggested 3-stream split (each is independently testable; later streams depend on earlier):

| Stream | Focus | LOC est | Tests est | CC time | Depends on |
|--------|-------|---------|-----------|---------|------------|
| **3b-1 · Infrastructure** | `atr_caps.py` module · BE+1T fix · Pkg 3a override hook | ~310 LOC | ~28 tests | ~2h | none (only Pkg 3a HEAD) |
| **3b-2 · TrailEngine + persistence** | `TrailEngine` class · HL/LH · chandelier · trail_state · cross_context · restart · concurrency | ~430 LOC | ~28 tests | ~3h | 3b-1 |
| **3b-3 · Layer 4 wiring** | Wire 5 existing services in order · update Sheet D doc | ~375 LOC | ~30 tests | ~2-3h | 3b-2 |

Each stream gets a separate Desktop MEGA-prompt. The G3 review on a finished stream can run concurrently with CC executing the next.

---

## §4 · Stream 3b-1 · Infrastructure

### §4.A · NEW · `backend/v9/systems/five_min/atr_caps.py` (~150 LOC)

The single source of truth for ATR-cap multipliers, pattern→family resolution, time_stops, and trail overrides. Imported by Pkg 1 (legacy keys), Pkg 3a (overrides), and Pkg 3b TrailEngine (xlsx-aligned keys + time_stops).

```python
"""ATR caps · pattern family resolution · time_stops · trail overrides.

D-094 §3.D dual-namespace pattern (Option 3 Superset):
- Legacy keys ("Reactive" / "OFA" / "Flag" / "Double_BT" / "HnS") preserve
  Pkg 1's shipped entry-stop behavior. DO NOT change values without
  Michael lock + D-094 amendment.
- xlsx-aligned keys ("OFA_Reactive" / "OFA_Initiative" / "Pennant" /
  "Wedge" / "Triangle") match Sheet C verbatim. Used by Pkg 3b chandelier
  and future Pkg 5a-c patterns. Future Pkg 1-rev (post-SHADOW) may
  migrate Pkg 1 to xlsx-aligned values.

D-094 §3.A: TRAIL_OVERRIDE_BY_PATTERN bridges Pkg 3a's day-type-only
targets_table with xlsx Sheet A row 14 (OFA Initiative on TDD → 6R+trail).

D-094 §3.C: PATTERN_TIME_STOPS implements Sheet D row 14 pattern-axis
time_stop. Layer 3 backstop in 3-layer trade management.
"""

from typing import Optional

# === ATR multipliers · single source of truth (D-094 §3.D ripple Option 3) ===

ATR_MULTIPLIERS = {
    # Pkg 1 legacy keys (entry stop · current shipped behavior · DO NOT change)
    "Reactive": 1.0,            # Pkg 1 REACTIVE entry stop
    "OFA": 1.5,                 # Pkg 1 INITIATIVE entry stop
    "Flag": 1.5,
    "Double_BT": 2.0,
    "HnS": 2.0,
    # xlsx-aligned keys (Sheet C · Pkg 3b chandelier · future Pkg 5+ patterns)
    "OFA_Reactive": 1.5,
    "OFA_Initiative": 2.0,
    "Pennant": 1.5,
    "Wedge": 2.0,
    "Triangle": 2.0,
}

# === Pattern→family canonical name resolver (D-094 §3.A) ===

def _pattern_to_family(pattern_name: str) -> Optional[str]:
    """Map runtime pattern_name to xlsx family for override + chandelier lookup.

    Runtime pattern_name comes from five_min detectors as 'REACTIVE' / 'INITIATIVE'.
    xlsx family names are 'OFA_Reactive' / 'OFA_Initiative'.
    Future Pkg 5a-c will add: 'Flag', 'Pennant', 'Wedge', 'Triangle', 'HnS', 'Double_BT'.
    """
    name = pattern_name.lower()
    if "initiative" in name:
        return "OFA_Initiative"
    if "reactive" in name:
        return "OFA_Reactive"
    return None


# === Trail overrides (D-094 §3.A · hybrid Option 3) ===

TRAIL_OVERRIDE_BY_PATTERN: dict[tuple[str, str], dict] = {
    # (day_type, pattern_family) → override fields to merge over targets_table base
    ("Trend_DD", "OFA_Initiative"): {
        "t3": "6R+trail",
        "trail_after_t2": True,
        "reason": "Dalton TDD second-leg · Sheet A row 14",
    },
    # Future Pkg 5a-c: add other (day_type, family) entries here
}


# === Pattern-axis time stops (D-094 §3.C · Layer 3 backstop) ===

PATTERN_TIME_STOPS = {
    "Flag":             20,   # Continuation
    "Pennant":          20,   # Continuation
    "OFA_Initiative":   20,   # Continuation
    "OFA_Reactive":     30,   # Reversal
    "Triangle":         30,   # Reversal default
    "Wedge":            30,   # Reversal
    "HnS":              30,   # Reversal
    "Double_BT":        30,   # Reversal
    "Wyckoff_Spring":   45,   # Wyckoff (Pkg 5+ pattern)
    "Wyckoff_Upthrust": 45,   # Wyckoff (Pkg 5+ pattern)
}


def compute_time_stop_minutes(
    day_type: str,
    pattern_family: Optional[str],
    *,
    targets_table: dict,
) -> Optional[int]:
    """Layer 3 backstop · first-to-fire wins between day-axis and pattern-axis.

    D-094 §3.C decision: min(day, pattern) honors both spec sources
    (Sheet D row 14 pattern-axis + targets_table.py day-axis).

    Args:
        day_type: e.g. 'Trend_DD', 'Variation', 'Normal'
        pattern_family: e.g. 'OFA_Initiative' (None if no family match)
        targets_table: TARGETS dict from targets_table.py (so this module
                       stays decoupled from Pkg 3a internals)

    Returns:
        Minutes to time-stop, or None if neither axis specifies one.
    """
    day_stop = targets_table.get(day_type, {}).get("time_stop_minutes")
    pat_stop = PATTERN_TIME_STOPS.get(pattern_family) if pattern_family else None
    candidates = [x for x in (day_stop, pat_stop) if x is not None]
    return min(candidates) if candidates else None


# === Chandelier ATR · continuous Wilder's smoothing (D-094 §3.D Q1 b2) ===

def compute_continuous_atr14(
    yesterday_bars: list,
    today_bars_so_far: list,
) -> Optional[float]:
    """Wilder's ATR-14 with continuous smoothing across yesterday→today seam.

    D-094 §3.D Q1 (b2) decision: a single Wilder ATR-14 series is computed
    over the concatenation `yesterday_bars + today_bars_so_far`. Smoothing
    persists across the overnight seam (no reset at session open).

    Overnight gap is included in the TR computation per Wilder canonical behavior.
    TR for today's first bar = max(today_high - today_low,
                                   abs(today_high - yesterday_last_close),
                                   abs(today_low - yesterday_last_close))
    This is intentional: overnight gaps ARE volatility per Wilder's original
    ATR formulation. ATR may be inflated on gap-up/down mornings; this is by design.
    Do NOT introduce a seam-reset that ignores overnight gaps without explicit
    spec change (see D-094 §3.D Q1).

    Args:
        yesterday_bars: ordered list of 5-min bars from prior session (at least 14)
        today_bars_so_far: ordered list of 5-min bars from current session up to now

    Returns:
        Wilder's ATR-14 as float, or None if insufficient data (<14 bars total).
    """
    all_bars = list(yesterday_bars) + list(today_bars_so_far)
    if len(all_bars) < 14:
        return None

    # Compute TR series
    trs = []
    for i, bar in enumerate(all_bars):
        if i == 0:
            # First bar of the entire series: TR = bar_range (no prev_close)
            trs.append(bar.high - bar.low)
        else:
            prev_close = all_bars[i - 1].close
            tr = max(
                bar.high - bar.low,
                abs(bar.high - prev_close),
                abs(bar.low - prev_close),
            )
            trs.append(tr)

    # Wilder's smoothing: first ATR-14 = simple average of first 14 TRs
    # Subsequent: ATR_i = ((ATR_{i-1} * 13) + TR_i) / 14
    atr = sum(trs[:14]) / 14
    for tr in trs[14:]:
        atr = ((atr * 13) + tr) / 14

    return float(atr)
```

**Tests (~15 in `tests/v9/systems/test_five_min/test_atr_caps.py`):**
1. `test_atr_multipliers_has_legacy_keys` — Reactive/OFA/Flag/Double_BT/HnS present with shipped values
2. `test_atr_multipliers_has_xlsx_keys` — OFA_Reactive/OFA_Initiative/Pennant/Wedge/Triangle present with Sheet C values
3. `test_pattern_to_family_reactive_lowercase`
4. `test_pattern_to_family_reactive_uppercase`
5. `test_pattern_to_family_initiative_lowercase`
6. `test_pattern_to_family_initiative_uppercase`
7. `test_pattern_to_family_unknown_returns_none`
8. `test_pattern_to_family_legacy_kind_REACTIVE`
9. `test_pattern_to_family_legacy_kind_INITIATIVE`
10. `test_trail_override_ofa_init_tdd_returns_6r_trail`
11. `test_trail_override_other_combos_return_none`
12. `test_compute_time_stop_min_of_both`
13. `test_compute_time_stop_day_only_when_pattern_none`
14. `test_compute_time_stop_pattern_only_when_day_none`
15. `test_compute_time_stop_both_none_returns_none`
16. `test_continuous_atr14_basic_14_bars`
17. `test_continuous_atr14_yesterday_only_at_session_open`
18. `test_continuous_atr14_includes_overnight_gap` (explicit · documents intentional Wilder behavior)
19. `test_continuous_atr14_insufficient_returns_none`

### §4.B · MODIFIED · `backend/v9/services/trade_manager/manager.py` (~30 LOC)

**Fix BE+1T bug** in `_apply_smart_be_after_t1` (D-094 Gap 1).

Locate the existing method (around line 244-263) and modify:

```python
def _apply_smart_be_after_t1(self, trade) -> None:
    """Move stop to BE+1T after T1 hit · D-094 Gap 1 fix.

    OLD behavior: stop = entry (BE) — too tight, no slippage room.
    NEW behavior: stop = entry + 1T (LONG) or entry - 1T (SHORT) per Sheet C
    'Trail logic (universal): +1R → ratchet to BE. T1 hit → stop to entry+1T'.

    Also handles the edge case where stop is ALREADY at BE+1T (idempotent · no-op).
    """
    from backend.v9.systems.five_min.constants import MES_TICK_SIZE  # = 0.25
    direction = trade.direction.upper()
    entry = float(trade.entry_price)
    tick = MES_TICK_SIZE
    if direction == "LONG":
        target_stop = entry + tick
        # Only move if tighter (per Gap 13 'never widen')
        if trade.stop is None or trade.stop < target_stop:
            trade.stop = target_stop
    elif direction == "SHORT":
        target_stop = entry - tick
        if trade.stop is None or trade.stop > target_stop:
            trade.stop = target_stop
    else:
        return  # Unknown direction · log warning upstream
    # cross_context audit per Gap 11
    import json
    audit_entry = {
        "event": "stop_move",
        "from": float(trade.stop_before) if hasattr(trade, "stop_before") else None,
        "to": float(trade.stop),
        "reason": "BE+1T after T1 hit",
        "bar_ts": str(self._current_bar_ts) if hasattr(self, "_current_bar_ts") else None,
    }
    if not isinstance(trade.cross_context, list):
        trade.cross_context = []
    trade.cross_context.append(audit_entry)
```

**Forbidden zone:** everything else in `manager.py` is forbidden — only this method changes.

**Tests (~6 in `tests/v9/services/test_trade_manager.py` · extend existing file):**
1. `test_be_plus_1t_long_moves_to_entry_plus_025`
2. `test_be_plus_1t_short_moves_to_entry_minus_025`
3. `test_be_plus_1t_idempotent_if_already_set`
4. `test_be_plus_1t_never_widens` (LONG stop already > BE+1T → no change)
5. `test_be_plus_1t_logs_cross_context`
6. `test_be_plus_1t_cross_context_serializes_with_datetime` (regression for json.dumps default=str)

**Required import addition:** `from backend.v9.systems.five_min.constants import MES_TICK_SIZE` (verify this constant exists; if not, add it to a constants file).

### §4.C · MODIFIED · `backend/v9/systems/day_type/targets_table.py` (~30 LOC)

Add `resolve_trail_config()` helper that consults the override table (D-094 §3.A).

```python
# At top of file, add import (must not create circular import — verify):
from backend.v9.systems.five_min.atr_caps import (
    TRAIL_OVERRIDE_BY_PATTERN,
    _pattern_to_family,
)
# ... existing TARGETS dict and get_targets() function ...

def resolve_trail_config(day_type: str, pattern_name: Optional[str]) -> dict:
    """Resolve trail config with pattern override (D-094 §3.A hybrid).

    If (day_type, pattern_family) has an override, merge it on top of the
    base targets_table config. Otherwise return base config unchanged.

    Args:
        day_type: e.g. 'Trend_DD', 'Variation'
        pattern_name: e.g. 'INITIATIVE' (None falls through to base)

    Returns:
        dict with at minimum 'trail_after_t2', 't3' keys.
    """
    base = TARGETS.get(day_type, {}).copy()
    if pattern_name is None:
        return base
    family = _pattern_to_family(pattern_name)
    if family is None:
        return base
    override = TRAIL_OVERRIDE_BY_PATTERN.get((day_type, family))
    if override is None:
        return base
    base.update(override)
    return base
```

**Tests (~6 in `tests/v9/systems/test_day_type/test_targets_table.py` · extend existing):**
1. `test_resolve_trail_config_tdd_initiative_overrides_to_6r_trail`
2. `test_resolve_trail_config_tdd_reactive_uses_base` (no override for reactive)
3. `test_resolve_trail_config_normal_initiative_uses_base` (override only TDD)
4. `test_resolve_trail_config_unknown_pattern_uses_base`
5. `test_resolve_trail_config_none_pattern_uses_base`
6. `test_resolve_trail_config_unknown_day_type_returns_empty`

### §4.D · MODIFIED · `backend/v9/services/trade_manager/manager.py` (minimal, ~10 LOC)

Switch the manager's T1 callback to call `resolve_trail_config()` when storing the trade's trail intent. Find the existing point where trade is created or T1 is handled, and capture `trail_after_t2` + `t3_label` from resolved config:

```python
# When trade is created or first reaches T1, store resolved config:
from backend.v9.systems.day_type.targets_table import resolve_trail_config
cfg = resolve_trail_config(trade.day_type, trade.pattern_name)
trade.quality["trail_after_t2"] = cfg.get("trail_after_t2", False)
trade.quality["t3_label"] = cfg.get("t3")  # e.g. "6R+trail" or "trail" or fixed R
```

(Exact insertion point depends on existing manager.py structure; Cursor will identify in code-read pass.)

### §4.E · Stream 3b-1 deliverables summary

| File | New/Modified | LOC | Tests |
|------|--------------|-----|-------|
| `atr_caps.py` | NEW | ~150 | 19 |
| `manager.py` (BE+1T fix) | MODIFIED | ~30 | 6 |
| `targets_table.py` (override hook) | MODIFIED | ~30 | 6 |
| `manager.py` (trail intent capture) | MODIFIED | ~10 | 0 (covered by Stream 3b-2 integration) |
| **Total Stream 3b-1** | | **~220** | **31** |

### §4.F · Stream 3b-1 forbidden zones

- ❌ Do NOT modify any other function in `manager.py` besides `_apply_smart_be_after_t1` + the trail-intent insertion point
- ❌ Do NOT modify Pkg 1 `adaptive_stop.py` `ATR_MULTIPLIERS` dict (only ADD new file `atr_caps.py`)
- ❌ Do NOT modify any test that currently uses `ATR_MULTIPLIERS["Reactive"] == 1.0` or `ATR_MULTIPLIERS["OFA"] == 1.5` (those values are preserved)
- ❌ Do NOT touch DLL or Sierra studies
- ❌ Do NOT touch frontend
- ✅ DO ensure `from backend.v9.systems.five_min.atr_caps import _pattern_to_family` works in `targets_table.py` without circular import (if circular, move `_pattern_to_family` to a shared `_resolvers.py` module)

### §4.G · Stream 3b-1 G3 review criteria (Cursor)

10-criterion gate. Stream-specific additions:
- (a) `ATR_MULTIPLIERS["Reactive"]` and `ATR_MULTIPLIERS["OFA"]` byte-identical to Pkg 1 shipped (1.0 and 1.5 respectively)
- (b) `_pattern_to_family("REACTIVE")` returns `"OFA_Reactive"` (uppercase input handled)
- (c) `TRAIL_OVERRIDE_BY_PATTERN[("Trend_DD", "OFA_Initiative")]` contains `t3: "6R+trail"` and `trail_after_t2: True`
- (d) `compute_continuous_atr14()` overnight-gap comment is present verbatim (Cursor will grep for "intentional" + "Wilder")
- (e) BE+1T fix uses `MES_TICK_SIZE` constant (not literal `0.25`)
- (f) BE+1T `_apply_smart_be_after_t1` is idempotent (calling twice doesn't double-move)
- (g) `cross_context.append({...})` uses dict literal (not f-string) — serializable downstream
- (h) Pkg 3a `get_targets()` and `compute_targets_for_day_type()` behavior unchanged (no regression on Pkg 3a tests · 572 systems suite stays green)

---

## §5 · Stream 3b-2 · TrailEngine + persistence

### §5.A · NEW · `backend/v9/services/trail_engine.py` (~250 LOC)

The orchestration class that subscribes to bar-close events and applies trail rules. SRP per D-094 Gap 9 — separate from `TradeManager` (which handles order I/O and trade lifecycle).

```python
"""TrailEngine · post-T2 trade management subscriber (D-094 Gap 9).

Lifecycle:
  1. On every 5-min bar close, BarRouter calls TrailEngine.on_bar_close(bar).
  2. TrailEngine queries TradeManager for all OPEN trades past T1.
  3. For each trade:
     a) If past T1 but not T2: apply BE+1T (already done by TradeManager · idempotent re-check).
     b) If past T2 and trail_after_t2 == True: apply HL/LH trail (5-bar lookback).
        Also apply chandelier trail (continuous Wilder's ATR-14 × family multiplier).
        Use tighter of the two (per Gap 13 'never widen').
     c) Apply Layer 4 services in order: mfe → cci_flat → tcci_cross → swi → day_type_targets_verify.
     d) Compute Layer 3 time_stop (min day-axis vs pattern-axis); close if elapsed.
  4. Every state change (stop move, exit) is logged to cross_context with
     json.dumps(default=str) per Gap 11.
  5. State snapshot persisted to trade.quality['trail_state'] per Gap 10.

Sierra tick fills ALWAYS win over computed trail (per Guardrail M13 · Gap 15).
If a stop fill is reported by Sierra while TrailEngine is computing → discard
the computed move, log entry.
"""
from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any

from backend.v9.systems.five_min.atr_caps import (
    ATR_MULTIPLIERS,
    _pattern_to_family,
    compute_time_stop_minutes,
    compute_continuous_atr14,
)
from backend.v9.systems.day_type.targets_table import TARGETS


@dataclass
class TrailState:
    """Persistable trail state (Gap 10 · JSON-serializable)."""
    max_high_since_t2: Optional[float] = None     # for LONG chandelier anchor
    min_low_since_t2: Optional[float] = None       # for SHORT chandelier anchor
    last_5_lows: list[float] = None                # for LONG HL/LH trail
    last_5_highs: list[float] = None               # for SHORT HL/LH trail
    chandelier_engaged: bool = False
    t2_bar_ts: Optional[str] = None                # ISO timestamp
    t2_atr_at_engage: Optional[float] = None       # frozen ATR at T2 hit (D-094 Gap 5)

    def to_dict(self) -> dict:
        return {
            "max_high_since_t2": self.max_high_since_t2,
            "min_low_since_t2": self.min_low_since_t2,
            "last_5_lows": self.last_5_lows or [],
            "last_5_highs": self.last_5_highs or [],
            "chandelier_engaged": self.chandelier_engaged,
            "t2_bar_ts": self.t2_bar_ts,
            "t2_atr_at_engage": self.t2_atr_at_engage,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TrailState":
        return cls(
            max_high_since_t2=data.get("max_high_since_t2"),
            min_low_since_t2=data.get("min_low_since_t2"),
            last_5_lows=data.get("last_5_lows", []),
            last_5_highs=data.get("last_5_highs", []),
            chandelier_engaged=data.get("chandelier_engaged", False),
            t2_bar_ts=data.get("t2_bar_ts"),
            t2_atr_at_engage=data.get("t2_atr_at_engage"),
        )


class TrailEngine:
    """Post-T2 trade management orchestrator.

    Inputs: BarRouter bar-close events, TradeManager open trades.
    Outputs: stop adjustments via TradeManager.update_stop(), exits via close_trade().
    """

    def __init__(self, trade_manager, bar_router, db_session_factory):
        self.tm = trade_manager
        self.bar_router = bar_router
        self.db = db_session_factory
        # Subscribe to bar-close events
        bar_router.subscribe("bar_5min_close", self.on_bar_close)

    def on_bar_close(self, bar) -> None:
        """Main entry point · called by BarRouter on every 5-min close."""
        open_trades = self.tm.list_open_trades_past_t1()
        for trade in open_trades:
            try:
                self._process_trade(trade, bar)
            except Exception as exc:
                # NEVER swallow with debug · per pre-LIVE protocol use warning + log
                self._log_audit(trade, "trail_engine_error", {
                    "exc": repr(exc), "bar_ts": str(bar.ts),
                })
                # Continue with other trades

    def _process_trade(self, trade, bar) -> None:
        """Apply 3-layer logic for one trade on one bar close."""
        state = self._load_state(trade)

        # === Layer 3 backstop FIRST (cheapest check · fails fast) ===
        time_stop_min = compute_time_stop_minutes(
            day_type=trade.day_type,
            pattern_family=_pattern_to_family(trade.pattern_name or ""),
            targets_table=TARGETS,
        )
        if time_stop_min is not None:
            elapsed_min = (bar.ts - trade.entry_ts).total_seconds() / 60
            if elapsed_min >= time_stop_min:
                self._close_trade(trade, bar, reason="TIME_STOP_HIT", state=state)
                return

        # === Layer 1: MFE peak tighten (always check, even pre-T2) ===
        # (delegated to Stream 3b-3 wiring · stub here)
        # self._apply_layer4_mfe_peak(trade, bar, state)

        # === Layer 2: post-T2 trail (HL/LH + chandelier) ===
        if state.chandelier_engaged or self._is_past_t2(trade):
            if not state.chandelier_engaged:
                self._engage_chandelier(trade, bar, state)
            self._apply_hl_lh_trail(trade, bar, state)
            self._apply_chandelier_trail(trade, bar, state)

        # Persist updated state
        self._save_state(trade, state)

    # ... (helper methods: _engage_chandelier · _apply_hl_lh_trail ·
    #      _apply_chandelier_trail · _load_state · _save_state ·
    #      _close_trade · _log_audit · _is_past_t2 · _move_stop_tighter_only)
    # ~150 LOC across these helpers.
    # See §5.B-D for the key helpers' bodies.
```

### §5.B · HL/LH trail helper (~40 LOC)

```python
def _apply_hl_lh_trail(self, trade, bar, state: TrailState) -> None:
    """5-bar HL (LONG) / LH (SHORT) trail · D-094 Gap 2.

    LONG: new_stop = max(current_stop, min(last_5_bars.low))
    SHORT: new_stop = min(current_stop, max(last_5_bars.high))
    Tightens only · per Gap 13.
    """
    direction = trade.direction.upper()
    if direction == "LONG":
        state.last_5_lows = (state.last_5_lows or [])[-4:] + [float(bar.low)]
        if len(state.last_5_lows) >= 5:
            trail_candidate = min(state.last_5_lows)
            self._move_stop_tighter_only(
                trade, trail_candidate, reason="HL_TRAIL", bar=bar,
            )
    elif direction == "SHORT":
        state.last_5_highs = (state.last_5_highs or [])[-4:] + [float(bar.high)]
        if len(state.last_5_highs) >= 5:
            trail_candidate = max(state.last_5_highs)
            self._move_stop_tighter_only(
                trade, trail_candidate, reason="LH_TRAIL", bar=bar,
            )
```

### §5.C · Chandelier helper (~40 LOC)

```python
def _engage_chandelier(self, trade, bar, state: TrailState) -> None:
    """First-time engagement at T2 hit · freezes ATR per D-094 Gap 5."""
    direction = trade.direction.upper()
    state.chandelier_engaged = True
    state.t2_bar_ts = bar.ts.isoformat()
    state.max_high_since_t2 = float(bar.high) if direction == "LONG" else None
    state.min_low_since_t2 = float(bar.low) if direction == "SHORT" else None
    # Freeze ATR at engage (Gap 5 · do NOT recompute on subsequent bars)
    yesterday_bars = self._fetch_yesterday_bars(bar.ts.date())
    today_bars = self._fetch_today_bars_up_to(bar.ts)
    state.t2_atr_at_engage = compute_continuous_atr14(yesterday_bars, today_bars)


def _apply_chandelier_trail(self, trade, bar, state: TrailState) -> None:
    """Chandelier trail from peak ± multiplier × frozen ATR · D-094 Gap 3 + §3.D."""
    if state.t2_atr_at_engage is None:
        return  # Insufficient ATR data · skip silently with cross_context note
    family = _pattern_to_family(trade.pattern_name or "")
    if family is None:
        return
    multiplier = ATR_MULTIPLIERS.get(family)
    if multiplier is None:
        return
    direction = trade.direction.upper()
    if direction == "LONG":
        state.max_high_since_t2 = max(state.max_high_since_t2 or bar.high, float(bar.high))
        chandelier = state.max_high_since_t2 - multiplier * state.t2_atr_at_engage
        self._move_stop_tighter_only(trade, chandelier, reason="CHANDELIER_TRAIL", bar=bar)
    elif direction == "SHORT":
        state.min_low_since_t2 = min(state.min_low_since_t2 or bar.low, float(bar.low))
        chandelier = state.min_low_since_t2 + multiplier * state.t2_atr_at_engage
        self._move_stop_tighter_only(trade, chandelier, reason="CHANDELIER_TRAIL", bar=bar)
```

### §5.D · Tighten-only helper + audit (~30 LOC)

```python
def _move_stop_tighter_only(self, trade, candidate: float, *, reason: str, bar) -> None:
    """Move stop ONLY if tighter (LONG: candidate > current; SHORT: candidate < current).

    Per D-094 Gap 13 'never widen'. Logs to cross_context (Gap 11).
    """
    current = trade.stop
    direction = trade.direction.upper()
    if current is None:
        return  # No prior stop · shouldn't happen post-T1 · log
    if direction == "LONG" and candidate <= current:
        return
    if direction == "SHORT" and candidate >= current:
        return
    # Move
    audit = {
        "event": "stop_move",
        "from": float(current),
        "to": float(candidate),
        "reason": reason,
        "bar_ts": str(bar.ts),
    }
    if not isinstance(trade.cross_context, list):
        trade.cross_context = []
    trade.cross_context.append(audit)
    trade.stop = float(candidate)
    self.tm.persist_trade_update(trade)


def _log_audit(self, trade, event: str, payload: dict) -> None:
    """Append to cross_context with json-safe serialization (Gap 11)."""
    entry = {"event": event, **payload}
    # Test that json.dumps works (catches non-serializable accidentally)
    json.dumps(entry, default=str)
    if not isinstance(trade.cross_context, list):
        trade.cross_context = []
    trade.cross_context.append(entry)
```

### §5.E · State persistence + restart recovery (~50 LOC)

```python
def _save_state(self, trade, state: TrailState) -> None:
    """Persist trail state to trade.quality['trail_state'] (Gap 10)."""
    if not isinstance(trade.quality, dict):
        trade.quality = {}
    trade.quality["trail_state"] = state.to_dict()
    self.tm.persist_trade_update(trade)


def _load_state(self, trade) -> TrailState:
    """Restore trail state from trade.quality (Gap 14 · restart recovery)."""
    data = (trade.quality or {}).get("trail_state")
    if data is None:
        return TrailState()
    try:
        return TrailState.from_dict(data)
    except Exception as exc:
        # Conservative: log warning, return empty state · next bar will rebuild
        self._log_audit(trade, "trail_state_load_failed", {"exc": repr(exc)})
        # Fallback: recompute max_high_since_t2 from v9_bars_5min
        return self._reconstruct_state_from_db(trade)


def _reconstruct_state_from_db(self, trade) -> TrailState:
    """Rebuild state from v9_bars_5min query (Gap 14 fallback)."""
    t2_ts = trade.t2_filled_at
    if t2_ts is None:
        return TrailState()
    bars = self.db.query_bars_since(t2_ts)
    state = TrailState()
    state.t2_bar_ts = t2_ts.isoformat()
    state.chandelier_engaged = True
    if trade.direction.upper() == "LONG":
        state.max_high_since_t2 = max((b.high for b in bars), default=None)
        state.last_5_lows = [b.low for b in bars[-5:]]
    else:
        state.min_low_since_t2 = min((b.low for b in bars), default=None)
        state.last_5_highs = [b.high for b in bars[-5:]]
    # NOTE: t2_atr_at_engage NOT recoverable without prior persist; leave None
    # · chandelier inactive until next bar gives data
    return state
```

### §5.F · Concurrency (Gap 15)

```python
# In TradeManager (modified): on Sierra fill, set trade.fill_lock=True
# In TrailEngine._move_stop_tighter_only: check trade.fill_lock first
def _move_stop_tighter_only(self, trade, candidate, *, reason, bar):
    if getattr(trade, "fill_lock", False):
        self._log_audit(trade, "trail_compute_discarded_sierra_fill", {
            "candidate": float(candidate), "reason": reason,
        })
        return
    # ... rest as before
```

### §5.G · Tests for Stream 3b-2 (~28 in `tests/v9/services/test_trail_engine.py`)

Coverage areas:

**HL/LH trail (6 tests)**
1. `test_hl_trail_long_5_bar_low_tightens_stop`
2. `test_hl_trail_long_never_widens`
3. `test_hl_trail_short_5_bar_high_tightens_stop`
4. `test_hl_trail_short_never_widens`
5. `test_hl_trail_needs_5_bars_before_firing`
6. `test_hl_trail_sliding_window_drops_oldest`

**Chandelier (6 tests)**
7. `test_chandelier_engages_at_t2`
8. `test_chandelier_atr_frozen_at_engage`
9. `test_chandelier_long_uses_max_high_minus_multiplier_atr`
10. `test_chandelier_short_uses_min_low_plus_multiplier_atr`
11. `test_chandelier_never_widens`
12. `test_chandelier_skips_if_no_atr_data`

**Time stop (4 tests)**
13. `test_time_stop_fires_when_elapsed`
14. `test_time_stop_uses_min_day_pattern`
15. `test_time_stop_no_close_when_both_none`
16. `test_time_stop_exit_reason_time_stop_hit`

**State persistence + restart (5 tests)**
17. `test_save_state_persists_to_quality`
18. `test_load_state_restores_from_quality`
19. `test_load_state_corrupt_falls_back_to_db_reconstruct`
20. `test_load_state_missing_returns_empty`
21. `test_state_roundtrip_json_serializable`

**Cross-context audit (3 tests)**
22. `test_stop_move_appends_to_cross_context`
23. `test_cross_context_json_serializable_with_datetime`
24. `test_cross_context_preserves_history`

**Concurrency / Sierra fill (2 tests)**
25. `test_trail_compute_discarded_when_fill_lock_set`
26. `test_fill_lock_logged_to_cross_context`

**Integration (2 tests)**
27. `test_end_to_end_long_trade_t2_hit_then_5_bars_trail_then_stop_out`
28. `test_end_to_end_short_trade_chandelier_only_no_hl_lh`

### §5.H · Stream 3b-2 forbidden zones

- ❌ Do NOT modify `TradeManager` core logic (only ADD `list_open_trades_past_t1()` helper + `persist_trade_update()` helper if not already present)
- ❌ Do NOT touch DB schema migrations (use existing `trade.quality` JSON column)
- ❌ Do NOT modify Pkg 1 ATR functions in `adaptive_stop.py`
- ❌ Do NOT subscribe to anything besides `bar_5min_close` event in BarRouter
- ✅ DO add `MES_TICK_SIZE` constant somewhere central if missing (e.g. `backend/v9/systems/five_min/constants.py`)

---

## §6 · Stream 3b-3 · Layer 4 wiring

### §6.A · Approach

Wire the 5 existing Layer 4 services (currently dead code) into `TrailEngine`. Order per D-094 §3.B.3:

1. `mfe_peak_tighten` — universal · Layer 1 primary stagnation detector
2. `cci_flat_tighten` — Woodies-specific · S4 trades only
3. `tcci_cross_exit` — Woodies-specific · S4 trades only
4. `swi_tighten` — per D-094 §3.B.1 keep TIGHTEN 25% behavior
5. `day_type_targets_verify` — most dangerous · ordered last

Each wire: ~70-80 LOC + 5-6 tests.

### §6.B · MFE peak tighten wire (~75 LOC + 6 tests)

In `TrailEngine._process_trade()`, between Layer 3 time_stop and Layer 2 post-T2 trail, add:

```python
# === Layer 1: MFE peak tighten (D-094 §3.C Layer 1) ===
self._apply_layer4_mfe_peak(trade, bar, state)
```

Method body:

```python
def _apply_layer4_mfe_peak(self, trade, bar, state: TrailState) -> None:
    """Layer 1 stagnation detector · Constitution V3 PART 5 B11."""
    from backend.v9.services.layer4.mfe_peak_tighten import evaluate
    result = evaluate(
        trade=trade,
        current_bar=bar,
        # service-specific args per existing signature
    )
    if result is None:
        return
    action = result.get("action")
    if action == "TIGHTEN_STOP":
        new_stop = result["new_stop"]
        self._move_stop_tighter_only(
            trade, new_stop, reason=f"MFE_PEAK_TIGHTEN · {result.get('reasoning_notes')}", bar=bar,
        )
    elif action == "CLOSE_ALL":
        self._close_trade(trade, bar, reason="MFE_PEAK_CLOSE_ALL", state=state)
```

**Cursor pre-flight:** Read `backend/v9/services/layer4/mfe_peak_tighten.py` to confirm exact `evaluate()` signature + return shape. Adapt the call site to match.

### §6.C · cci_flat + tcci_cross wires (~75 LOC + 8 tests)

```python
# Inside _process_trade, after MFE wire, before Layer 2 trail:
# Only fire for S4 (Woodies) trades
if trade.source_system == "S4_WOODIES":
    self._apply_layer4_cci_flat(trade, bar, state)
    self._apply_layer4_tcci_cross(trade, bar, state)
```

Both methods follow the same pattern as `_apply_layer4_mfe_peak` — read existing service signatures and adapt.

### §6.D · swi_tighten wire (~75 LOC + 5 tests)

Per D-094 §3.B.1: keep `tighten 25%` semantics (the existing service's behavior · NOT close-all).

```python
def _apply_layer4_swi_tighten(self, trade, bar, state: TrailState) -> None:
    """SWI red → tighten stop by 25% (D-094 §3.B.1 keeps softened behavior).

    Sheet D row 4 spec says 'Close entire position' but code stays at TIGHTEN 25%.
    Post-SHADOW: re-evaluate if SHADOW data shows SWI red precedes full reversal.
    """
    from backend.v9.services.layer4.swi_tighten import evaluate
    result = evaluate(trade=trade, current_bar=bar)
    if result is None:
        return
    if result.get("action") == "TIGHTEN_STOP":
        self._move_stop_tighter_only(
            trade, result["new_stop"], reason="SWI_RED_TIGHTEN_25", bar=bar,
        )
```

### §6.E · day_type_targets_verify wire (~75 LOC + 6 tests)

Last in order per D-094 §3.B.3 because it can close trades mid-flight.

```python
def _apply_layer4_day_type_verify(self, trade, bar, state: TrailState) -> None:
    """Day-type targets validity check · Constitution V3 PART 5 B12.

    Closes trade if day-type re-classification invalidates the targets
    (e.g. day was Trend_Normal at entry, reclassified to Nontrend mid-trade).
    DANGEROUS · fires LAST in the chain.
    """
    from backend.v9.services.layer4.day_type_targets_verify import evaluate
    result = evaluate(trade=trade, current_bar=bar)
    if result is None:
        return
    if result.get("action") == "CLOSE_ALL":
        self._close_trade(trade, bar, reason="DAY_TYPE_INVALIDATED", state=state)
```

### §6.F · Sheet D documentation update

In addition to code, Stream 3b-3 must add a `code_status` column to Sheet D (`MEMS26_V9_Pattern_Tables_Enhanced.xlsx`) with the drift documentation per D-094 §3.B.1. Cursor will note this in the handoff but the actual xlsx update is Michael's (out-of-band).

Alternative: create `docs/spec/SHEET_D_CODE_STATUS.md` as a markdown sidecar documenting all drifts. Row 4 entry:

```
| Row | Spec verbatim | Code status | Re-evaluation |
| 4 | "SWI red → Close entire position" | softened to TIGHTEN 25% in `swi_tighten.py` (per D-094 §3.B.1) | DEMO re-evaluation pending · upgrade to close-all if SHADOW data shows full reversal correlation |
```

### §6.G · Stream 3b-3 deliverables summary

| Wire | LOC | Tests |
|------|-----|-------|
| mfe_peak_tighten | ~75 | 6 |
| cci_flat_tighten | ~75 | 4 |
| tcci_cross_exit | ~75 | 4 |
| swi_tighten | ~75 | 5 |
| day_type_targets_verify | ~75 | 6 |
| Sheet D doc sidecar | ~30 (markdown) | 0 |
| Integration tests | — | 5 |
| **Total Stream 3b-3** | **~405** | **30** |

### §6.H · Stream 3b-3 forbidden zones

- ❌ Do NOT modify the body of any Layer 4 `evaluate()` function (they exist · just wire them)
- ❌ Do NOT add new Layer 4 services (the 5 missing ones — CCI ±200, ±100, ZL, opposing pattern, new trend pattern — are deferred to Pkg 4a)
- ❌ Do NOT change the cci_flat / tcci_cross firing gate from "S4 only" to "all systems"
- ✅ DO use the exact `evaluate()` return shape each service exports (Cursor reads them in pre-flight)
- ✅ DO log each wire's firing to `cross_context` with the specific reason string

---

## §7 · Cross-stream G3 review checklist (Cursor)

Standard 10-criterion gate. Pkg 3b-specific additions across all 3 streams:

1. **Anti-regression on Pkg 1**: `pytest tests/v9/systems/test_five_min/test_adaptive_stop.py` stays green (all 5 ATR_MULTIPLIERS legacy values preserved per D-094 §3.D ripple Option 3)
2. **Anti-regression on Pkg 3a**: `pytest tests/v9/systems/test_day_type/` and `tests/v9/api/test_targets_routes.py` stay green
3. **Anti-regression on Pkg 2bc**: chronic toxicity block in `five_min_system.py` byte-identical to `cf6383e` baseline
4. **Wilder overnight-gap comment present**: grep `compute_continuous_atr14` for "intentional" + "Wilder" + "overnight gap"
5. **BE+1T uses tick constant**: grep `_apply_smart_be_after_t1` for `MES_TICK_SIZE` (not literal `0.25`)
6. **`json.dumps(default=str)` everywhere `cross_context` is serialized**: grep for `cross_context.append` and verify default=str pattern is used in serialization
7. **3-layer ordering**: in `TrailEngine._process_trade`, time_stop check is FIRST (cheapest fail-fast) · MFE peak SECOND · post-T2 trail THIRD · Layer 4 services in §3.B.3 order
8. **Layer 4 wires read evaluate() returns correctly**: each `_apply_layer4_*` method handles None + every documented action key
9. **Concurrency check present**: `_move_stop_tighter_only` checks `trade.fill_lock`
10. **Commit message contains §4 Phase A flag verbatim**

---

## §8 · Test summary (all 3 streams)

| Stream | Test files | Test count |
|--------|-----------|------------|
| 3b-1 | test_atr_caps.py (NEW) + test_trade_manager.py (extend) + test_targets_table.py (extend) | 31 |
| 3b-2 | test_trail_engine.py (NEW) | 28 |
| 3b-3 | test_trail_engine_layer4_wires.py (NEW) | 30 |
| **Total NEW** | | **89 tests** |

Aggregate test suite target: pre-Pkg-3b ~572 systems suite + ~6 trade_manager + ~7 targets_table → post-Pkg-3b ~672 tests overall.

---

## §9 · Out-of-scope (deferred to later packages)

| Item | Reason | Defer to |
|------|--------|----------|
| CCI ±200 cross exit (Sheet D row 1) | Service doesn't exist · need to build | Pkg 4a (Risk Rules Critical 3) |
| CCI ±100 cross exit (Sheet D row 2) | Service doesn't exist | Pkg 4a |
| CCI ZL cross exit (Sheet D row 3) | Service doesn't exist | Pkg 4a |
| Opposing pattern exit (Sheet D row 5) | Pattern detectors not all built yet | Pkg 4a |
| New trend pattern exit (Sheet D row 6) | Pattern detectors not all built yet | Pkg 4a |
| Pattern overrides for Flag/Pennant/HnS on day types (§3.A) | Patterns not built · only OFA Initiative in Pkg 3b | Pkg 5a-c |
| Type C "no fire if T2 already hit X bars ago" | Type C semantics still TBD | Pkg 6 |
| Migrating Pkg 1 entry stops to xlsx-aligned multipliers | Requires SHADOW data to validate | Pkg 1-rev (post-SHADOW) |
| Contract split (33/33/34 or 50/50) | Separate concern from trail mechanics | Pkg 3c |
| BTC/STC suppression (final 90min bull day for H&S Top) | DEMO-decided modes · Pkg 7 territory | Pkg 7 |
| Sheet D upgrade SWI red to close-all | Requires SHADOW correlation data | post-SHADOW review |

---

## §10 · Phase A vs DEMO+ classification (D-094 §4)

Pkg 3b ships **mechanical** trail implementation. Numeric parameters are seeded from Sheet C verbatim (5-bar HL/LH lookback · 1×ATR per family · 20/30/45 min pattern time_stops · 80% MFE retracement threshold) but NOT calibrated against SHADOW data.

**Commit message MUST include this exact paragraph (Michael 2026-05-24 §4 lock):**

> *"Pkg 3b ships mechanical trail mechanics per D-094 §1-§3 spec.*
> *Numeric parameters (ATR multipliers · HL/LH lookback bars · MFE retracement %)*
> *are seeded from Sheet C verbatim values, NOT calibrated against SHADOW data.*
> *Post-SHADOW Pkg 1-rev + Pkg 3b-rev will re-tune these numerics if data shows*
> *Layer 3 firing > 20% of exits, or if T2→exit avg duration drifts from spec.*
> *Do NOT modify these numerics in Phase A without explicit Michael lock + D-094 amendment."*

Post-Pkg-3b ship: update `mems26-systems-registry.canvas.tsx` to mark rows `#9 Trailing stop after T1` and `#13 ATR-adaptive stops` as "Phase A mechanical · DEMO+ parametric" instead of blanket DEMO+.

---

## §11 · Execution plan recommendation

1. **Cursor**: this handoff is complete · ready for Desktop
2. **Desktop**: convert §4 (Stream 3b-1) to MEGA-prompt for CC (~2-3h CC execution)
3. **CC**: executes Stream 3b-1 · commits · reports
4. **Cursor**: G3 review of Stream 3b-1 (~30min)
5. **Desktop**: convert §5 (Stream 3b-2) to MEGA-prompt · CC executes (~3h)
6. **Cursor**: G3 review of Stream 3b-2 (~45min)
7. **Desktop**: convert §6 (Stream 3b-3) to MEGA-prompt · CC executes (~2-3h)
8. **Cursor**: G3 review of Stream 3b-3 + cross-stream integration check (~1h)
9. **Michael**: G4 smoke trade · DB-only end-to-end with full Pkg 0+1+2a+2bc+3a+3b stack
10. **Post-ship**: registry update + Sheet D `code_status` column update

Total wall time estimate: ~12-15 hours across CC + Cursor + Desktop coordination.

---

## §12 · References

- **D-094** (THIS HANDOFF'S AUTHORITY · LOCKED): `docs/decisions/D-094_PKG3B_TRAIL_DECISIONS.md`
- **D-091** (S2 LIVE scope): `docs/decisions/D-091_S2_LIVE_SCOPE.md`
- **MEMS26_V9_Pattern_Tables_Enhanced.xlsx** (Sheet C STOP STRATEGY · Sheet D 8 PRIORITIES)
- **S2_Master_Summary.xlsx** (Sheets A/B/C/D · referenced for context)
- **Constitution V3 PART 5 B11+B12** (MFE peak tighten · day-type targets verify)
- **Pkg 1 adaptive_stop.py** code: `backend/v9/systems/five_min/adaptive_stop.py`
- **Pkg 3a targets_table.py** code: `backend/v9/systems/day_type/targets_table.py`
- **TradeManager BE bug**: `backend/v9/services/trade_manager/manager.py:257`
- **Layer 4 dead services**: `backend/v9/services/layer4/*.py`
- **mems26-systems-registry.canvas.tsx** (registry to update post-ship)

---

*End of DESKTOP_PKG3B_TRAIL_LOGIC_HANDOFF.md · 2026-05-24 19:00 IL · Cursor authorship · ready for Desktop MEGA-prompt conversion*
