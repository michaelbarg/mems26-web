"""E2 — S6 BE too early on trend days + E4 confluence scoring (2026-08-11).

E2: S6_TREND_BE_DELAY_V1 — on Trend days, skip immediate BE after T1.
    The trailing stop handles the runner instead.
E4: S2×S4 confluence boost — +10pts in S7 score when confluence_tag present.
"""
import inspect
import pytest


class TestTrendBEDelay:
    """E2: verify the trend-day BE delay code path."""

    def test_flag_in_code(self):
        from backend.v9.services.trade_manager import manager
        src = inspect.getsource(manager.TradeManager._apply_smart_be_after_t1)
        assert "S6_TREND_BE_DELAY_V1" in src

    def test_trend_check_in_code(self):
        from backend.v9.services.trade_manager import manager
        src = inspect.getsource(manager.TradeManager._apply_smart_be_after_t1)
        assert "Trend" in src
        assert "day_type_at_entry" in src

    def test_delay_returns_early(self):
        """E2 delay must return early on Trend days (skipping BE move)."""
        from backend.v9.services.trade_manager import manager
        src = inspect.getsource(manager.TradeManager._apply_smart_be_after_t1)
        # The delay block must contain a return statement
        delay_idx = src.index("S6_TREND_BE_DELAY")
        delay_block = src[delay_idx:delay_idx + 500]
        assert "return" in delay_block


class TestConfluenceScoreBoost:
    """E4: S2×S4 confluence boost in S7 score."""

    def test_confluence_component_exists(self):
        from backend.v9.systems import system7_score
        src = inspect.getsource(system7_score.score)
        assert "s2_s4_confluence" in src
        assert "confluence_tag" in src
        assert "quality_boost" in src

    def test_confluence_adds_10_pts(self):
        from backend.v9.systems.system7_score import score
        setup_no_conf = {"direction": "LONG", "pattern": "REACTIVE_LONG"}
        setup_with_conf = {
            "direction": "LONG", "pattern": "REACTIVE_LONG",
            "confluence_tag": {"quality_boost": True, "counterpart_system": 4},
        }
        r1 = score(setup=setup_no_conf, market_context=None, bar_ts=None)
        r2 = score(setup=setup_with_conf, market_context=None, bar_ts=None)
        assert r2["components"]["s2_s4_confluence"] == 10
        assert r1["components"]["s2_s4_confluence"] == 0
        assert r2["score"] == r1["score"] + 10

    def test_no_tag_no_boost(self):
        from backend.v9.systems.system7_score import score
        r = score(setup={"direction": "LONG"}, market_context=None, bar_ts=None)
        assert r["components"]["s2_s4_confluence"] == 0
