"""Item-19 — daily-loss / consecutive-loss STOP-DAY halt (Michael 2026-07-03).

Michael approved a −$450 daily-loss halt as the LIVE-framework runtime gate.
The 06-29 finding: all circuit breakers were inert in demo (passes_strict_checks
only ran for mode="live"). This gate is block-only, works in ALL modes when
RISK_HALT_V1=1, and reuses the gateway's own running counters. Default OFF.

Behavioral, fails-on-old: drives the REAL route_setup with the counters primed.
Old code (no gate) → the fire routes; new code → blocked_by=daily_loss_halt.
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


def _bare_gateway(monkeypatch):
    monkeypatch.setattr(tg, "is_within_firing_window", lambda: True)
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
    monkeypatch.setattr(gw, "_execute_shadow",
                        lambda setup, sid, ctx: {"trade_id": 77}, raising=False)
    monkeypatch.setattr(gw, "_selfheal_demo_slot", lambda: None, raising=False)
    return gw


def _setup():
    return {
        "firing_system": 4, "direction": "SHORT", "classification": "ZLR",
        "confidence": 0.7, "entry_price": 7500.0, "stop": 7505.0,
        "t1": 7492.0, "t2": None, "t3": None, "metadata": {"pattern": "ZLR"},
    }


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for f in ("RISK_HALT_V1", "RISK_DAILY_LOSS_CAP", "RISK_CONSECUTIVE_LOSS_LIMIT",
              "DAYTYPE_PLAYBOOK", "DEDUP_FIRE_GUARD", "RR_ENTRY_GATE_V1",
              "TREND_DIRECTION_GATE", "REACTIVE_LOCATION_GATE", "DAYTYPE_POSITION_GATE"):
        monkeypatch.delenv(f, raising=False)


def test_flag_off_never_halts(monkeypatch):
    gw = _bare_gateway(monkeypatch)
    gw._daily_pnl = -9999.0  # deep in the red
    r = gw.route_setup(_setup(), 4)
    assert r.get("blocked_by") is None, "halt must be OFF by default (today's DEMO is unrestricted)"
    assert r.get("shadow") == 77


def test_daily_loss_halt_blocks_at_cap(monkeypatch):
    monkeypatch.setenv("RISK_HALT_V1", "1")
    monkeypatch.setenv("RISK_DAILY_LOSS_CAP", "450")
    gw = _bare_gateway(monkeypatch)
    gw._daily_pnl = -450.0  # exactly at the cap
    r = gw.route_setup(_setup(), 4)
    assert r.get("blocked_by") == "daily_loss_halt"


def test_daily_loss_halt_allows_above_cap(monkeypatch):
    monkeypatch.setenv("RISK_HALT_V1", "1")
    monkeypatch.setenv("RISK_DAILY_LOSS_CAP", "450")
    gw = _bare_gateway(monkeypatch)
    gw._daily_pnl = -300.0  # still within budget
    r = gw.route_setup(_setup(), 4)
    assert r.get("blocked_by") is None
    assert r.get("shadow") == 77


def test_consecutive_loss_halt_only_when_limit_set(monkeypatch):
    """Consecutive-loss halt must NOT bite unless a limit is explicitly set
    (Michael has not fixed that number yet — default 0 = off)."""
    monkeypatch.setenv("RISK_HALT_V1", "1")
    gw = _bare_gateway(monkeypatch)
    gw._consecutive_losses = 9
    r = gw.route_setup(_setup(), 4)
    assert r.get("blocked_by") is None, "no consecutive limit set → must not halt"


def test_consecutive_loss_halt_blocks_when_limit_set(monkeypatch):
    monkeypatch.setenv("RISK_HALT_V1", "1")
    monkeypatch.setenv("RISK_CONSECUTIVE_LOSS_LIMIT", "2")
    gw = _bare_gateway(monkeypatch)
    gw._consecutive_losses = 2
    r = gw.route_setup(_setup(), 4)
    assert r.get("blocked_by") == "consecutive_loss_halt"
