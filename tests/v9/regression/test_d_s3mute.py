"""D-S3MUTE: S3 Footprint mute flag — fire suppression test.

Calls PRODUCTION FootprintSystem._fire with a real signal+bar.
Asserts on the consumer: gateway.route_setup called or not.

if reverted → RED because without the S3_MUTE guard in _fire,
  flag=True still routes to gateway (fire not suppressed).
"""

import pytest
from unittest.mock import MagicMock

import backend.v9.shared.atr as atr_mod


def _set_mute(monkeypatch, on: bool):
    monkeypatch.setattr(atr_mod, "S3_MUTE", on)
    # Also patch the import target inside footprint_system
    import backend.v9.systems.footprint.footprint_system as fps_mod
    # _fire does `from backend.v9.shared.atr import S3_MUTE` at call time,
    # so patching atr_mod is sufficient. But ensure module-level cache cleared.


def _make_system():
    """Create a FootprintSystem with mock gateway and aligned flow state."""
    from backend.v9.systems.footprint.footprint_system import FootprintSystem
    fs = FootprintSystem(db_path=":memory:")
    fs.current_state["running"] = True
    # Set flow state so calculate_size returns 'full' (aux_count=3)
    fs._cumulative_delta = 100.0  # positive = aligned with LONG
    fs._last_dominance = "BUYER_DOMINATE"  # aligned with LONG
    fs._last_initiative_type = "INITIATIVE_UP"  # aligned with LONG
    # Inject mock gateway to track route_setup calls
    fs._gateway = MagicMock()
    fs._gateway.route_setup.return_value = {"shadow": "SHADOW-TEST", "blocked_by": None}
    return fs


def _make_signal():
    return {
        "signal": "ABSORPTION",
        "direction": "LONG",
        "strength": 0.7,
        "level": 7600.0,
        "evidence": "test",
    }


def _make_bar():
    return {
        "ts": "2026-06-02T14:30:00",
        "open": 7595.0, "high": 7610.0, "low": 7590.0, "close": 7605.0,
        "volume": 500, "tick_size": 0.25,
        "ask_vol": 300, "bid_vol": 200,
    }


def _make_event():
    event = MagicMock()
    event.ts = "2026-06-02T14:30:00"
    event.bar_id = "test_bar"
    event.session = "RTH"
    return event


def test_s3_mute_on_no_fire(monkeypatch):
    """D-S3MUTE: Flag ON → _fire returns early, gateway NOT called.

    if reverted → RED because without the guard, gateway.route_setup is called.
    """
    _set_mute(monkeypatch, True)
    fs = _make_system()

    fs._fire(_make_signal(), _make_bar(), _make_event())

    fs._gateway.route_setup.assert_not_called()


def test_s3_mute_off_fires_normally(monkeypatch):
    """D-S3MUTE: Flag OFF → _fire proceeds, gateway IS called.

    if reverted → this test still passes (no guard = fires). The pair proves
    the gate works: ON blocks, OFF allows.
    """
    _set_mute(monkeypatch, False)
    fs = _make_system()

    fs._fire(_make_signal(), _make_bar(), _make_event())

    fs._gateway.route_setup.assert_called_once()
    call_args = fs._gateway.route_setup.call_args
    assert call_args[0][1] == 3, "Should route as system_id=3"
