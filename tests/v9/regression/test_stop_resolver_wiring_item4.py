"""Item-4 wiring — STOP_RESOLVER_V1 replaces a financed stop at the gateway.

Drives the REAL route_setup with a financed (too-tight) stop and a monkeypatched
bar feed that carries a structural rung. With the flag ON the gateway must
re-derive the stop into the ATR band; with it OFF the stop is untouched.
Fails on pre-wiring code (the resolver block didn't exist).
"""
import pytest

from backend.v9.gateway.trading_gateway import TradingGateway
from backend.v9.gateway.cooldown import CooldownManager, ClusterGuard
import backend.v9.gateway.trading_gateway as tg


class _NoVeto:
    def check_veto(self, direction):
        return False

    def record_outcome(self, *a):
        pass


# newest→oldest (route_setup reverses); highs above the 7500 short entry = rungs
_BARS_DESC = [{"high": 7506, "low": 7499, "close": 7501},
              {"high": 7508, "low": 7500, "close": 7502},
              {"high": 7507, "low": 7500, "close": 7501},
              {"high": 7505, "low": 7499, "close": 7500}]


def _bare_gateway(monkeypatch, captured):
    monkeypatch.setattr(tg, "is_within_firing_window", lambda: True)
    import backend.v9.db.read as _read
    monkeypatch.setattr(_read, "read_all", lambda *a, **k: list(_BARS_DESC))
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
    gw._daily_trades = 0
    gw._daily_pnl = 0.0
    gw._consecutive_losses = 0

    def _cap(setup, sid, ctx):
        captured.update(setup)
        return {"trade_id": 5}

    monkeypatch.setattr(gw, "_execute_shadow", _cap, raising=False)
    monkeypatch.setattr(gw, "_selfheal_demo_slot", lambda: None, raising=False)
    return gw


def _financed_short():
    return {"firing_system": 4, "direction": "SHORT", "classification": "ZLR",
            "confidence": 0.65, "entry_price": 7500.0, "stop": 7500.5,  # 0.5pt financed
            "t1": 7496.0, "t2": None, "t3": None, "metadata": {"pattern": "ZLR"}}


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    for f in ("FEED_WATCHDOG", "LAYER0_CHOP_GATE", "OPENING_TYPE_GATE", "DAYTYPE_PLAYBOOK",
              "DAYTYPE_POSITION_GATE", "TREND_DIRECTION_GATE", "REACTIVE_LOCATION_GATE",
              "RR_ENTRY_GATE_V1", "RISK_HALT_V1", "DEDUP_FIRE_GUARD",
              "DAYTYPE_TARGETS_STRUCTURAL", "DAY_DIRECTION_DOCTRINE_V1"):
        monkeypatch.delenv(f, raising=False)


def test_resolver_replaces_financed_stop_when_on(monkeypatch):
    monkeypatch.setenv("STOP_RESOLVER_V1", "1")
    captured = {}
    gw = _bare_gateway(monkeypatch, captured)
    gw.route_setup(_financed_short(), 4)
    assert captured["stop"] > 7503.0, f"financed 0.5pt stop not widened (got {captured['stop']})"
    assert captured["stop"] > 7500.0, "SHORT stop must stay above entry"


def test_resolver_untouched_when_off(monkeypatch):
    monkeypatch.delenv("STOP_RESOLVER_V1", raising=False)
    captured = {}
    gw = _bare_gateway(monkeypatch, captured)
    gw.route_setup(_financed_short(), 4)
    assert captured["stop"] == 7500.5, "flag OFF must leave the stop untouched"
