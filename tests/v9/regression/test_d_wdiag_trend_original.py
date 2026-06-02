"""D-WDIAG: trend_original flows to get_current() / cross_context.

Anti-tautological: calls PRODUCTION WoodiesSystem.process_bar + get_current().
Asserts on the real consumer (get_current), not on the intermediate studies dict.

if reverted P2 → RED because trend_original won't appear in current_state
  (P1 sets it in studies, but without P2 the explicit update dict skips it).
"""

import asyncio
import pytest
from unittest.mock import MagicMock

import backend.v9.shared.atr as atr_mod


def _set_flag(monkeypatch, on: bool):
    monkeypatch.setenv("S4_EXTREME_TREND_RELABEL", "true" if on else "")
    import backend.v9.systems.woodies.trend_relabel as trl
    pass  # flag() reads os.environ directly


def _make_bar(cci_14=250.0, trend_state="YELLOW", ts=1717340100):
    """Build a bar dict with DLL study values (Sierra source-of-truth path).

    hfe_detected/zlr_detected are False to avoid PatternResult validation
    errors (stop=None). The test target is trend_original in current_state,
    not pattern detection.
    """
    return {
        "ts": ts,
        "open": 7600.0, "high": 7610.0, "low": 7590.0, "close": 7605.0,
        "volume": 1000,
        "cci_14": cci_14,
        "cci_6_tcci": 180.0,
        "ema_34": 7595.0,
        "lsma_value": 7598.0,
        "lsma_above_price": False,
        "swi_value": 40.0,
        "czi_value": 8.0,
        "trend_state": trend_state,
        "predictor_next_cci": 260.0,
        "hfe_detected": False,
        "hfe_direction": "NONE",
        "hfe_extreme_bars_ago": 0,
        "zlr_detected": False,
        "zlr_direction": "NONE",
    }


def _make_system():
    """Create a WoodiesSystem with no DB dependency, RTH gate off."""
    from backend.v9.systems.woodies.woodies_system import WoodiesSystem
    ws = WoodiesSystem(db_path=":memory:", rth_only=False)
    # Seed enough bars for study computation fallback (not needed with DLL values,
    # but avoids edge-case errors in pattern engine).
    for _ in range(15):
        ws._highs.append(7600.0)
        ws._lows.append(7590.0)
        ws._closes.append(7595.0)
    ws.current_state["running"] = True
    return ws


# ══════════════════════════════════════════════════════════════════
# Core test: trend_original reaches get_current() (P1 + P2)
# ══════════════════════════════════════════════════════════════════

def test_trend_original_in_get_current_after_relabel(monkeypatch):
    """D-WDIAG: Flag ON + YELLOW + CCI=250 → get_current() has
    trend_original='YELLOW' and trend_state='BLUE'.

    if reverted P2 → RED because trend_original won't appear in current_state.
    """
    _set_flag(monkeypatch, True)
    ws = _make_system()

    asyncio.get_event_loop().run_until_complete(ws.process_bar(_make_bar(
        cci_14=250.0, trend_state="YELLOW",
    )))

    state = ws.get_current()
    assert state.get("trend_original") == "YELLOW", (
        f"trend_original should be 'YELLOW' (pre-relabel). Got: {state.get('trend_original')}"
    )
    assert state.get("trend_state") == "BLUE", (
        f"trend_state should be 'BLUE' (post-relabel). Got: {state.get('trend_state')}"
    )


def test_trend_original_no_relabel_when_flag_off(monkeypatch):
    """D-WDIAG: Flag OFF + YELLOW + CCI=250 → trend_original='YELLOW',
    trend_state stays 'YELLOW' (no relabel).

    if reverted P2 → RED because trend_original missing from current_state.
    """
    _set_flag(monkeypatch, False)
    ws = _make_system()

    asyncio.get_event_loop().run_until_complete(ws.process_bar(_make_bar(
        cci_14=250.0, trend_state="YELLOW",
    )))

    state = ws.get_current()
    assert state.get("trend_original") == "YELLOW", (
        f"trend_original should be 'YELLOW'. Got: {state.get('trend_original')}"
    )
    assert state.get("trend_state") == "YELLOW", (
        f"trend_state should stay 'YELLOW' when flag OFF. Got: {state.get('trend_state')}"
    )


def test_trend_original_blue_stays_blue(monkeypatch):
    """D-WDIAG: Flag ON + BLUE (natural) + CCI=250 → trend_original='BLUE',
    trend_state='BLUE'. No relabel needed — original was already valid.

    if reverted P2 → RED because trend_original missing from current_state.
    """
    _set_flag(monkeypatch, True)
    ws = _make_system()

    asyncio.get_event_loop().run_until_complete(ws.process_bar(_make_bar(
        cci_14=250.0, trend_state="BLUE",
    )))

    state = ws.get_current()
    assert state.get("trend_original") == "BLUE", (
        f"trend_original should be 'BLUE' (natural, no relabel). Got: {state.get('trend_original')}"
    )
    assert state.get("trend_state") == "BLUE", (
        f"trend_state should be 'BLUE'. Got: {state.get('trend_state')}"
    )


def test_trend_original_negative_extreme(monkeypatch):
    """D-WDIAG: Flag ON + GRAY + CCI=-220 → relabel to RED,
    trend_original='GRAY'.

    if reverted P2 → RED because trend_original missing from current_state.
    """
    _set_flag(monkeypatch, True)
    ws = _make_system()

    asyncio.get_event_loop().run_until_complete(ws.process_bar(_make_bar(
        cci_14=-220.0, trend_state="GRAY",
    )))

    state = ws.get_current()
    assert state.get("trend_original") == "GRAY", (
        f"trend_original should be 'GRAY'. Got: {state.get('trend_original')}"
    )
    assert state.get("trend_state") == "RED", (
        f"trend_state should be 'RED' (negative extreme relabel). Got: {state.get('trend_state')}"
    )
