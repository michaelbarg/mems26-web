"""I-61 regression — no setup may leave the gateway with targets on the wrong side.

Live incident (2026-07-02 ~19:15, trades 279/280): REACTIVE_LONG @7525 reached
Sierra with t2=7518 and t3=7524.25 — BELOW entry on a LONG — so the bracket
contracts "hit target" instantly and the trade disintegrated. The S2 path has
no A7 validator; the gateway is the last line.

Drives the REAL route_setup (gates off) and inspects the setup the shadow
executor receives. Fails on pre-I-61 code.
"""
import pytest

from backend.v9.gateway.trading_gateway import TradingGateway
from backend.v9.gateway.cooldown import CooldownManager, ClusterGuard


class _NoVeto:
    def check_veto(self, direction):
        return False

    def record_outcome(self, *a):
        pass


def _bare_gateway(monkeypatch, captured):
    # Freeze the B-13 session gate OPEN — green at any wall-clock hour.
    import backend.v9.gateway.trading_gateway as _tg
    monkeypatch.setattr(_tg, "is_within_firing_window", lambda: True)
    gw = TradingGateway.__new__(TradingGateway)
    gw._recent_fires = []
    gw.shadow_trades = []
    gw._slot_candidates = []
    gw._rr_selection_enabled = False
    gw.cooldown = CooldownManager()
    gw.cluster_guard = ClusterGuard()
    gw.ssv = _NoVeto()
    gw.demo_slot = None
    gw.live_slot = None
    gw._demo_enabled_systems = set()
    gw._live_enabled_systems = set()
    gw._trade_manager = None
    gw._system_registry = {}

    def _capture_shadow(setup, sid, ctx):
        captured.update(setup)
        return {"trade_id": 42}

    monkeypatch.setattr(gw, "_execute_shadow", _capture_shadow, raising=False)
    monkeypatch.setattr(gw, "_selfheal_demo_slot", lambda: None, raising=False)
    return gw


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for f in ("FEED_WATCHDOG", "LAYER0_CHOP_GATE", "OPENING_TYPE_GATE",
              "TREND_DIRECTION_GATE", "REACTIVE_LOCATION_GATE", "DAYTYPE_PLAYBOOK",
              "DAYTYPE_POSITION_GATE", "DIRECTION_CONTEXT", "CONT_TREND_FILTER",
              "DAYTYPE_TARGETS_STRUCTURAL", "OPPOSITE_EXIT_V1", "DEDUP_FIRE_GUARD"):
        monkeypatch.delenv(f, raising=False)


def test_long_with_targets_below_entry_gets_them_dropped(monkeypatch):
    """The 279/280 ladder: LONG @7525, t1=7539 (ok), t2=7518, t3=7524.25 (wrong side)."""
    captured = {}
    gw = _bare_gateway(monkeypatch, captured)
    gw.route_setup({
        "firing_system": 2, "direction": "LONG", "classification": "REACTIVE_LONG",
        "confidence": 0.75, "entry_price": 7525.0, "stop": 7517.25,
        "t1": 7539.0, "t2": 7518.0, "t3": 7524.25, "metadata": {},
    }, 2)
    assert captured["t1"] == 7539.0, "correct-side target must stay"
    assert captured["t2"] is None, "t2 below LONG entry must be dropped (I-61)"
    assert captured["t3"] is None, "t3 below LONG entry must be dropped (I-61)"


def test_short_with_target_above_entry_dropped(monkeypatch):
    captured = {}
    gw = _bare_gateway(monkeypatch, captured)
    gw.route_setup({
        "firing_system": 4, "direction": "SHORT", "classification": "ZLR",
        "confidence": 0.65, "entry_price": 7532.0, "stop": 7545.25,
        "t1": 7527.0, "t2": 7547.75, "t3": None, "metadata": {"pattern": "ZLR"},
    }, 4)
    assert captured["t1"] == 7527.0
    assert captured["t2"] is None, "t2 above SHORT entry must be dropped (I-61)"


def test_valid_ladder_untouched(monkeypatch):
    captured = {}
    gw = _bare_gateway(monkeypatch, captured)
    gw.route_setup({
        "firing_system": 2, "direction": "LONG", "classification": "BULL_FLAG_LONG",
        "confidence": 0.8, "entry_price": 7500.0, "stop": 7492.0,
        "t1": 7508.0, "t2": 7516.0, "t3": 7530.0, "metadata": {},
    }, 2)
    assert (captured["t1"], captured["t2"], captured["t3"]) == (7508.0, 7516.0, 7530.0)
