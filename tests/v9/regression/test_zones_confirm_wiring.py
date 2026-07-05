"""Wiring tests — item-22 target zones + item-6 entry confirm at the gateway."""
import pytest

from backend.v9.gateway.trading_gateway import TradingGateway
from backend.v9.gateway.cooldown import CooldownManager, ClusterGuard
import backend.v9.gateway.trading_gateway as tg


class _NoVeto:
    def check_veto(self, direction):
        return False

    def record_outcome(self, *a):
        pass


def _bare(monkeypatch, captured, bars_desc=None, tpo=None):
    monkeypatch.setattr(tg, "is_within_firing_window", lambda: True)
    import backend.v9.db.read as _read
    monkeypatch.setattr(_read, "read_all", lambda *a, **k: list(bars_desc or []))
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
    monkeypatch.setattr(gw, "_capture_cross_context",
                        lambda: {"tpo_system": tpo or {}}, raising=False)

    def _cap(setup, sid, ctx):
        captured.update(setup)
        return {"trade_id": 7}

    monkeypatch.setattr(gw, "_execute_shadow", _cap, raising=False)
    monkeypatch.setattr(gw, "_selfheal_demo_slot", lambda: None, raising=False)
    return gw


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    for f in ("FEED_WATCHDOG", "LAYER0_CHOP_GATE", "OPENING_TYPE_GATE", "DAYTYPE_PLAYBOOK",
              "DAYTYPE_POSITION_GATE", "TREND_DIRECTION_GATE", "REACTIVE_LOCATION_GATE",
              "RR_ENTRY_GATE_V1", "RISK_HALT_V1", "DEDUP_FIRE_GUARD", "STOP_RESOLVER_V1",
              "DAYTYPE_TARGETS_STRUCTURAL", "DAY_DIRECTION_DOCTRINE_V1",
              "TARGET_ZONES_V1", "S4_ENTRY_CONFIRM_V1"):
        monkeypatch.delenv(f, raising=False)


def test_entry_confirm_blocks_unconfirmed_short_when_on(monkeypatch):
    """SHORT but the signal bar closed UP (7500→7504) → blocked when flag ON."""
    monkeypatch.setenv("S4_ENTRY_CONFIRM_V1", "1")
    captured = {}
    gw = _bare(monkeypatch, captured, bars_desc=[{"open": 7500, "close": 7504,
                                                  "high": 7505, "low": 7499}])
    r = gw.route_setup({"firing_system": 4, "direction": "SHORT", "classification": "ZLR",
                        "confidence": 0.7, "entry_price": 7500.0, "stop": 7508.0,
                        "t1": 7492.0, "metadata": {}}, 4)
    assert r.get("blocked_by") == "entry_not_confirmed"


def test_entry_confirm_allows_confirmed_short(monkeypatch):
    """SHORT and the signal bar closed DOWN (7504→7500) → allowed."""
    monkeypatch.setenv("S4_ENTRY_CONFIRM_V1", "1")
    captured = {}
    gw = _bare(monkeypatch, captured, bars_desc=[{"open": 7504, "close": 7500,
                                                  "high": 7505, "low": 7499}])
    r = gw.route_setup({"firing_system": 4, "direction": "SHORT", "classification": "ZLR",
                        "confidence": 0.7, "entry_price": 7500.0, "stop": 7508.0,
                        "t1": 7492.0, "metadata": {}}, 4)
    assert r.get("blocked_by") is None


def test_entry_confirm_off_never_blocks(monkeypatch):
    captured = {}
    gw = _bare(monkeypatch, captured, bars_desc=[{"open": 7500, "close": 7504,
                                                  "high": 7505, "low": 7499}])
    r = gw.route_setup({"firing_system": 4, "direction": "SHORT", "classification": "ZLR",
                        "confidence": 0.7, "entry_price": 7500.0, "stop": 7508.0,
                        "t1": 7492.0, "metadata": {}}, 4)
    assert r.get("blocked_by") is None
