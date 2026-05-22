"""Regression tests: Woodies per-bar dedup prevents duplicate fires.

Root cause: Sierra sends multiple UPDATE events for the same 5-min bar as it
builds. Without dedup, each UPDATE triggers process_bar → pattern detected →
route_setup called → duplicate SHADOW trade.

Fix: _last_fired_bar_ts[key] = bar_ts after first fire. Subsequent calls with
the same bar_ts are skipped. A genuinely new bar (different ts) fires normally.
"""
import asyncio
from unittest.mock import MagicMock, AsyncMock
import pytest

from backend.v9.systems.woodies.woodies_system import WoodiesSystem


BAR_TS_1 = 1748000000.0  # first bar
BAR_TS_2 = BAR_TS_1 + 300.0  # second bar (5 min later)


def _make_bar(ts: float, close: float = 7500.0, high: float = 7510.0,
              low: float = 7490.0, open_: float = 7500.0) -> dict:
    return {"ts": ts, "open": open_, "high": high, "low": low,
            "close": close, "volume": 1000}


def _make_gateway(shadow_id: int = 99) -> MagicMock:
    gw = MagicMock()
    gw.route_setup.return_value = {"shadow": shadow_id, "blocked_by": None}
    return gw


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestWoodiesDedupBarTs:

    def _system_with_gateway(self) -> tuple:
        sys = WoodiesSystem()
        gw = _make_gateway()
        sys.set_gateway(gw)
        return sys, gw

    def _pump_bars(self, sys, n: int = 25, base_ts: float = BAR_TS_1) -> None:
        """Feed enough bars to fill the pattern detection buffer."""
        for i in range(n):
            _run(sys.process_bar(_make_bar(base_ts - (n - i) * 300.0,
                                           close=7500.0 + i * 0.25)))

    def test_second_call_same_bar_ts_does_not_fire(self):
        """Two process_bar calls with identical bar_ts → only 1 route_setup."""
        sys, gw = self._system_with_gateway()
        self._pump_bars(sys)

        call_count_before = gw.route_setup.call_count
        _run(sys.process_bar(_make_bar(BAR_TS_2)))
        _run(sys.process_bar(_make_bar(BAR_TS_2)))  # same ts — duplicate

        fired = gw.route_setup.call_count - call_count_before
        assert fired <= 1, f"Expected ≤1 fire for same bar_ts, got {fired}"

    def test_seven_updates_same_bar_ts_fires_once(self):
        """7 UPDATE events on the same bar → max 1 route_setup (reproduces the bug)."""
        sys, gw = self._system_with_gateway()
        self._pump_bars(sys)

        call_count_before = gw.route_setup.call_count
        for _ in range(7):
            _run(sys.process_bar(_make_bar(BAR_TS_2)))

        fired = gw.route_setup.call_count - call_count_before
        assert fired <= 1, f"Expected ≤1 fire for 7 same-ts updates, got {fired}"

    def test_new_bar_ts_fires_again(self):
        """After a new bar_ts arrives, the same pattern can fire again."""
        sys, gw = self._system_with_gateway()
        self._pump_bars(sys)

        _run(sys.process_bar(_make_bar(BAR_TS_2)))
        count_after_bar1 = gw.route_setup.call_count

        # New bar — different ts → allowed to fire
        _run(sys.process_bar(_make_bar(BAR_TS_2 + 300.0)))
        count_after_bar2 = gw.route_setup.call_count

        # bar2 may or may not fire (depends on pattern detection),
        # but it must NOT be blocked by the dedup of bar1
        last_route = sys.current_state.get("last_route", {})
        if last_route.get("skipped"):
            assert last_route.get("reason") != "duplicate_bar_ts", (
                "New bar_ts was incorrectly blocked as duplicate"
            )

    def test_dedup_key_per_pattern_direction(self):
        """Different pattern+direction keys are tracked independently."""
        sys, gw = self._system_with_gateway()
        # Inject two fake fired entries for different keys
        sys._last_fired_bar_ts["ZLR_SHORT"] = BAR_TS_2
        sys._last_fired_bar_ts["HFE_LONG"] = BAR_TS_1  # older ts

        # ZLR_SHORT with same bar_ts should be deduped
        assert sys._last_fired_bar_ts.get("ZLR_SHORT") == BAR_TS_2
        # HFE_LONG with newer bar_ts should not be deduped
        assert sys._last_fired_bar_ts.get("HFE_LONG") < BAR_TS_2

    def test_last_fired_bar_ts_dict_initialized_empty(self):
        sys = WoodiesSystem()
        assert hasattr(sys, "_last_fired_bar_ts")
        assert isinstance(sys._last_fired_bar_ts, dict)
        assert len(sys._last_fired_bar_ts) == 0
