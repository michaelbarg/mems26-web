"""D-094 R:R Fire Selection tests — flag OFF=first-wins, flag ON=best-R:R."""

import asyncio
import pytest
from unittest.mock import patch, MagicMock

from backend.v9.gateway.rr_score import compute_rr_score


# ══════════ D2: compute_rr_score unit tests ══════════


class TestComputeRRScore:
    def test_long_ofa_reactive(self):
        """OFA Reactive LONG: split 25/50/25, entry=5250, stop=5248, t1=5254, t2=5258, t3=5262."""
        setup = {
            "entry_price": 5250.0, "stop": 5248.0,
            "t1": 5254.0, "t2": 5258.0, "t3": 5262.0,
            "classification": "REACTIVE_LONG",
        }
        rr = compute_rr_score(setup)
        # risk = |5250-5248| = 2
        # reward = |5254-5250|*0.25 + |5258-5250|*0.50 + |5262-5250|*0.25
        #        = 4*0.25 + 8*0.50 + 12*0.25 = 1 + 4 + 3 = 8
        # R:R = 8/2 = 4.0
        assert rr == 4.0

    def test_short_flag(self):
        """Flag SHORT: split 50/50/0, entry=5250, stop=5252, t1=5246, t2=5242."""
        setup = {
            "entry_price": 5250.0, "stop": 5252.0,
            "t1": 5246.0, "t2": 5242.0, "t3": 0.0,
            "classification": "BEAR_FLAG_SHORT",
        }
        rr = compute_rr_score(setup)
        # risk = |5250-5252| = 2
        # reward = |5246-5250|*0.50 + |5242-5250|*0.50 + 0 = 2 + 4 = 6
        # R:R = 6/2 = 3.0
        assert rr == 3.0

    def test_entry_equals_stop_returns_none(self):
        setup = {"entry_price": 5250.0, "stop": 5250.0, "t1": 5255.0, "t2": 5260.0, "t3": 0.0}
        assert compute_rr_score(setup) is None

    def test_unknown_pattern_equal_split(self):
        """Unknown classification → equal split across non-zero targets."""
        setup = {
            "entry_price": 5250.0, "stop": 5248.0,
            "t1": 5254.0, "t2": 5258.0, "t3": 0.0,
            "classification": "UNKNOWN_PATTERN",
        }
        rr = compute_rr_score(setup)
        # equal split over 2 targets: 0.5 each
        # reward = 4*0.5 + 8*0.5 = 6, risk = 2 → R:R = 3.0
        assert rr == 3.0

    def test_missing_prices_returns_none(self):
        setup = {"entry_price": 0.0, "stop": 0.0, "t1": 0.0, "t2": 0.0, "t3": 0.0}
        assert compute_rr_score(setup) is None


# ══════════ D3+D5: Gateway buffering tests ══════════


@pytest.fixture
def gateway_off():
    """Gateway with RR_FIRE_SELECTION=OFF (first-wins)."""
    with patch.dict("os.environ", {"RR_FIRE_SELECTION": ""}):
        from backend.v9.gateway.trading_gateway import TradingGateway
        gw = TradingGateway()
        gw.enable_demo(2)
        gw.enable_demo(4)
        return gw


@pytest.fixture
def gateway_on():
    """Gateway with RR_FIRE_SELECTION=ON (buffering)."""
    with patch.dict("os.environ", {"RR_FIRE_SELECTION": "true"}):
        from backend.v9.gateway.trading_gateway import TradingGateway
        gw = TradingGateway()
        gw.enable_demo(2)
        gw.enable_demo(4)
        return gw


def _setup(entry, stop, t1, t2, t3=0.0, system_id=2, classification="REACTIVE_LONG"):
    return {
        "entry_price": entry, "stop": stop,
        "t1": t1, "t2": t2, "t3": t3,
        "direction": "LONG", "confidence": 0.75,
        "classification": classification,
        "firing_system": system_id,
        "metadata": {"pattern": classification, "sizing": 3},
    }


class TestFlagOff:
    """Flag OFF: first-wins behavior unchanged."""

    def test_demo_first_wins(self, gateway_off):
        gw = gateway_off
        r1 = gw.route_setup(_setup(5250, 5248, 5254, 5258), 2)
        r2 = gw.route_setup(_setup(5250, 5248, 5260, 5270), 4)
        # First call fills demo slot
        assert r1.get("demo") is not None
        # Second call: slot occupied
        assert r2.get("demo") is None

    def test_shadow_always_records(self, gateway_off):
        gw = gateway_off
        r1 = gw.route_setup(_setup(5250, 5248, 5254, 5258), 2)
        r2 = gw.route_setup(_setup(5250, 5248, 5260, 5270), 4)
        assert r1.get("shadow") is not None
        assert r2.get("shadow") is not None


class TestFlagOn:
    """Flag ON: same-bar buffering with R:R selection."""

    def test_candidates_buffered_not_filled_immediately(self, gateway_on):
        gw = gateway_on
        r = gw.route_setup(_setup(5250, 5248, 5254, 5258), 2)
        # SHADOW still recorded immediately
        assert r.get("shadow") is not None
        # DEMO NOT filled yet (buffered)
        assert r.get("demo") is None
        assert gw.demo_slot is None
        assert len(gw._slot_candidates) == 1

    def test_bar_close_selects_highest_rr(self, gateway_on):
        gw = gateway_on
        # Setup 1: R:R = 4.0 (from test_long_ofa_reactive)
        gw.route_setup(_setup(5250, 5248, 5254, 5258, 5262, system_id=2, classification="REACTIVE_LONG"), 2)
        # Setup 2: R:R = 3.0 (closer targets)
        gw.route_setup(_setup(5250, 5248, 5252, 5254, 5256, system_id=4, classification="REACTIVE_LONG"), 4)

        assert len(gw._slot_candidates) == 2
        # Flush
        asyncio.run(gw.on_bar_close())
        # Winner = system 2 (R:R=4.0 > 3.0)
        assert gw.demo_slot is not None
        assert gw._slot_candidates == []

    def test_shadow_unaffected_by_buffering(self, gateway_on):
        gw = gateway_on
        r1 = gw.route_setup(_setup(5250, 5248, 5254, 5258), 2)
        r2 = gw.route_setup(_setup(5250, 5248, 5260, 5270), 4)
        # Both SHADOW recorded immediately
        assert r1.get("shadow") is not None
        assert r2.get("shadow") is not None
        assert len(gw.shadow_trades) == 2

    def test_losers_logged_as_outranked(self, gateway_on, caplog):
        import logging
        gw = gateway_on
        with caplog.at_level(logging.INFO):
            gw.route_setup(_setup(5250, 5248, 5254, 5258, 5262, system_id=2), 2)
            gw.route_setup(_setup(5250, 5248, 5252, 5254, 5256, system_id=4), 4)
            asyncio.run(gw.on_bar_close())
        assert any("OUTRANKED" in r.getMessage() for r in caplog.records)

    def test_tie_break_confidence_then_system(self, gateway_on):
        """Same R:R → higher confidence wins. Same conf → lower system_id wins."""
        gw = gateway_on
        s1 = _setup(5250, 5248, 5254, 5258, 5262, system_id=4, classification="REACTIVE_LONG")
        s1["confidence"] = 0.8
        s2 = _setup(5250, 5248, 5254, 5258, 5262, system_id=2, classification="REACTIVE_LONG")
        s2["confidence"] = 0.9
        gw.route_setup(s1, 4)
        gw.route_setup(s2, 2)
        asyncio.run(gw.on_bar_close())
        # s2 wins (higher confidence, same R:R)
        assert gw.demo_slot is not None

    def test_no_flush_when_flag_off(self, gateway_off):
        gw = gateway_off
        gw._slot_candidates = [{"setup": {}, "system_id": 2, "cross_context": {}}]
        asyncio.run(gw.on_bar_close())
        # Should be no-op (flag off)
        assert len(gw._slot_candidates) == 1
