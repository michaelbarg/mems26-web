"""RUNNER_TRAIL_V1 momentum-widen refinement (2026-06-22).

Once the runner is a STRONG leg (favorable ≥ widen_at_R × risk), the trail uses the wider
k_wide so it rides the leg instead of cutting on the first pullback (today's 195/196). Config-
gated: absent widen_at_R/k_wide → k_eff == k (exactly the current behavior, no change).

Anti-tautological: SAME bar, config-with-widen vs config-without → different stop. RED if the
widen logic is removed (the strong-leg test would fall back to the tight stop).
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


def _make_trade():
    t = MagicMock()
    t.entry_price = 7400.0
    t.stop = 7400.25            # current stop = BE+1T (smart-BE already applied)
    t.direction = "LONG"
    t.t1_hit_ts = datetime.now(timezone.utc)
    t.quality = {"initial_stop": 7390.0}   # risk = 10pt
    t.cross_context = []
    t.id = 999
    t.state = "PARTIAL"
    return t


def _mgr():
    from backend.v9.services.trade_manager.manager import TradeManager
    tm = TradeManager.__new__(TradeManager)
    tm._db = MagicMock()
    tm._emitter = MagicMock()
    tm._emitter.emit = MagicMock()
    return tm


@pytest.fixture(autouse=True)
def _enable(monkeypatch):
    monkeypatch.setenv("RUNNER_TRAIL_V1", "1")
    monkeypatch.setenv("STOP_ANCHORS_V2", "1")


def _run(cfg, bar_high):
    tm = _mgr()
    trade = _make_trade()
    with patch("backend.v9.config_loader.load_stop_anchors", return_value=cfg):
        tm.apply_trail_after_t1(trade, bar_high=bar_high, bar_low=bar_high - 4.0)
    return trade.stop


def test_no_widen_config_is_current_behavior():
    # no widen keys → k=1.0 → trail = 7440 − 1×10 = 7430 (unchanged behavior)
    assert _run({"runner_trail": {"k_risk": 1.0}}, 7440.0) == 7430.0


def test_strong_leg_widens_trail():
    # fav = 7440−7400 = 40 = 4.0R ≥ 1.5R → k_wide=2.0 → trail = 7440 − 2×10 = 7420 (MORE room)
    assert _run({"runner_trail": {"k_risk": 1.0, "widen_at_R": 1.5, "k_wide": 2.0}}, 7440.0) == 7420.0


def test_weak_leg_stays_tight():
    # fav = 7412−7400 = 12 = 1.2R < 1.5R → k stays 1.0 → trail = 7412 − 10 = 7402 (tight)
    assert _run({"runner_trail": {"k_risk": 1.0, "widen_at_R": 1.5, "k_wide": 2.0}}, 7412.0) == 7402.0
