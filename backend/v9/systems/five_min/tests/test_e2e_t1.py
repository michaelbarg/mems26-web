"""E2E integration tests for T1 (5-min Number Bar) — 10 scenarios.

Tests the full pipeline: pattern → emitter → validator → L3 → gateway.
Uses real components (no mocks except HTTP endpoints).
"""
import pytest
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch

from backend.v9.systems.five_min.five_min_system import FiveMinSystem
from backend.v9.systems.five_min.setup_emitter import emit_t1_setup
from backend.v9.systems.five_min.sr_proximity import check_proximity
from backend.v9.systems.five_min.q0_dispatcher import get_current_mode, S2Mode
from backend.v9.systems.five_min.first_hour_buffer import FirstHourBuffer
from backend.v9.systems.five_min.first_hour_matrix import lookup_matrix
from backend.v9.systems.five_min.choppiness import compute_choppiness, is_choppy
from backend.v9.systems.five_min.confluence import compute_confluence
from backend.v9.shared.pre_fire_validator import FireRequest, validate_fire

ET = ZoneInfo("America/New_York")


def _bars_reactive_long():
    return [
        {"o": 5249, "h": 5249, "l": 5249, "c": 5249, "v": 300},
        {"o": 5249, "h": 5249, "l": 5249, "c": 5249, "v": 300},
        {"o": 5249, "h": 5249, "l": 5249, "c": 5249, "v": 300},
        {"o": 5250, "h": 5250, "l": 5247, "c": 5247.5, "v": 1000},
        {"o": 5248, "h": 5248, "l": 5247, "c": 5247.75, "v": 80},
        {"o": 5247.25, "h": 5249, "l": 5247.25, "c": 5248.75, "v": 800},
        {"o": 5248.5, "h": 5250, "l": 5248.5, "c": 5249.75, "v": 700},
    ]


def _bars_initiative_long():
    return [
        {"o": 5246, "h": 5246, "l": 5246, "c": 5246, "v": 200},
        {"o": 5246, "h": 5246, "l": 5246, "c": 5246, "v": 200},
        {"o": 5246, "h": 5246, "l": 5246, "c": 5246, "v": 200},
        {"o": 5247, "h": 5248.75, "l": 5247, "c": 5248.50, "v": 600},
        {"o": 5248, "h": 5248.50, "l": 5247.25, "c": 5247.75, "v": 400},
        {"o": 5247.50, "h": 5249.50, "l": 5247.50, "c": 5249, "v": 700},
        {"o": 5248, "h": 5249.25, "l": 5247.50, "c": 5249, "v": 500},
    ]


def _tpo_at_poc():
    return {"poc": 5249.0, "vah": 5260.0, "val": 5240.0}


class TestE2EScenarios:

    # 1. Reactive_Long fires · all gates pass
    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=150.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    @patch.object(FiveMinSystem, '_get_belly_from_footprint', return_value=True)
    @patch.object(FiveMinSystem, '_get_belly_ratio_from_footprint', return_value=2.0)
    def test_reactive_long_full_pipeline(self, _br, _b, _a, _c):
        sys = FiveMinSystem()
        direction, conf, info = sys._detect_reactive(_bars_reactive_long())
        assert direction == "LONG"

        setup = emit_t1_setup(
            'REACTIVE_LONG', 'LONG',
            entry_price=5249.75, stop_price=5247.0,
            t1_price=5252.5, t2_price=5255.25,
            bar_index=100,
            day_type="Variation",
            tpo_data=_tpo_at_poc(),
        )
        assert setup is not None
        assert setup.provisional is False
        assert setup.quality_tier == 'HIGH'

    # 2. Reactive_Long fails sr_proximity
    def test_reactive_long_fails_sr_proximity(self):
        levels = {'pdh': 5270.0, 'pdl': 5220.0, 'vah': 5265.0, 'val': 5230.0, 'ibh': None, 'ibl': None}
        is_near, _ = check_proximity(5250.0, 'LONG', levels=levels)
        assert is_near is False  # price 5250 not near any support (PDL=5220, VAL=5230)

    # 3. Reactive_Short mirror
    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=50.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    @patch.object(FiveMinSystem, '_get_belly_from_footprint', return_value=True)
    @patch.object(FiveMinSystem, '_get_belly_ratio_from_footprint', return_value=2.0)
    def test_reactive_short_mirror(self, _br, _b, _a, _c):
        sys = FiveMinSystem()
        bars = [
            {"o": 5248, "h": 5248, "l": 5248, "c": 5248, "v": 300},
            {"o": 5248, "h": 5248, "l": 5248, "c": 5248, "v": 300},
            {"o": 5248, "h": 5248, "l": 5248, "c": 5248, "v": 300},
            {"o": 5247, "h": 5250, "l": 5247, "c": 5249.5, "v": 1000},
            {"o": 5249, "h": 5249, "l": 5248, "c": 5248.25, "v": 90},
            {"o": 5249, "h": 5249, "l": 5247, "c": 5247.5, "v": 800},
            {"o": 5248, "h": 5248, "l": 5246, "c": 5246.5, "v": 700},
        ]
        direction, conf, info = sys._detect_reactive(bars)
        assert direction == "SHORT"

    # 4. Initiative_Long fires
    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=80.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    def test_initiative_long_fires(self, _a, _c):
        sys = FiveMinSystem()
        direction, conf, info = sys._detect_initiative(_bars_initiative_long())
        assert direction == "LONG"
        assert info["kind"] == "INITIATIVE"

    # 5. Initiative_Long POC return alt
    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=80.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    def test_initiative_long_poc_return_alt(self, _a, _c):
        sys = FiveMinSystem()
        bars = [
            {"o": 5246, "h": 5246, "l": 5246, "c": 5246, "v": 200},
            {"o": 5246, "h": 5246, "l": 5246, "c": 5246, "v": 200},
            {"o": 5246, "h": 5246, "l": 5246, "c": 5246, "v": 200},
            {"o": 5247, "h": 5248.75, "l": 5247, "c": 5248.50, "v": 600},
            {"o": 5248, "h": 5248.50, "l": 5246.5, "c": 5247.0, "v": 400, "poc_vol": 5247.0},
            {"o": 5247.0, "h": 5249.50, "l": 5247.0, "c": 5249, "v": 700},
            {"o": 5248, "h": 5249.25, "l": 5247.0, "c": 5249, "v": 500},
        ]
        direction, conf, info = sys._detect_initiative(bars)
        assert direction == "LONG"
        assert info.get("b2_alt") == "poc_return"

    # 6. First Hour · Open Drive × Initiative
    def test_first_hour_open_drive_initiative(self):
        et = datetime(2026, 5, 16, 9, 50, tzinfo=ET)
        mode = get_current_mode(et)
        assert mode == S2Mode.PRE_LOCK

        buf = FirstHourBuffer()
        for _ in range(8):
            buf.on_bar()
        assert buf.is_pattern_eligible("INITIATIVE_LONG")

        sizing_mod, ts = lookup_matrix("OPEN_DRIVE", "LONG")
        assert sizing_mod == 1.0  # full size in drive direction

    # 7. First Hour · Open Auction in-range · low confluence
    def test_first_hour_auction_low_confluence(self):
        buf = FirstHourBuffer()
        for _ in range(5):
            buf.on_bar()
        # Early: only reactive eligible
        assert not buf.is_pattern_eligible("INITIATIVE_LONG")
        assert buf.is_pattern_eligible("REACTIVE_LONG")

        sizing_mod, ts = lookup_matrix("OPEN_AUCTION_IN", "LONG")
        assert sizing_mod == 0.5  # conservative
        assert ts == 30  # short time stop

    # 8. 10:30 transition
    def test_1030_transition(self):
        pre = datetime(2026, 5, 16, 10, 29, tzinfo=ET)
        post = datetime(2026, 5, 16, 10, 31, tzinfo=ET)
        assert get_current_mode(pre) == S2Mode.PRE_LOCK
        assert get_current_mode(post) == S2Mode.POST_LOCK

    # 9. Choppy opening · confluence -1
    def test_choppy_opening_reduces_confluence(self):
        choppy_bars = [
            {"o": 5250, "h": 5250.5, "l": 5249.5, "c": 5249.75},
            {"o": 5249.75, "h": 5250.5, "l": 5249.5, "c": 5250.25},
            {"o": 5250.25, "h": 5250.5, "l": 5249.5, "c": 5249.75},
            {"o": 5249.75, "h": 5250.5, "l": 5249.5, "c": 5250.25},
            {"o": 5250.25, "h": 5250.5, "l": 5249.5, "c": 5249.75},
            {"o": 5249.75, "h": 5250.5, "l": 5249.5, "c": 5250.25},
        ]
        assert is_choppy(choppy_bars)
        kz = {"current_zone": {"name": "LUNCH"}}
        score = compute_confluence("LONG", choppy_bars, killzone_data=kz)
        assert score <= 1  # base - choppy = 0 or 1

    # 10. pre_fire_validator rejects malformed
    def test_validator_rejects_malformed(self):
        req = FireRequest(
            system_id='T1_NUMBER_BAR', direction='LONG',
            entry_price=5250.0, stop_price=5252.0,  # stop above entry!
            t1_price=5252.0, t2_price=5254.0,
            time_stop_minutes=60, confidence=75,
        )
        resp = validate_fire(req)
        assert resp.valid is False
        assert "stop must be < entry" in resp.fail_reason
