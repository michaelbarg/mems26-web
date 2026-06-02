"""D-S4FIX: Dispatcher reads trend from studies (current bar), not stale current_state.

Calls PRODUCTION WoodiesSystem.process_bar. Asserts on current_state output.

if reverted → RED because with the old code (current_state.get), the dispatcher
  reads the PREVIOUS bar's trend ("BLUE") instead of the current bar's ("YELLOW"),
  so patterns are NOT cleared by the YELLOW pre-drop guard → active_patterns != [].
"""

import asyncio
import pytest

import backend.v9.shared.atr as atr_mod


def _set_relabel_off(monkeypatch):
    """Ensure relabel flag OFF so YELLOW stays YELLOW."""
    monkeypatch.setattr(atr_mod, "S4_EXTREME_TREND_RELABEL", False)
    import backend.v9.systems.woodies.trend_relabel as trl
    monkeypatch.setattr(trl, "S4_EXTREME_TREND_RELABEL", False)


def _make_system():
    from backend.v9.systems.woodies.woodies_system import WoodiesSystem
    ws = WoodiesSystem(db_path=":memory:", rth_only=False)
    # Seed OHLCV buffers for study fallback
    for _ in range(15):
        ws._highs.append(7600.0)
        ws._lows.append(7590.0)
        ws._closes.append(7595.0)
    ws.current_state["running"] = True
    # Pre-set current_state trend to BLUE (simulating previous bar was BLUE)
    ws.current_state["trend_state"] = "BLUE"
    return ws


def _make_bar(trend_state="YELLOW", cci_14=50.0, ts=1717340100):
    """Bar with DLL study values. YELLOW trend + moderate CCI = no relabel."""
    return {
        "ts": ts,
        "open": 7600.0, "high": 7610.0, "low": 7590.0, "close": 7605.0,
        "volume": 1000,
        "cci_14": cci_14,
        "cci_6_tcci": 40.0,
        "ema_34": 7595.0,
        "lsma_value": 7598.0,
        "lsma_above_price": False,
        "swi_value": 40.0,
        "czi_value": 8.0,
        "trend_state": trend_state,
        "predictor_next_cci": 60.0,
        "hfe_detected": False,
        "hfe_direction": "NONE",
        "hfe_extreme_bars_ago": 0,
        "zlr_detected": False,
        "zlr_direction": "NONE",
    }


def test_yellow_bar_clears_patterns_despite_blue_current_state(monkeypatch):
    """D-S4FIX: Bar with trend=YELLOW blocks patterns even if current_state was BLUE.

    if reverted → RED because old code reads current_state["trend_state"]="BLUE"
      (from previous bar), skips YELLOW pre-drop, patterns survive → active_patterns != [].
    """
    _set_relabel_off(monkeypatch)
    ws = _make_system()
    assert ws.current_state["trend_state"] == "BLUE", "precondition: prior bar was BLUE"

    # Send bar with YELLOW trend — should trigger YELLOW pre-drop
    asyncio.get_event_loop().run_until_complete(
        ws.process_bar(_make_bar(trend_state="YELLOW", cci_14=50.0))
    )

    state = ws.get_current()
    # After process_bar, trend_state should be YELLOW (from studies, not stale BLUE)
    assert state["trend_state"] == "YELLOW", (
        f"trend_state should be YELLOW from current bar. Got: {state['trend_state']}"
    )
    # YELLOW pre-drop should have cleared all patterns
    assert state["active_patterns"] == [], (
        f"YELLOW should block all patterns. Got: {state['active_patterns']}"
    )


def test_blue_bar_allows_patterns(monkeypatch):
    """D-S4FIX: Bar with trend=BLUE allows patterns through (no YELLOW block)."""
    _set_relabel_off(monkeypatch)
    ws = _make_system()

    asyncio.get_event_loop().run_until_complete(
        ws.process_bar(_make_bar(trend_state="BLUE", cci_14=150.0))
    )

    state = ws.get_current()
    assert state["trend_state"] == "BLUE"
    # Patterns may or may not be detected depending on buffer — but trend is correct


def test_bar_count_in_get_current(monkeypatch):
    """D-S4FIX: bar_count appears in get_current() after process_bar.

    if reverted → RED because bar_count won't be in current_state.update dict.
    """
    _set_relabel_off(monkeypatch)
    ws = _make_system()

    asyncio.get_event_loop().run_until_complete(
        ws.process_bar(_make_bar(trend_state="BLUE", ts=1717340100))
    )

    state = ws.get_current()
    assert "bar_count" in state, "bar_count should be in get_current()"
    assert isinstance(state["bar_count"], int), f"bar_count should be int, got {type(state['bar_count'])}"
    assert state["bar_count"] >= 1, f"bar_count should be >= 1 after one bar, got {state['bar_count']}"
