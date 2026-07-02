"""I-60 regression — a BLOCKED fire must not poison the dedup window.

Live incident (2026-07-02 18:50): ZLR SHORT #1 blocked by cont_trend_filter;
retry #2 (higher confidence, 7s later) rejected as duplicate_fire — of a fire
that never traded. Root: dedup registered on ATTEMPT, before the gates.

Behavioral, fails-on-old: drives the REAL route_setup twice — first blocked by
the (monkeypatched) playbook gate which sits AFTER the dedup section, then
unblocked. Old code: second call → duplicate_fire. New code: second call routes.
"""
import types

import pytest

from backend.v9.gateway.trading_gateway import TradingGateway
from backend.v9.gateway.cooldown import CooldownManager, ClusterGuard


class _NoVeto:
    def check_veto(self, direction):
        return False

    def record_outcome(self, *a):
        pass


def _bare_gateway(monkeypatch):
    # Freeze the B-13 session gate OPEN — these tests must be green at any
    # wall-clock hour (they went red at 23:4x IL when RTH closed).
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
    monkeypatch.setattr(gw, "_execute_shadow",
                        lambda setup, sid, ctx: {"trade_id": 99},
                        raising=False)
    monkeypatch.setattr(gw, "_selfheal_demo_slot", lambda: None, raising=False)
    return gw


def _setup_dict():
    return {
        "firing_system": 4, "direction": "SHORT", "classification": "ZLR",
        "confidence": 0.65, "entry_price": 7527.25, "stop": 7530.0,
        "t1": 7524.0, "t2": None, "t3": None, "metadata": {"pattern": "ZLR"},
    }


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for f in ("FEED_WATCHDOG", "LAYER0_CHOP_GATE", "OPENING_TYPE_GATE",
              "TREND_DIRECTION_GATE", "REACTIVE_LOCATION_GATE",
              "DAYTYPE_POSITION_GATE", "DIRECTION_CONTEXT", "CONT_TREND_FILTER",
              "DAYTYPE_TARGETS_STRUCTURAL", "OPPOSITE_EXIT_V1", "COOLDOWN_2STOP_V1"):
        monkeypatch.delenv(f, raising=False)
    monkeypatch.setenv("DEDUP_FIRE_GUARD", "1")


def test_blocked_fire_does_not_poison_dedup(monkeypatch):
    gw = _bare_gateway(monkeypatch)

    # Attempt #1: playbook gate (downstream of the dedup section) blocks it.
    monkeypatch.setenv("DAYTYPE_PLAYBOOK", "1")
    import backend.v9.systems.daytype_playbook as pb

    class _Skip:
        verdict, contracts, reason = "SKIP", 0, "test-skip"
        allow = False

    monkeypatch.setattr(pb, "decide", lambda **kw: _Skip())
    r1 = gw.route_setup(_setup_dict(), 4)
    assert r1.get("blocked_by") == "daytype_playbook"

    # Attempt #2 (same signal, 'seconds' later): gate now open → MUST route,
    # not die as duplicate_fire (fails on pre-I-60 code).
    monkeypatch.delenv("DAYTYPE_PLAYBOOK", raising=False)
    r2 = gw.route_setup(_setup_dict(), 4)
    assert r2.get("blocked_by") is None, f"blocked_by={r2.get('blocked_by')} — blocked fire poisoned dedup (I-60)"
    assert r2.get("shadow") == 99


def test_true_duplicate_still_blocked(monkeypatch):
    gw = _bare_gateway(monkeypatch)
    r1 = gw.route_setup(_setup_dict(), 4)
    assert r1.get("shadow") == 99
    r2 = gw.route_setup(_setup_dict(), 4)
    assert r2.get("blocked_by") == "duplicate_fire", "a REAL duplicate (after a routed fire) must still be blocked"
